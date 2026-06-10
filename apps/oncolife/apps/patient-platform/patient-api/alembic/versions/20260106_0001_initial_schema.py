"""Initial schema - Patient API

Revision ID: 0001
Revises: 
Create Date: 2026-01-06

This migration creates the initial database schema for the Patient API.
It includes all core tables for:
- Users and Patients
- Conversations and Messages
- Diary entries
- Education content
- Patient questions
- Referrals
- Medical records
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    
    # ==========================================================================
    # Users Table
    # ==========================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('cognito_sub', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_uuid', 'users', ['uuid'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # ==========================================================================
    # Conversations Table
    # ==========================================================================
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_state', sa.String(50), default='active', nullable=False),
        sa.Column('symptom_list', postgresql.JSONB(), nullable=True),
        sa.Column('severity_list', postgresql.JSONB(), nullable=True),
        sa.Column('medication_list', postgresql.JSONB(), nullable=True),
        sa.Column('longer_summary', sa.Text(), nullable=True),
        sa.Column('bulleted_summary', sa.Text(), nullable=True),
        sa.Column('overall_feeling', sa.String(50), nullable=True),
        sa.Column('triage_level', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_index('ix_conversations_uuid', 'conversations', ['uuid'])
    op.create_index('ix_conversations_patient_uuid', 'conversations', ['patient_uuid'])
    op.create_index('ix_conversations_created_at', 'conversations', ['created_at'])
    
    # ==========================================================================
    # Messages Table
    # ==========================================================================
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender', sa.String(50), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    
    # ==========================================================================
    # Diary Entries Table
    # ==========================================================================
    op.create_table(
        'diary_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('mood', sa.String(50), nullable=True),
        sa.Column('energy_level', sa.Integer(), nullable=True),
        sa.Column('pain_level', sa.Integer(), nullable=True),
        sa.Column('symptoms_summary', postgresql.JSONB(), nullable=True),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_index('ix_diary_entries_patient_uuid', 'diary_entries', ['patient_uuid'])
    op.create_index('ix_diary_entries_entry_date', 'diary_entries', ['entry_date'])
    
    # ==========================================================================
    # Patient Questions Table
    # ==========================================================================
    op.create_table(
        'patient_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('share_with_physician', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_answered', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('category', sa.String(50), default='other', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_patient_questions_patient_uuid', 'patient_questions', ['patient_uuid'])
    op.create_index('ix_patient_questions_share', 'patient_questions', ['share_with_physician'])
    
    # ==========================================================================
    # Education Content Table
    # ==========================================================================
    op.create_table(
        'education_content',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('symptom_id', sa.String(100), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('s3_key', sa.String(500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_index('ix_education_content_symptom_id', 'education_content', ['symptom_id'])
    
    # ==========================================================================
    # Chemo Tracking Table
    # ==========================================================================
    op.create_table(
        'chemo_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('treatment_date', sa.Date(), nullable=False),
        sa.Column('treatment_type', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_index('ix_chemo_entries_patient_uuid', 'chemo_entries', ['patient_uuid'])
    op.create_index('ix_chemo_entries_treatment_date', 'chemo_entries', ['treatment_date'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('chemo_entries')
    op.drop_table('education_content')
    op.drop_table('patient_questions')
    op.drop_table('diary_entries')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('users')

