# System Architecture

## Current development architecture

```text
Laptop webcam
    |
    | Browser permission + operator-triggered still capture
    v
Next.js dashboard
    |
    | HTTPS in deployed environments
    | Multipart image upload + administrator Bearer token
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

## Webcam capture lifecycle

1. An administrator opens the webcam page.
2. The browser requests camera permission using `getUserMedia`.
3. The operator starts the camera preview.
4. A still frame is captured only after an explicit enrollment or recognition action.
5. The browser uploads the still frame to the API as multipart form data.
6. The API validates file type and size, decodes the image, and requires exactly one sufficiently large detected face.
7. YuNet detects the face and SFace extracts a normalized feature vector.
8. During enrollment, the feature vector is encrypted before it is stored.
9. During recognition, the vector is compared with active employees who have an enrolled template and recorded consent.
10. A candidate attendance event is created with `pending` review status. The original uploaded image is not stored by application code.
11. An authorized administrator must review the candidate.

## Biometric data handling

- Raw image bytes are held in request memory for inference and are not written to application-managed storage.
- Face templates are encrypted using Fernet before persistence.
- The encryption key is supplied through `BIOMETRIC_ENCRYPTION_KEY`.
- The browser never receives stored biometric templates.
- Deleting a template clears the stored template and consent metadata.
- Database backups, logs, crash dumps, reverse proxies, and infrastructure may have separate retention behavior; production operators must review those systems too.

## Current limitations

- Browser-triggered still-image capture only; no continuous recognition loop.
- No liveness or presentation-attack detection.
- No calibrated threshold or independent accuracy evaluation.
- A three-minute cooldown suppresses repeated webcam candidates for the same employee, direction, and laptop-webcam source; this is a basic duplicate guard, not a complete shift or attendance policy.
- No multi-frame temporal confirmation or duplicate-event suppression for webcam recognition.
- No production-grade identity provider, per-user RBAC, or signed device protocol.
- No automated biometric retention/deletion schedule.
- No production deployment or security certification.

## Production direction

A future edge deployment should perform capture and inference on a managed local node, use a durable event queue, sign device requests, and send only minimal attendance candidates to the API. A non-biometric fallback must remain available.

## Product scope

The application intentionally implements ordinary employee check-in and check-out only. Shift scheduling, lateness, overtime, payroll, and complex HR workflows are out of scope. Administrators can inspect an employee's attendance history, review webcam-generated candidates, and enter a reasoned manual correction.
