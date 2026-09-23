"""Add draft language and optimistic card versions."""
from alembic import op
from app.db.migrations import upgrade_draft_locale
from app.db.card_version_migration import upgrade_card_version

revision = "0002_locale_version"
down_revision = "0001_catalog"
branch_labels = None
depends_on = None


def upgrade():
    upgrade_draft_locale(op.get_bind())
    upgrade_card_version(op.get_bind())


def downgrade():
    raise RuntimeError("Destructive catalog downgrade is disabled; restore a verified backup instead")
