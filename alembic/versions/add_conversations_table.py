"""Add conversations table

Revision ID: add_conversations_table
Revises: f8e7a0f03ee6
Create Date: 2026-01-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_conversations_table'
down_revision: Union[str, None] = 'f8e7a0f03ee6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists before creating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'conversations' not in inspector.get_table_names():
        # Create conversations table
        op.create_table(
            'conversations',
            sa.Column('conversation_id', sa.String(length=255), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('last_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('conversation_id')
        )
        op.create_index('ix_conversations_created_at', 'conversations', ['created_at'], unique=False)
        op.create_index('ix_conversations_updated_at', 'conversations', ['updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_conversations_updated_at', table_name='conversations')
    op.drop_index('ix_conversations_created_at', table_name='conversations')
    op.drop_table('conversations')
