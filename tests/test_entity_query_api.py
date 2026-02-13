"""
Tests for Generic Entity Query API

Tests the unified entity query interface for all 30+ entity types.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from aegis.agents.data_tools import DataMoatTools
from aegis.agents.entity_registry import EntityType, ENTITY_METADATA, get_entity_metadata


class TestEntityRegistry:
    """Test entity registry functionality."""
    
    def test_all_entity_types_have_metadata(self):
        """Test that all EntityType enum values have metadata."""
        for entity_type in EntityType:
            metadata = get_entity_metadata(entity_type)
            assert metadata is not None, f"Missing metadata for {entity_type.value}"
            assert "table" in metadata, f"Missing table for {entity_type.value}"
            assert "description" in metadata, f"Missing description for {entity_type.value}"
    
    def test_entity_count_matches_enum(self):
        """Test that entity count matches number of enum values."""
        from aegis.agents.entity_registry import get_entity_count, list_all_entity_types
        
        enum_count = len(EntityType)
        metadata_count = get_entity_count()
        list_count = len(list_all_entity_types())
        
        assert metadata_count == enum_count, f"Metadata count ({metadata_count}) != enum count ({enum_count})"
        assert list_count == enum_count, f"List count ({list_count}) != enum count ({enum_count})"
    
    def test_time_series_entities_have_time_column(self):
        """Test that time-series entities have time_column defined."""
        time_series_types = [EntityType.VITAL, EntityType.LAB_RESULT, EntityType.WEARABLE_METRIC]
        
        for entity_type in time_series_types:
            metadata = get_entity_metadata(entity_type)
            assert metadata.get("time_column") is not None, f"Missing time_column for {entity_type.value}"
            assert metadata.get("primary_key") is None, f"Time-series entity {entity_type.value} should not have primary_key"


class TestDataMoatTools:
    """Test DataMoatTools generic entity query methods."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool."""
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire = AsyncMock(return_value=conn.__aenter__())
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        return pool
    
    @pytest.fixture
    def tools(self, mock_pool):
        """Create DataMoatTools instance with mock pool."""
        return DataMoatTools(pool=mock_pool, tenant_id="test-tenant")
    
    @pytest.mark.asyncio
    async def test_get_entity_by_id_success(self, tools, mock_pool):
        """Test successful get_entity_by_id for regular entity."""
        conn = await mock_pool.acquire()
        mock_row = {
            "id": "patient-123",
            "mrn": "MRN001",
            "given_name": "John",
            "family_name": "Doe",
        }
        conn.fetchrow = AsyncMock(return_value=mock_row)
        
        result = await tools.get_entity_by_id("patient", "patient-123")
        
        assert "error" not in result
        assert result["entity_type"] == "patient"
        assert result["entity_id"] == "patient-123"
        assert result["data"]["id"] == "patient-123"
    
    @pytest.mark.asyncio
    async def test_get_entity_by_id_not_found(self, tools, mock_pool):
        """Test get_entity_by_id when entity not found."""
        conn = await mock_pool.acquire()
        conn.fetchrow = AsyncMock(return_value=None)
        
        result = await tools.get_entity_by_id("patient", "nonexistent")
        
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_entity_by_id_invalid_type(self, tools):
        """Test get_entity_by_id with invalid entity type."""
        result = await tools.get_entity_by_id("invalid_type", "id-123")
        
        assert "error" in result
        assert "unknown entity type" in result["error"].lower()
        assert "available_types" in result
    
    @pytest.mark.asyncio
    async def test_get_entity_by_id_time_series_without_time(self, tools):
        """Test get_entity_by_id for time-series entity without time filter."""
        result = await tools.get_entity_by_id("vital", "patient-123")
        
        assert "error" in result
        assert "time_filter" in result["error"].lower() or "time" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_entity_by_id_time_series_with_time(self, tools, mock_pool):
        """Test get_entity_by_id for time-series entity with time filter."""
        conn = await mock_pool.acquire()
        mock_row = {
            "patient_id": "patient-123",
            "vital_type": "blood_pressure",
            "value": 120.0,
            "time": datetime(2024, 1, 1, 12, 0, 0),
        }
        conn.fetchrow = AsyncMock(return_value=mock_row)
        
        result = await tools.get_entity_by_id(
            "vital",
            "patient-123",
            time_filter={"time": "2024-01-01T12:00:00Z"}
        )
        
        assert "error" not in result
        assert result["entity_type"] == "vital"
    
    @pytest.mark.asyncio
    async def test_list_entities_success(self, tools, mock_pool):
        """Test successful list_entities."""
        conn = await mock_pool.acquire()
        mock_rows = [
            {"id": "patient-1", "mrn": "MRN001", "given_name": "John"},
            {"id": "patient-2", "mrn": "MRN002", "given_name": "Jane"},
        ]
        conn.fetch = AsyncMock(return_value=mock_rows)
        conn.fetchrow = AsyncMock(return_value={"total": 2})
        
        result = await tools.list_entities("patient", limit=10, offset=0)
        
        assert "error" not in result
        assert result["entity_type"] == "patient"
        assert len(result["entities"]) == 2
        assert result["total"] == 2
    
    @pytest.mark.asyncio
    async def test_list_entities_with_filters(self, tools, mock_pool):
        """Test list_entities with filters."""
        conn = await mock_pool.acquire()
        mock_rows = [{"id": "claim-1", "status": "denied"}]
        conn.fetch = AsyncMock(return_value=mock_rows)
        conn.fetchrow = AsyncMock(return_value={"total": 1})
        
        # Mock column info for filter validation
        conn.fetch = AsyncMock(side_effect=[
            [{"column_name": "id"}, {"column_name": "status"}, {"column_name": "tenant_id"}],  # Column info
            mock_rows,  # Actual query result
        ])
        
        result = await tools.list_entities("claim", filters={"status": "denied"})
        
        assert "error" not in result
        assert result["entity_type"] == "claim"
    
    @pytest.mark.asyncio
    async def test_list_entities_with_time_range(self, tools, mock_pool):
        """Test list_entities with time range for time-series entity."""
        conn = await mock_pool.acquire()
        mock_rows = [
            {"patient_id": "patient-123", "vital_type": "bp", "time": datetime(2024, 1, 1, 12, 0, 0)},
        ]
        
        # Mock column info
        conn.fetch = AsyncMock(side_effect=[
            [{"column_name": "patient_id"}, {"column_name": "time"}, {"column_name": "tenant_id"}],
            mock_rows,
        ])
        conn.fetchrow = AsyncMock(return_value={"total": 1})
        
        result = await tools.list_entities(
            "vital",
            time_range={"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-01-31T23:59:59Z"}
        )
        
        assert "error" not in result
        assert result["entity_type"] == "vital"
    
    @pytest.mark.asyncio
    async def test_list_entities_invalid_filter_column(self, tools, mock_pool):
        """Test list_entities with invalid filter column name."""
        conn = await mock_pool.acquire()
        
        # Mock column info (only valid columns)
        conn.fetch = AsyncMock(side_effect=[
            [{"column_name": "id"}, {"column_name": "tenant_id"}],  # Valid columns only
            [],  # No results
        ])
        conn.fetchrow = AsyncMock(return_value={"total": 0})
        
        # Invalid column name should be ignored
        result = await tools.list_entities("patient", filters={"invalid_column": "value"})
        
        # Should not error, but invalid filter is ignored
        assert "error" not in result
    
    @pytest.mark.asyncio
    async def test_get_entity_registry(self, tools):
        """Test get_entity_registry returns all entity types."""
        result = await tools.get_entity_registry()
        
        assert "total_entity_types" in result
        assert "entities" in result
        assert "description" in result
        assert result["total_entity_types"] > 30
        assert len(result["entities"]) == result["total_entity_types"]


