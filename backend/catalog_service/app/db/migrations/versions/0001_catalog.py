"""Create the catalog or adopt an intact pre-migration catalog without rewriting rows."""
from alembic import op
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db.migrations.baseline import Base

revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = inspect(connection)
    existing = set(inspector.get_table_names()) - {"alembic_version"}
    if not existing:
        # This frozen snapshot belongs only to revision 0001, never to live models.
        Base.metadata.create_all(connection)
        return

    expected = set(Base.metadata.tables)
    if existing != expected:
        raise RuntimeError("Catalog baseline mismatch: unexpected or missing tables; restore/check backup before upgrade")
    differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    for table in Base.metadata.sorted_tables:
        actual_pk = inspector.get_pk_constraint(table.name)["constrained_columns"]
        if set(actual_pk) != {column.name for column in table.primary_key}:
            differences.append(("primary_key", table.name))
        checks = inspector.get_check_constraints(table.name)
        expected_checks = [c for c in table.constraints if c.__class__.__name__ == "CheckConstraint"]
        if len(checks) != len(expected_checks):
            differences.append(("check_constraints", table.name))
    if differences:
        raise RuntimeError(f"Catalog baseline mismatch; no data changed: {differences!r}")
    # Alembic records the revision; existing domain tables and rows stay untouched.


def downgrade():
    raise RuntimeError("Destructive catalog downgrade is disabled; restore a verified backup instead")
