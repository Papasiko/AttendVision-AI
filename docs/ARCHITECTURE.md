# Architecture

Camera (RTSP) -> Edge AI node -> FastAPI -> PostgreSQL -> Next.js console.

The edge node is responsible for local capture, detection/tracking, temporal confirmation, and retry buffering. The API validates device events and enforces event-key idempotency. PostgreSQL stores operational records. The browser must never receive biometric templates.

## Event lifecycle

1. Camera frame is sampled locally.
2. Edge node creates a candidate after quality and temporal checks.
3. Direction is in, out, or unknown; uncertain cases remain reviewable.
4. Edge node posts a stable event_key and retries with that same key.
5. API stores the event as pending review.
6. An authorized reviewer confirms or corrects it (workflow planned).

Production work still required: authentication, RBAC, device request signatures, migrations, durable edge queue, metrics, monitoring, and review workflows.
