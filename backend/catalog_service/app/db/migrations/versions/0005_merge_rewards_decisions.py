"""Join rewards and catalog decisions migrations without rewriting either history."""

revision = "0005_merge_rewards_decisions"
down_revision = ("0004_engagement", "0003_catalog_decisions")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Destructive catalog downgrade is disabled; restore a verified backup instead")
