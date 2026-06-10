"""
API Version 1.

This module contains all v1 API endpoints, organized by domain:
- auth: Authentication endpoints
- patients: Patient management
- chat: Symptom checker conversations
- profile: User profile management
- summaries: Conversation summaries

All v1 endpoints are prefixed with /api/v1/
"""

from .router import router

__all__ = ["router"]





