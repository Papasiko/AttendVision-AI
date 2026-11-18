from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=2, max_length=160)
    department: str | None = Field(default=None, max_length=120)


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    department: str | None = Field(default=None, max_length=120)
    status: Literal["active", "inactive"] | None = None


class EmployeeRead(EmployeeCreate):
    id: int
    status: str
    created_at: datetime
    face_enrolled: bool = False
    model_config = ConfigDict(from_attributes=True)


class DeviceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    device_type: str = Field(default="camera", max_length=40)
    location: str | None = Field(default=None, max_length=160)


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=160)
    status: Literal["active", "inactive", "pending"] | None = None


class DeviceRead(DeviceCreate):
    id: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AttendanceEventCreate(BaseModel):
    event_key: str = Field(min_length=8, max_length=100)
    employee_id: int | None = None
    direction: Literal["in", "out", "unknown"]
    occurred_at: datetime
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_device: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class ManualAttendanceCreate(BaseModel):
    employee_id: int
    direction: Literal["in", "out"]
    occurred_at: datetime
    note: str = Field(min_length=3, max_length=500)


class AttendanceReview(BaseModel):
    review_status: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=500)


class AttendanceEventRead(BaseModel):
    id: int
    event_key: str
    employee_id: int | None
    direction: str
    occurred_at: datetime
    confidence: float | None
    review_status: str
    source_device: str | None
    note: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SummaryRead(BaseModel):
    date: str
    active_employees: int
    present: int
    absent: int
    pending_review: int
    events_today: int
