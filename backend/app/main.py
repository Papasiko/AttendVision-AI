import json
from datetime import date, datetime, time, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
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
    version="0.2.0",
    description="Authenticated attendance operations API. Face inference is a separate, unvalidated edge integration.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
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
