import csv
import io
import json
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.face_recognition import FaceEngineError, best_match, encrypt_template, extract_embedding
from app.face_schemas import FaceEnrollmentResult, FaceRecognitionResult
from app.models import AttendanceEvent, AuditLog, Device, Employee
from app.schemas import (
    AttendanceEventCreate,
    AttendanceEventRead,
    AttendanceReview,
    DeviceCreate,
    DeviceRead,
    DeviceUpdate,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    ManualAttendanceCreate,
)
from app.security import require_admin, require_ingest_access

Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="AttendVision AI API",
    version="0.3.0",
    description="Authenticated attendance API with experimental local webcam face matching and mandatory human review.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def audit(db: Session, actor: str, action: str, entity_type: str, entity_id: str, details: str | None = None):
    db.add(AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
    ))


def day_bounds(day: date):
    return (
        datetime.combine(day, time.min, tzinfo=timezone.utc),
        datetime.combine(day, time.max, tzinfo=timezone.utc),
    )


@app.post("/api/v1/employees/{employee_id}/face-enroll", response_model=FaceEnrollmentResult, tags=["biometrics"])
async def enroll_employee_face(
    employee_id: int,
    consent: bool = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    if employee.status != "active":
        raise HTTPException(status_code=409, detail="only active employees can be enrolled")
    if consent is not True:
        raise HTTPException(status_code=400, detail="explicit biometric consent is required")
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="upload a JPEG, PNG, or WebP image")
    raw = await image.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="image exceeds 5 MB")
    try:
        encrypted = encrypt_template(extract_embedding(raw))
    except FaceEngineError as exc:
        status_code = 503 if "model" in str(exc).lower() or "key" in str(exc).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    employee.face_template = encrypted
    employee.face_consent = True
    employee.face_consent_at = datetime.now(timezone.utc)
    audit(db, actor, "employee.face_enrolled", "employee", employee_id, "Encrypted template stored; source image discarded")
    db.commit()
    return FaceEnrollmentResult(employee_id=employee_id, enrolled=True, message="قالب رمزنگاری‌شده ثبت شد؛ تصویر خام ذخیره نشد.")


@app.delete("/api/v1/employees/{employee_id}/face-template", tags=["biometrics"])
def delete_employee_face(
    employee_id: int,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    employee.face_template = None
    employee.face_consent = False
    employee.face_consent_at = None
    audit(db, actor, "employee.face_deleted", "employee", employee_id, "Biometric template and consent flag deleted")
    db.commit()
    return {"deleted": True, "employee_id": employee_id}


@app.post("/api/v1/face/recognize", response_model=FaceRecognitionResult, tags=["biometrics"])
async def recognize_face(
    direction: str = Form(..., pattern="^(in|out)$"),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="upload a JPEG, PNG, or WebP image")
    raw = await image.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="image exceeds 5 MB")
    try:
        query_embedding = extract_embedding(raw)
        enrolled = db.scalars(
            select(Employee).where(
                Employee.status == "active",
                Employee.face_consent.is_(True),
                Employee.face_template.is_not(None),
            )
        ).all()
        matched_id, score = best_match(
            query_embedding,
            [(employee.id, employee.face_template) for employee in enrolled if employee.face_template],
        )
    except FaceEngineError as exc:
        status_code = 503 if "model" in str(exc).lower() or "key" in str(exc).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    employee = db.get(Employee, matched_id) if matched_id is not None else None
    now = datetime.now(timezone.utc)

    # Avoid repeated webcam submissions creating multiple attendance candidates
    # for the same employee and direction during a short cooldown window.
    if employee is not None:
        cooldown_start = now - timedelta(minutes=3)
        duplicate = db.scalar(
            select(AttendanceEvent)
            .where(
                AttendanceEvent.employee_id == employee.id,
                AttendanceEvent.direction == direction,
                AttendanceEvent.source_device == "laptop-webcam",
                AttendanceEvent.occurred_at >= cooldown_start,
                AttendanceEvent.review_status.in_(["pending", "approved"]),
            )
            .order_by(AttendanceEvent.occurred_at.desc())
            .limit(1)
        )
        if duplicate is not None:
            return FaceRecognitionResult(
                matched=True,
                employee_id=employee.id,
                employee_name=employee.full_name,
                score=round(max(0.0, score), 4),
                event_id=duplicate.id,
                review_status=duplicate.review_status,
                message="A recent event already exists for this employee and direction; duplicate submission was suppressed.",
            )

    event = AttendanceEvent(
        event_key=f"webcam-{uuid.uuid4().hex}",
        employee_id=matched_id,
        direction=direction if matched_id is not None else "unknown",
        occurred_at=now,
        confidence=max(0.0, score),
        review_status="pending",
        source_device="laptop-webcam",
        note=f"Face match candidate score={score:.4f}; requires human review" if employee else "No enrolled face matched; requires manual identification",
    )
    db.add(event)
    db.flush()
    audit(db, actor, "face.recognition_candidate", "attendance_event", event.id, f"matched={matched_id is not None}; score={score:.4f}")
    db.commit()
    return FaceRecognitionResult(
        matched=employee is not None,
        employee_id=employee.id if employee else None,
        employee_name=employee.full_name if employee else None,
        score=round(max(0.0, score), 4),
        event_id=event.id,
        review_status="pending",
        message="نامزد شناسایی ثبت شد و باید توسط مدیر بازبینی شود." if employee else "چهره‌ای تطبیق داده نشد؛ رویداد برای شناسایی دستی ثبت شد.",
    )

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "attendvision-api", "environment": settings.app_env}


