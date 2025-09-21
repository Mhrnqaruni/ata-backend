"""Add multi-model AI grading fields to Result model

Revision ID: b5f8d7c9e2a1
Revises: c83545b01f3a
Create Date: 2024-09-21 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5f8d7c9e2a1'
down_revision: Union[str, Sequence[str], None] = 'c83545b01f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fields to support multi-model AI grading with consensus tracking."""
    # Add new fields to results table
    op.add_column('results', sa.Column('ai_responses', sa.JSON(), nullable=True))
    op.add_column('results', sa.Column('consensus_achieved', sa.String(), nullable=True))
    op.add_column('results', sa.Column('teacher_override', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove multi-model AI grading fields."""
    op.drop_column('results', 'teacher_override')
    op.drop_column('results', 'consensus_achieved')
    op.drop_column('results', 'ai_responses')