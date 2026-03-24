"""Create tags and session_tags tables

Revision ID: 003_tags
Revises: 002_sessions_messages_chunks
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "003_tags"
down_revision: Union[str, None] = "002_sessions_messages_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tags table
    op.create_table(
        "tags",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False, server_default="#6b7280"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )

    # Index on user_id for fast tag listing
    op.create_index("ix_tags_user_id", "tags", ["user_id"])

    # Session-tags association table
    op.create_table(
        "session_tags",
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("session_tags")
    op.drop_index("ix_tags_user_id", table_name="tags")
    op.drop_table("tags")
