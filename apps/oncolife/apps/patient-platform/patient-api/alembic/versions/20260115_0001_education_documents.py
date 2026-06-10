"""Create education PDF tables

Revision ID: 20260115_0001
Revises: 20260114_0002
Create Date: 2026-01-15 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260115_0001'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create education_pdfs table (symptom-specific PDF files)
    op.create_table(
        'education_pdfs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symptom_code', sa.String(50), nullable=False, index=True, comment='Symptom code (e.g., NAU-203, FEV-202)'),
        sa.Column('symptom_name', sa.String(100), nullable=False, comment='Human-readable symptom name'),
        sa.Column('title', sa.String(255), nullable=False, comment='Document title'),
        sa.Column('source', sa.String(100), nullable=True, comment='Source organization (ACS, NCI, Chemocare, etc.)'),
        sa.Column('file_path', sa.String(500), nullable=False, comment='Relative path to PDF file'),
        sa.Column('summary', sa.Text, nullable=True, comment='Brief summary of document content'),
        sa.Column('keywords', sa.ARRAY(sa.String), nullable=True, comment='Keywords for search'),
        sa.Column('display_order', sa.Integer, nullable=False, default=1, comment='Order for display within symptom'),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True, comment='Whether document is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create education_handbooks table
    op.create_table(
        'education_handbooks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(255), nullable=False, comment='Handbook title'),
        sa.Column('description', sa.Text, nullable=True, comment='Handbook description'),
        sa.Column('file_path', sa.String(500), nullable=False, comment='Relative path to PDF file'),
        sa.Column('handbook_type', sa.String(50), nullable=False, default='general', comment='Type: general, emergency, medication'),
        sa.Column('display_order', sa.Integer, nullable=False, default=1, comment='Order for display'),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create education_regimen_pdfs table for chemo regimen-specific content
    op.create_table(
        'education_regimen_pdfs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('regimen_code', sa.String(50), nullable=False, index=True, comment='Regimen code (e.g., R-CHOP, FOLFOX)'),
        sa.Column('regimen_name', sa.String(100), nullable=False, comment='Human-readable regimen name'),
        sa.Column('title', sa.String(255), nullable=False, comment='Document title'),
        sa.Column('source', sa.String(100), nullable=True, comment='Source organization'),
        sa.Column('file_path', sa.String(500), nullable=False, comment='Relative path to PDF file'),
        sa.Column('document_type', sa.String(50), nullable=False, default='overview', comment='Type: overview, drug_info, side_effects'),
        sa.Column('drug_name', sa.String(100), nullable=True, comment='Drug name if drug-specific'),
        sa.Column('summary', sa.Text, nullable=True, comment='Brief summary'),
        sa.Column('display_order', sa.Integer, nullable=False, default=1),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )
    
    # Create indexes for better query performance
    op.create_index('ix_education_pdfs_symptom_active', 'education_pdfs', ['symptom_code', 'is_active'])
    op.create_index('ix_education_regimen_pdfs_regimen_active', 'education_regimen_pdfs', ['regimen_code', 'is_active'])


def downgrade() -> None:
    op.drop_index('ix_education_regimen_pdfs_regimen_active', table_name='education_regimen_pdfs')
    op.drop_index('ix_education_pdfs_symptom_active', table_name='education_pdfs')
    op.drop_table('education_regimen_pdfs')
    op.drop_table('education_handbooks')
    op.drop_table('education_pdfs')
