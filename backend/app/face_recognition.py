"""Local YuNet + SFace inference. Images are processed in memory and never persisted."""
import json
import os
from functools import lru_cache

import cv2
import numpy as np
from cryptography.fernet import Fernet, InvalidToken

YUNET_PATH = os.getenv("YUNET_MODEL_PATH", "/models/face_detection_yunet_2023mar.onnx")
SFACE_PATH = os.getenv("SFACE_MODEL_PATH", "/models/face_recognition_sface_2021dec.onnx")
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.45"))


class FaceEngineError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _engine():
    if not os.path.exists(YUNET_PATH) or not os.path.exists(SFACE_PATH):
        raise FaceEngineError("Face model files are missing. Rebuild the API image.")
    detector = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.85, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF_create(SFACE_PATH, "")
    return detector, recognizer


def extract_embedding(image_bytes: bytes) -> list[float]:
    if not image_bytes or len(image_bytes) > 5 * 1024 * 1024:
        raise FaceEngineError("Image must be between 1 byte and 5 MB.")
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FaceEngineError("Invalid image.")
    height, width = image.shape[:2]
    if width < 160 or height < 160:
        raise FaceEngineError("Image resolution is too low.")
    detector, recognizer = _engine()
    detector.setInputSize((width, height))
    _, faces = detector.detect(image)
    if faces is None or len(faces) != 1:
        raise FaceEngineError("Exactly one clear face must be visible.")
    face = faces[0]
    if float(face[-1]) < 0.90 or min(float(face[2]), float(face[3])) < 80:
        raise FaceEngineError("Face is too small or image quality is insufficient.")
    aligned = recognizer.alignCrop(image, face)
    feature = recognizer.feature(aligned).reshape(-1).astype(np.float32)
    norm = float(np.linalg.norm(feature))
    if norm == 0:
        raise FaceEngineError("Could not extract a face template.")
    return (feature / norm).astype(float).tolist()


def encrypt_template(embedding: list[float]) -> str:
    key = os.getenv("BIOMETRIC_ENCRYPTION_KEY", "")
    if not key:
        raise FaceEngineError("BIOMETRIC_ENCRYPTION_KEY is required before enrollment.")
    try:
        return Fernet(key.encode()).encrypt(json.dumps(embedding).encode()).decode()
    except (ValueError, TypeError) as exc:
        raise FaceEngineError("BIOMETRIC_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def decrypt_template(value: str) -> list[float]:
    key = os.getenv("BIOMETRIC_ENCRYPTION_KEY", "")
    if not key:
        raise FaceEngineError("BIOMETRIC_ENCRYPTION_KEY is not configured.")
    try:
        raw = Fernet(key.encode()).decrypt(value.encode())
        return json.loads(raw)
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise FaceEngineError("Could not decrypt stored face template.") from exc


def best_match(query: list[float], templates: list[tuple[int, str]]) -> tuple[int | None, float]:
    best_id, best_score = None, -1.0
    query_vector = np.asarray(query, dtype=np.float32)
    for employee_id, encrypted in templates:
        candidate = np.asarray(decrypt_template(encrypted), dtype=np.float32)
        score = float(np.dot(query_vector, candidate) / (np.linalg.norm(query_vector) * np.linalg.norm(candidate)))
        if score > best_score:
            best_id, best_score = employee_id, score
    if best_score < FACE_MATCH_THRESHOLD:
        return None, best_score
    return best_id, best_score
