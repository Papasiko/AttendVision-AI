from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_employee_create_and_list():
    response = client.post("/api/v1/employees", json={"employee_code": "TEST-001", "full_name": "Test Employee", "department": "QA"})
    assert response.status_code in (201, 409)
    listing = client.get("/api/v1/employees")
    assert listing.status_code == 200
    assert isinstance(listing.json(), list)
