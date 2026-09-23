"""Add task topics and explicit proposal rejections without resetting catalog data."""
from alembic import op
import sqlalchemy as sa

revision = "0003_catalog_decisions"
down_revision = "0002_locale_version"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("task_cards", sa.Column("topic", sa.String(32), nullable=True))
    op.create_table(
        "selection_decision_rejections",
        sa.Column("decision_id", sa.Uuid(), sa.ForeignKey("selection_decisions.id"), primary_key=True),
        sa.Column("proposal_id", sa.Uuid(), sa.ForeignKey("proposals.id"), primary_key=True),
    )
    # Old decisions were complete selection snapshots. Preserve their meaning;
    # proposals submitted afterwards must stay pending.
    op.execute(sa.text("""
        INSERT INTO selection_decision_rejections (decision_id, proposal_id)
        SELECT d.id, p.id FROM selection_decisions d
        JOIN proposals p ON p.task_id = d.task_id AND p.created_at <= d.created_at
        WHERE NOT EXISTS (
            SELECT 1 FROM selection_decision_proposals s
            WHERE s.decision_id = d.id AND s.proposal_id = p.id
        )
    """))


def downgrade():
    raise RuntimeError("Destructive catalog downgrade is disabled; restore a verified backup instead")