class TestSQLInjectionProtection:
    """Test SQL injection protection."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool."""
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire = AsyncMock(return_value=conn.__aenter__())
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        return pool
    
    @pytest.mark.asyncio
    async def test_table_name_whitelist(self):
        """Test that table names are validated against whitelist."""
        tools = DataMoatTools(pool=None, tenant_id="test")
        
        # Try to inject malicious table name
        # This should fail because table name comes from metadata whitelist
        result = await tools.get_entity_by_id("patient", "id-123")
        
        # Should fail gracefully (no pool), not with SQL error
        assert "error" in result
        assert "database not available" in result["error"].lower() or "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_column_name_validation(self, mock_pool):
        """Test that filter column names are validated."""
        tools = DataMoatTools(pool=mock_pool, tenant_id="test")
        conn = await mock_pool.acquire()
        
        # Mock column info to only return safe columns
        conn.fetch = AsyncMock(side_effect=[
            [{"column_name": "id"}, {"column_name": "tenant_id"}],  # Only safe columns
            [],  # Query result
        ])
        conn.fetchrow = AsyncMock(return_value={"total": 0})
        
        # Try SQL injection in column name
        result = await tools.list_entities(
            "patient",
            filters={"'; DROP TABLE patients; --": "value"}
        )
        
        # Should not execute SQL injection - invalid column is ignored
        assert "error" not in result or "database not available" in result.get("error", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
