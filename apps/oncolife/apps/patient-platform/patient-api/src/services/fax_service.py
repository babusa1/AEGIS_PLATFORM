"""
Fax Receiving Service.

This service handles the complete fax reception pipeline:
1. Receive webhook from fax provider (Sinch, Twilio, Phaxio, etc.)
2. Download fax document from provider's URL or decode base64
3. Upload to S3 with encryption (AWS KMS)
4. Store metadata in database
5. Trigger OCR processing

Supported Fax Providers:
- Sinch (your current provider)
- Twilio Fax
- Phaxio
- RingCentral
- eFax

Usage:
    from services import FaxService
    
    fax_service = FaxService(db)
    result = await fax_service.receive_fax(webhook_payload)
"""

import base64
import hashlib
import hmac
import httpx
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from uuid import UUID
import uuid

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from core.config import settings
from core.logging import get_logger
from core.exceptions import ExternalServiceError, ValidationError

from db.models.referral import PatientReferral, ReferralDocument, ReferralStatus

logger = get_logger(__name__)


# =============================================================================
# FAX PROVIDER WEBHOOK FORMATS
# =============================================================================

class FaxProviderType:
    """Supported fax provider types."""
    SINCH = "sinch"
    TWILIO = "twilio"
    PHAXIO = "phaxio"
    RINGCENTRAL = "ringcentral"
    EFAX = "efax"
    GENERIC = "generic"


