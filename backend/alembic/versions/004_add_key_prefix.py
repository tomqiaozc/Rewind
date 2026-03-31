"""Add key_prefix column to api_keys table

Revision ID: 004_add_key_prefix
Revises: 003_tags
Create Date: 2026-03-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_add_key_prefix"
down_revision: Union[str, None] = "003_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("key_prefix", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "key_prefix")
