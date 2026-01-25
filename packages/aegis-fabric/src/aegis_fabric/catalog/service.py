"""Data Catalog Service"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class DatasetType(str, Enum):
    TABLE = "table"
    VIEW = "view"
    STREAM = "stream"
    API = "api"
    FILE = "file"


@dataclass
class SchemaField:
    name: str
    data_type: str
    description: str = ""
    nullable: bool = True
    sensitivity: str = "internal"  # public, internal, confidential, restricted


@dataclass
class CatalogEntry:
    id: str
    name: str
    description: str
    dataset_type: DatasetType
    source_system: str
    schema_fields: list[SchemaField] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    owner: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    row_count: int | None = None
    sensitivity_level: str = "internal"


class DataCatalog:
    """
    Searchable data catalog with metadata.
    
    HITRUST 07.a: Asset inventory
    SOC 2: Data inventory and classification
    """
    
    def __init__(self):
        self._entries: dict[str, CatalogEntry] = {}
        self._tags_index: dict[str, list[str]] = {}
    
    def register(self, entry: CatalogEntry) -> str:
        """Register a dataset in the catalog."""
        self._entries[entry.id] = entry
        
        # Index by tags
        for tag in entry.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = []
            self._tags_index[tag].append(entry.id)
        
        logger.info("Dataset registered", id=entry.id, name=entry.name)
        return entry.id
    
    def get(self, entry_id: str) -> CatalogEntry | None:
        """Get a catalog entry by ID."""
        return self._entries.get(entry_id)
    
    def search(self, query: str, tags: list[str] | None = None,
              source_system: str | None = None) -> list[CatalogEntry]:
        """Search the catalog."""
        results = list(self._entries.values())
        query_lower = query.lower()
        
        # Filter by query
        if query:
            results = [e for e in results if 
                      query_lower in e.name.lower() or 
                      query_lower in e.description.lower()]
        
        # Filter by tags
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        
        # Filter by source
        if source_system:
            results = [e for e in results if e.source_system == source_system]
        
        return results
    
    def list_by_tag(self, tag: str) -> list[CatalogEntry]:
        """List entries by tag."""
        entry_ids = self._tags_index.get(tag, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]
    
    def list_by_sensitivity(self, level: str) -> list[CatalogEntry]:
        """List entries by sensitivity level."""
        return [e for e in self._entries.values() if e.sensitivity_level == level]
    
    def update_metadata(self, entry_id: str, metadata: dict):
        """Update entry metadata."""
        if entry_id in self._entries:
            self._entries[entry_id].metadata.update(metadata)
            self._entries[entry_id].updated_at = datetime.utcnow()
    
    def add_tag(self, entry_id: str, tag: str):
        """Add a tag to an entry."""
        if entry_id in self._entries:
            entry = self._entries[entry_id]
            if tag not in entry.tags:
                entry.tags.append(tag)
                if tag not in self._tags_index:
                    self._tags_index[tag] = []
                self._tags_index[tag].append(entry_id)
    
    def get_statistics(self) -> dict:
        """Get catalog statistics."""
        entries = list(self._entries.values())
        return {
            "total_datasets": len(entries),
            "by_type": {t.value: len([e for e in entries if e.dataset_type == t]) 
                       for t in DatasetType},
            "by_sensitivity": {},
            "total_tags": len(self._tags_index),
            "sources": list(set(e.source_system for e in entries))
        }
