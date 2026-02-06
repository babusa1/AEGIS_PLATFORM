"""
Expert-in-the-Loop Feedback System

Allows clinicians to verify terminology mappings once, creating permanent
Knowledge Base assets that improve future matching accuracy.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import structlog

from aegis.ingestion.normalization import CodeMapping

logger = structlog.get_logger(__name__)


@dataclass
class MappingVerification:
    """A verified mapping from expert feedback."""
    id: str
    local_code: str
    local_description: str
    standard_code: str
    standard_system: str
    standard_description: str
    verified_by: str  # User ID
    verified_at: datetime
    source_system: str
    confidence: float = 1.0  # Expert-verified = 1.0
    notes: Optional[str] = None


class MappingKnowledgeBase:
    """
    Knowledge Base for storing verified terminology mappings.
    
    Once a clinician verifies a mapping, it becomes a permanent asset
    that improves future matching accuracy.
    """
    
    def __init__(self, db_pool=None):
        """
        Initialize knowledge base.
        
        Args:
            db_pool: Database connection pool for storage
        """
        self.db_pool = db_pool
        self._cache: Dict[str, MappingVerification] = {}  # In-memory cache
    
    async def get_verified_mapping(
        self,
        local_code: str,
        source_system: str,
    ) -> Optional[CodeMapping]:
        """
        Get verified mapping from knowledge base.
        
        Args:
            local_code: Local code to look up
            source_system: Source system name
            
        Returns:
            CodeMapping if verified mapping exists
        """
        cache_key = f"{source_system}:{local_code}"
        
        # Check cache first
        if cache_key in self._cache:
            verification = self._cache[cache_key]
            return CodeMapping(
                local_code=verification.local_code,
                local_description=verification.local_description,
                standard_code=verification.standard_code,
                standard_system=verification.standard_system,
                standard_description=verification.standard_description,
                confidence=verification.confidence,
                mapping_method="expert_verified",
                verified_by=verification.verified_by,
                verified_at=verification.verified_at,
                source_system=verification.source_system,
            )
        
        # Query database if available
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT * FROM verified_code_mappings
                        WHERE local_code = $1 AND source_system = $2
                        ORDER BY verified_at DESC
                        LIMIT 1
                    """, local_code, source_system)
                    
                    if row:
                        verification = MappingVerification(
                            id=row['id'],
                            local_code=row['local_code'],
                            local_description=row['local_description'],
                            standard_code=row['standard_code'],
                            standard_system=row['standard_system'],
                            standard_description=row['standard_description'],
                            verified_by=row['verified_by'],
                            verified_at=row['verified_at'],
                            source_system=row['source_system'],
                            confidence=row.get('confidence', 1.0),
                            notes=row.get('notes'),
                        )
                        self._cache[cache_key] = verification
                        
                        return CodeMapping(
                            local_code=verification.local_code,
                            local_description=verification.local_description,
                            standard_code=verification.standard_code,
                            standard_system=verification.standard_system,
                            standard_description=verification.standard_description,
                            confidence=verification.confidence,
                            mapping_method="expert_verified",
                            verified_by=verification.verified_by,
                            verified_at=verification.verified_at,
                            source_system=verification.source_system,
                        )
            except Exception as e:
                logger.error("Failed to query knowledge base", error=str(e))
        
        return None
    
    async def verify_mapping(
        self,
        mapping: CodeMapping,
        verified_by: str,
        notes: Optional[str] = None,
    ) -> MappingVerification:
        """
        Store a verified mapping in the knowledge base.
        
        Args:
            mapping: CodeMapping to verify
            verified_by: User ID who verified
            notes: Optional notes about the verification
            
        Returns:
            MappingVerification stored
        """
        verification = MappingVerification(
            id=f"{mapping.source_system}:{mapping.local_code}:{datetime.utcnow().isoformat()}",
            local_code=mapping.local_code,
            local_description=mapping.local_description,
            standard_code=mapping.standard_code,
            standard_system=mapping.standard_system,
            standard_description=mapping.standard_description,
            verified_by=verified_by,
            verified_at=datetime.utcnow(),
            source_system=mapping.source_system or "unknown",
            confidence=1.0,  # Expert-verified = maximum confidence
            notes=notes,
        )
        
        # Store in cache
        cache_key = f"{verification.source_system}:{verification.local_code}"
        self._cache[cache_key] = verification
        
        # Store in database if available
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO verified_code_mappings (
                            id, local_code, local_description, standard_code,
                            standard_system, standard_description, verified_by,
                            verified_at, source_system, confidence, notes
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (local_code, source_system) 
                        DO UPDATE SET
                            standard_code = EXCLUDED.standard_code,
                            standard_description = EXCLUDED.standard_description,
                            verified_by = EXCLUDED.verified_by,
                            verified_at = EXCLUDED.verified_at,
                            confidence = EXCLUDED.confidence,
                            notes = EXCLUDED.notes
                    """,
                        verification.id,
                        verification.local_code,
                        verification.local_description,
                        verification.standard_code,
                        verification.standard_system,
                        verification.standard_description,
                        verification.verified_by,
                        verification.verified_at,
                        verification.source_system,
                        verification.confidence,
                        verification.notes,
                    )
                logger.info("Stored verified mapping in knowledge base", mapping_id=verification.id)
            except Exception as e:
                logger.error("Failed to store verified mapping", error=str(e))
        
        return verification
    
    async def list_verified_mappings(
        self,
        source_system: Optional[str] = None,
        verified_by: Optional[str] = None,
        limit: int = 100,
    ) -> List[MappingVerification]:
        """List verified mappings from knowledge base."""
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    query = "SELECT * FROM verified_code_mappings WHERE 1=1"
                    params = []
                    
                    if source_system:
                        query += " AND source_system = $" + str(len(params) + 1)
                        params.append(source_system)
                    
                    if verified_by:
                        query += " AND verified_by = $" + str(len(params) + 1)
                        params.append(verified_by)
                    
                    query += " ORDER BY verified_at DESC LIMIT $" + str(len(params) + 1)
                    params.append(limit)
                    
                    rows = await conn.fetch(query, *params)
                    return [
                        MappingVerification(
                            id=row['id'],
                            local_code=row['local_code'],
                            local_description=row['local_description'],
                            standard_code=row['standard_code'],
                            standard_system=row['standard_system'],
                            standard_description=row['standard_description'],
                            verified_by=row['verified_by'],
                            verified_at=row['verified_at'],
                            source_system=row['source_system'],
                            confidence=row.get('confidence', 1.0),
                            notes=row.get('notes'),
                        )
                        for row in rows
                    ]
            except Exception as e:
                logger.error("Failed to list verified mappings", error=str(e))
        
        return list(self._cache.values())[:limit]