class FaxService:
    """
    Service for receiving and processing fax documents.
    
    Handles:
    - Webhook signature validation
    - Document download from provider URL
    - Base64 document decoding
    - S3 upload with encryption
    - Metadata storage
    - OCR pipeline triggering
    """
    
    def __init__(
        self,
        db: Session,
        s3_client: Optional[Any] = None,
    ):
        """
        Initialize fax service.
        
        Args:
            db: Database session
            s3_client: AWS S3 client (optional)
        """
        self.db = db
        self._s3_client = s3_client
        self.aws_region = settings.aws_region
        self.bucket = settings.s3_referral_bucket
    
    @property
    def s3_client(self):
        """Get or create S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                region_name=self.aws_region,
            )
        return self._s3_client
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    async def receive_fax(
        self,
        provider: str,
        payload: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for receiving a fax webhook.
        
        Args:
            provider: Fax provider type (sinch, twilio, etc.)
            payload: Webhook payload from the provider
            raw_body: Raw request body for signature verification
            signature: Webhook signature header
            
        Returns:
            Dict with referral UUID and status
        """
        logger.info(f"Receiving fax from provider: {provider}")
        
        # Step 1: Validate webhook signature
        if settings.fax_webhook_secret:
            self._validate_signature(provider, raw_body, signature)
        
        # Step 2: Parse provider-specific payload
        fax_data = self._parse_webhook_payload(provider, payload)
        
        # Step 3: Create referral record
        referral = PatientReferral(
            status=ReferralStatus.RECEIVED.value,
            fax_number=fax_data.get("from_number"),
            fax_received_at=fax_data.get("received_at") or datetime.utcnow(),
        )
        self.db.add(referral)
        self.db.flush()
        
        referral_uuid = referral.uuid
        logger.info(f"Created referral: {referral_uuid}")
        
        try:
            # Step 4: Get the document (download URL or base64)
            document_bytes, content_type = await self._get_document(
                provider=provider,
                payload=fax_data,
            )
            
            if not document_bytes:
                raise ValidationError(
                    message="No document content in webhook payload",
                    field="document",
                )
            
            # Step 5: Upload to S3 with encryption
            s3_key = await self._upload_to_s3(
                document_bytes=document_bytes,
                referral_uuid=referral_uuid,
                content_type=content_type,
                fax_id=fax_data.get("fax_id"),
            )
            
            # Step 6: Create document record
            document = ReferralDocument(
                referral_uuid=referral_uuid,
                s3_bucket=self.bucket,
                s3_key=s3_key,
                file_name=fax_data.get("file_name", f"{fax_data.get('fax_id')}.pdf"),
                file_type=content_type,
                file_size_bytes=len(document_bytes),
                page_count=fax_data.get("pages", 1),
            )
            self.db.add(document)
            
            # Update referral status
            referral.status = ReferralStatus.PROCESSING.value
            self.db.commit()
            
            logger.info(f"Fax uploaded to S3: s3://{self.bucket}/{s3_key}")
            
            return {
                "success": True,
                "referral_uuid": str(referral_uuid),
                "s3_bucket": self.bucket,
                "s3_key": s3_key,
                "status": ReferralStatus.PROCESSING.value,
                "message": "Fax received and queued for OCR processing",
            }
            
        except Exception as e:
            referral.status = ReferralStatus.FAILED.value
            referral.status_message = str(e)
            self.db.commit()
            logger.error(f"Fax processing failed: {referral_uuid} - {e}")
            raise
    
    # =========================================================================
    # WEBHOOK SIGNATURE VALIDATION
    # =========================================================================
    
    def _validate_signature(
        self,
        provider: str,
        raw_body: Optional[bytes],
        signature: Optional[str],
    ) -> None:
        """
        Validate webhook signature based on provider.
        
        Different providers use different signature methods:
        - Sinch: HMAC-SHA256
        - Twilio: HMAC-SHA1
        - Phaxio: HMAC-SHA256
        """
        if not signature or not raw_body:
            raise ValidationError(
                message="Missing webhook signature",
                field="signature",
            )
        
        secret = settings.fax_webhook_secret.encode()
        
        if provider in [FaxProviderType.SINCH, FaxProviderType.PHAXIO]:
            # HMAC-SHA256
            expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        elif provider == FaxProviderType.TWILIO:
            # HMAC-SHA1 (Twilio style)
            expected = hmac.new(secret, raw_body, hashlib.sha1).hexdigest()
        else:
            # Default to SHA256
            expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature.lower(), expected.lower()):
            logger.warning(f"Invalid webhook signature from {provider}")
            raise ValidationError(
                message="Invalid webhook signature",
                field="signature",
            )
    
    # =========================================================================
    # PAYLOAD PARSING
    # =========================================================================
    
    def _parse_webhook_payload(
        self,
        provider: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Parse provider-specific webhook payload into standardized format.
        
        Standardized format:
        {
            "fax_id": str,
            "from_number": str,
            "to_number": str,
            "received_at": datetime,
            "pages": int,
            "download_url": str (optional),
            "document_base64": str (optional),
            "file_name": str (optional),
        }
        """
        if provider == FaxProviderType.SINCH:
            return self._parse_sinch_payload(payload)
        elif provider == FaxProviderType.TWILIO:
            return self._parse_twilio_payload(payload)
        elif provider == FaxProviderType.PHAXIO:
            return self._parse_phaxio_payload(payload)
        elif provider == FaxProviderType.RINGCENTRAL:
            return self._parse_ringcentral_payload(payload)
        else:
            return self._parse_generic_payload(payload)
    
    def _parse_sinch_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Sinch fax webhook payload."""
        return {
            "fax_id": payload.get("faxId") or payload.get("id"),
            "from_number": payload.get("fromNumber") or payload.get("from"),
            "to_number": payload.get("toNumber") or payload.get("to"),
            "received_at": self._parse_timestamp(payload.get("receivedAt") or payload.get("timestamp")),
            "pages": payload.get("pages") or payload.get("pageCount", 1),
            "download_url": payload.get("documentUrl") or payload.get("mediaUrl"),
            "document_base64": payload.get("document") or payload.get("content"),
            "file_name": payload.get("fileName"),
        }
    
    def _parse_twilio_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Twilio fax webhook payload."""
        return {
            "fax_id": payload.get("FaxSid") or payload.get("Sid"),
            "from_number": payload.get("From"),
            "to_number": payload.get("To"),
            "received_at": self._parse_timestamp(payload.get("DateCreated")),
            "pages": int(payload.get("NumPages", 1)),
            "download_url": payload.get("MediaUrl"),
            "document_base64": None,  # Twilio uses URL
            "file_name": f"{payload.get('FaxSid', 'fax')}.pdf",
        }
    
    def _parse_phaxio_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Phaxio fax webhook payload."""
        fax = payload.get("fax", payload)
        return {
            "fax_id": str(fax.get("id")),
            "from_number": fax.get("from_number"),
            "to_number": fax.get("to_number"),
            "received_at": self._parse_timestamp(fax.get("completed_at")),
            "pages": fax.get("num_pages", 1),
            "download_url": fax.get("pdf_url"),
            "document_base64": None,
            "file_name": f"{fax.get('id')}.pdf",
        }
    
    def _parse_ringcentral_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse RingCentral fax webhook payload."""
        return {
            "fax_id": payload.get("uuid") or payload.get("id"),
            "from_number": payload.get("from", {}).get("phoneNumber"),
            "to_number": payload.get("to", [{}])[0].get("phoneNumber") if payload.get("to") else None,
            "received_at": self._parse_timestamp(payload.get("creationTime")),
            "pages": payload.get("pageCount", 1),
            "download_url": payload.get("attachments", [{}])[0].get("uri") if payload.get("attachments") else None,
            "document_base64": None,
            "file_name": f"{payload.get('uuid', 'fax')}.pdf",
        }
    
    def _parse_generic_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse generic fax webhook payload."""
        return {
            "fax_id": payload.get("fax_id") or payload.get("id") or str(uuid.uuid4()),
            "from_number": payload.get("from_number") or payload.get("from"),
            "to_number": payload.get("to_number") or payload.get("to"),
            "received_at": self._parse_timestamp(payload.get("received_at") or payload.get("timestamp")),
            "pages": payload.get("pages") or payload.get("page_count", 1),
            "download_url": payload.get("download_url") or payload.get("media_url") or payload.get("url"),
            "document_base64": payload.get("document") or payload.get("content") or payload.get("base64"),
            "file_name": payload.get("file_name"),
        }
    
    def _parse_timestamp(self, ts: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if not ts:
            return None
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            # Try common formats
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S%z",
            ]:
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
        return None
    
    # =========================================================================
    # DOCUMENT RETRIEVAL
    # =========================================================================
    
    async def _get_document(
        self,
        provider: str,
        payload: Dict[str, Any],
    ) -> Tuple[bytes, str]:
        """
        Get document content from webhook payload.
        
        Supports:
        - Download from URL
        - Decode from base64
        
        Returns:
            Tuple of (document_bytes, content_type)
        """
        download_url = payload.get("download_url")
        document_base64 = payload.get("document_base64")
        
        # Priority 1: Download from URL
        if download_url:
            return await self._download_document(download_url, provider)
        
        # Priority 2: Decode base64
        if document_base64:
            return self._decode_base64_document(document_base64)
        
        raise ValidationError(
            message="No document URL or base64 content in payload",
            field="document",
        )
    
    async def _download_document(
        self,
        url: str,
        provider: str,
    ) -> Tuple[bytes, str]:
        """
        Download document from provider URL.
        
        Args:
            url: Document download URL
            provider: Fax provider (for auth if needed)
            
        Returns:
            Tuple of (document_bytes, content_type)
        """
        logger.info(f"Downloading document from: {url[:50]}...")
        
        headers = {}
        
        # Some providers require authentication for downloads
        # Add provider-specific auth headers here if needed
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "application/pdf")
                
                # Clean up content type (remove charset, etc.)
                if ";" in content_type:
                    content_type = content_type.split(";")[0].strip()
                
                return response.content, content_type
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to download document: {e}")
            raise ExternalServiceError(
                message=f"Failed to download fax document: {e}",
                service_name="Fax Provider",
            )
    
    def _decode_base64_document(
        self,
        document_base64: str,
    ) -> Tuple[bytes, str]:
        """
        Decode base64-encoded document.
        
        Handles:
        - Plain base64
        - Data URI format (data:application/pdf;base64,...)
        
        Returns:
            Tuple of (document_bytes, content_type)
        """
        content_type = "application/pdf"  # Default
        
        # Check for data URI format
        if document_base64.startswith("data:"):
            # Format: data:application/pdf;base64,XXXXX
            parts = document_base64.split(",", 1)
            if len(parts) == 2:
                metadata, document_base64 = parts
                if ";" in metadata:
                    content_type = metadata.split(":")[1].split(";")[0]
        
        try:
            document_bytes = base64.b64decode(document_base64)
            return document_bytes, content_type
        except Exception as e:
            logger.error(f"Failed to decode base64 document: {e}")
            raise ValidationError(
                message="Invalid base64 document content",
                field="document_base64",
            )
    
    # =========================================================================
    # S3 UPLOAD
    # =========================================================================
    
    async def _upload_to_s3(
        self,
        document_bytes: bytes,
        referral_uuid: UUID,
        content_type: str,
        fax_id: Optional[str] = None,
    ) -> str:
        """
        Upload document to S3 with encryption.
        
        Args:
            document_bytes: Document content
            referral_uuid: Referral UUID for folder structure
            content_type: MIME type
            fax_id: Optional fax ID for filename
            
        Returns:
            S3 object key
        """
        # Generate S3 key with date-based folder structure
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        file_name = fax_id or str(referral_uuid)
        
        # Determine extension from content type
        ext = "pdf"
        if "tiff" in content_type.lower():
            ext = "tiff"
        elif "image" in content_type.lower():
            ext = "png"
        
        s3_key = f"referrals/{date_path}/{file_name}.{ext}"
        
        try:
            # Upload with server-side encryption (SSE-S3)
            # For HIPAA, you may want SSE-KMS with a custom key
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=document_bytes,
                ContentType=content_type,
                ServerSideEncryption="aws:kms",  # Use KMS for HIPAA compliance
                # KMSMasterKeyId=settings.kms_key_id,  # Uncomment for custom key
                Metadata={
                    "referral_uuid": str(referral_uuid),
                    "uploaded_at": datetime.utcnow().isoformat(),
                },
            )
            
            logger.info(f"Uploaded to S3: s3://{self.bucket}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise ExternalServiceError(
                message="Failed to upload document to S3",
                service_name="AWS S3",
            )
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def get_document_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned URL for document access.
        
        Args:
            s3_key: S3 object key
            expires_in: URL expiration in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": s3_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise ExternalServiceError(
                message="Failed to generate document URL",
                service_name="AWS S3",
            )





