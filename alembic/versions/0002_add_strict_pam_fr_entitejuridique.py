"""Add strict_pam_fr flag to EntiteJuridique.

This migration adds a per-EntiteJuridique strict IHE PAM France compliance
flag (strict_pam_fr) that disables A08 update events (emission/reception)
when true. Defaults to true.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_strict_pam_fr_entitejuridique"
down_revision = "0001_initial_placeholder"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add column with server default '1' so existing rows become strict.
    op.add_column(
        "entitejuridique",
        sa.Column("strict_pam_fr", sa.Boolean(), nullable=False, server_default="1")
    )
    # Optional: normalize default (SQLite keeps server_default); no data backfill needed.


def downgrade() -> None:
    # Downgrade: remove the column (supported on modern SQLite). If unsupported, manual rebuild needed.
    try:
        op.drop_column("entitejuridique", "strict_pam_fr")
    except Exception:
        # Fallback note: SQLite <3.35 cannot drop columns; in such case manual table
        # recreation would be required. We silently ignore to keep downgrade path tolerant.
        pass
