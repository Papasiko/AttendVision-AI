"""Safe placeholder interface. No biometric inference is implemented here."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass(frozen=True)
class AttendanceCandidate:
    event_key: str
    direction: Literal["in", "out", "unknown"]
    occurred_at: datetime
    confidence: float | None
    employee_reference: str | None
    requires_review: bool = True

class VisionAdapterNotConfigured(RuntimeError):
    pass

class VisionAdapter:
    def process_frame(self, frame: object) -> AttendanceCandidate:
        raise VisionAdapterNotConfigured("No validated model is configured.")
