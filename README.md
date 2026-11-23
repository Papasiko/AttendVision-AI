# AttendVision AI

A privacy-conscious, web-based attendance management system built with **FastAPI**, **PostgreSQL**, **Next.js**, and an experimental local face-matching pipeline.

> **Project status:** Development / evaluation MVP. This repository is not a production-certified biometric attendance system. Face matching is experimental, requires human review, and must not be used as the sole basis for employment, disciplinary, or access-control decisions.

## Features

- Dashboard opens without a token prompt; a same-origin Next.js proxy attaches the administrator Bearer token server-side
- Employee management and individual attendance history
- Idempotent attendance event ingestion
- Three-minute duplicate suppression for repeated webcam submissions with the same employee and direction
- Human review queue with approval and rejection
- Daily attendance summaries, date-range reports, and CSV export
- Administrator-entered attendance corrections with an audit trail
- Audit logging for administrative actions
- Browser-based laptop webcam preview
- Explicit, operator-confirmed face enrollment
- YuNet face detection and SFace feature extraction
- Encrypted face templates; uploaded source frames are not intentionally persisted
- PostgreSQL with Alembic migrations
- Docker-based development environment

## Architecture

```text
Laptop webcam -> Browser capture -> Next.js server proxy -> FastAPI -> YuNet / SFace
                                      |
                                      v
                              Encrypted face template
                                      |
                                      v
                              PostgreSQL database
                                      |
                                      v
                         Pending attendance review
                                      |
                                      v
                              Admin dashboard
```

The browser does not continuously upload a video stream. Face enrollment captures a still frame only when the operator explicitly presses the enrollment action. Automatic recognition starts only after the operator explicitly presses **Start automatic scanning**; while that session is active, one still frame is submitted every three seconds. The API processes each uploaded image in memory and does not intentionally persist the raw frame. For enrolled employees, only an encrypted face feature template is stored. **This is not liveness detection:** the system does not verify that a face comes from a live person, so photos or screen replays may fool it.

## Requirements

- Docker Desktop with Docker Compose
- Git
- Node.js 20 or newer (for the dashboard)
- Python 3.11+ (only if running backend tools outside Docker)

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/Papasiko/AttendVision-AI.git
cd AttendVision-AI
```

### 2. Create local secrets

Generate a Fernet-compatible encryption key:

```bash
python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Copy `.env.example` to `.env` in the repository root, then replace every placeholder with a newly generated secret:

```dotenv
ADMIN_API_TOKEN=replace-with-a-long-random-admin-secret
DEVICE_API_TOKEN=replace-with-a-different-device-secret
POSTGRES_PASSWORD=replace-with-a-long-random-hex-password
BIOMETRIC_ENCRYPTION_KEY=paste-the-generated-fernet-key-here
FACE_MATCH_THRESHOLD=0.45
```

On Windows PowerShell, copy the template with `Copy-Item .env.example .env`; on macOS/Linux use `cp .env.example .env`. Generate secrets with a password manager or a cryptographically secure random generator. For the biometric key, use the Python command above. The API container will refuse to start if the required administrator, device, or database secrets are missing; do not use example values in a real environment.

Keep this file private. Never commit secrets or real employee biometric data. Back up the encryption key securely: encrypted templates cannot be recovered if the key is lost.

### 3. Start the API and database

```bash
docker compose up --build
```

The first build downloads the YuNet and SFace model files and may take several minutes. Keep the root `.env` file private. API documentation is available at:

- API health: http://localhost:8000/health
- OpenAPI docs: http://localhost:8000/docs

### 4. Start the dashboard

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The dashboard opens directly; there is no browser token prompt. For each API request, the Next.js server-side proxy first uses the server's `ADMIN_API_TOKEN` environment variable and otherwise reads `ADMIN_API_TOKEN` from the repository-root `.env` file. The token is added to the upstream request on the server and is not sent to browser JavaScript.

#### Windows PowerShell notes

From Windows PowerShell 5.1, use the Windows command shim if script execution blocks `npm`:

```powershell
cd C:\Users\<your-user>\AttendVision-AI
docker compose up -d --build
cd frontend
npm.cmd install
npm.cmd run dev
```