@app.get("/api/v1/auth/check", tags=["auth"])
def auth_check(actor: str = Depends(require_admin)):
    return {"authenticated": True, "role": actor}


@app.get("/api/v1/employees", response_model=list[EmployeeRead], tags=["employees"])
def list_employees(
    q: str | None = None,
    status: str | None = Query(default=None, pattern="^(active|inactive)$"),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    query = select(Employee)
    if q:
        query = query.where(
            Employee.full_name.ilike(f"%{q}%") | Employee.employee_code.ilike(f"%{q}%")
        )
    if status:
        query = query.where(Employee.status == status)
    return db.scalars(query.order_by(Employee.full_name)).all()


@app.post("/api/v1/employees", response_model=EmployeeRead, status_code=201, tags=["employees"])
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    employee = Employee(**payload.model_dump())
    db.add(employee)
    try:
        audit(db, actor, "employee.created", "employee", "new", payload.employee_code)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="employee_code already exists")
    db.refresh(employee)
    return employee


@app.patch("/api/v1/employees/{employee_id}", response_model=EmployeeRead, tags=["employees"])
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(employee, key, value)
    audit(db, actor, "employee.updated", "employee", employee_id, json.dumps(changes))
    db.commit()
    db.refresh(employee)
    return employee


@app.get("/api/v1/devices", response_model=list[DeviceRead], tags=["devices"])
def list_devices(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return db.scalars(select(Device).order_by(Device.name)).all()


@app.post("/api/v1/devices", response_model=DeviceRead, status_code=201, tags=["devices"])
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    device = Device(**payload.model_dump(), status="pending")
    db.add(device)
    db.flush()
    audit(db, actor, "device.created", "device", device.id, payload.name)
    db.commit()
    db.refresh(device)
    return device


@app.patch("/api/v1/devices/{device_id}", response_model=DeviceRead, tags=["devices"])
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(device, key, value)
    audit(db, actor, "device.updated", "device", device_id, json.dumps(changes))
    db.commit()
    db.refresh(device)
    return device


@app.get("/api/v1/attendance/events", response_model=list[AttendanceEventRead], tags=["attendance"])
def list_events(
    limit: int = Query(default=100, ge=1, le=500),
    day: date | None = None,
    review_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    query = select(AttendanceEvent)
    if day:
        start, end = day_bounds(day)
        query = query.where(AttendanceEvent.occurred_at >= start, AttendanceEvent.occurred_at <= end)
    if review_status:
        query = query.where(AttendanceEvent.review_status == review_status)
    return db.scalars(query.order_by(AttendanceEvent.occurred_at.desc()).limit(limit)).all()


@app.post("/api/v1/attendance/events", response_model=AttendanceEventRead, status_code=201, tags=["attendance"])
def ingest_event(
    payload: AttendanceEventCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_ingest_access),
):
    if payload.employee_id is not None and db.get(Employee, payload.employee_id) is None:
        raise HTTPException(status_code=404, detail="employee not found")
    existing = db.scalar(select(AttendanceEvent).where(AttendanceEvent.event_key == payload.event_key))
    if existing:
        return existing
    event = AttendanceEvent(**payload.model_dump(), review_status="pending")
    db.add(event)
    try:
        db.flush()
        audit(db, actor, "attendance.ingested", "attendance_event", event.id, payload.event_key)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(AttendanceEvent).where(AttendanceEvent.event_key == payload.event_key))
        if existing:
            return existing
        raise
    db.refresh(event)
    return event


@app.post("/api/v1/attendance/manual", response_model=AttendanceEventRead, status_code=201, tags=["attendance"])
def manual_attendance(
    payload: ManualAttendanceCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    event = AttendanceEvent(
        event_key=f"manual-{datetime.now(timezone.utc).timestamp()}-{payload.employee_id}",
        employee_id=payload.employee_id,
        direction=payload.direction,
        occurred_at=payload.occurred_at,
        review_status="approved",
        source_device="manual",
        note=payload.note,
    )
    db.add(event)
    db.flush()
    audit(db, actor, "attendance.manual", "attendance_event", event.id, payload.note)
    db.commit()
    db.refresh(event)
    return event


@app.get("/api/v1/attendance/review", response_model=list[AttendanceEventRead], tags=["review"])
def review_queue(
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    return db.scalars(
        select(AttendanceEvent)
        .where(AttendanceEvent.review_status == "pending")
        .order_by(AttendanceEvent.occurred_at.desc())
        .limit(limit)
    ).all()


@app.patch("/api/v1/attendance/events/{event_id}/review", response_model=AttendanceEventRead, tags=["review"])
def review_event(
    event_id: int,
    payload: AttendanceReview,
    db: Session = Depends(get_db),
    actor: str = Depends(require_admin),
):
    event = db.get(AttendanceEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="attendance event not found")
    if event.review_status != "pending":
        raise HTTPException(status_code=409, detail="only pending events can be reviewed")
    event.review_status = payload.review_status
    if payload.note:
        event.note = payload.note
    audit(db, actor, f"attendance.{payload.review_status}", "attendance_event", event_id, payload.note)
    db.commit()
    db.refresh(event)
    return event


@app.get("/api/v1/reports/daily", tags=["reports"])
def daily_report(
    day: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    start, end = day_bounds(day)
    active = db.scalar(select(func.count(Employee.id)).where(Employee.status == "active")) or 0
    events = db.scalars(
        select(AttendanceEvent)
        .where(AttendanceEvent.occurred_at >= start, AttendanceEvent.occurred_at <= end)
        .order_by(AttendanceEvent.occurred_at.desc())
    ).all()
    latest_by_employee: dict[int, AttendanceEvent] = {}
    for event in events:
        if event.employee_id is not None and event.review_status == "approved":
            latest_by_employee.setdefault(event.employee_id, event)
    present = sum(1 for event in latest_by_employee.values() if event.direction == "in")
    pending = sum(1 for event in events if event.review_status == "pending")
    return {
        "date": day.isoformat(),
        "active_employees": active,
        "present": present,
        "absent": max(active - present, 0),
        "pending_review": pending,
        "events_today": len(events),
    }



@app.get("/api/v1/reports/period", tags=["reports"])
def period_report(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if (end_date - start_date).days > 366:
        raise HTTPException(status_code=422, detail="date range cannot exceed 367 days")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    rows = db.execute(
        select(AttendanceEvent, Employee.full_name, Employee.employee_code)
        .outerjoin(Employee, Employee.id == AttendanceEvent.employee_id)
        .where(AttendanceEvent.occurred_at >= start, AttendanceEvent.occurred_at < end)
        .order_by(AttendanceEvent.occurred_at.desc())
    ).all()
    approved = sum(1 for event, _, _ in rows if event.review_status == "approved")
    pending = sum(1 for event, _, _ in rows if event.review_status == "pending")
    rejected = sum(1 for event, _, _ in rows if event.review_status == "rejected")
    unique_employees = len({event.employee_id for event, _, _ in rows if event.employee_id is not None and event.review_status == "approved"})
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_events": len(rows),
        "approved_events": approved,
        "pending_events": pending,
        "rejected_events": rejected,
        "employees_with_approved_events": unique_employees,
    }


@app.get("/api/v1/reports/export.csv", tags=["reports"])
def export_attendance_csv(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if (end_date - start_date).days > 366:
        raise HTTPException(status_code=422, detail="date range cannot exceed 367 days")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    rows = db.execute(
        select(AttendanceEvent, Employee.full_name, Employee.employee_code)
        .outerjoin(Employee, Employee.id == AttendanceEvent.employee_id)
        .where(AttendanceEvent.occurred_at >= start, AttendanceEvent.occurred_at < end)
        .order_by(AttendanceEvent.occurred_at.asc())
    ).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["event_id", "employee_code", "employee_name", "direction", "occurred_at_utc", "review_status", "source_device", "similarity_score", "note"])
    def safe_cell(value):
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
            return "\u0027" + value
        return value
    for event, full_name, employee_code in rows:
        writer.writerow([
            event.id,
            safe_cell(employee_code or ""),
            safe_cell(full_name or "Unidentified"),
            event.direction,
            event.occurred_at.isoformat(),
            event.review_status,
            safe_cell(event.source_device or ""),
            event.confidence if event.confidence is not None else "",
            safe_cell(event.note or ""),
        ])
    filename = f"attendvision-{start_date.isoformat()}-to-{end_date.isoformat()}.csv"
    return Response(
        content="\\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/v1/audit", tags=["audit"])
def list_audit(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": row.id,
            "actor": row.actor,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": row.details,
            "created_at": row.created_at,
        }
        for row in rows
    ]
