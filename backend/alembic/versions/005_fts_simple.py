"""Switch FTS config from 'english' to 'simple' for CJK support

Revision ID: 005_fts_simple
Revises: 004_add_key_prefix
Create Date: 2026-03-31
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_fts_simple"
down_revision: Union[str, None] = "004_add_key_prefix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old generated column and recreate with 'simple' config.
    # PostgreSQL does not allow ALTER on GENERATED columns, so drop + add.
    op.drop_index("idx_chunks_fts", table_name="message_chunks")
    op.execute("ALTER TABLE message_chunks DROP COLUMN search_vector")
    op.execute(
        """
        ALTER TABLE message_chunks
            ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('simple', coalesce(content, '') || ' ' || coalesce(tool_context, ''))
            ) STORED
        """
    )
    op.create_index(
        "idx_chunks_fts",
        "message_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_chunks_fts", table_name="message_chunks")
    op.execute("ALTER TABLE message_chunks DROP COLUMN search_vector")
    op.execute(
        """
        ALTER TABLE message_chunks
            ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(content, '') || ' ' || coalesce(tool_context, ''))
            ) STORED
        """
    )
    op.create_index(
        "idx_chunks_fts",
        "message_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )
