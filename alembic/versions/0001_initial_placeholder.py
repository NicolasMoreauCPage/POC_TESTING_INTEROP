"""Initial placeholder migration.

Generate actual DDL by running:

    alembic revision --autogenerate -m "initial schema"
    alembic upgrade head

This placeholder keeps history consistent for future structured migrations.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial_placeholder'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Intentionally empty; generate real schema with autogenerate.
    pass


def downgrade() -> None:
    pass