Keep the root `.env` file in the project root (next to `docker-compose.yml`), not inside `frontend`. It must contain a non-empty line in this format:

```dotenv
ADMIN_API_TOKEN=your-admin-secret
```

If the dashboard reports that `ADMIN_API_TOKEN` is missing, stop the Next.js process with `Ctrl+C`, confirm the root `.env` file and variable name, then restart `npm.cmd run dev`. Do not paste the secret into browser code or commit `.env` to Git.

## Laptop webcam workflow

1. Open the **Laptop Webcam** section in the dashboard.
2. Allow the browser to access the camera and select the intended webcam.
3. Create employee records in the **Employees** section.
4. Obtain and document the employee's informed, freely given consent through your organization's approved process.
5. With the camera preview running, select the employee and use **Enroll Face Template**. The checkbox in the UI is an operator attestation; it is not a substitute for a consent record or legal review.
6. For automatic scanning, select **Check-in** or **Check-out**, then explicitly press **Start automatic scanning**. While enabled, the browser submits one still frame every three seconds; press **Stop automatic scanning** or turn off the camera to end the session. The selected direction stays fixed until scanning is stopped and changed.
7. Automatic frames that do not match an enrolled employee do not create unidentified attendance rows. Matched employees create a pending candidate, with repeat matches suppressed for three minutes.
8. Review every candidate in the **Review Queue** before treating it as an attendance record. Administrators can also add a manual check-in or check-out from the Attendance page; the action requires a reason and is audited.

Camera access works on `localhost`. If the dashboard is accessed from another device, browsers generally require HTTPS to grant camera access.

## Scope

This project intentionally focuses on ordinary check-in/check-out attendance. Shift scheduling, lateness calculations, overtime, payroll, and complex HR workflows are out of scope.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/employees/{id}/face-enroll` | Enroll an employee face template |
| DELETE | `/api/v1/employees/{id}/face-template` | Delete an employee face template |
| POST | `/api/v1/face/recognize` | Create a recognition candidate for review |
| GET | `/api/v1/attendance/events` | List attendance events |
| PATCH | `/api/v1/attendance/events/{id}/review` | Approve or reject a candidate |
| GET | `/api/v1/reports/daily?day=YYYY-MM-DD` | Daily summary based on each employee's latest approved event |
| GET | `/api/v1/reports/period?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | Date-range event and review statistics |
| GET | `/api/v1/reports/export.csv?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | Server-generated UTF-8 CSV export (up to 367 days) |

All biometric endpoints require administrator authentication. Uploaded files must be JPEG, PNG, or WebP and no larger than 5 MB.

## Development and tests

From the `backend` directory:

```bash
pip install -e ".[dev]"
alembic upgrade head
pytest
ruff check .
```

From the `frontend` directory:

```bash
npm install
npm run lint
npm run build
```

## Security and privacy limitations

- This is an experimental implementation, not a certified biometric system.
- There is no presentation-attack detection (PAD) or liveness detection. Printed photos, screen replays, and other spoofing attacks may succeed.
- The default similarity threshold is a starting value only. It has not been calibrated for your camera, lighting, workforce, or operating environment.
- Similarity scores are not probabilities.
- Every recognition result is marked `pending` and requires a human reviewer.
- The browser currently sends a still image only after an explicit operator action; continuous background recognition is not implemented.
- The API still validates `ADMIN_API_TOKEN`; the same-origin Next.js proxy adds it server-side for dashboard and webcam requests, and the browser never receives the token.
- The dashboard has no interactive user sign-in. Anyone who can reach the dashboard can perform administrator actions; keep it on localhost or a trusted private network and do not expose it publicly.
- The dashboard has no interactive sign-in: anyone who can reach it can perform administrator actions. Keep it bound to localhost or a trusted private network and do not expose it publicly.
- The current administrator token is a simple shared secret, not a full user identity and role-management system.
- HTTPS, secret rotation, retention automation, incident response, and a formal biometric impact assessment are required before any real deployment.
- Provide a meaningful non-biometric attendance alternative.

Read [Privacy and Security](docs/PRIVACY_SECURITY.md), [Architecture](docs/ARCHITECTURE.md), and [Evaluation Plan](docs/EVALUATION.md) before enabling biometric processing.

## License

See [LICENSE](LICENSE).
