"""
Authentication Service - Patient API
=====================================

Service for AWS Cognito authentication operations.
Handles signup, login, password management, and user deletion.

Usage:
    from services import AuthService
    
    auth_service = AuthService(patient_db, doctor_db)
    result = auth_service.signup(email, password, first_name, last_name)
"""

import os
import hmac
import hashlib
import base64
import logging
from typing import Optional, Tuple, Dict, Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Database models
from db.patient_models import (
    PatientInfo,
    PatientConfigurations,
    PatientDiaryEntries,
    PatientPhysicianAssociations,
    Conversations,
)
from db.doctor_models import StaffProfiles

# Core
from core.logging import get_logger
from core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
    ExternalServiceError,
)

load_dotenv()
logger = get_logger(__name__)


class AuthService:
    """
    Service for authentication operations using AWS Cognito.
    
    Provides:
    - User signup with Cognito and local DB records
    - User login with token generation
    - Password management
    - User deletion (soft delete)
    
    All operations are logged for audit purposes.
    """
    
    # Default physician and clinic for new patients
    DEFAULT_PHYSICIAN_UUID = 'bea3fce0-42f9-4a00-ae56-4e2591ca17c5'
    DEFAULT_CLINIC_UUID = 'ab4dac8e-f9dc-4399-b9bd-781a9d540139'
    
    def __init__(
        self,
        patient_db: Session,
        doctor_db: Optional[Session] = None,
        cognito_client: Optional[Any] = None,
    ):
        """
        Initialize the auth service.
        
        Args:
            patient_db: Patient database session
            doctor_db: Doctor database session (optional)
            cognito_client: AWS Cognito client (optional, creates one if not provided)
        """
        self.patient_db = patient_db
        self.doctor_db = doctor_db
        self._cognito_client = cognito_client
        
        # Load Cognito configuration
        self.user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
        self.client_id = os.getenv("COGNITO_CLIENT_ID")
        self.client_secret = os.getenv("COGNITO_CLIENT_SECRET")
        self.aws_region = os.getenv("AWS_REGION", "us-west-2")
    
    @property
    def cognito_client(self):
        """Get or create Cognito client."""
        if self._cognito_client is None:
            self._cognito_client = boto3.client(
                "cognito-idp",
                region_name=self.aws_region,
            )
        return self._cognito_client
    
    def _get_secret_hash(self, username: str) -> str:
        """
        Calculate the SecretHash for Cognito API calls.
        
        Args:
            username: The username (email)
            
        Returns:
            Base64-encoded secret hash
        """
        if not self.client_secret:
            return ""
        
        msg = username + self.client_id
        dig = hmac.new(
            key=self.client_secret.encode("utf-8"),
            msg=msg.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(dig).decode()
    
    def _validate_cognito_config(self) -> None:
        """Validate that Cognito is properly configured."""
        if not self.user_pool_id:
            raise ExternalServiceError(
                message="COGNITO_USER_POOL_ID not configured",
                service_name="Cognito",
            )
        if not self.client_id:
            raise ExternalServiceError(
                message="COGNITO_CLIENT_ID not configured",
                service_name="Cognito",
            )
    
    # =========================================================================
    # Signup
    # =========================================================================
    
    def signup(
        self,
        email: str,
        first_name: str,
        last_name: str,
        physician_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user account.
        
        Creates the user in:
        1. AWS Cognito (authentication)
        2. Local patient database (patient info & config)
        3. Physician association
        
        Args:
            email: User's email address
            first_name: User's first name
            last_name: User's last name
            physician_email: Optional physician email to associate with
            
        Returns:
            Dict with user info and status
            
        Raises:
            ConflictError: If email already exists
            ExternalServiceError: If Cognito operation fails
        """
        logger.info(f"Signup attempt: email={email}")
        self._validate_cognito_config()
        
        # Check if user already exists
        existing = self.patient_db.query(PatientInfo).filter(
            PatientInfo.email_address == email,
            PatientInfo.is_deleted == False,
        ).first()
        
        if existing:
            logger.warning(f"Signup conflict: email={email}")
            raise ConflictError(
                message=f"A user with email {email} already exists",
                resource_type="User",
                resource_id=email,
            )
        
        try:
            # Create user in Cognito
            user_attributes = [
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "given_name", "Value": first_name},
                {"Name": "family_name", "Value": last_name},
            ]
            
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=user_attributes,
                ForceAliasCreation=False,
            )
            
            # Extract UUID from Cognito response
            user_sub = None
            for attr in response["User"]["Attributes"]:
                if attr["Name"] == "sub":
                    user_sub = attr["Value"]
                    break
            
            if not user_sub:
                logger.error(f"Signup missing sub: email={email}")
                raise ExternalServiceError(
                    message="User created but UUID not returned",
                    service_name="Cognito",
                )
            
            logger.info(f"Cognito user created: email={email} uuid={user_sub}")
            
            # Create local database records
            self._create_patient_records(
                user_sub=user_sub,
                email=email,
                first_name=first_name,
                last_name=last_name,
                physician_email=physician_email,
            )
            
            logger.info(f"Signup complete: email={email} uuid={user_sub}")
            
            return {
                "message": f"User {email} created successfully. A temporary password has been sent to their email.",
                "email": email,
                "user_status": response["User"]["UserStatus"],
                "uuid": user_sub,
            }
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"Cognito signup error: code={error_code} msg={error_message}")
            raise ExternalServiceError(
                message=f"AWS Cognito error: {error_message}",
                service_name="Cognito",
            )
    
    def _create_patient_records(
        self,
        user_sub: str,
        email: str,
        first_name: str,
        last_name: str,
        physician_email: Optional[str] = None,
    ) -> None:
        """Create patient records in the database."""
        # Create patient info
        new_patient = PatientInfo(
            uuid=user_sub,
            email_address=email,
            first_name=first_name,
            last_name=last_name,
        )
        self.patient_db.add(new_patient)
        
        # Create patient configuration
        new_config = PatientConfigurations(uuid=user_sub)
        self.patient_db.add(new_config)
        
        # Associate with physician
        associated_physician_uuid = self._find_physician(physician_email)
        
        new_association = PatientPhysicianAssociations(
            patient_uuid=user_sub,
            physician_uuid=associated_physician_uuid,
            clinic_uuid=self.DEFAULT_CLINIC_UUID,
        )
        self.patient_db.add(new_association)
        
        self.patient_db.commit()
        logger.info(f"Patient records created: uuid={user_sub}")
    
    def _find_physician(self, physician_email: Optional[str]) -> str:
        """Find physician UUID by email, or return default."""
        if physician_email and self.doctor_db:
            physician = self.doctor_db.query(StaffProfiles).filter(
                StaffProfiles.email_address == physician_email,
                StaffProfiles.role == 'physician',
            ).first()
            
            if physician:
                return str(physician.staff_uuid)
            else:
                logger.warning(f"Physician not found: {physician_email}, using default")
        
        return self.DEFAULT_PHYSICIAN_UUID
    
    # =========================================================================
    # Login
    # =========================================================================
    
    def login(
        self,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Authenticate a user and return tokens.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Dict with tokens or challenge info
            
        Raises:
            AuthenticationError: If credentials are invalid
            ExternalServiceError: If Cognito operation fails
        """
        logger.info(f"Login attempt: email={email}")
        self._validate_cognito_config()
        
        try:
            auth_parameters = {
                "USERNAME": email,
                "PASSWORD": password,
            }
            
            if self.client_secret:
                auth_parameters["SECRET_HASH"] = self._get_secret_hash(email)
            
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                AuthParameters=auth_parameters,
            )
            
            if "AuthenticationResult" in response:
                logger.info(f"Login success: email={email}")
                auth_result = response["AuthenticationResult"]
                return {
                    "valid": True,
                    "message": "Login credentials are valid",
                    "user_status": "CONFIRMED",
                    "tokens": {
                        "access_token": auth_result["AccessToken"],
                        "refresh_token": auth_result["RefreshToken"],
                        "id_token": auth_result["IdToken"],
                        "token_type": auth_result["TokenType"],
                    },
                }
            
            elif "ChallengeName" in response:
                challenge_name = response["ChallengeName"]
                session = response.get("Session")
                logger.info(f"Login challenge: email={email} challenge={challenge_name}")
                
                if challenge_name == "NEW_PASSWORD_REQUIRED":
                    return {
                        "valid": True,
                        "message": "Password change required",
                        "user_status": "FORCE_CHANGE_PASSWORD",
                        "session": session,
                    }
                else:
                    return {
                        "valid": True,
                        "message": f"Challenge required: {challenge_name}",
                        "user_status": "CHALLENGE_REQUIRED",
                        "session": session,
                    }
            
            return {"valid": False, "message": "Unexpected response"}
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"Login error: email={email} code={error_code}")
            
            if error_code in ["NotAuthorizedException", "UserNotFoundException"]:
                return {
                    "valid": False,
                    "message": "Invalid email or password",
                }
            
            raise ExternalServiceError(
                message=f"AWS Cognito error: {error_message}",
                service_name="Cognito",
            )
    
    # =========================================================================
    # Complete New Password
    # =========================================================================
    
    def complete_new_password(
        self,
        email: str,
        new_password: str,
        session: str,
    ) -> Dict[str, Any]:
        """
        Complete the new password setup flow.
        
        Args:
            email: User's email
            new_password: The new password
            session: Session token from login challenge
            
        Returns:
            Dict with tokens
            
        Raises:
            AuthenticationError: If session is invalid
            ValidationError: If password doesn't meet requirements
            ExternalServiceError: If Cognito operation fails
        """
        logger.info(f"Complete new password: email={email}")
        self._validate_cognito_config()
        
        try:
            challenge_responses = {
                "USERNAME": email,
                "NEW_PASSWORD": new_password,
            }
            
            if self.client_secret:
                challenge_responses["SECRET_HASH"] = self._get_secret_hash(email)
            
            response = self.cognito_client.admin_respond_to_auth_challenge(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                Session=session,
                ChallengeResponses=challenge_responses,
            )
            
            if "AuthenticationResult" in response:
                logger.info(f"Password change success: email={email}")
                auth_result = response["AuthenticationResult"]
                return {
                    "message": "Password successfully changed and user authenticated.",
                    "tokens": {
                        "access_token": auth_result["AccessToken"],
                        "refresh_token": auth_result["RefreshToken"],
                        "id_token": auth_result["IdToken"],
                        "token_type": auth_result["TokenType"],
                    },
                }
            
            raise AuthenticationError(
                message="Could not set new password",
            )
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"Password change error: email={email} code={error_code}")
            
            if error_code in ["NotAuthorizedException", "CodeMismatchException", "ExpiredCodeException"]:
                raise AuthenticationError(
                    message="Invalid or expired session. Please try logging in again.",
                )
            
            if error_code == "InvalidPasswordException":
                raise ValidationError(
                    message=f"Password does not meet requirements: {error_message}",
                    field="new_password",
                )
            
            raise ExternalServiceError(
                message=f"AWS Cognito error: {error_message}",
                service_name="Cognito",
            )
    
    # =========================================================================
    # Delete Patient
    # =========================================================================
    
    def delete_patient(
        self,
        email: Optional[str] = None,
        uuid: Optional[str] = None,
        skip_aws: bool = False,
    ) -> None:
        """
        Soft delete a patient and all related data.
        
        Args:
            email: Patient's email (optional if uuid provided)
            uuid: Patient's UUID (optional if email provided)
            skip_aws: If True, skip Cognito deletion
            
        Raises:
            ValidationError: If neither email nor uuid provided
            NotFoundError: If patient not found
            ExternalServiceError: If Cognito deletion fails
        """
        if not email and not uuid:
            raise ValidationError(
                message="Either email or uuid must be provided",
                field="identifier",
            )
        
        # Find the patient
        patient = None
        if uuid:
            try:
                patient_uuid = UUID(uuid)
                patient = self.patient_db.query(PatientInfo).filter(
                    PatientInfo.uuid == patient_uuid
                ).first()
                logger.warning(f"Delete patient: uuid={uuid}")
            except ValueError:
                raise ValidationError(
                    message="Invalid UUID format",
                    field="uuid",
                )
        else:
            patient = self.patient_db.query(PatientInfo).filter(
                PatientInfo.email_address == email
            ).first()
            logger.warning(f"Delete patient: email={email}")
        
        if not patient:
            identifier = uuid or email
            raise NotFoundError(
                message=f"Patient not found: {identifier}",
                resource_type="Patient",
                resource_id=identifier,
            )
        
        user_id = patient.uuid
        user_email = patient.email_address
        logger.warning(f"Deleting patient: uuid={user_id} email={user_email}")
        
        # Soft delete all related records
        try:
            self.patient_db.query(PatientDiaryEntries).filter(
                PatientDiaryEntries.patient_uuid == user_id
            ).update({"is_deleted": True})
            
            self.patient_db.query(PatientPhysicianAssociations).filter(
                PatientPhysicianAssociations.patient_uuid == user_id
            ).update({"is_deleted": True})
            
            self.patient_db.query(PatientConfigurations).filter(
                PatientConfigurations.uuid == user_id
            ).update({"is_deleted": True})
            
            self.patient_db.query(PatientInfo).filter(
                PatientInfo.uuid == user_id
            ).update({"is_deleted": True})
            
        except Exception as e:
            self.patient_db.rollback()
            logger.error(f"DB cleanup failed: uuid={user_id} error={e}")
            raise
        
        # Delete from Cognito if not skipped
        if not skip_aws:
            try:
                self.cognito_client.admin_delete_user(
                    UserPoolId=self.user_pool_id,
                    Username=user_email,
                )
                logger.info(f"Cognito user deleted: uuid={user_id}")
            except ClientError as e:
                self.patient_db.rollback()
                logger.error(f"Cognito delete failed: {e.response['Error']['Message']}")
                raise ExternalServiceError(
                    message="Failed to delete user from authentication service",
                    service_name="Cognito",
                )
        else:
            logger.info(f"Skipped Cognito deletion: uuid={user_id}")
        
        self.patient_db.commit()
        logger.warning(f"Patient deleted: uuid={user_id} email={user_email}")
    
    # =========================================================================
    # Logout
    # =========================================================================
    
    def logout(self) -> Dict[str, str]:
        """
        Client-side logout acknowledgment.
        
        The actual logout happens client-side by deleting tokens.
        This endpoint is a formality for logging.
        
        Returns:
            Success message
        """
        logger.info("Logout acknowledged")
        return {"message": "Logout successful"}





