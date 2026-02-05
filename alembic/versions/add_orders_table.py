"""Add orders table

Revision ID: add_orders_table_001
Revises: add_conversations_table
Create Date: 2026-01-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_orders_table_001'
down_revision: Union[str, None] = 'add_conversations_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create OrderStatus enum type
    order_status_enum = postgresql.ENUM(
        'PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED',
        name='orderstatus',
        create_type=False
    )
    
    # Check if enum exists, create if not
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'orderstatus'"
    )).scalar()
    
    if result is None:
        order_status_enum.create(conn, checkfirst=False)
    
    # Check if table exists before creating
    inspector = sa.inspect(conn)
    if 'orders' not in inspector.get_table_names():
        # Create orders table
        op.create_table(
            'orders',
            sa.Column('order_id', sa.String(length=255), nullable=False),
            sa.Column('status', order_status_enum, nullable=False),
            sa.Column('expected_delivery_date', sa.Date(), nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('refundable', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('order_id')
        )
        op.create_index('ix_orders_status', 'orders', ['status'], unique=False)
        op.create_index('ix_orders_created_at', 'orders', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_orders_created_at', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')
    op.drop_table('orders')
    
    # Drop enum type
    order_status_enum = postgresql.ENUM(
        'PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED',
        name='orderstatus'
    )
    order_status_enum.drop(op.get_bind(), checkfirst=True)
