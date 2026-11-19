from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.config import settings
import app.main as main_module
from app.main import app

settings.admin_api_token = "test-admin-token"
settings.device_api_token = "test-device-token"
client = TestClient(app)
ADMIN = {"Authorization": "Bearer test-admin-token"}
DEVICE = {"Authorization": "Bearer test-device-token"}


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_admin_routes_require_token():
    assert client.get("/api/v1/employees").status_code == 401
    assert client.get("/api/v1/employees", headers=ADMIN).status_code == 200


def test_employee_create_update_and_duplicate():
    code = f"TEST-{datetime.now(timezone.utc).timestamp()}"
    payload = {"employee_code": code, "full_name": "Test Employee", "department": "QA"}
    created = client.post("/api/v1/employees", json=payload, headers=ADMIN)
    assert created.status_code == 201
    employee_id = created.json()["id"]
    assert client.post("/api/v1/employees", json=payload, headers=ADMIN).status_code == 409
    updated = client.patch(
        f"/api/v1/employees/{employee_id}",
        json={"department": "Engineering"},
        headers=ADMIN,
    )
    assert updated.status_code == 200
    assert updated.json()["department"] == "Engineering"


def test_device_can_ingest_idempotent_events_and_admin_can_review():
    code = f"EVT-{datetime.now(timezone.utc).timestamp()}"
    employee = client.post(
        "/api/v1/employees",
        json={"employee_code": code, "full_name": "Review Test"},
        headers=ADMIN,
    )
    assert employee.status_code == 201
    event_payload = {
        "event_key": f"event-{datetime.now(timezone.utc).timestamp()}",
        "employee_id": employee.json()["id"],
        "direction": "in",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "confidence": 0.91,
        "source_device": "front-door",
    }
    first = client.post("/api/v1/attendance/events", json=event_payload, headers=DEVICE)
    second = client.post("/api/v1/attendance/events", json=event_payload, headers=DEVICE)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["review_status"] == "pending"
    reviewed = client.patch(
        f"/api/v1/attendance/events/{first.json()['id']}/review",
        json={"review_status": "approved", "note": "Verified by supervisor"},
        headers=ADMIN,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["review_status"] == "approved"
    history = client.get(
        f"/api/v1/attendance/events?employee_id={employee.json()['id']}",
        headers=ADMIN,
    )
    assert history.status_code == 200
    assert all(item["employee_id"] == employee.json()["id"] for item in history.json())



def test_daily_report_and_audit_endpoints():
    report = client.get("/api/v1/reports/daily", headers=ADMIN)
    assert report.status_code == 200
    assert "present" in report.json()
    audit = client.get("/api/v1/audit", headers=ADMIN)
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)


def test_period_report_and_csv_export():
    code = f"PERIOD-{datetime.now(timezone.utc).timestamp()}"
    employee = client.post(
        "/api/v1/employees",
        json={"employee_code": code, "full_name": "=1+1"},
        headers=ADMIN,
    )
    assert employee.status_code == 201
    employee_id = employee.json()["id"]
    occurred_at = datetime.now(timezone.utc).isoformat()
    manual = client.post(
        "/api/v1/attendance/manual",
        json={
            "employee_id": employee_id,
            "direction": "in",
            "occurred_at": occurred_at,
            "note": "=HYPERLINK(\"https://example.invalid\")",
        },
        headers=ADMIN,
    )
    assert manual.status_code == 201

    day = datetime.now(timezone.utc).date().isoformat()
    report = client.get(
        f"/api/v1/reports/period?start_date={day}&end_date={day}",
        headers=ADMIN,
    )
    assert report.status_code == 200
    assert report.json()["total_events"] >= 1
    assert report.json()["approved_events"] >= 1
    assert report.json()["employees_with_approved_events"] >= 1

    exported = client.get(
        f"/api/v1/reports/export.csv?start_date={day}&end_date={day}",
        headers=ADMIN,
    )
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
    assert "employee_code" in exported.text
    assert code in exported.text
    assert "'=1+1" in exported.text
    assert "'=HYPERLINK(" in exported.text


def test_automatic_face_scan_does_not_create_unidentified_events(monkeypatch):
    monkeypatch.setattr(main_module, "extract_embedding", lambda image: [1.0])
    monkeypatch.setattr(main_module, "best_match", lambda query, templates: (None, -1.0))
    before_ids = {
        event["id"]
        for event in client.get("/api/v1/attendance/events?limit=500", headers=ADMIN).json()
    }

    response = client.post(
        "/api/v1/face/recognize",
        data={"direction": "in", "auto_scan": "true"},
        files={"image": ("frame.jpg", b"frame", "image/jpeg")},
        headers=ADMIN,
    )

    assert response.status_code == 200
    assert response.json()["matched"] is False
    assert response.json()["event_id"] is None
    after_ids = {
        event["id"]
        for event in client.get("/api/v1/attendance/events?limit=500", headers=ADMIN).json()
    }
    assert after_ids == before_ids


def test_automatic_face_scan_creates_one_candidate_and_suppresses_repeats(monkeypatch):
    code = f"AUTO-{datetime.now(timezone.utc).timestamp()}"
    employee = client.post(
        "/api/v1/employees",
        json={"employee_code": code, "full_name": "Automatic Scan Test"},
        headers=ADMIN,
    )
    assert employee.status_code == 201
    employee_id = employee.json()["id"]
    monkeypatch.setattr(main_module, "extract_embedding", lambda image: [1.0])
    monkeypatch.setattr(main_module, "best_match", lambda query, templates: (employee_id, 0.99))

    payload = {
        "data": {"direction": "in", "auto_scan": "true"},
        "files": {"image": ("frame.jpg", b"frame", "image/jpeg")},
        "headers": ADMIN,
    }
    first = client.post("/api/v1/face/recognize", **payload)
    second = client.post("/api/v1/face/recognize", **payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["matched"] is True
    assert first.json()["review_status"] == "pending"
    assert second.json()["event_id"] == first.json()["event_id"]
    events = client.get(
        f"/api/v1/attendance/events?employee_id={employee_id}",
        headers=ADMIN,
    ).json()
    webcam_events = [event for event in events if event["source_device"] == "laptop-webcam"]
    assert len(webcam_events) == 1


def test_period_report_rejects_invalid_ranges():
    day = datetime.now(timezone.utc).date().isoformat()
    earlier = "2000-01-01"
    invalid = client.get(
        f"/api/v1/reports/period?start_date={day}&end_date={earlier}",
        headers=ADMIN,
    )
    assert invalid.status_code == 422
