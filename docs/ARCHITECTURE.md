# System Architecture

## Current development architecture

```text
Laptop webcam
    |
    | Browser permission + operator-triggered still capture
    v
Browser dashboard (Next.js)
    |
    | Same-origin /api/* request (JSON, CSV, or multipart image)
    v
Next.js server-side API proxy
    |
    | Reads ADMIN_API_TOKEN from server environment,
    | falling back to the repository-root .env file
    | Adds Authorization: Bearer ... server-side
    v
FastAPI service
    |
    +--> YuNet face detector
    |
    +--> SFace feature extractor
    |
    +--> Fernet encryption / decryption
    |
    v
PostgreSQL
    |
    +--> Employee records and encrypted face templates
    +--> Attendance event candidates
    +--> Administrative audit records
    |
    v
Human review queue
```

## API proxy and administrator-token flow

1. The browser opens the dashboard without an API-token login form.
2. Dashboard requests use same-origin paths such as `/api/v1/employees`, `/api/v1/attendance/events`, and `/api/v1/reports/export.csv`.
3. The catch-all Next.js route in `frontend/app/api/[...path]/route.ts` forwards the request to FastAPI.
4. The proxy obtains `ADMIN_API_TOKEN` from the Next.js server environment. If it is not set, the route reads the `ADMIN_API_TOKEN` entry from the repository-root `.env` file.
5. The proxy attaches the Bearer token to the upstream request. The secret is not embedded in browser bundles or returned in the proxy response.
6. FastAPI continues to validate the administrator token using its existing authentication dependency.

The proxy defaults to `http://127.0.0.1:8000`. Set `ATTENDVISION_API_URL` in the repository-root `.env` file to use a different API origin. Keep the root `.env` private and out of version control.

**This is tokenless dashboard access, not a full authentication system.** The dashboard does not identify individual operators. Anyone who can reach the dashboard can invoke the administrator proxy. Keep the development dashboard on localhost or a trusted private network; do not expose it publicly.

## Webcam capture lifecycle

1. An operator opens the webcam page and grants browser camera permission.
2. The operator starts the camera preview.
3. A still frame is captured for face enrollment or one-shot recognition only after the corresponding action is explicitly selected.
4. Automatic recognition starts only after the operator explicitly starts an automatic-scanning session.
5. While that session is active, the browser submits one still frame every three seconds through the same-origin Next.js API proxy.
6. The proxy forwards the multipart request to FastAPI and adds the administrator token server-side.
7. The API validates file type and size, decodes the image, and requires exactly one sufficiently large detected face.
8. YuNet detects the face and SFace extracts a normalized feature vector.
9. During enrollment, the feature vector is encrypted before it is stored.
10. During recognition, the vector is compared with active employees who have an enrolled template and recorded consent.
11. A matched candidate is stored with `pending` review status. Repeated webcam submissions for the same employee and direction are suppressed during the three-minute cooldown.
12. The original uploaded image is not stored by application code; an authorized administrator must review the candidate.

## Biometric data handling

- Raw image bytes are held in request memory for inference and are not written to application-managed storage.
- Face templates are encrypted using Fernet before persistence.
- The encryption key is supplied through `BIOMETRIC_ENCRYPTION_KEY`.
- The browser never receives stored biometric templates or the administrator API token.
- Deleting a template clears the stored template and consent metadata.
- Database backups, logs, crash dumps, reverse proxies, and infrastructure may have separate retention behaviour; production operators must review those systems too.

## Current limitations

- Automatic webcam scanning is operator-started and sends still frames every three seconds; it is not continuous video streaming.
- No liveness or presentation-attack detection.
- No calibrated threshold or independent accuracy evaluation.
- The three-minute cooldown is a basic duplicate guard, not a complete attendance policy.
- No production-grade identity provider, per-user RBAC, or signed device protocol.
- No automated biometric retention/deletion schedule.
- No production deployment or security certification.

## Production direction

A future edge deployment should perform capture and inference on a managed local node, use a durable event queue, sign device requests, and send only minimal attendance candidates to the API. A non-biometric fallback must remain available. Before a multi-user or public deployment, add individual authentication, role-based authorization, request protections, monitoring, and a documented security review.

## Product scope

The application intentionally implements ordinary employee check-in and check-out only. Shift scheduling, lateness, overtime, payroll, and complex HR workflows are out of scope. Administrators can inspect an employee's attendance history, review webcam-generated candidates, and enter a reasoned manual correction.
