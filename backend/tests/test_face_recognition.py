import base64
import secrets

import pytest
from cryptography.fernet import Fernet

from app.face_recognition import FaceEngineError, best_match, decrypt_template, encrypt_template


def test_face_template_is_encrypted_and_round_trips(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("BIOMETRIC_ENCRYPTION_KEY", key)
    embedding = [0.25, 0.5, 0.75]
    encrypted = encrypt_template(embedding)
    assert encrypted != str(embedding)
    assert decrypt_template(encrypted) == embedding


def test_face_template_requires_encryption_key(monkeypatch):
    monkeypatch.delenv("BIOMETRIC_ENCRYPTION_KEY", raising=False)
    with pytest.raises(FaceEngineError, match="required"):
        encrypt_template([1.0, 0.0])


def test_matching_returns_no_match_when_no_templates(monkeypatch):
    monkeypatch.setenv("FACE_MATCH_THRESHOLD", "0.45")
    employee_id, score = best_match([1.0, 0.0], [])
    assert employee_id is None
    assert score == -1.0


def test_matching_returns_best_candidate(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("BIOMETRIC_ENCRYPTION_KEY", key)
    monkeypatch.setenv("FACE_MATCH_THRESHOLD", "0.45")
    first = encrypt_template([1.0, 0.0, 0.0])
    second = encrypt_template([0.0, 1.0, 0.0])
    employee_id, score = best_match([0.99, 0.01, 0.0], [(10, first), (20, second)])
    assert employee_id == 10
    assert score > 0.99
