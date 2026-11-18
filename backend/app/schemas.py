from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=2, max_length=160)
    department: str | None = Field(default=None, max_length=120)

class EmployeeRead(EmployeeCreate):
    id: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DeviceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    device_type: str = Field(default="camera", max_length=40)
    location: str | None = Field(default=None, max_length=160)

class DeviceRead(DeviceCreate):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class AttendanceEventCreate(BaseModel):
    event_key: str = Field(min_length=8, max_length=100)
    employee_id: int | None = None
    direction: str
    occurred_at: datetime
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_device: str | None = None

class AttendanceEventRead(BaseModel):
    id: int
    event_key: str
    employee_id: int | None
    direction: str
    occurred_at: datetime
    confidence: float | None
    review_status: str
    source_device: str | None
    model_config = ConfigDict(from_attributes=True)
