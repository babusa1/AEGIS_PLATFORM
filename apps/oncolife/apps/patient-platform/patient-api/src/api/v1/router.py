"""
================================================================================
Main Router for API Version 1 - Patient API
================================================================================

Module:         router.py
Description:    Aggregates all v1 endpoint routers into a single router
                for the Patient API platform.

Created:        2025-12-11
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Endpoints:
    /health     - Health check endpoints
    /auth       - Authentication (signup, login, logout, password, delete)
    /onboarding - Patient onboarding flow (fax, OCR, welcome, setup)
    /patients   - Patient management
    /chat       - Symptom checker chat (REST + WebSocket)
    /chemo      - Chemotherapy dates
    /diary      - Patient diary entries
    /summaries  - Conversation summaries
    /profile    - Patient profile and configuration
    /education  - Patient education resources
    /questions  - Questions for doctor feature

Usage:
    from api.v1 import router as api_v1_router
    
    app.include_router(api_v1_router, prefix="/api/v1")

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""

from fastapi import APIRouter

from .endpoints import (
    auth, chat, patients, profile, health, 
    chemo, diary, summaries, onboarding, education, questions, docs
)

# Create main v1 router
router = APIRouter()

# Include all endpoint routers
router.include_router(
    health.router,
    tags=["Health"]
)

router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

router.include_router(
    onboarding.router,
    tags=["Patient Onboarding"]
)

router.include_router(
    patients.router,
    prefix="/patients",
    tags=["Patients"]
)

router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat / Symptom Checker"]
)

router.include_router(
    chemo.router,
    prefix="/chemo",
    tags=["Chemotherapy"]
)

router.include_router(
    diary.router,
    prefix="/diary",
    tags=["Diary"]
)

router.include_router(
    summaries.router,
    prefix="/summaries",
    tags=["Summaries"]
)

router.include_router(
    profile.router,
    prefix="/profile",
    tags=["Profile"]
)

router.include_router(
    education.router,
    prefix="/education",
    tags=["Patient Education"]
)

router.include_router(
    questions.router,
    prefix="/questions",
    tags=["Questions to Ask Doctor"]
)

router.include_router(
    docs.router,
    prefix="/docs",
    tags=["API Documentation"],
    include_in_schema=False,  # Don't show docs endpoints in docs
)

