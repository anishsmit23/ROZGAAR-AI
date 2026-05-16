from __future__ import annotations

import asyncio
import io
import logging
import os
from dataclasses import dataclass

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _env_value(name: str, *, required: bool = False, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip():
        if required:
            raise RuntimeError(f"{name} must be configured")
        return ""
    return value.strip()


@dataclass(frozen=True)
class S3Settings:
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    bucket_resumes: str = "generated-resumes"
    region: str = "auto"


def _load_settings() -> S3Settings:
    return S3Settings(
        endpoint_url=_env_value("S3_ENDPOINT_URL", required=True),
        access_key_id=_env_value("S3_ACCESS_KEY_ID", required=True),
        secret_access_key=_env_value("S3_SECRET_ACCESS_KEY", required=True),
        bucket_resumes=_env_value("S3_BUCKET_RESUMES", default="generated-resumes"),
        region=_env_value("S3_REGION", default="auto"),
    )


class S3StorageClient:
    def __init__(self) -> None:
        self.settings = _load_settings()
        self.client = boto3.client(
            "s3",
            endpoint_url=self.settings.endpoint_url,
            aws_access_key_id=self.settings.access_key_id,
            aws_secret_access_key=self.settings.secret_access_key,
            region_name=self.settings.region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    @property
    def bucket(self) -> str:
        return self.settings.bucket_resumes

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in {"404", "NoSuchBucket", "NotFound", "301", "400"}:
                create_kwargs: dict[str, str] = {"Bucket": self.bucket}
                if self.settings.region and self.settings.region != "auto":
                    create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self.settings.region}
                self.client.create_bucket(**create_kwargs)
                logger.info("Created storage bucket: %s", self.bucket)
                return
            raise

    def upload_pdf(self, key: str, pdf_bytes: bytes) -> str:
        self.ensure_bucket()
        self.client.upload_fileobj(
            Fileobj=io.BytesIO(pdf_bytes),
            Bucket=self.bucket,
            Key=key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
        logger.info("Uploaded %s bytes to %s/%s", len(pdf_bytes), self.bucket, key)
        return key

    def get_presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        return self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
        logger.info("Deleted object %s/%s", self.bucket, key)


async def upload_pdf(key: str, pdf_bytes: bytes) -> str:
    client = S3StorageClient()
    return await asyncio.to_thread(client.upload_pdf, key, pdf_bytes)


async def get_presigned_url(key: str, expires_seconds: int = 3600) -> str:
    client = S3StorageClient()
    return await asyncio.to_thread(client.get_presigned_url, key, expires_seconds)


async def delete_object(key: str) -> None:
    client = S3StorageClient()
    await asyncio.to_thread(client.delete_object, key)


def ensure_bucket(bucket: str | None = None) -> None:
    client = S3StorageClient()
    if bucket and bucket != client.bucket:
        raise RuntimeError("Custom buckets are not supported by the storage wrapper")
    client.ensure_bucket()


def upload_file(filename: str, data: bytes, content_type: str = "application/pdf") -> None:
    client = S3StorageClient()
    if content_type != "application/pdf":
        logger.warning("upload_file ignores content_type and uploads as application/pdf")
    client.upload_pdf(filename, data)


def download_file(filename: str) -> bytes:
    client = S3StorageClient()
    response = client.client.get_object(Bucket=client.bucket, Key=filename)
    try:
        body = response["Body"]
        return body.read()
    finally:
        response["Body"].close()
