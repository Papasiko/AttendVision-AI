from pydantic import BaseModel, Field


class FaceEnrollmentResult(BaseModel):
    employee_id: int
    enrolled: bool
    message: str


class FaceRecognitionResult(BaseModel):
    matched: bool
    employee_id: int | None = None
    employee_name: str | None = None
    score: float
    event_id: int | None = None
    review_status: str | None = None
    message: str
