# AttendVision Web Console

The Next.js dashboard connects to the FastAPI backend through a same-origin server-side API proxy.

## Dashboard features

- Opens directly without an API-token login form
- Employee creation and employee listing
- Daily overview, attendance history, and manual check-in / check-out
- Human review queue with approve / reject actions
- Daily summaries and date-range CSV export
- Laptop webcam preview, face-template enrollment, one-shot recognition, and operator-started automatic scanning

## How API access works

The browser sends dashboard requests to the Next.js application under `/api/...`. The catch-all route at `app/api/[...path]/route.ts` forwards those requests to FastAPI and adds the administrator Bearer token on the server.

For each request, the proxy uses `process.env.ADMIN_API_TOKEN` when present. Otherwise, it reads the `ADMIN_API_TOKEN` entry from the repository-root `.env` file. The secret is never embedded in browser JavaScript or returned to the browser.

The API still enforces administrator-token validation. This change removes manual token entry; it does not create individual user accounts or role-based access control.

## Run locally

Start Docker Desktop first, then open a PowerShell terminal at the repository root:

```powershell
docker compose up -d --build
```

Open a second terminal and start the dashboard:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

On macOS/Linux, use `npm install` and `npm run dev`.

Open [http://localhost:3000](http://localhost:3000). The dashboard should load directly without asking for an API token.

## Environment configuration

Keep the private `.env` file in the repository root, next to `docker-compose.yml`; do not put it in `frontend/`. At minimum, the root `.env` must contain the same administrator secret configured for the API:

```dotenv
ADMIN_API_TOKEN=your-admin-secret
```

The proxy connects to `http://127.0.0.1:8000` by default. To use a different API origin, set `ATTENDVISION_API_URL` in the root `.env` file, for example:

```dotenv
ATTENDVISION_API_URL=http://127.0.0.1:8000
```

Restart the Next.js process after changing environment configuration.

### Troubleshooting: ADMIN_API_TOKEN missing

1. Confirm that `.env` exists in the repository root, not in `frontend/`.
2. Confirm that the variable is spelled exactly `ADMIN_API_TOKEN` and has a non-empty value.
3. Stop the dashboard with `Ctrl+C` and restart it with `npm.cmd run dev` (PowerShell) or `npm run dev` (macOS/Linux).
4. Confirm Docker Desktop is running and the API container is healthy. A missing-token message is a Next.js proxy configuration issue; an API connection error indicates the backend may be unavailable.

Do not paste the token into browser code, screenshots, support requests, or Git commits.

## Access and security warning

There is no interactive sign-in on the dashboard. Anyone who can reach the dashboard can invoke administrator actions through its proxy. Keep it on localhost or a trusted private network; do not expose it to the public internet. Use a proper identity provider and per-user authorization before any multi-user or public deployment.

## Webcam notes

Camera access is supported on `localhost` and secure HTTPS origins. The browser uploads still frames only for explicit enrollment, one-shot recognition, or while an operator-started automatic-scanning session is active. During automatic scanning, one still frame is submitted every three seconds. Recognition candidates remain pending until reviewed. The experimental matcher has no liveness or presentation-attack detection and is not suitable as a reliable identity or access-control mechanism.

## Checks

```bash
npm run lint
npm run build
```
