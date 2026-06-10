"""Initial schema - Doctor API

Revision ID: 0001
Revises: 
Create Date: 2026-01-06

This migration creates the initial database schema for the Doctor API.
It includes all core tables for:
- Clinics
- Staff/Physicians
- Audit logs
- Analytics
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
    # Clinics Table
    # ==========================================================================
    op.create_table(
        'clinics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('zip_code', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_index('ix_clinics_uuid', 'clinics', ['uuid'])
    
    # ==========================================================================
    # Staff Table (Physicians, Nurses, Admin)
    # ==========================================================================
    op.create_table(
        'staff',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cognito_sub', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('role', sa.String(50), nullable=False),  # physician, nurse, admin
        sa.Column('clinic_id', sa.Integer(), sa.ForeignKey('clinics.id'), nullable=True),
        sa.Column('physician_id', sa.Integer(), sa.ForeignKey('staff.id'), nullable=True),  # For staff assigned to physician
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_staff_uuid', 'staff', ['uuid'])
    op.create_index('ix_staff_email', 'staff', ['email'])
    op.create_index('ix_staff_role', 'staff', ['role'])
    op.create_index('ix_staff_clinic_id', 'staff', ['clinic_id'])
    
    # ==========================================================================
    # Physician-Patient Assignment Table
    # ==========================================================================
    op.create_table(
        'physician_patients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('physician_id', sa.Integer(), sa.ForeignKey('staff.id', ondelete='CASCADE'), nullable=False),
        sa.Column('patient_uuid', postgresql.UUID(as_uuid=True), nullable=False),  # References patient in patient DB
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('physician_id', 'patient_uuid', name='uq_physician_patient'),
    )
    op.create_index('ix_physician_patients_physician_id', 'physician_patients', ['physician_id'])
    op.create_index('ix_physician_patients_patient_uuid', 'physician_patients', ['patient_uuid'])
    
    # ==========================================================================
    # Audit Log Table (HIPAA Compliance)
    # ==========================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_role', sa.String(50), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    
    # ==========================================================================
    # Weekly Reports Table
    # ==========================================================================
    op.create_table(
        'weekly_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('physician_id', sa.Integer(), sa.ForeignKey('staff.id'), nullable=False),
        sa.Column('report_week_start', sa.Date(), nullable=False),
        sa.Column('report_week_end', sa.Date(), nullable=False),
        sa.Column('report_data', postgresql.JSONB(), nullable=True),
        sa.Column('patient_count', sa.Integer(), default=0, nullable=False),
        sa.Column('total_alerts', sa.Integer(), default=0, nullable=False),
        sa.Column('total_questions', sa.Integer(), default=0, nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('physician_id', 'report_week_start', name='uq_physician_week'),
    )
    op.create_index('ix_weekly_reports_physician_id', 'weekly_reports', ['physician_id'])
    op.create_index('ix_weekly_reports_week_start', 'weekly_reports', ['report_week_start'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('weekly_reports')
    op.drop_table('audit_logs')
    op.drop_table('physician_patients')
    op.drop_table('staff')
    op.drop_table('clinics')

