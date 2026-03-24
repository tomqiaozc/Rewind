"""Create sessions, messages, message_chunks tables

Revision ID: 002_sessions_messages_chunks
Revises: 001_initial
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "002_sessions_messages_chunks"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sessions table
    op.create_table(
        "sessions",
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
        sa.Column("session_key", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        # Temporal
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        # Counts
        sa.Column("user_messages", sa.Integer(), server_default="0", nullable=False),
        sa.Column("assistant_messages", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_messages", sa.Integer(), server_default="0", nullable=False),
        # Tokens
        sa.Column("total_input_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_output_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_cached_tokens", sa.BigInteger(), server_default="0", nullable=False),
        # Context
        sa.Column("project_ref", sa.Text(), nullable=True),
        sa.Column("project_name", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        # Content references
        sa.Column("content_key", sa.Text(), nullable=True),
        sa.Column("content_size", sa.BigInteger(), nullable=True),
        sa.Column("raw_key", sa.Text(), nullable=True),
        sa.Column("raw_size", sa.BigInteger(), nullable=True),
        # Versioning
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("raw_hash", sa.Text(), nullable=True),
        sa.Column("parser_revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
        # User organization
        sa.Column(
            "is_starred",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "session_key"),
    )

    # Messages table
    op.create_table(
        "messages",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        # Tool metadata
        sa.Column("tool_name", sa.Text(), nullable=True),
        sa.Column("tool_call_id", sa.Text(), nullable=True),
        sa.Column("tool_status", sa.Text(), nullable=True),
        # Tokens
        sa.Column("input_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.BigInteger(), server_default="0", nullable=False),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("session_id", "ordinal"),
    )

    # Message chunks table (without the tsvector GENERATED column — added via raw SQL)
    op.create_table(
        "message_chunks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_context", sa.Text(), nullable=True),
        sa.UniqueConstraint("message_id", "chunk_index"),
    )

    # Add tsvector GENERATED ALWAYS AS stored column via raw SQL
    op.execute(
        """
        ALTER TABLE message_chunks
            ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(content, '') || ' ' || coalesce(tool_context, ''))
            ) STORED
        """
    )

    # GIN index on search_vector for FTS
    op.create_index(
        "idx_chunks_fts",
        "message_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_chunks_fts", table_name="message_chunks")
    op.drop_table("message_chunks")
    op.drop_table("messages")
    op.drop_table("sessions")
