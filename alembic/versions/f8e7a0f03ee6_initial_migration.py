"""Initial migration

Revision ID: f8e7a0f03ee6
Revises: 
Create Date: 2026-01-06 08:35:57.848520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f8e7a0f03ee6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ApprovalStatus enum type (checkfirst handles if it already exists)
    approval_status_enum = postgresql.ENUM(
        'PENDING', 'APPROVED', 'REJECTED',
        name='approvalstatus',
        create_type=False  # Don't auto-create, we'll handle it manually
    )
    
    # Check if enum exists, create if not
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'approvalstatus'"
    )).scalar()
    
    if result is None:
        approval_status_enum.create(conn, checkfirst=False)
    
    # Check if table exists before creating
    inspector = sa.inspect(conn)
    if 'approvals' not in inspector.get_table_names():
        # Create approvals table
        op.create_table(
            'approvals',
            sa.Column('approval_id', sa.String(length=255), nullable=False),
            sa.Column('order_id', sa.String(length=255), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('status', approval_status_enum, nullable=False, server_default='PENDING'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('approval_id')
        )
        op.create_index('ix_approvals_order_id', 'approvals', ['order_id'], unique=False)
        op.create_index('ix_approvals_status', 'approvals', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_approvals_status', table_name='approvals')
    op.drop_index('ix_approvals_order_id', table_name='approvals')
    op.drop_table('approvals')
    
    # Drop enum type
    approval_status_enum = postgresql.ENUM(
        'PENDING', 'APPROVED', 'REJECTED',
        name='approvalstatus'
    )
    approval_status_enum.drop(op.get_bind(), checkfirst=True)
