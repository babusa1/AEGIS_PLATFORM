"""
Conversation Summary Routes

This module provides endpoints for retrieving conversation summaries and details:

Routes:
- GET /summaries/{year}/{month}: Fetch conversation summaries for a specific month and year
- GET /summaries/{conversation_uuid}: Fetch longer summary by conversationUUID

All routes require authentication and operate on the logged-in user's data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List
import uuid

# Database and model imports
from db.database import get_patient_db
from db.patient_models import Conversations
from routers.auth.dependencies import get_current_user, TokenData
from routers.chat.constants import ConversationState
from .models import ConversationSummarySchema, ConversationDetailSchema
from utils.timezone_utils import utc_to_user_timezone, format_datetime_for_display

router = APIRouter()

def convert_conversation_to_user_timezone(conversation, user_timezone: str = "America/Los_Angeles"):
    """Convert conversation timestamps to user timezone for display."""
    # Create a copy of the conversation data to avoid modifying the database object
    conversation_data = {
        "uuid": str(conversation.uuid),  # Convert UUID to string
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "conversation_state": conversation.conversation_state,
        "symptom_list": conversation.symptom_list,
        "severity_list": conversation.severity_list,
        "longer_summary": conversation.longer_summary,
        "medication_list": conversation.medication_list,
        "bulleted_summary": conversation.bulleted_summary,
        "overall_feeling": conversation.overall_feeling,
    }
    
    # Convert timestamps to user timezone
    if conversation_data["created_at"]:
        conversation_data["created_at"] = utc_to_user_timezone(conversation_data["created_at"], user_timezone)
    if conversation_data["updated_at"]:
        conversation_data["updated_at"] = utc_to_user_timezone(conversation_data["updated_at"], user_timezone)
    
    return conversation_data

@router.get("/summaries/{year}/{month}", response_model=list[ConversationSummarySchema], tags=["summaries"])
async def get_summaries_by_month(
    year: int,
    month: int,
    db: Session = Depends(get_patient_db),
    current_user: TokenData = Depends(get_current_user),
    timezone: str = Query(default="America/Los_Angeles", description="User's timezone")
):
    """
    Get all conversation summaries that have been processed (have bulleted_summary) for a specific month and year.
    """
    try:
        conversations = db.query(Conversations).filter(
            Conversations.patient_uuid == current_user.sub,
            Conversations.bulleted_summary.isnot(None),
            extract('year', Conversations.created_at) == year,
            extract('month', Conversations.created_at) == month
        ).order_by(Conversations.created_at.desc()).all()
        
        # Convert timestamps to user timezone and create proper response objects
        response_data = []
        for conversation in conversations:
            conversation_data = convert_conversation_to_user_timezone(conversation, timezone)
            response_data.append(ConversationSummarySchema(**conversation_data))
        
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summaries/{conversation_uuid}", response_model=ConversationDetailSchema, tags=["summaries"])
async def get_conversation_details(
    conversation_uuid: str,
    db: Session = Depends(get_patient_db),
    current_user: TokenData = Depends(get_current_user),
    timezone: str = Query(default="America/Los_Angeles", description="User's timezone")
):
    """
    Get detailed information about a specific conversation that has been processed.
    """
    try:
        conversation = db.query(Conversations).filter(
            Conversations.uuid == conversation_uuid,
            Conversations.patient_uuid == current_user.sub,
            Conversations.bulleted_summary.isnot(None)
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Convert timestamps to user timezone and create proper response object
        conversation_data = convert_conversation_to_user_timezone(conversation, timezone)
        return ConversationDetailSchema(**conversation_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 