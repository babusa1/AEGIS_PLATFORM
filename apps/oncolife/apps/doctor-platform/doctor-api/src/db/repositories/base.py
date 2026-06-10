"""
Base Repository - Doctor API
============================

This module provides a generic base repository class with common
CRUD operations that can be extended by specific repositories.

The repository pattern abstracts database operations, making the
code more testable and maintainable.

Usage:
    class MyModelRepository(BaseRepository[MyModel]):
        def __init__(self, db: Session):
            super().__init__(MyModel, db)
        
        # Add custom methods here
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.logging import get_logger
from core.exceptions import NotFoundError, DatabaseError

logger = get_logger(__name__)

# Type variable for the model class
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository with common CRUD operations.
    
    Provides standard create, read, update, delete operations
    that can be inherited and extended by specific repositories.
    
    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages
    
    Attributes:
        model: The SQLAlchemy model class
        db: The database session
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize the repository.
        
        Args:
            model: The SQLAlchemy model class
            db: The database session
        """
        self.model = model
        self.db = db
    
    # =========================================================================
    # Create Operations
    # =========================================================================
    
    def create(self, **kwargs) -> ModelType:
        """
        Create a new record.
        
        Args:
            **kwargs: Field values for the new record
            
        Returns:
            The created model instance
        """
        try:
            instance = self.model(**kwargs)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            logger.debug(f"Created {self.model.__name__}: {instance}")
            return instance
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to create {self.model.__name__}",
                operation="create"
            )
    
    def create_no_commit(self, **kwargs) -> ModelType:
        """
        Create a new record without committing.
        
        Useful when creating multiple records in a transaction.
        Caller is responsible for committing.
        
        Args:
            **kwargs: Field values for the new record
            
        Returns:
            The created model instance (not yet committed)
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        return instance
    
    def bulk_create(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction.
        
        Args:
            items: List of dictionaries with field values
            
        Returns:
            List of created model instances
        """
        try:
            instances = [self.model(**item) for item in items]
            self.db.add_all(instances)
            self.db.commit()
            for instance in instances:
                self.db.refresh(instance)
            logger.debug(f"Bulk created {len(instances)} {self.model.__name__} records")
            return instances
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to bulk create {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to bulk create {self.model.__name__}",
                operation="bulk_create"
            )
    
    # =========================================================================
    # Read Operations
    # =========================================================================
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get a record by its integer ID.
        
        Args:
            id: The record's primary key ID
            
        Returns:
            The model instance, or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_by_id_or_fail(self, id: int) -> ModelType:
        """
        Get a record by ID, raising an error if not found.
        
        Args:
            id: The record's primary key ID
            
        Returns:
            The model instance
            
        Raises:
            NotFoundError: If the record doesn't exist
        """
        instance = self.get_by_id(id)
        if not instance:
            raise NotFoundError(
                message=f"{self.model.__name__} not found",
                resource_type=self.model.__name__,
                resource_id=id
            )
        return instance
    
    def get_by_uuid(self, uuid: UUID, uuid_field: str = "uuid") -> Optional[ModelType]:
        """
        Get a record by its UUID.
        
        Args:
            uuid: The record's UUID
            uuid_field: Name of the UUID field (default: "uuid")
            
        Returns:
            The model instance, or None if not found
        """
        return self.db.query(self.model).filter(
            getattr(self.model, uuid_field) == uuid
        ).first()
    
    def get_by_uuid_or_fail(self, uuid: UUID, uuid_field: str = "uuid") -> ModelType:
        """
        Get a record by UUID, raising an error if not found.
        
        Args:
            uuid: The record's UUID
            uuid_field: Name of the UUID field (default: "uuid")
            
        Returns:
            The model instance
            
        Raises:
            NotFoundError: If the record doesn't exist
        """
        instance = self.get_by_uuid(uuid, uuid_field)
        if not instance:
            raise NotFoundError(
                message=f"{self.model.__name__} not found",
                resource_type=self.model.__name__,
                resource_id=str(uuid)
            )
        return instance
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            order_by: Field name to order by
            descending: If True, order descending
            
        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            if descending:
                order_field = order_field.desc()
            query = query.order_by(order_field)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self) -> int:
        """
        Count all records.
        
        Returns:
            Total number of records
        """
        return self.db.query(self.model).count()
    
    def exists(self, **kwargs) -> bool:
        """
        Check if a record exists with the given field values.
        
        Args:
            **kwargs: Field values to check
            
        Returns:
            True if a matching record exists
        """
        filters = [
            getattr(self.model, key) == value
            for key, value in kwargs.items()
            if hasattr(self.model, key)
        ]
        return self.db.query(self.model).filter(and_(*filters)).first() is not None
    
    def find_by(self, **kwargs) -> List[ModelType]:
        """
        Find records matching the given field values.
        
        Args:
            **kwargs: Field values to match
            
        Returns:
            List of matching model instances
        """
        filters = [
            getattr(self.model, key) == value
            for key, value in kwargs.items()
            if hasattr(self.model, key)
        ]
        return self.db.query(self.model).filter(and_(*filters)).all()
    
    def find_one_by(self, **kwargs) -> Optional[ModelType]:
        """
        Find a single record matching the given field values.
        
        Args:
            **kwargs: Field values to match
            
        Returns:
            The first matching model instance, or None
        """
        filters = [
            getattr(self.model, key) == value
            for key, value in kwargs.items()
            if hasattr(self.model, key)
        ]
        return self.db.query(self.model).filter(and_(*filters)).first()
    
    # =========================================================================
    # Update Operations
    # =========================================================================
    
    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """
        Update an existing record.
        
        Args:
            instance: The model instance to update
            **kwargs: Field values to update
            
        Returns:
            The updated model instance
        """
        try:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
            logger.debug(f"Updated {self.model.__name__}: {instance}")
            return instance
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to update {self.model.__name__}",
                operation="update"
            )
    
    def update_by_id(self, id: int, **kwargs) -> ModelType:
        """
        Update a record by its ID.
        
        Args:
            id: The record's primary key ID
            **kwargs: Field values to update
            
        Returns:
            The updated model instance
            
        Raises:
            NotFoundError: If the record doesn't exist
        """
        instance = self.get_by_id_or_fail(id)
        return self.update(instance, **kwargs)
    
    # =========================================================================
    # Delete Operations
    # =========================================================================
    
    def delete(self, instance: ModelType) -> bool:
        """
        Delete a record.
        
        Args:
            instance: The model instance to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            self.db.delete(instance)
            self.db.commit()
            logger.debug(f"Deleted {self.model.__name__}: {instance}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete {self.model.__name__}: {e}")
            raise DatabaseError(
                message=f"Failed to delete {self.model.__name__}",
                operation="delete"
            )
    
    def delete_by_id(self, id: int) -> bool:
        """
        Delete a record by its ID.
        
        Args:
            id: The record's primary key ID
            
        Returns:
            True if deletion was successful
            
        Raises:
            NotFoundError: If the record doesn't exist
        """
        instance = self.get_by_id_or_fail(id)
        return self.delete(instance)
    
    # =========================================================================
    # Transaction Helpers
    # =========================================================================
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.rollback()
    
    def refresh(self, instance: ModelType) -> None:
        """Refresh an instance from the database."""
        self.db.refresh(instance)





