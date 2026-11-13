"""source registry and health metadata

Revision ID: 8b6c5a2f4d01
Revises: 1a20f1481fdc
"""

from alembic import op
import sqlalchemy as sa


revision = "8b6c5a2f4d01"
down_revision = "1a20f1481fdc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("crawl_sources") as batch:
        batch.add_column(sa.Column("profile_id", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("connector_type", sa.String(length=30), nullable=False, server_default="html_static"))
        batch.add_column(sa.Column("integration_status", sa.String(length=30), nullable=False, server_default="legal_review"))
        batch.add_column(sa.Column("health_score", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_health_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("terms_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("robots_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("approval_notes", sa.Text(), nullable=True))
        batch.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("approved_by_id", sa.Integer(), nullable=True))
        batch.create_index("ix_crawl_sources_profile_id", ["profile_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("crawl_sources") as batch:
        batch.drop_index("ix_crawl_sources_profile_id")
        for column in ("approved_by_id", "approved_at", "approval_notes", "robots_url", "terms_url", "last_health_at", "consecutive_failures", "health_score", "integration_status", "connector_type", "profile_version", "profile_id"):
            batch.drop_column(column)
