"""
API V1 Endpoints.

This package contains all endpoint handlers organized by domain.
Each module corresponds to a logical grouping of API endpoints.

Endpoints:
- auth: Authentication (signup, login, logout, password)
- onboarding: Patient onboarding flow (fax, OCR, welcome, setup)
- chat: Symptom checker chat (REST + WebSocket)
- chemo: Chemotherapy date management
- diary: Patient diary entries
- docs: Secured API documentation (production)
- education: Patient education resources and summaries
- health: Health check
- patients: Patient management
- profile: Patient profile and configuration
- questions: Questions to ask doctor
- summaries: Conversation summaries
"""

from . import auth, chat, chemo, diary, docs, education, health, onboarding, patients, profile, questions, summaries

__all__ = [
    "auth",
    "chat",
    "chemo",
    "diary",
    "docs",
    "education",
    "health",
    "onboarding",
    "patients",
    "profile",
    "questions",
    "summaries",
]

