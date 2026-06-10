"""
Base Service - Doctor API
=========================

This module provides a base class for all services.
Services encapsulate business logic and coordinate between
the API layer and data repositories.

Usage:
    class MyService(BaseService):
        def __init__(self, db: Session):
            super().__init__(db)
            self.my_repo = MyRepository(db)
        
        def do_something(self, data):
            # Business logic here
            return self.my_repo.create(**data)
"""

from sqlalchemy.orm import Session

from core.logging import get_logger

logger = get_logger(__name__)


class BaseService:
    """
    Base class for all service classes.
    
    Provides common functionality and database session access
    for all services in the application.
    
    Attributes:
        db: The database session for the service
        logger: Logger instance for the service
    """
    
    def __init__(self, db: Session):
        """
        Initialize the service.
        
        Args:
            db: The database session
        """
        self.db = db
        self.logger = get_logger(self.__class__.__name__)
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.rollback()





