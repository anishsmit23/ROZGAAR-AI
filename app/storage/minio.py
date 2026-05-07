from __future__ import annotations

import io

from minio import Minio

from app.config import settings

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,
)


def ensure_bucket():
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)


def upload_file(filename: str, data: bytes, content_type: str = "application/pdf"):
    ensure_bucket()
    client.put_object(
        settings.MINIO_BUCKET,
        filename,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def download_file(filename: str) -> bytes:
    response = client.get_object(settings.MINIO_BUCKET, filename)
    return response.read()


def get_minio_client() -> Minio:
    return client
