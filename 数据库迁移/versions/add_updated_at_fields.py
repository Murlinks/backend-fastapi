"""Add updated_at fields to expenses and budgets tables

Revision ID: add_updated_at_fields
Revises: 
Create Date: 2024-01-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_updated_at_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add updated_at columns to expenses and budgets tables"""
    
    # Add updated_at column to expenses table
    op.add_column('expenses', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Add updated_at column to budgets table
    op.add_column('budgets', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Update existing records to have updated_at = created_at
    op.execute("UPDATE expenses SET updated_at = created_at WHERE updated_at IS NULL")
    op.execute("UPDATE budgets SET updated_at = created_at WHERE updated_at IS NULL")
    
    # Make updated_at columns non-nullable
    op.alter_column('expenses', 'updated_at', nullable=False)
    op.alter_column('budgets', 'updated_at', nullable=False)


def downgrade() -> None:
    """Remove updated_at columns from expenses and budgets tables"""
    
    # Remove updated_at column from expenses table
    op.drop_column('expenses', 'updated_at')
    
    # Remove updated_at column from budgets table
    op.drop_column('budgets', 'updated_at')