"""
Base Repository with Generic CRUD Operations.

This module provides a generic repository base class that:
- Implements common CRUD operations
- Provides type-safe generic interface
- Handles common error cases
- Supports pagination and filtering

All domain-specific repositories should inherit from BaseRepository.

Usage:
    class PatientRepository(BaseRepository[Patient]):
        def __init__(self, db: Session):
            super().__init__(Patient, db)
        
        # Add custom methods
        def find_by_email(self, email: str) -> Optional[Patient]:
            return self.db.query(Patient).filter_by(email=email).first()
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from db.base import Base
from core.exceptions import NotFoundException, DatabaseException
from core.logging import get_logger

logger = get_logger(__name__)

# Type variable for the model class
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository with CRUD operations.
    
    Provides a consistent interface for database operations
    across all entity types.
    
    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages
    
    Attributes:
        model: The model class
        db: Database session
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize the repository.
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db
    
    # =========================================================================
    # READ OPERATIONS
    # =========================================================================
    
    def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Get a single record by its UUID.
        
        Args:
            id: UUID of the record
        
        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter(
            self.model.uuid == id
        ).first()
    
    def get_by_id_or_raise(self, id: UUID) -> ModelType:
        """
        Get a single record by UUID, raising exception if not found.
        
        Args:
            id: UUID of the record
        
        Returns:
            Model instance
        
        Raises:
            NotFoundException: If record doesn't exist
        """
        instance = self.get_by_id(id)
        if instance is None:
            raise NotFoundException(
                f"{self.model.__name__} with ID {id} not found"
            )
        return instance
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            order_by: Column name to order by (default: created_at)
            order_desc: Whether to order descending
        
        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        # Apply ordering
        if order_by:
            order_column = getattr(self.model, order_by, None)
            if order_column is not None:
                query = query.order_by(
                    desc(order_column) if order_desc else asc(order_column)
                )
        elif hasattr(self.model, "created_at"):
            query = query.order_by(
                desc(self.model.created_at) if order_desc else asc(self.model.created_at)
            )
        
        return query.offset(skip).limit(limit).all()
    
    def count(self) -> int:
        """
        Get total count of records.
        
        Returns:
            Total number of records
        """
        return self.db.query(self.model).count()
    
    def exists(self, id: UUID) -> bool:
        """
        Check if a record exists.
        
        Args:
            id: UUID to check
        
        Returns:
            True if record exists
        """
        return self.db.query(
            self.db.query(self.model).filter(self.model.uuid == id).exists()
        ).scalar()
    
    def filter_by(self, **kwargs) -> List[ModelType]:
        """
        Filter records by attribute values.
        
        Args:
            **kwargs: Attribute name-value pairs to filter by
        
        Returns:
            List of matching records
        
        Example:
            patients = repo.filter_by(is_active=True, care_team_uuid=team_id)
        """
        return self.db.query(self.model).filter_by(**kwargs).all()
    
    def find_one_by(self, **kwargs) -> Optional[ModelType]:
        """
        Find a single record by attribute values.
        
        Args:
            **kwargs: Attribute name-value pairs to filter by
        
        Returns:
            Matching record or None
        """
        return self.db.query(self.model).filter_by(**kwargs).first()
    
    # =========================================================================
    # CREATE OPERATIONS
    # =========================================================================
    
    def create(self, data: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            data: Dictionary of attribute values
        
        Returns:
            Created model instance
        """
        try:
            instance = self.model(**data)
            self.db.add(instance)
            self.db.flush()  # Get the ID without committing
            
            logger.info(
                f"Created {self.model.__name__}",
                extra={"id": str(instance.uuid) if hasattr(instance, "uuid") else None}
            )
            
            return instance
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise DatabaseException(
                f"Failed to create {self.model.__name__}",
                original_error=e
            )
    
    def create_many(self, data_list: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records.
        
        Args:
            data_list: List of dictionaries with attribute values
        
        Returns:
            List of created model instances
        """
        try:
            instances = [self.model(**data) for data in data_list]
            self.db.add_all(instances)
            self.db.flush()
            
            logger.info(
                f"Created {len(instances)} {self.model.__name__} records"
            )
            
            return instances
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__} records: {e}")
            raise DatabaseException(
                f"Failed to create {self.model.__name__} records",
                original_error=e
            )
    
    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================
    
    def update(self, id: UUID, data: Dict[str, Any]) -> ModelType:
        """
        Update an existing record.
        
        Args:
            id: UUID of the record to update
            data: Dictionary of attribute values to update
        
        Returns:
            Updated model instance
        
        Raises:
            NotFoundException: If record doesn't exist
        """
        instance = self.get_by_id_or_raise(id)
        
        try:
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            self.db.flush()
            
            logger.info(
                f"Updated {self.model.__name__}",
                extra={"id": str(id)}
            )
            
            return instance
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise DatabaseException(
                f"Failed to update {self.model.__name__}",
                original_error=e
            )
    
    def update_instance(self, instance: ModelType, data: Dict[str, Any]) -> ModelType:
        """
        Update an existing model instance.
        
        Args:
            instance: Model instance to update
            data: Dictionary of attribute values to update
        
        Returns:
            Updated model instance
        """
        try:
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            self.db.flush()
            return instance
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise DatabaseException(
                f"Failed to update {self.model.__name__}",
                original_error=e
            )
    
    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================
    
    def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: UUID of the record to delete
        
        Returns:
            True if deleted, False if not found
        """
        instance = self.get_by_id(id)
        if instance is None:
            return False
        
        try:
            self.db.delete(instance)
            self.db.flush()
            
            logger.info(
                f"Deleted {self.model.__name__}",
                extra={"id": str(id)}
            )
            
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise DatabaseException(
                f"Failed to delete {self.model.__name__}",
                original_error=e
            )
    
    def delete_or_raise(self, id: UUID) -> None:
        """
        Delete a record, raising exception if not found.
        
        Args:
            id: UUID of the record to delete
        
        Raises:
            NotFoundException: If record doesn't exist
        """
        if not self.delete(id):
            raise NotFoundException(
                f"{self.model.__name__} with ID {id} not found"
            )
    
    def delete_many(self, ids: List[UUID]) -> int:
        """
        Delete multiple records by ID.
        
        Args:
            ids: List of UUIDs to delete
        
        Returns:
            Number of records deleted
        """
        try:
            count = self.db.query(self.model).filter(
                self.model.uuid.in_(ids)
            ).delete(synchronize_session=False)
            
            self.db.flush()
            
            logger.info(
                f"Deleted {count} {self.model.__name__} records"
            )
            
            return count
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__} records: {e}")
            raise DatabaseException(
                f"Failed to delete {self.model.__name__} records",
                original_error=e
            )





