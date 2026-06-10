"""
Base Service Class.

This module provides a base class for all services with:
- Database session management
- Logging integration
- Common utility methods

All domain-specific services should inherit from BaseService.
"""

from typing import TypeVar, Generic, Type
from sqlalchemy.orm import Session

from db.repositories.base import BaseRepository
from core.logging import get_logger

# Type variable for repository
RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService:
    """
    Base class for all services.
    
    Provides common functionality including:
    - Database session access
    - Logging setup
    - Transaction management helpers
    
    Attributes:
        db: Database session
        logger: Logger instance for this service
    """
    
    def __init__(self, db: Session):
        """
        Initialize the service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.logger = get_logger(self.__class__.__module__)
    
    def commit(self) -> None:
        """
        Commit the current transaction.
        
        Use sparingly - prefer to let the dependency injection
        handle commits at the request boundary.
        """
        self.db.commit()
    
    def rollback(self) -> None:
        """
        Rollback the current transaction.
        
        Use when you need to explicitly rollback within a service method.
        """
        self.db.rollback()
    
    def flush(self) -> None:
        """
        Flush pending changes to the database.
        
        This makes changes visible within the current transaction
        without committing.
        """
        self.db.flush()





