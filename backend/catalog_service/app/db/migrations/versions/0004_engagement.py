"""Add action streaks and an idempotent engagement ledger; preserve past rewards."""
from alembic import op
import sqlalchemy as sa

revision = "0004_engagement"
down_revision = "0003_rewards"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "coin_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_type", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("task_cards.id"), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("detail", sa.String(32), server_default="", nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("owner_type", "owner_id", "task_id", "reason", "detail", name="uq_coin_award"),
        sa.CheckConstraint("amount > 0", name="ck_coin_amount"),
        sa.CheckConstraint("owner_type IN ('business', 'student')", name="ck_coin_owner"),
    )
    op.create_index("ix_coin_transactions_owner_id", "coin_transactions", ["owner_id"])
    op.create_table(
        "action_days",
        sa.Column("owner_type", sa.String(16), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.CheckConstraint("owner_type IN ('business', 'student')", name="ck_action_owner"),
    )


def downgrade():
    raise RuntimeError("Destructive catalog downgrade is disabled; restore a verified backup instead")
