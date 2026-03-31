"""Enable pg_trgm extension and create trigram index for CJK search

Revision ID: 006_cjk_trigram_search
Revises: 005_fts_simple
Create Date: 2026-03-31
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_cjk_trigram_search"
down_revision: Union[str, None] = "005_fts_simple"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX idx_chunks_content_trgm "
        "ON message_chunks USING gin (content gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_content_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
