"""Add consent tracking and encrypted face templates."""
import sqlalchemy as sa
from alembic import op

revision = "0002_face_templates"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("employees", sa.Column("face_template", sa.Text(), nullable=True))
    op.add_column("employees", sa.Column("face_consent", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("employees", sa.Column("face_consent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("employees", "face_consent_at")
    op.drop_column("employees", "face_consent")
    op.drop_column("employees", "face_template")
