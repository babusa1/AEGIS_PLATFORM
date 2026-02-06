"""
Immutable Audit Log Storage

HIPAA-compliant append-only audit logging with cryptographic integrity verification.
Prevents modification or deletion of audit records for medicolegal compliance.

Features:
- Append-only storage (no UPDATE/DELETE operations)
- Hash chain for integrity verification
- Database-level immutability enforcement
- Blockchain-style chaining for tamper detection
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import json
import structlog

from aegis.security.audit import AuditEvent, AuditEventType, AuditSeverity

logger = structlog.get_logger(__name__)


class ImmutableAuditLogger:
    """
    Immutable Audit Logger with append-only storage and hash chaining.
    
    Implements HIPAA-compliant audit logging where records cannot be
    modified or deleted once written.
    """
    
    def __init__(self, pool=None):
        """
        Initialize immutable audit logger.
        
        Args:
            pool: Database connection pool
        """
        self.pool = pool
        self._buffer: List[tuple] = []  # List of (event, record_hash, chain_hash, previous_hash)
        self._max_buffer = 100
        self._schema_ensured = False
    
    async def _ensure_schema(self):
        """Ensure immutable audit log schema exists."""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                # Create immutable audit log table (append-only)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS immutable_audit_log (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        sequence_number BIGSERIAL NOT NULL,
                        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                        
                        -- Event data
                        event_type VARCHAR(100) NOT NULL,
                        severity VARCHAR(50) NOT NULL,
                        user_id VARCHAR(255),
                        tenant_id VARCHAR(100),
                        action VARCHAR(255) NOT NULL,
                        resource_type VARCHAR(100),
                        resource_id VARCHAR(255),
                        ip_address VARCHAR(45),
                        session_id VARCHAR(255),
                        details JSONB NOT NULL DEFAULT '{}',
                        success BOOLEAN NOT NULL DEFAULT true,
                        error_message TEXT,
                        contains_phi BOOLEAN NOT NULL DEFAULT false,
                        phi_types TEXT[] DEFAULT '{}',
                        
                        -- Integrity fields
                        previous_hash VARCHAR(64),  -- Hash of previous record
                        record_hash VARCHAR(64) NOT NULL,  -- Hash of this record
                        chain_hash VARCHAR(64) NOT NULL,  -- Cumulative hash chain
                        
                        -- Metadata
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        
                        -- Constraints
                        CONSTRAINT immutable_audit_log_sequence_unique UNIQUE (sequence_number),
                        CONSTRAINT immutable_audit_log_hash_unique UNIQUE (record_hash)
                    );
                    
                    -- Create index for hash chain verification
                    CREATE INDEX IF NOT EXISTS idx_immutable_audit_sequence 
                        ON immutable_audit_log(sequence_number);
                    
                    CREATE INDEX IF NOT EXISTS idx_immutable_audit_chain_hash 
                        ON immutable_audit_log(chain_hash);
                    
                    CREATE INDEX IF NOT EXISTS idx_immutable_audit_timestamp 
                        ON immutable_audit_log(timestamp DESC);
                    
                    CREATE INDEX IF NOT EXISTS idx_immutable_audit_user 
                        ON immutable_audit_log(user_id, timestamp DESC);
                    
                    CREATE INDEX IF NOT EXISTS idx_immutable_audit_resource 
                        ON immutable_audit_log(resource_type, resource_id, timestamp DESC);
                    
                    -- Prevent UPDATE/DELETE operations (immutability enforcement)
                    CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        RAISE EXCEPTION 'Immutable audit log: UPDATE and DELETE operations are not allowed';
                    END;
                    $$ LANGUAGE plpgsql;
                    
                    DROP TRIGGER IF EXISTS immutable_audit_log_prevent_update ON immutable_audit_log;
                    CREATE TRIGGER immutable_audit_log_prevent_update
                        BEFORE UPDATE OR DELETE ON immutable_audit_log
                        FOR EACH ROW
                        EXECUTE FUNCTION prevent_audit_log_modification();
                """)
                logger.info("Immutable audit log schema ensured")
                
        except Exception as e:
            logger.error(f"Failed to ensure immutable audit schema: {e}")
    
    def _calculate_record_hash(self, event: AuditEvent, previous_hash: Optional[str] = None) -> str:
        """
        Calculate SHA-256 hash of audit record.
        
        Includes:
        - All event fields
        - Previous hash (for chaining)
        - Timestamp
        """
        # Create deterministic JSON representation
        record_data = {
            "id": str(event.id),
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "user_id": event.user_id,
            "tenant_id": event.tenant_id,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "ip_address": event.ip_address,
            "session_id": event.session_id,
            "details": event.details,
            "success": event.success,
            "error_message": event.error_message,
            "contains_phi": event.contains_phi,
            "phi_types": event.phi_types,
            "previous_hash": previous_hash or "",
        }
        
        # Serialize and hash
        record_json = json.dumps(record_data, sort_keys=True, default=str)
        return hashlib.sha256(record_json.encode()).hexdigest()
    
    def _calculate_chain_hash(self, record_hash: str, previous_chain_hash: Optional[str] = None) -> str:
        """
        Calculate cumulative chain hash (blockchain-style).
        
        Chain hash = SHA256(record_hash + previous_chain_hash)
        """
        if previous_chain_hash:
            chain_data = f"{record_hash}{previous_chain_hash}"
        else:
            chain_data = record_hash
        
        return hashlib.sha256(chain_data.encode()).hexdigest()
    
    async def _get_last_chain_hash(self) -> Optional[str]:
        """Get the chain hash of the last record in the audit log."""
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT chain_hash 
                    FROM immutable_audit_log 
                    ORDER BY sequence_number DESC 
                    LIMIT 1
                """)
                return row["chain_hash"] if row else None
        except Exception as e:
            logger.error(f"Failed to get last chain hash: {e}")
            return None
    
    async def log(self, event: AuditEvent) -> str:
        """
        Log an audit event to immutable storage.
        
        Returns the event ID.
        """
        # Ensure schema exists
        if not self._schema_ensured and self.pool:
            await self._ensure_schema()
            self._schema_ensured = True
        
        # Get previous chain hash for linking
        previous_chain_hash = await self._get_last_chain_hash()
        
        # Calculate hashes
        previous_hash = previous_chain_hash  # Use chain hash as previous hash
        record_hash = self._calculate_record_hash(event, previous_hash)
        chain_hash = self._calculate_chain_hash(record_hash, previous_chain_hash)
        
        # Buffer for batch insert
        self._buffer.append((event, record_hash, chain_hash, previous_hash))
        
        # Flush if buffer is full
        if len(self._buffer) >= self._max_buffer:
            await self.flush()
        
        return event.id
    
    async def flush(self):
        """Flush buffer to immutable audit log."""
        if not self._buffer or not self.pool:
            return
        
        events_to_flush = self._buffer.copy()
        self._buffer.clear()
        
        try:
            async with self.pool.acquire() as conn:
                for event, record_hash, chain_hash, previous_hash in events_to_flush:
                    await conn.execute("""
                        INSERT INTO immutable_audit_log (
                            id, timestamp, event_type, severity,
                            user_id, tenant_id, action,
                            resource_type, resource_id,
                            ip_address, session_id,
                            details, success, error_message,
                            contains_phi, phi_types,
                            previous_hash, record_hash, chain_hash
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                    """,
                        event.id,
                        event.timestamp,
                        event.event_type.value,
                        event.severity.value,
                        event.user_id,
                        event.tenant_id,
                        event.action,
                        event.resource_type,
                        event.resource_id,
                        event.ip_address,
                        event.session_id,
                        json.dumps(event.details),
                        event.success,
                        event.error_message,
                        event.contains_phi,
                        event.phi_types,
                        previous_hash,
                        record_hash,
                        chain_hash,
                    )
            
            logger.debug(f"Flushed {len(events_to_flush)} events to immutable audit log")
            
        except Exception as e:
            logger.error(f"Failed to flush immutable audit events: {e}")
            # Re-add to buffer
            self._buffer.extend(events_to_flush)
    
    async def verify_integrity(self, start_sequence: Optional[int] = None, end_sequence: Optional[int] = None) -> Dict[str, Any]:
        """
        Verify integrity of audit log hash chain.
        
        Returns:
            Dict with verification results and any detected tampering
        """
        if not self.pool:
            return {
                "verified": False,
                "error": "Database pool not available",
                "tampered_records": [],
            }
        
        try:
            async with self.pool.acquire() as conn:
                # Get records in sequence order
                query = "SELECT * FROM immutable_audit_log WHERE 1=1"
                params = []
                
                if start_sequence:
                    query += f" AND sequence_number >= ${len(params) + 1}"
                    params.append(start_sequence)
                
                if end_sequence:
                    query += f" AND sequence_number <= ${len(params) + 1}"
                    params.append(end_sequence)
                
                query += " ORDER BY sequence_number ASC"
                
                rows = await conn.fetch(query, *params)
                
                if not rows:
                    return {
                        "verified": True,
                        "total_records": 0,
                        "tampered_records": [],
                    }
                
                tampered_records = []
                previous_chain_hash = None
                
                for i, row in enumerate(rows):
                    # Reconstruct event for hash calculation
                    event = AuditEvent(
                        id=row["id"],
                        timestamp=row["timestamp"],
                        event_type=AuditEventType(row["event_type"]),
                        severity=AuditSeverity(row["severity"]),
                        user_id=row["user_id"],
                        tenant_id=row["tenant_id"],
                        action=row["action"],
                        resource_type=row["resource_type"],
                        resource_id=row["resource_id"],
                        ip_address=row["ip_address"],
                        session_id=row["session_id"],
                        details=json.loads(row["details"]) if row["details"] else {},
                        success=row["success"],
                        error_message=row["error_message"],
                        contains_phi=row["contains_phi"],
                        phi_types=row.get("phi_types", []),
                    )
                    
                    # Calculate expected hashes
                    expected_record_hash = self._calculate_record_hash(event, row["previous_hash"])
                    expected_chain_hash = self._calculate_chain_hash(expected_record_hash, previous_chain_hash)
                    
                    # Verify
                    if expected_record_hash != row["record_hash"]:
                        tampered_records.append({
                            "sequence_number": row["sequence_number"],
                            "id": str(row["id"]),
                            "issue": "record_hash_mismatch",
                            "expected": expected_record_hash,
                            "actual": row["record_hash"],
                        })
                    
                    if expected_chain_hash != row["chain_hash"]:
                        tampered_records.append({
                            "sequence_number": row["sequence_number"],
                            "id": str(row["id"]),
                            "issue": "chain_hash_mismatch",
                            "expected": expected_chain_hash,
                            "actual": row["chain_hash"],
                        })
                    
                    previous_chain_hash = row["chain_hash"]
                
                return {
                    "verified": len(tampered_records) == 0,
                    "total_records": len(rows),
                    "tampered_records": tampered_records,
                    "last_chain_hash": previous_chain_hash,
                }
                
        except Exception as e:
            logger.error(f"Failed to verify audit log integrity: {e}")
            return {
                "verified": False,
                "error": str(e),
                "tampered_records": [],
            }
    
    async def get_events(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        Query immutable audit events (read-only).
        
        Note: This is read-only - records cannot be modified or deleted.
        """
        if not self.pool:
            return []
        
        query = "SELECT * FROM immutable_audit_log WHERE 1=1"
        params = []
        param_idx = 1
        
        if user_id:
            query += f" AND user_id = ${param_idx}"
            params.append(user_id)
            param_idx += 1
        
        if resource_type:
            query += f" AND resource_type = ${param_idx}"
            params.append(resource_type)
            param_idx += 1
        
        if resource_id:
            query += f" AND resource_id = ${param_idx}"
            params.append(resource_id)
            param_idx += 1
        
        if event_type:
            query += f" AND event_type = ${param_idx}"
            params.append(event_type.value)
            param_idx += 1
        
        if start_time:
            query += f" AND timestamp >= ${param_idx}"
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            query += f" AND timestamp <= ${param_idx}"
            params.append(end_time)
            param_idx += 1
        
        query += f" ORDER BY sequence_number DESC LIMIT ${param_idx}"
        params.append(limit)
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
            
            return [
                AuditEvent(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    event_type=AuditEventType(row["event_type"]),
                    severity=AuditSeverity(row["severity"]),
                    user_id=row["user_id"],
                    tenant_id=row["tenant_id"],
                    action=row["action"],
                    resource_type=row["resource_type"],
                    resource_id=row["resource_id"],
                    ip_address=row["ip_address"],
                    session_id=row["session_id"],
                    details=json.loads(row["details"]) if row["details"] else {},
                    success=row["success"],
                    error_message=row["error_message"],
                    contains_phi=row["contains_phi"],
                    phi_types=row.get("phi_types", []),
                )
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to query immutable audit events: {e}")
            return []


# Global instance
_immutable_audit_logger: Optional[ImmutableAuditLogger] = None


def get_immutable_audit_logger(pool=None) -> ImmutableAuditLogger:
    """Get global immutable audit logger instance."""
    global _immutable_audit_logger
    if _immutable_audit_logger is None:
        _immutable_audit_logger = ImmutableAuditLogger(pool=pool)
    return _immutable_audit_logger


def configure_immutable_audit_logger(pool=None) -> ImmutableAuditLogger:
    """Configure global immutable audit logger."""
    global _immutable_audit_logger
    _immutable_audit_logger = ImmutableAuditLogger(pool=pool)
    return _immutable_audit_logger
