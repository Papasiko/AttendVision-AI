# Privacy and security baseline

Face recognition is biometric processing and may be legally restricted. This project is not legal advice or a compliance certification.

Before any real biometric use: obtain jurisdiction-specific legal review; document a valid lawful basis; provide clear notice and a usable non-biometric alternative; complete a DPIA where required; avoid raw-frame retention by default; encrypt biometric templates; restrict access; define retention and deletion; audit access; and implement incident response.

Authentication, RBAC, signed device ingestion, encrypted template storage, retention jobs, and deletion workflows are not yet implemented. Do not expose this API publicly or use it with real biometric data until these controls are implemented and reviewed. Never commit employee records, face images, embeddings, credentials, or production exports.
