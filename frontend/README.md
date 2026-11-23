# AttendVision Web Console

The Next.js dashboard is connected to the FastAPI backend and provides:

- No dashboard token prompt; the Next.js server-side proxy attaches the API Bearer token without exposing it to browser code
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

Open http://localhost:3000. The dashboard opens directly and reads `ADMIN_API_TOKEN` from the repository-root `.env` file on the Next.js server. No token is entered in the browser.

The server-side proxy connects to `http://127.0.0.1:8000` by default. Set `ATTENDVISION_API_URL` in the repository-root `.env` if the API is hosted elsewhere. The administrator token is never sent to browser JavaScript.

> **Access note:** The dashboard has no interactive sign-in. Anyone who can reach the dashboard can perform administrator actions. Keep it on localhost or a trusted private network; do not expose it publicly.

## Webcam notes

Camera access is supported on `localhost` and secure HTTPS origins. The browser sends a still frame only after the operator presses an action button. Recognition candidates remain pending until an administrator reviews them. This experimental matcher has no liveness or presentation-attack detection and must not be treated as a reliable identity or access-control system.

## Checks

```bash
npm run lint
npm run build
```
