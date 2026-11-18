# Privacy and Security

## Important notice

Face recognition is biometric processing and may be subject to strict legal requirements. This project is an experimental software implementation, not legal advice, a compliance assessment, or a security certification.

Do not enroll real employees until the organization has completed a jurisdiction-specific legal and privacy review.

## Data handling in this implementation

| Data | Handling |
|---|---|
| Webcam preview | Displayed locally in the browser |
| Enrollment / recognition frame | Sent only after an operator action; processed in API memory |
| Raw uploaded frame | Not intentionally persisted by application code |
| Face feature template | Encrypted with Fernet before database storage |
| Attendance candidate | Stored with pending review status |
| Administrative action | Recorded in the audit log |

Infrastructure outside the application (for example, reverse proxies, container logs, database backups, endpoint monitoring, and browser extensions) may have independent data retention. Review these systems before deployment.

## Required controls before real-world use

1. Obtain jurisdiction-specific legal advice and identify a valid lawful basis for biometric processing.
2. Provide clear notice and obtain valid, informed, freely given consent where consent is the applicable basis.
3. Offer an accessible non-biometric attendance alternative without disadvantage.
4. Complete a Data Protection Impact Assessment (DPIA) where required.
5. Define retention periods and deletion procedures for templates, events, backups, and audit records.
6. Restrict access to the API, database, encryption key, and backups.
7. Use HTTPS and secure secret management; rotate credentials and encryption keys through a documented process.
8. Implement per-user authentication, role-based authorization, rate limiting, monitoring, and incident response.
9. Validate model licensing and maintain model/version provenance.
10. Independently evaluate false matches, false non-matches, demographic performance, lighting, camera placement, and spoofing resistance.

## Known security limitations

- The current administrator authentication uses a shared Bearer token.
- There is no liveness or presentation-attack detection.
- A printed photograph or screen replay may be accepted as a face image.
- The default similarity threshold is not calibrated and is not a probability.
- Webcam recognition is operator-triggered, not an unattended access-control mechanism.
- The UI consent checkbox is an operator attestation, not proof of a legally valid consent process.
- The application does not currently implement automated retention expiry or deletion from backups.

Never use a recognition result as the sole basis for disciplinary, employment, payroll, or physical-access decisions. Human review and a non-biometric alternative are required.
