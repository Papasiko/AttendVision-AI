# AttendVision AI

**Privacy-conscious, edge-first attendance platform with face-recognition integration points.**

AttendVision AI is an industrial-style portfolio project for a small workplace (initial target: fewer than 50 employees, one entrance camera). It demonstrates a maintainable architecture for camera ingestion, attendance workflows, reviewable recognition decisions, and operational reporting.

> **Status:** Foundation / MVP scaffold. This repository does not claim production-grade face recognition accuracy, liveness detection, or security certification. The vision adapter is deliberately an integration boundary until a model, representative evaluation dataset, and deployment hardware have been selected and validated.

## Product principles

- **Edge-first:** camera frames should be processed near the camera; only minimal events move to the application API.
- **Privacy by default:** no raw-frame retention by default; biometric templates are sensitive data and require an explicit lawful basis, informed notice/consent where applicable, encryption, retention limits, and deletion workflows before real deployment.
- **Human review:** uncertain matches and ambiguous entry/exit direction are review tasks, not automatic facts.
- **Auditable:** manual corrections and administrative actions are recorded.
- **Resilient:** idempotent event ingestion and a path for offline edge buffering.
- **Honest metrics:** accuracy, latency, and PAD claims must come from a documented evaluation, never placeholder numbers.

## Architecture

```text
IP camera (RTSP)
    |
    v
Edge AI node (OpenCV + detector/embedding adapter)
    |  signed, minimal attendance events
    v
FastAPI application ---- Redis (optional queue/cache)
    |
    v
PostgreSQL (employees, devices, shifts, events, audit)
    |
    v
Next.js web console
```

The initial repository provides a runnable API foundation and a web-console starting point. Model inference, RTSP capture, queue workers, and biometric enrollment are isolated follow-on modules; they are not represented as complete features yet.

## Repository layout

- `backend/` — FastAPI service, SQLAlchemy models, API schemas, tests
- `frontend/` — Next.js + TypeScript dashboard starter
- `vision/` — edge processing contract and safe placeholder adapter
- `docs/` — architecture, privacy, evaluation, and deployment notes
- `.github/workflows/` — CI checks

## Quick start (API)

Requirements: Python 3.11+

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> and <http://127.0.0.1:8000/health>.

The default development configuration uses SQLite. Set `DATABASE_URL` to a PostgreSQL URL for a deployment-like environment.

## Quick start (Docker)

```bash
docker compose up --build
```

API: <http://localhost:8000/health>. PostgreSQL is exposed on port 5432. The frontend is a separate app and can be started from `frontend/` with `npm install && npm run dev`.

## Configuration

Copy `backend/.env.example` to `backend/.env` and adjust values. Never commit secrets, real employee data, face images, or biometric templates.

## Security and privacy

This project is not a legal compliance guarantee. Before processing real biometric data, complete a jurisdiction-specific privacy/legal review, document the lawful basis, provide a meaningful non-biometric alternative, restrict access, encrypt biometric material, define retention/deletion, and conduct a DPIA where required. See [Privacy & Security](docs/PRIVACY_SECURITY.md).

## Development

```bash
cd backend
pip install -e ".[dev]"
pytest
ruff check .
```

CI is configured to run backend tests and lint checks. Frontend and end-to-end checks will be expanded as the UI grows.

## Roadmap

1. API foundation, health checks, employee/device/attendance data contracts
2. Authentication, RBAC, audit trail, migrations, and admin workflows
3. Edge camera ingestion and event signing/idempotency
4. Evaluated detector/embedding integration and PAD assessment
5. Shift rules, reports, review queue, and operational monitoring
6. Security hardening, load testing, deployment runbooks, and pilot

## License

MIT — see [LICENSE](LICENSE).
