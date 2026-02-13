"""
Generic Entity Query API Routes

REST endpoints for querying any entity type in the Data Moat.
Supports all 30+ entity types with unified query interface.
"""

from typing import Any, Optional, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from aegis.api.auth import TenantContext, get_tenant_context
from aegis.agents.data_tools import DataMoatTools
from aegis.agents.entity_registry import EntityType, list_all_entity_types, get_entity_count

router = APIRouter(prefix="/entities", tags=["Entities"])


async def get_data_moat_tools(request: Request, tenant_context: TenantContext = Depends(get_tenant_context)) -> DataMoatTools:
    """
    Get DataMoatTools instance with database pool.
    """
    pool = None
    if hasattr(request.app.state, "db") and request.app.state.db:
        pool = getattr(request.app.state.db, "postgres", None)
    
    return DataMoatTools(pool=pool, tenant_id=tenant_context.tenant_id)


# =============================================================================
# Response Models
# =============================================================================

class EntityResponse(BaseModel):
    """Single entity response."""
    entity_type: str
    entity_id: str
    data: Dict[str, Any]


class EntityListResponse(BaseModel):
    """List of entities response."""
    entity_type: str
    entities: list[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    has_more: bool


class EntityRegistryResponse(BaseModel):
    """Entity registry response."""
    total_entity_types: int
    entities: list[Dict[str, Any]]
    description: str


class TimeFilter(BaseModel):
    """Time filter for time-series queries."""
    time: Optional[str] = Field(None, description="Specific timestamp for get_entity_by_id")
    start_time: Optional[str] = Field(None, description="Start time for list_entities")
    end_time: Optional[str] = Field(None, description="End time for list_entities")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/registry", response_model=EntityRegistryResponse)
async def get_entity_registry(
    tools: DataMoatTools = Depends(get_data_moat_tools),
):
    """
    Get the Data Moat entity registry.
    
    Returns all 30+ entity types available for querying.
    """
    registry = await tools.get_entity_registry()
    return registry


@router.get("/{entity_type}/{entity_id}", response_model=EntityResponse)
async def get_entity_by_id(
    entity_type: str,
    entity_id: str,
    time: Optional[str] = Query(None, description="Timestamp for time-series entities (ISO format)"),
    tools: DataMoatTools = Depends(get_data_moat_tools),
):
    """
    Get a single entity by type and ID.
    
    Supports all 30+ entity types:
    - Regular entities: patient, condition, claim, denial, etc.
    - Time-series entities: vital, lab_result, wearable_metric (requires time parameter)
    
    Examples:
    - GET /entities/patient/patient-123
    - GET /entities/vital/patient-123?time=2024-01-01T00:00:00Z
    """
    # Validate entity type
    try:
        EntityType(entity_type.lower())
    except ValueError:
        available = [e.value for e in EntityType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown entity type: {entity_type}. Available types: {available}",
        )
    
    # Prepare time filter for time-series entities
    time_filter = None
    if time:
        time_filter = {"time": time}
    
    result = await tools.get_entity_by_id(
        entity_type=entity_type,
        entity_id=entity_id,
        time_filter=time_filter,
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in result["error"].lower() else status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )
    
    return EntityResponse(**result)


@router.get("/{entity_type}", response_model=EntityListResponse)
async def list_entities(
    entity_type: str,
    filters: Optional[str] = Query(None, description="JSON string of filters: {\"column\": \"value\"}"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    start_time: Optional[str] = Query(None, description="Start time for time-series queries (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time for time-series queries (ISO format)"),
    tools: DataMoatTools = Depends(get_data_moat_tools),
):
    """
    List entities by type with optional filters.
    
    Supports all 30+ entity types with filtering, pagination, and time-range queries.
    
    Examples:
    - GET /entities/patient?limit=10&offset=0
    - GET /entities/claim?filters={"status":"denied"}
    - GET /entities/vital?start_time=2024-01-01T00:00:00Z&end_time=2024-01-31T23:59:59Z
    """
    # Validate entity type
    try:
        EntityType(entity_type.lower())
    except ValueError:
        available = [e.value for e in EntityType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown entity type: {entity_type}. Available types: {available}",
        )
    
    # Parse filters JSON
    filter_dict = None
    if filters:
        try:
            import json
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filters JSON format",
            )
    
    # Prepare time range for time-series entities
    time_range = None
    if start_time or end_time:
        time_range = {}
        if start_time:
            time_range["start_time"] = start_time
        if end_time:
            time_range["end_time"] = end_time
    
    result = await tools.list_entities(
        entity_type=entity_type,
        filters=filter_dict,
        limit=limit,
        offset=offset,
        time_range=time_range,
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )
    
    return EntityListResponse(**result)
