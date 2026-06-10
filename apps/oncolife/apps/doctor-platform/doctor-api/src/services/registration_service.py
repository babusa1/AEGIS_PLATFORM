"""
Registration Service - Doctor API
=================================

Admin-controlled physician and staff registration.

Key Security Rules:
- Physicians are NOT self-signup users
- Only admins can create physician accounts
- Physicians can create staff under them
- All registrations are audited

Flow:
1. Admin creates physician → Invite email sent
2. Physician sets password + MFA
3. Physician can now add staff
4. Staff sets password → Scoped to physician
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
import secrets
import string

from sqlalchemy.orm import Session
from sqlalchemy import text

from .base import BaseService
from core.logging import get_logger
from core.exceptions import (
    ValidationError, 
    AuthorizationError, 
    ConflictError,
    NotFoundError,
)

logger = get_logger(__name__)


class RegistrationService(BaseService):
    """
    Service for admin-controlled registration.
    
    Implements the required registration flow:
    - Admin-initiated physician creation
    - Physician-controlled staff creation
    - Invite email generation
    - Audit logging
    """
    
    def __init__(self, db: Session, cognito_client=None, ses_client=None):
        """
        Initialize registration service.
        
        Args:
            db: Database session
            cognito_client: Optional boto3 cognito client
            ses_client: Optional boto3 SES client
        """
        super().__init__(db)
        self._cognito = cognito_client
        self._ses = ses_client
    
    @property
    def cognito(self):
        """Lazy load Cognito client."""
        if self._cognito is None:
            import boto3
            self._cognito = boto3.client('cognito-idp')
        return self._cognito
    
    @property
    def ses(self):
        """Lazy load SES client."""
        if self._ses is None:
            import boto3
            self._ses = boto3.client('ses')
        return self._ses
    
    # =========================================================================
    # Physician Registration (Admin-Initiated)
    # =========================================================================
    
    def register_physician_by_admin(
        self,
        admin_uuid: UUID,
        email: str,
        first_name: str,
        last_name: str,
        npi_number: str,
        clinic_uuid: UUID,
    ) -> Dict[str, Any]:
        """
        Admin-initiated physician registration.
        
        Flow:
        1. Verify admin has permission
        2. Create physician in database
        3. Create user in Cognito (FORCE_CHANGE_PASSWORD)
        4. Send invite email
        5. Log the action
        
        Args:
            admin_uuid: UUID of the admin performing the action
            email: Physician's email
            first_name: Physician's first name
            last_name: Physician's last name
            npi_number: National Provider Identifier
            clinic_uuid: Clinic to associate physician with
            
        Returns:
            Registration result with invite status
            
        Raises:
            AuthorizationError: If admin doesn't have permission
            ConflictError: If email already exists
            ValidationError: If data is invalid
        """
        logger.info(f"Admin {admin_uuid} registering physician: {email}")
        
        # 1. Verify admin permission
        if not self._is_admin(admin_uuid):
            raise AuthorizationError(
                "Only administrators can create physician accounts"
            )
        
        # 2. Validate inputs
        self._validate_physician_data(email, first_name, last_name, npi_number)
        
        # 3. Check for existing email
        if self._email_exists(email):
            raise ConflictError(
                f"Email {email} is already registered"
            )
        
        # 4. Create physician in database
        physician_uuid = self._create_physician_record(
            email=email,
            first_name=first_name,
            last_name=last_name,
            npi_number=npi_number,
            clinic_uuid=clinic_uuid,
        )
        
        # 5. Create Cognito user with temp password
        temp_password = self._generate_temp_password()
        
        try:
            self._create_cognito_user(
                email=email,
                temp_password=temp_password,
                role="physician",
                user_uuid=physician_uuid,
            )
        except Exception as e:
            # Rollback DB if Cognito fails
            logger.error(f"Cognito creation failed: {e}")
            self._delete_physician_record(physician_uuid)
            raise
        
        # 6. Send invite email
        invite_sent = self._send_physician_invite(
            email=email,
            first_name=first_name,
            temp_password=temp_password,
        )
        
        # 7. Audit log
        self._log_registration(
            admin_uuid=admin_uuid,
            registered_uuid=physician_uuid,
            registered_role="physician",
            registered_email=email,
        )
        
        logger.info(f"Physician {email} registered by admin {admin_uuid}")
        
        return {
            "success": True,
            "physician_uuid": str(physician_uuid),
            "email": email,
            "invite_sent": invite_sent,
            "status": "FORCE_CHANGE_PASSWORD",
            "message": f"Physician account created. Invite sent to {email}",
        }
    
    # =========================================================================
    # Staff Registration (Physician-Controlled)
    # =========================================================================
    
    def register_staff_by_physician(
        self,
        physician_uuid: UUID,
        email: str,
        first_name: str,
        last_name: str,
        role: str,  # nurse, ma, navigator
    ) -> Dict[str, Any]:
        """
        Physician-controlled staff registration.
        
        Flow:
        1. Verify physician exists and is active
        2. Create staff in database (linked to physician)
        3. Create user in Cognito
        4. Send invite email
        5. Log the action
        
        Args:
            physician_uuid: UUID of the registering physician
            email: Staff member's email
            first_name: Staff member's first name
            last_name: Staff member's last name
            role: Staff role (nurse, ma, navigator)
            
        Returns:
            Registration result
            
        Raises:
            AuthorizationError: If physician not authorized
            ConflictError: If email exists
            ValidationError: If invalid data
        """
        logger.info(f"Physician {physician_uuid} registering staff: {email}")
        
        # 1. Verify physician
        physician = self._get_physician(physician_uuid)
        if not physician:
            raise AuthorizationError("Invalid physician")
        
        # 2. Validate role
        valid_roles = {'nurse', 'ma', 'navigator'}
        if role not in valid_roles:
            raise ValidationError(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                field="role"
            )
        
        # 3. Check existing email
        if self._email_exists(email):
            raise ConflictError(f"Email {email} is already registered")
        
        # 4. Get physician's clinic
        clinic_uuid = self._get_physician_clinic(physician_uuid)
        
        # 5. Create staff record
        staff_uuid = self._create_staff_record(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            physician_uuid=physician_uuid,
            clinic_uuid=clinic_uuid,
        )
        
        # 6. Create Cognito user
        temp_password = self._generate_temp_password()
        
        try:
            self._create_cognito_user(
                email=email,
                temp_password=temp_password,
                role="staff",
                user_uuid=staff_uuid,
                physician_uuid=physician_uuid,
                staff_role=role,
            )
        except Exception as e:
            logger.error(f"Cognito creation failed: {e}")
            self._delete_staff_record(staff_uuid)
            raise
        
        # 7. Send invite email
        invite_sent = self._send_staff_invite(
            email=email,
            first_name=first_name,
            temp_password=temp_password,
            physician_name=f"{physician['first_name']} {physician['last_name']}",
        )
        
        # 8. Audit log
        self._log_registration(
            admin_uuid=physician_uuid,
            registered_uuid=staff_uuid,
            registered_role=role,
            registered_email=email,
        )
        
        return {
            "success": True,
            "staff_uuid": str(staff_uuid),
            "email": email,
            "role": role,
            "physician_uuid": str(physician_uuid),
            "invite_sent": invite_sent,
            "status": "FORCE_CHANGE_PASSWORD",
        }
    
    # =========================================================================
    # Staff Permissions Check
    # =========================================================================
    
    def get_staff_permissions(self, staff_uuid: UUID) -> Dict[str, Any]:
        """
        Get permissions for a staff member.
        
        Nurse Navigator / MA can:
        - View dashboard
        - View patients (of their physician)
        - Flag concerns
        - Review shared questions
        
        Cannot:
        - Reassign patients
        - See other physicians' patients
        - Modify patient records
        - Create other staff
        
        Args:
            staff_uuid: UUID of the staff member
            
        Returns:
            Permissions dictionary
        """
        result = self.db.execute(
            text("""
                SELECT role, physician_uuid FROM staff
                WHERE id = :staff_uuid
            """),
            {"staff_uuid": str(staff_uuid)}
        ).fetchone()
        
        if not result:
            return {"error": "Staff not found"}
        
        role = result[0]
        physician_uuid = result[1]
        
        # Physician permissions
        if role == "physician":
            return {
                "role": "physician",
                "physician_uuid": str(physician_uuid) if physician_uuid else str(staff_uuid),
                "can_view_dashboard": True,
                "can_view_patients": True,
                "can_flag_concerns": True,
                "can_review_questions": True,
                "can_reassign_patients": True,
                "can_modify_records": True,
                "can_create_staff": True,
                "can_generate_reports": True,
                "patient_scope": "own",  # Only own patients
            }
        
        # Staff permissions (nurse, ma, navigator)
        return {
            "role": role,
            "physician_uuid": str(physician_uuid),
            "can_view_dashboard": True,
            "can_view_patients": True,
            "can_flag_concerns": True,
            "can_review_questions": True,
            "can_reassign_patients": False,
            "can_modify_records": False,
            "can_create_staff": False,
            "can_generate_reports": False,
            "patient_scope": "physician",  # Inherit from physician
        }
    
    def check_permission(
        self,
        staff_uuid: UUID,
        action: str,
    ) -> bool:
        """
        Check if staff member has permission for an action.
        
        Args:
            staff_uuid: UUID of the staff member
            action: Action to check (e.g., "modify_records")
            
        Returns:
            True if permitted, False otherwise
        """
        permissions = self.get_staff_permissions(staff_uuid)
        return permissions.get(f"can_{action}", False)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _is_admin(self, user_uuid: UUID) -> bool:
        """Check if user is an admin."""
        result = self.db.execute(
            text("""
                SELECT role FROM staff_profiles
                WHERE staff_uuid = :uuid
            """),
            {"uuid": str(user_uuid)}
        ).fetchone()
        
        return result and result[0] == 'admin'
    
    def _email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        result = self.db.execute(
            text("""
                SELECT COUNT(*) FROM staff_profiles
                WHERE email_address = :email
            """),
            {"email": email.lower()}
        ).fetchone()
        
        return result[0] > 0
    
    def _get_physician(self, physician_uuid: UUID) -> Optional[Dict[str, Any]]:
        """Get physician details."""
        result = self.db.execute(
            text("""
                SELECT staff_uuid, first_name, last_name, email_address
                FROM staff_profiles
                WHERE staff_uuid = :uuid AND role = 'physician'
            """),
            {"uuid": str(physician_uuid)}
        ).fetchone()
        
        if not result:
            return None
        
        return {
            "uuid": str(result[0]),
            "first_name": result[1],
            "last_name": result[2],
            "email": result[3],
        }
    
    def _get_physician_clinic(self, physician_uuid: UUID) -> Optional[UUID]:
        """Get clinic for a physician."""
        result = self.db.execute(
            text("""
                SELECT clinic_uuid FROM staff_associations
                WHERE physician_uuid = :uuid
                LIMIT 1
            """),
            {"uuid": str(physician_uuid)}
        ).fetchone()
        
        return UUID(result[0]) if result else None
    
    def _create_physician_record(
        self,
        email: str,
        first_name: str,
        last_name: str,
        npi_number: str,
        clinic_uuid: UUID,
    ) -> UUID:
        """Create physician record in database."""
        result = self.db.execute(
            text("""
                INSERT INTO staff_profiles (email_address, first_name, last_name, role, npi_number)
                VALUES (:email, :first_name, :last_name, 'physician', :npi)
                RETURNING staff_uuid
            """),
            {
                "email": email.lower(),
                "first_name": first_name,
                "last_name": last_name,
                "npi": npi_number,
            }
        )
        
        physician_uuid = result.fetchone()[0]
        
        # Create clinic association
        self.db.execute(
            text("""
                INSERT INTO staff_associations (staff_uuid, physician_uuid, clinic_uuid)
                VALUES (:staff_uuid, :physician_uuid, :clinic_uuid)
            """),
            {
                "staff_uuid": str(physician_uuid),
                "physician_uuid": str(physician_uuid),  # Self-association
                "clinic_uuid": str(clinic_uuid),
            }
        )
        
        self.db.commit()
        return UUID(str(physician_uuid))
    
    def _create_staff_record(
        self,
        email: str,
        first_name: str,
        last_name: str,
        role: str,
        physician_uuid: UUID,
        clinic_uuid: UUID,
    ) -> UUID:
        """Create staff record in database."""
        result = self.db.execute(
            text("""
                INSERT INTO staff_profiles (email_address, first_name, last_name, role)
                VALUES (:email, :first_name, :last_name, :role)
                RETURNING staff_uuid
            """),
            {
                "email": email.lower(),
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
            }
        )
        
        staff_uuid = result.fetchone()[0]
        
        # Create association with physician
        self.db.execute(
            text("""
                INSERT INTO staff_associations (staff_uuid, physician_uuid, clinic_uuid)
                VALUES (:staff_uuid, :physician_uuid, :clinic_uuid)
            """),
            {
                "staff_uuid": str(staff_uuid),
                "physician_uuid": str(physician_uuid),
                "clinic_uuid": str(clinic_uuid),
            }
        )
        
        self.db.commit()
        return UUID(str(staff_uuid))
    
    def _delete_physician_record(self, physician_uuid: UUID) -> None:
        """Delete physician record (rollback)."""
        self.db.execute(
            text("DELETE FROM staff_associations WHERE staff_uuid = :uuid"),
            {"uuid": str(physician_uuid)}
        )
        self.db.execute(
            text("DELETE FROM staff_profiles WHERE staff_uuid = :uuid"),
            {"uuid": str(physician_uuid)}
        )
        self.db.commit()
    
    def _delete_staff_record(self, staff_uuid: UUID) -> None:
        """Delete staff record (rollback)."""
        self.db.execute(
            text("DELETE FROM staff_associations WHERE staff_uuid = :uuid"),
            {"uuid": str(staff_uuid)}
        )
        self.db.execute(
            text("DELETE FROM staff_profiles WHERE staff_uuid = :uuid"),
            {"uuid": str(staff_uuid)}
        )
        self.db.commit()
    
    def _generate_temp_password(self, length: int = 12) -> str:
        """Generate a secure temporary password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure at least one of each type
        password = (
            secrets.choice(string.ascii_uppercase) +
            secrets.choice(string.ascii_lowercase) +
            secrets.choice(string.digits) +
            secrets.choice("!@#$%^&*") +
            password[4:]
        )
        return password
    
    def _create_cognito_user(
        self,
        email: str,
        temp_password: str,
        role: str,
        user_uuid: UUID,
        physician_uuid: Optional[UUID] = None,
        staff_role: Optional[str] = None,
    ) -> None:
        """Create user in AWS Cognito."""
        from core.config import settings
        
        user_attributes = [
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "custom:role", "Value": role},
            {"Name": "custom:user_uuid", "Value": str(user_uuid)},
        ]
        
        if physician_uuid:
            user_attributes.append({
                "Name": "custom:physician_id",
                "Value": str(physician_uuid)
            })
        
        if staff_role:
            user_attributes.append({
                "Name": "custom:staff_role",
                "Value": staff_role
            })
        
        self.cognito.admin_create_user(
            UserPoolId=settings.cognito_user_pool_id,
            Username=email,
            TemporaryPassword=temp_password,
            UserAttributes=user_attributes,
            MessageAction='SUPPRESS',  # We send our own email
        )
    
    def _send_physician_invite(
        self,
        email: str,
        first_name: str,
        temp_password: str,
    ) -> bool:
        """Send physician invite email."""
        from core.config import settings
        
        try:
            self.ses.send_email(
                Source=settings.ses_sender_email,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {
                        "Data": "Welcome to OncoLife - Physician Portal Access"
                    },
                    "Body": {
                        "Html": {
                            "Data": f"""
                            <h2>Welcome to OncoLife, Dr. {first_name}!</h2>
                            <p>Your physician account has been created.</p>
                            <p><strong>Login Credentials:</strong></p>
                            <ul>
                                <li>Username: {email}</li>
                                <li>Temporary Password: {temp_password}</li>
                            </ul>
                            <p>Please login at: https://doctor.oncolife.com</p>
                            <p>You will be required to:</p>
                            <ol>
                                <li>Change your temporary password</li>
                                <li>Set up MFA (recommended)</li>
                            </ol>
                            <p>Thank you,<br>OncoLife Team</p>
                            """
                        }
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send invite email: {e}")
            return False
    
    def _send_staff_invite(
        self,
        email: str,
        first_name: str,
        temp_password: str,
        physician_name: str,
    ) -> bool:
        """Send staff invite email."""
        from core.config import settings
        
        try:
            self.ses.send_email(
                Source=settings.ses_sender_email,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {
                        "Data": "Welcome to OncoLife - Staff Portal Access"
                    },
                    "Body": {
                        "Html": {
                            "Data": f"""
                            <h2>Welcome to OncoLife, {first_name}!</h2>
                            <p>You have been added as staff for Dr. {physician_name}.</p>
                            <p><strong>Login Credentials:</strong></p>
                            <ul>
                                <li>Username: {email}</li>
                                <li>Temporary Password: {temp_password}</li>
                            </ul>
                            <p>Please login at: https://doctor.oncolife.com</p>
                            <p>You will be required to change your password on first login.</p>
                            <p>Thank you,<br>OncoLife Team</p>
                            """
                        }
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send invite email: {e}")
            return False
    
    def _log_registration(
        self,
        admin_uuid: UUID,
        registered_uuid: UUID,
        registered_role: str,
        registered_email: str,
    ) -> None:
        """Log registration action for audit."""
        try:
            self.db.execute(
                text("""
                    INSERT INTO audit_logs (
                        user_id, user_role, action, entity_type, entity_id, 
                        metadata, accessed_at
                    ) VALUES (
                        :admin_uuid, 'admin', :action, 'registration', 
                        :registered_uuid, :metadata::jsonb, :timestamp
                    )
                """),
                {
                    "admin_uuid": str(admin_uuid),
                    "action": f"register_{registered_role}",
                    "registered_uuid": str(registered_uuid),
                    "metadata": f'{{"email": "{registered_email}", "role": "{registered_role}"}}',
                    "timestamp": datetime.utcnow(),
                }
            )
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to log registration: {e}")
    
    def _validate_physician_data(
        self,
        email: str,
        first_name: str,
        last_name: str,
        npi_number: str,
    ) -> None:
        """Validate physician registration data."""
        if not email or "@" not in email:
            raise ValidationError("Valid email required", field="email")
        
        if not first_name or len(first_name.strip()) < 1:
            raise ValidationError("First name required", field="first_name")
        
        if not last_name or len(last_name.strip()) < 1:
            raise ValidationError("Last name required", field="last_name")
        
        if not npi_number or not npi_number.isdigit() or len(npi_number) != 10:
            raise ValidationError("NPI must be 10 digits", field="npi_number")



