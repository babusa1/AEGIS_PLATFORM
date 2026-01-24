"""
Patient Messaging Connector

Ingests patient-provider communications, secure messages, and chat.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult

logger = structlog.get_logger(__name__)


class MessageStatus(str, Enum):
    """Message delivery status."""
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class MessageCategory(str, Enum):
    """Category of message."""
    GENERAL = "general"
    APPOINTMENT = "appointment"
    MEDICATION = "medication"
    LAB_RESULT = "lab-result"
    SYMPTOM = "symptom"
    CARE_PLAN = "care-plan"
    URGENT = "urgent"
    ADMINISTRATIVE = "administrative"


class ParticipantRole(str, Enum):
    """Role of message participant."""
    PATIENT = "patient"
    PROVIDER = "provider"
    CARE_MANAGER = "care-manager"
    NURSE = "nurse"
    SYSTEM = "system"


@dataclass
class MessageParticipant:
    """Participant in a message thread."""
    participant_id: str
    role: ParticipantRole
    display_name: str | None = None


@dataclass
class MessageAttachment:
    """File attachment."""
    attachment_id: str
    content_type: str
    filename: str
    size_bytes: int | None = None
    url: str | None = None


@dataclass
class Message:
    """Parsed message."""
    message_id: str
    thread_id: str | None
    patient_id: str
    sender: MessageParticipant
    recipients: list[MessageParticipant]
    subject: str | None
    body: str
    category: MessageCategory
    status: MessageStatus
    sent_at: datetime
    read_at: datetime | None = None
    attachments: list[MessageAttachment] = field(default_factory=list)
    reply_to_id: str | None = None
    metadata: dict = field(default_factory=dict)


class MessagingConnector(BaseConnector):
    """
    Messaging Connector for patient communications.
    
    Supports:
    - FHIR Communication resources
    - Custom JSON message formats
    - Secure messaging platforms
    - Portal messages
    
    Usage:
        connector = MessagingConnector(tenant_id="hospital-a")
        result = await connector.parse(message_data)
    """
    
    def __init__(self, tenant_id: str, source_system: str = "messaging"):
        super().__init__(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "messaging"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """Parse message data."""
        errors = []
        
        if not isinstance(data, dict):
            return ConnectorResult(success=False, errors=["Data must be a dict"])
        
        # Check if FHIR Communication or custom format
        if data.get("resourceType") == "Communication":
            message = self._parse_fhir_communication(data)
        else:
            message = self._parse_custom_message(data)
        
        if not message:
            return ConnectorResult(success=False, errors=["Failed to parse message"])
        
        # Transform to vertices/edges
        try:
            vertices, edges = self._transform(message)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        logger.info(
            "Message parse complete",
            message_id=message.message_id,
            category=message.category.value,
            has_attachments=len(message.attachments) > 0,
        )
        
        return ConnectorResult(
            success=True,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={
                "message_id": message.message_id,
                "thread_id": message.thread_id,
                "category": message.category.value,
                "status": message.status.value,
            },
        )
    
    async def validate(self, data: Any) -> list[str]:
        """Validate message data."""
        errors = []
        if not isinstance(data, dict):
            errors.append("Data must be a dict")
            return errors
        
        # Check for required fields
        if data.get("resourceType") == "Communication":
            if not data.get("subject"):
                errors.append("Missing subject (patient)")
        else:
            if not data.get("patient_id"):
                errors.append("Missing patient_id")
            if not data.get("body") and not data.get("payload"):
                errors.append("Missing message body")
        
        return errors
    
    def _parse_fhir_communication(self, data: dict) -> Message | None:
        """Parse FHIR Communication resource."""
        try:
            # Extract ID
            message_id = data.get("id", self._generate_id("msg-"))
            
            # Get patient from subject
            subject = data.get("subject", {})
            patient_id = self._extract_reference(subject)
            
            # Get sender
            sender_ref = data.get("sender", {})
            sender = MessageParticipant(
                participant_id=self._extract_reference(sender_ref),
                role=self._determine_role(sender_ref),
                display_name=sender_ref.get("display"),
            )
            
            # Get recipients
            recipients = []
            for recipient in data.get("recipient", []):
                recipients.append(MessageParticipant(
                    participant_id=self._extract_reference(recipient),
                    role=self._determine_role(recipient),
                    display_name=recipient.get("display"),
                ))
            
            # Get payload (body)
            body = ""
            for payload in data.get("payload", []):
                if "contentString" in payload:
                    body += payload["contentString"]
            
            # Get category
            category = MessageCategory.GENERAL
            for cat in data.get("category", []):
                for coding in cat.get("coding", []):
                    code = coding.get("code", "").lower()
                    if code in [c.value for c in MessageCategory]:
                        category = MessageCategory(code)
                        break
            
            # Get status
            status_str = data.get("status", "completed")
            status_map = {
                "completed": MessageStatus.DELIVERED,
                "in-progress": MessageStatus.SENT,
                "preparation": MessageStatus.DRAFT,
                "entered-in-error": MessageStatus.FAILED,
            }
            status = status_map.get(status_str, MessageStatus.SENT)
            
            # Get sent time
            sent_str = data.get("sent", "")
            sent_at = datetime.fromisoformat(sent_str.replace("Z", "+00:00")) if sent_str else datetime.utcnow()
            
            # Get thread from basedOn or partOf
            thread_id = None
            if data.get("basedOn"):
                thread_id = self._extract_reference(data["basedOn"][0])
            
            return Message(
                message_id=message_id,
                thread_id=thread_id,
                patient_id=patient_id,
                sender=sender,
                recipients=recipients,
                subject=None,  # FHIR Communication doesn't have subject text
                body=body,
                category=category,
                status=status,
                sent_at=sent_at,
            )
            
        except Exception as e:
            logger.error("Failed to parse FHIR Communication", error=str(e))
            return None
    
    def _parse_custom_message(self, data: dict) -> Message | None:
        """Parse custom JSON message format."""
        try:
            message_id = data.get("message_id", data.get("id", self._generate_id("msg-")))
            
            # Parse sender
            sender_data = data.get("sender", {})
            sender = MessageParticipant(
                participant_id=sender_data.get("id", "unknown"),
                role=ParticipantRole(sender_data.get("role", "patient")),
                display_name=sender_data.get("name"),
            )
            
            # Parse recipients
            recipients = []
            for r in data.get("recipients", []):
                recipients.append(MessageParticipant(
                    participant_id=r.get("id", "unknown"),
                    role=ParticipantRole(r.get("role", "provider")),
                    display_name=r.get("name"),
                ))
            
            # Parse category
            cat_str = data.get("category", "general")
            category = MessageCategory(cat_str) if cat_str in [c.value for c in MessageCategory] else MessageCategory.GENERAL
            
            # Parse status
            status_str = data.get("status", "sent")
            status = MessageStatus(status_str) if status_str in [s.value for s in MessageStatus] else MessageStatus.SENT
            
            # Parse timestamps
            sent_str = data.get("sent_at", data.get("timestamp", ""))
            sent_at = datetime.fromisoformat(sent_str) if sent_str else datetime.utcnow()
            
            read_str = data.get("read_at")
            read_at = datetime.fromisoformat(read_str) if read_str else None
            
            # Parse attachments
            attachments = []
            for att in data.get("attachments", []):
                attachments.append(MessageAttachment(
                    attachment_id=att.get("id", self._generate_id("att-")),
                    content_type=att.get("content_type", "application/octet-stream"),
                    filename=att.get("filename", "attachment"),
                    size_bytes=att.get("size"),
                    url=att.get("url"),
                ))
            
            return Message(
                message_id=message_id,
                thread_id=data.get("thread_id"),
                patient_id=data.get("patient_id", ""),
                sender=sender,
                recipients=recipients,
                subject=data.get("subject"),
                body=data.get("body", data.get("content", "")),
                category=category,
                status=status,
                sent_at=sent_at,
                read_at=read_at,
                attachments=attachments,
                reply_to_id=data.get("reply_to_id"),
                metadata=data.get("metadata", {}),
            )
            
        except Exception as e:
            logger.error("Failed to parse custom message", error=str(e))
            return None
    
    def _extract_reference(self, ref: dict) -> str:
        """Extract ID from FHIR reference."""
        reference = ref.get("reference", "")
        if "/" in reference:
            return reference.split("/")[-1]
        return reference or ref.get("id", "unknown")
    
    def _determine_role(self, ref: dict) -> ParticipantRole:
        """Determine participant role from reference."""
        reference = ref.get("reference", "").lower()
        if "patient" in reference:
            return ParticipantRole.PATIENT
        elif "practitioner" in reference:
            return ParticipantRole.PROVIDER
        return ParticipantRole.PROVIDER
    
    def _transform(self, message: Message) -> tuple[list[dict], list[dict]]:
        """Transform message to vertices/edges."""
        vertices = []
        edges = []
        
        # Create Communication vertex
        comm_id = f"Communication/{message.message_id}"
        patient_id = f"Patient/{message.patient_id}"
        
        comm_vertex = self._create_vertex(
            label="Communication",
            id=comm_id,
            properties={
                "message_id": message.message_id,
                "thread_id": message.thread_id,
                "subject": message.subject,
                "body": message.body[:1000] if message.body else None,  # Truncate for graph
                "body_length": len(message.body) if message.body else 0,
                "category": message.category.value,
                "status": message.status.value,
                "sent_at": message.sent_at.isoformat(),
                "read_at": message.read_at.isoformat() if message.read_at else None,
                "sender_id": message.sender.participant_id,
                "sender_role": message.sender.role.value,
                "recipient_count": len(message.recipients),
                "has_attachments": len(message.attachments) > 0,
            }
        )
        vertices.append(comm_vertex)
        
        # Link to patient
        edges.append(self._create_edge(
            label="HAS_COMMUNICATION",
            from_label="Patient",
            from_id=patient_id,
            to_label="Communication",
            to_id=comm_id,
        ))
        
        # Link sender
        if message.sender.role == ParticipantRole.PATIENT:
            edges.append(self._create_edge(
                label="SENT_BY",
                from_label="Communication",
                from_id=comm_id,
                to_label="Patient",
                to_id=patient_id,
            ))
        else:
            sender_id = f"Practitioner/{message.sender.participant_id}"
            edges.append(self._create_edge(
                label="SENT_BY",
                from_label="Communication",
                from_id=comm_id,
                to_label="Practitioner",
                to_id=sender_id,
            ))
        
        # Link recipients
        for recipient in message.recipients:
            if recipient.role == ParticipantRole.PATIENT:
                edges.append(self._create_edge(
                    label="SENT_TO",
                    from_label="Communication",
                    from_id=comm_id,
                    to_label="Patient",
                    to_id=patient_id,
                ))
            else:
                recipient_id = f"Practitioner/{recipient.participant_id}"
                edges.append(self._create_edge(
                    label="SENT_TO",
                    from_label="Communication",
                    from_id=comm_id,
                    to_label="Practitioner",
                    to_id=recipient_id,
                ))
        
        # Link to thread if reply
        if message.reply_to_id:
            reply_to = f"Communication/{message.reply_to_id}"
            edges.append(self._create_edge(
                label="REPLY_TO",
                from_label="Communication",
                from_id=comm_id,
                to_label="Communication",
                to_id=reply_to,
            ))
        
        # Create attachment vertices
        for att in message.attachments:
            att_id = f"Attachment/{att.attachment_id}"
            att_vertex = self._create_vertex(
                label="Attachment",
                id=att_id,
                properties={
                    "content_type": att.content_type,
                    "filename": att.filename,
                    "size_bytes": att.size_bytes,
                }
            )
            vertices.append(att_vertex)
            
            edges.append(self._create_edge(
                label="HAS_ATTACHMENT",
                from_label="Communication",
                from_id=comm_id,
                to_label="Attachment",
                to_id=att_id,
            ))
        
        return vertices, edges


# Sample message for testing
SAMPLE_MESSAGE = {
    "message_id": "MSG-001",
    "thread_id": "THREAD-001",
    "patient_id": "PAT12345",
    "sender": {
        "id": "PAT12345",
        "role": "patient",
        "name": "John Smith",
    },
    "recipients": [
        {
            "id": "DR-001",
            "role": "provider",
            "name": "Dr. Jane Wilson",
        }
    ],
    "subject": "Question about medication",
    "body": "Hi Dr. Wilson, I've been experiencing some side effects from the new medication. Should I continue taking it?",
    "category": "medication",
    "status": "sent",
    "sent_at": "2024-01-15T14:30:00",
    "attachments": [],
}
