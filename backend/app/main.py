from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Base, engine, get_db
from app.models import AttendanceEvent, Device, Employee
from app.schemas import AttendanceEventCreate, AttendanceEventRead, DeviceCreate, DeviceRead, EmployeeCreate, EmployeeRead

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AttendVision AI API", version="0.1.0", description="Attendance workflow API; inference runs in a separate edge adapter.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "attendvision-api", "environment": settings.app_env}

@app.get("/api/v1/employees", response_model=list[EmployeeRead], tags=["employees"])
def list_employees(db: Session = Depends(get_db)):
    return db.scalars(select(Employee).order_by(Employee.full_name)).all()

@app.post("/api/v1/employees", response_model=EmployeeRead, status_code=201, tags=["employees"])
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    employee = Employee(**payload.model_dump())
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="employee_code already exists")
    db.refresh(employee)
    return employee

@app.get("/api/v1/devices", response_model=list[DeviceRead], tags=["devices"])
def list_devices(db: Session = Depends(get_db)):
    return db.scalars(select(Device).order_by(Device.name)).all()

@app.post("/api/v1/devices", response_model=DeviceRead, status_code=201, tags=["devices"])
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

@app.get("/api/v1/attendance/events", response_model=list[AttendanceEventRead], tags=["attendance"])
def list_events(limit: int = 100, db: Session = Depends(get_db)):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return db.scalars(select(AttendanceEvent).order_by(AttendanceEvent.occurred_at.desc()).limit(limit)).all()

@app.post("/api/v1/attendance/events", response_model=AttendanceEventRead, status_code=201, tags=["attendance"])
def ingest_event(payload: AttendanceEventCreate, db: Session = Depends(get_db)):
    if payload.direction not in {"in", "out", "unknown"}:
        raise HTTPException(status_code=422, detail="direction must be in, out, or unknown")
    if payload.employee_id is not None and db.get(Employee, payload.employee_id) is None:
        raise HTTPException(status_code=404, detail="employee not found")
    existing = db.scalar(select(AttendanceEvent).where(AttendanceEvent.event_key == payload.event_key))
    if existing:
        return existing
    event = AttendanceEvent(**payload.model_dump(), review_status="pending")
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(AttendanceEvent).where(AttendanceEvent.event_key == payload.event_key))
        if existing:
            return existing
        raise
    db.refresh(event)
    return event
