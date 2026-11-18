"""Initial AttendVision schema."""
from alembic import op
import sqlalchemy as sa
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("employees", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("employee_code", sa.String(40), nullable=False), sa.Column("full_name", sa.String(160), nullable=False), sa.Column("department", sa.String(120)), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_employees_employee_code", "employees", ["employee_code"], unique=True)
    op.create_index("ix_employees_full_name", "employees", ["full_name"])
    op.create_table("devices", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("device_type", sa.String(40), nullable=False, server_default="camera"), sa.Column("location", sa.String(160)), sa.Column("status", sa.String(20), nullable=False, server_default="pending"))
    op.create_table("attendance_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_key", sa.String(100), nullable=False), sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id")), sa.Column("direction", sa.String(10), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("confidence", sa.Float()), sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"), sa.Column("source_device", sa.String(120)))
    op.create_index("ix_attendance_events_event_key", "attendance_events", ["event_key"], unique=True)
    op.create_index("ix_attendance_events_occurred_at", "attendance_events", ["occurred_at"])
def downgrade():
    op.drop_index("ix_attendance_events_occurred_at", table_name="attendance_events")
    op.drop_index("ix_attendance_events_event_key", table_name="attendance_events")
    op.drop_table("attendance_events")
    op.drop_table("devices")
    op.drop_index("ix_employees_full_name", table_name="employees")
    op.drop_index("ix_employees_employee_code", table_name="employees")
    op.drop_table("employees")
