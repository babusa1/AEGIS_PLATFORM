"""
AEGIS Workflow Versioning

Version control for workflow definitions with rollback support.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from enum import Enum
import copy
import uuid
import json
import hashlib
import structlog

logger = structlog.get_logger(__name__)


class VersionStatus(str, Enum):
    """Status of a workflow version."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class WorkflowVersion:
    """A specific version of a workflow definition."""
    id: str
    workflow_id: str
    version_number: int
    status: VersionStatus
    definition: dict[str, Any]
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    comment: str = ""
    
    # Change tracking
    changes_from_previous: list[str] = field(default_factory=list)
    checksum: str = ""
    
    # Activation
    activated_at: datetime | None = None
    activated_by: str | None = None


@dataclass 
class VersionDiff:
    """Differences between two workflow versions."""
    version_a: int
    version_b: int
    added_nodes: list[str] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    modified_nodes: list[str] = field(default_factory=list)
    added_edges: list[str] = field(default_factory=list)
    removed_edges: list[str] = field(default_factory=list)
    config_changes: dict[str, Any] = field(default_factory=dict)


class WorkflowVersionManager:
    """
    Manages workflow definition versions.
    
    Features:
    - Create new versions
    - Track changes between versions
    - Rollback to previous versions
    - Compare versions
    - Version activation control
    """
    
    def __init__(self):
        # Storage: workflow_id -> list of versions
        self._versions: dict[str, list[WorkflowVersion]] = {}
        self._active_versions: dict[str, int] = {}  # workflow_id -> version_number
    
    def _compute_checksum(self, definition: dict) -> str:
        """Compute a checksum for a workflow definition."""
        content = json.dumps(definition, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _compute_changes(
        self,
        old_def: dict | None,
        new_def: dict,
    ) -> list[str]:
        """Compute list of changes between definitions."""
        if old_def is None:
            return ["Initial version"]
        
        changes = []
        
        # Compare nodes
        old_nodes = {n.get("id"): n for n in old_def.get("nodes", [])}
        new_nodes = {n.get("id"): n for n in new_def.get("nodes", [])}
        
        for node_id in set(new_nodes.keys()) - set(old_nodes.keys()):
            changes.append(f"Added node: {node_id}")
        
        for node_id in set(old_nodes.keys()) - set(new_nodes.keys()):
            changes.append(f"Removed node: {node_id}")
        
        for node_id in set(old_nodes.keys()) & set(new_nodes.keys()):
            if old_nodes[node_id] != new_nodes[node_id]:
                changes.append(f"Modified node: {node_id}")
        
        # Compare edges
        old_edges = set(
            f"{e.get('source')}->{e.get('target')}"
            for e in old_def.get("edges", [])
        )
        new_edges = set(
            f"{e.get('source')}->{e.get('target')}"
            for e in new_def.get("edges", [])
        )
        
        for edge in new_edges - old_edges:
            changes.append(f"Added edge: {edge}")
        
        for edge in old_edges - new_edges:
            changes.append(f"Removed edge: {edge}")
        
        # Compare config
        old_config = old_def.get("config", {})
        new_config = new_def.get("config", {})
        
        if old_config != new_config:
            changes.append("Configuration changed")
        
        return changes or ["No significant changes"]
    
    def create_version(
        self,
        workflow_id: str,
        definition: dict[str, Any],
        created_by: str = "system",
        comment: str = "",
        auto_activate: bool = False,
    ) -> WorkflowVersion:
        """
        Create a new version of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            definition: The workflow definition
            created_by: User who created this version
            comment: Version comment/description
            auto_activate: Whether to activate this version immediately
        
        Returns:
            WorkflowVersion
        """
        # Get existing versions
        versions = self._versions.get(workflow_id, [])
        
        # Determine version number
        if versions:
            version_number = max(v.version_number for v in versions) + 1
            previous_def = versions[-1].definition
        else:
            version_number = 1
            previous_def = None
        
        # Create version
        version_id = str(uuid.uuid4())
        checksum = self._compute_checksum(definition)
        changes = self._compute_changes(previous_def, definition)
        
        version = WorkflowVersion(
            id=version_id,
            workflow_id=workflow_id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            definition=copy.deepcopy(definition),
            created_by=created_by,
            comment=comment,
            changes_from_previous=changes,
            checksum=checksum,
        )
        
        # Store version
        if workflow_id not in self._versions:
            self._versions[workflow_id] = []
        self._versions[workflow_id].append(version)
        
        logger.info(
            "Created workflow version",
            workflow_id=workflow_id,
            version=version_number,
            changes=len(changes),
        )
        
        # Auto-activate if requested
        if auto_activate:
            self.activate_version(workflow_id, version_number, created_by)
        
        return version
    
    def activate_version(
        self,
        workflow_id: str,
        version_number: int,
        activated_by: str = "system",
    ) -> WorkflowVersion:
        """
        Activate a specific version of a workflow.
        
        This marks the version as the current active version.
        Previous active version is deprecated.
        
        Args:
            workflow_id: ID of the workflow
            version_number: Version to activate
            activated_by: User activating the version
        
        Returns:
            Activated WorkflowVersion
        """
        versions = self._versions.get(workflow_id, [])
        
        target_version = None
        for version in versions:
            # Deprecate current active version
            if version.status == VersionStatus.ACTIVE:
                version.status = VersionStatus.DEPRECATED
            
            # Find target version
            if version.version_number == version_number:
                target_version = version
        
        if target_version is None:
            raise ValueError(f"Version {version_number} not found for workflow {workflow_id}")
        
        # Activate the target version
        target_version.status = VersionStatus.ACTIVE
        target_version.activated_at = datetime.now(timezone.utc)
        target_version.activated_by = activated_by
        
        self._active_versions[workflow_id] = version_number
        
        logger.info(
            "Activated workflow version",
            workflow_id=workflow_id,
            version=version_number,
            activated_by=activated_by,
        )
        
        return target_version
    
    def rollback(
        self,
        workflow_id: str,
        target_version: int,
        rolled_back_by: str = "system",
    ) -> WorkflowVersion:
        """
        Rollback to a previous version.
        
        This activates the target version and creates a new version
        with the same definition for audit trail.
        
        Args:
            workflow_id: ID of the workflow
            target_version: Version number to rollback to
            rolled_back_by: User performing the rollback
        
        Returns:
            New WorkflowVersion (copy of target)
        """
        versions = self._versions.get(workflow_id, [])
        
        # Find target version
        target = None
        for version in versions:
            if version.version_number == target_version:
                target = version
                break
        
        if target is None:
            raise ValueError(f"Version {target_version} not found for workflow {workflow_id}")
        
        # Create new version with the old definition
        new_version = self.create_version(
            workflow_id=workflow_id,
            definition=target.definition,
            created_by=rolled_back_by,
            comment=f"Rollback to version {target_version}",
            auto_activate=True,
        )
        
        logger.info(
            "Rolled back workflow",
            workflow_id=workflow_id,
            from_version=self._active_versions.get(workflow_id),
            to_version=target_version,
            new_version=new_version.version_number,
        )
        
        return new_version
    
    def get_version(
        self,
        workflow_id: str,
        version_number: int | None = None,
    ) -> WorkflowVersion | None:
        """
        Get a specific version or the active version.
        
        Args:
            workflow_id: ID of the workflow
            version_number: Specific version (None = active)
        
        Returns:
            WorkflowVersion or None
        """
        versions = self._versions.get(workflow_id, [])
        
        if not versions:
            return None
        
        if version_number is None:
            # Return active version
            for version in versions:
                if version.status == VersionStatus.ACTIVE:
                    return version
            # Fallback to latest
            return versions[-1]
        
        # Find specific version
        for version in versions:
            if version.version_number == version_number:
                return version
        
        return None
    
    def get_active_definition(self, workflow_id: str) -> dict | None:
        """Get the active workflow definition."""
        version = self.get_version(workflow_id)
        return version.definition if version else None
    
    def list_versions(
        self,
        workflow_id: str,
        include_archived: bool = False,
    ) -> list[WorkflowVersion]:
        """
        List all versions of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            include_archived: Whether to include archived versions
        
        Returns:
            List of WorkflowVersions (newest first)
        """
        versions = self._versions.get(workflow_id, [])
        
        if not include_archived:
            versions = [v for v in versions if v.status != VersionStatus.ARCHIVED]
        
        return sorted(versions, key=lambda v: v.version_number, reverse=True)
    
    def compare_versions(
        self,
        workflow_id: str,
        version_a: int,
        version_b: int,
    ) -> VersionDiff:
        """
        Compare two versions of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            version_a: First version number
            version_b: Second version number
        
        Returns:
            VersionDiff with detailed changes
        """
        va = self.get_version(workflow_id, version_a)
        vb = self.get_version(workflow_id, version_b)
        
        if va is None or vb is None:
            raise ValueError("One or both versions not found")
        
        diff = VersionDiff(version_a=version_a, version_b=version_b)
        
        # Compare nodes
        nodes_a = {n.get("id"): n for n in va.definition.get("nodes", [])}
        nodes_b = {n.get("id"): n for n in vb.definition.get("nodes", [])}
        
        diff.added_nodes = list(set(nodes_b.keys()) - set(nodes_a.keys()))
        diff.removed_nodes = list(set(nodes_a.keys()) - set(nodes_b.keys()))
        diff.modified_nodes = [
            node_id for node_id in set(nodes_a.keys()) & set(nodes_b.keys())
            if nodes_a[node_id] != nodes_b[node_id]
        ]
        
        # Compare edges
        edges_a = set(
            f"{e.get('source')}->{e.get('target')}"
            for e in va.definition.get("edges", [])
        )
        edges_b = set(
            f"{e.get('source')}->{e.get('target')}"
            for e in vb.definition.get("edges", [])
        )
        
        diff.added_edges = list(edges_b - edges_a)
        diff.removed_edges = list(edges_a - edges_b)
        
        # Compare config
        config_a = va.definition.get("config", {})
        config_b = vb.definition.get("config", {})
        
        all_keys = set(config_a.keys()) | set(config_b.keys())
        for key in all_keys:
            val_a = config_a.get(key)
            val_b = config_b.get(key)
            if val_a != val_b:
                diff.config_changes[key] = {"from": val_a, "to": val_b}
        
        return diff
    
    def archive_version(
        self,
        workflow_id: str,
        version_number: int,
    ) -> bool:
        """Archive a version (cannot be undone easily)."""
        version = self.get_version(workflow_id, version_number)
        
        if version is None:
            return False
        
        if version.status == VersionStatus.ACTIVE:
            raise ValueError("Cannot archive active version")
        
        version.status = VersionStatus.ARCHIVED
        logger.info(
            "Archived workflow version",
            workflow_id=workflow_id,
            version=version_number,
        )
        
        return True
    
    def get_version_history(
        self,
        workflow_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get version history for audit purposes.
        
        Returns summary of each version for display.
        """
        versions = self.list_versions(workflow_id, include_archived=True)[:limit]
        
        return [
            {
                "version": v.version_number,
                "status": v.status.value,
                "created_at": v.created_at.isoformat(),
                "created_by": v.created_by,
                "comment": v.comment,
                "changes": v.changes_from_previous,
                "checksum": v.checksum,
                "activated_at": v.activated_at.isoformat() if v.activated_at else None,
            }
            for v in versions
        ]


# =============================================================================
# Global Instance
# =============================================================================

_version_manager: WorkflowVersionManager | None = None


def get_version_manager() -> WorkflowVersionManager:
    """Get the global version manager instance."""
    global _version_manager
    if _version_manager is None:
        _version_manager = WorkflowVersionManager()
    return _version_manager
