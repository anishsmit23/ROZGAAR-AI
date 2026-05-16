"""
Backward-compatible MinIO storage client using boto3 S3-compatible API.

This module provides a MinIO-like interface but uses the new boto3-based
S3-compatible storage client. It's maintained for backward compatibility
with existing tests. New code should use minio_client.py directly.
"""
import io
import logging
from pathlib import Path

from app.storage.minio_client import S3StorageClient

logger = logging.getLogger(__name__)

# Global S3 storage client (initialized lazily)
_storage_client: S3StorageClient | None = None


def get_storage_client() -> S3StorageClient:
    """Get or create the S3 storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = S3StorageClient()
    return _storage_client


def ensure_bucket(bucket: str) -> None:
    """Ensure bucket exists, create if not."""
    import asyncio
    
    client = get_storage_client()
    try:
        asyncio.run(client.ensure_bucket(bucket))
        logger.info(f"Ensured bucket exists: {bucket}")
    except Exception as exc:
        logger.error(f"Failed to ensure bucket {bucket}: {exc}")
        raise


def upload_bytes(
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload bytes to S3-compatible storage.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
        data: Binary data to upload
        content_type: MIME type (default: application/octet-stream)
    
    Returns:
        Object name/key that was uploaded
    """
    import asyncio
    
    client = get_storage_client()
    try:
        asyncio.run(client.upload_pdf(object_name, data))
        logger.info(f"Uploaded {object_name} to {bucket}")
        return object_name
    except Exception as exc:
        logger.error(f"Failed to upload {object_name} to {bucket}: {exc}")
        raise


def download_bytes(bucket: str, object_name: str) -> bytes:
    """
    Download bytes from S3-compatible storage.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
    
    Returns:
        Binary data downloaded from storage
    """
    import asyncio
    
    client = get_storage_client()
    # Note: Actual download implementation would require adding a method to S3StorageClient
    # For now, this is a placeholder that raises NotImplementedError
    raise NotImplementedError("Use S3StorageClient directly for download operations")


def get_presigned_url(bucket: str, object_name: str, expires: int = 3600) -> str:
    """
    Generate a presigned URL for accessing an object.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
        expires: Expiration time in seconds (default: 3600)
    
    Returns:
        Presigned URL string
    """
    import asyncio
    
    client = get_storage_client()
    try:
        url = asyncio.run(client.get_presigned_url(object_name, expires))
        logger.info(f"Generated presigned URL for {object_name}")
        return url
    except Exception as exc:
        logger.error(f"Failed to generate presigned URL for {object_name}: {exc}")
        raise


def delete_object(bucket: str, object_name: str) -> None:
    """
    Delete an object from S3-compatible storage.
    
    Args:
        bucket: Bucket name
        object_name: Object key/path
    """
    import asyncio
    
    client = get_storage_client()
    try:
        asyncio.run(client.delete_object(object_name))
        logger.info(f"Deleted {object_name} from {bucket}")
    except Exception as exc:
        logger.error(f"Failed to delete {object_name} from {bucket}: {exc}")
        raise


class MinIOClient:
    """
    Backward-compatible MinIO client using boto3 S3-compatible API.
    
    Deprecated: Use S3StorageClient from minio_client.py directly.
    This class is maintained for backward compatibility with existing tests.
    """
    
    def __init__(self):
        """Initialize MinIO client."""
        self.client = get_storage_client()
    
    def ensure_bucket(self, bucket: str) -> None:
        """Ensure bucket exists, create if not."""
        ensure_bucket(bucket)
    
    def upload_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to MinIO."""
        return upload_bytes(bucket, object_name, data, content_type)
    
    def get_presigned_url(self, bucket: str, object_name: str, expires: int = 3600) -> str:
        """Generate presigned URL."""
        return get_presigned_url(bucket, object_name, expires)
    
    def delete_object(self, bucket: str, object_name: str) -> None:
        """Delete object from MinIO."""
        delete_object(bucket, object_name)



def upload_file(filename: str, data: bytes, content_type: str = "application/pdf"):
    ensure_bucket()
    client.put_object(
        get_settings().minio_bucket,
        filename,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def download_file(filename: str) -> bytes:
    response = client.get_object(get_settings().minio_bucket, filename)
    return response.read()
