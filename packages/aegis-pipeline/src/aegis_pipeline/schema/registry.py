"""Schema Registry for data validation"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import json
import structlog

logger = structlog.get_logger(__name__)


class SchemaFormat(str, Enum):
    JSON = "json"
    AVRO = "avro"
    PROTOBUF = "protobuf"


class Compatibility(str, Enum):
    BACKWARD = "backward"
    FORWARD = "forward"
    FULL = "full"
    NONE = "none"


@dataclass
class SchemaVersion:
    version: int
    schema: dict
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass 
class SchemaEntry:
    subject: str
    format: SchemaFormat
    compatibility: Compatibility
    versions: list[SchemaVersion] = field(default_factory=list)


class SchemaRegistry:
    """
    Schema registry for data validation.
    
    SOC 2 Processing Integrity: Data validation
    """
    
    def __init__(self):
        self._schemas: dict[str, SchemaEntry] = {}
    
    def register(self, subject: str, schema: dict,
                format: SchemaFormat = SchemaFormat.JSON,
                compatibility: Compatibility = Compatibility.BACKWARD) -> int:
        """Register a new schema version."""
        if subject not in self._schemas:
            self._schemas[subject] = SchemaEntry(
                subject=subject,
                format=format,
                compatibility=compatibility
            )
        
        entry = self._schemas[subject]
        new_version = len(entry.versions) + 1
        
        # Check compatibility
        if entry.versions and compatibility != Compatibility.NONE:
            if not self._check_compatibility(entry.versions[-1].schema, schema, compatibility):
                raise ValueError(f"Schema not compatible with {compatibility.value}")
        
        entry.versions.append(SchemaVersion(version=new_version, schema=schema))
        logger.info("Schema registered", subject=subject, version=new_version)
        
        return new_version
    
    def get_schema(self, subject: str, version: int | None = None) -> dict | None:
        """Get schema by subject and version."""
        entry = self._schemas.get(subject)
        if not entry or not entry.versions:
            return None
        
        if version is None:
            return entry.versions[-1].schema
        
        for v in entry.versions:
            if v.version == version:
                return v.schema
        
        return None
    
    def validate(self, subject: str, data: dict, version: int | None = None) -> tuple[bool, list[str]]:
        """Validate data against schema."""
        schema = self.get_schema(subject, version)
        if not schema:
            return False, ["Schema not found"]
        
        errors = []
        
        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        properties = schema.get("properties", {})
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if not self._check_type(value, expected_type):
                    errors.append(f"Field {field}: expected {expected_type}")
        
        return len(errors) == 0, errors
    
    def _check_compatibility(self, old: dict, new: dict, mode: Compatibility) -> bool:
        """Check schema compatibility."""
        old_fields = set(old.get("properties", {}).keys())
        new_fields = set(new.get("properties", {}).keys())
        
        if mode == Compatibility.BACKWARD:
            # New schema can read old data
            return old_fields <= new_fields
        elif mode == Compatibility.FORWARD:
            # Old schema can read new data
            return new_fields <= old_fields
        elif mode == Compatibility.FULL:
            return old_fields == new_fields
        
        return True
    
    def _check_type(self, value: Any, expected: str | None) -> bool:
        """Check if value matches expected type."""
        if expected is None:
            return True
        
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        expected_type = type_map.get(expected)
        if expected_type:
            return isinstance(value, expected_type)
        
        return True
