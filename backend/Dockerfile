FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml requirements-face.txt ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
RUN pip install --no-cache-dir . && pip install --no-cache-dir -r requirements-face.txt
RUN mkdir -p /models && \
    curl -fL "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -o /models/face_detection_yunet_2023mar.onnx && \
    curl -fL "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" -o /models/face_recognition_sface_2021dec.onnx
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
