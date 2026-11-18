# AttendVision Web Console

The Next.js dashboard is connected to the FastAPI backend and provides:

- Administrator sign-in using the configured Bearer token
- Employee creation and employee listing
- Daily overview and attendance history
- Manual check-in / check-out with a required reason
- Pending recognition review with approve / reject actions
- Daily summaries and date-range CSV export
- Explicitly operator-triggered laptop webcam capture and face-template enrollment

## Run locally

Start the API and PostgreSQL from the repository root first:

```bash
docker compose up --build
```

Then, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and sign in with the `ADMIN_API_TOKEN` value from the root `.env` file.

The dashboard uses `NEXT_PUBLIC_API_URL` when provided; otherwise it connects to `http://localhost:8000`. Set this variable at build time if the API is hosted elsewhere.

## Webcam notes

Camera access is supported on `localhost` and secure HTTPS origins. The browser sends a still frame only after the operator presses an action button. Recognition candidates remain pending until an administrator reviews them. This experimental matcher has no liveness or presentation-attack detection and must not be treated as a reliable identity or access-control system.

## Checks

```bash
npm run lint
npm run build
```
