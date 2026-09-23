"""Persist business rewards; existing tasks receive no retroactive rewards."""
from alembic import op
import sqlalchemy as sa

revision = "0003_rewards"
down_revision = "0002_locale_version"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "daily_visits",
        sa.Column("business_id", sa.Uuid(), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
    )
    op.create_table(
        "reward_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("task_cards.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("coins", sa.Integer(), nullable=False),
        sa.Column("reputation", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("task_id", "kind", name="uq_reward_task_kind"),
        sa.CheckConstraint("coins > 0 AND reputation > 0", name="ck_reward_positive"),
    )
    op.create_index("ix_reward_events_business_id", "reward_events", ["business_id"])


def downgrade():
    raise RuntimeError("Destructive catalog downgrade is disabled; restore a verified backup instead")
