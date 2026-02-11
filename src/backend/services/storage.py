"""
Proof-of-delivery storage abstraction.
Supports local filesystem (default) and AWS S3.
Controlled by PROOF_STORAGE env var: "local" or "s3".
"""

import os
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.backend.core.config import settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """Upload file data. Returns the storage key."""
        ...

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Get a URL to access the file."""
        ...

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[dict]:
        """List files with metadata. Returns list of dicts with keys: key, size, last_modified."""
        ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        file_path = os.path.join(self.base_dir, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        logger.info(f"Saved proof to local: {file_path}")
        return key

    def get_url(self, key: str) -> str:
        return f"/delivery/proof/{key}"

    def get_file_path(self, key: str) -> Optional[str]:
        """Local-only: return absolute file path for FileResponse."""
        path = os.path.join(self.base_dir, key)
        return path if os.path.exists(path) else None

    def list_files(self, prefix: str = "") -> List[dict]:
        if not os.path.exists(self.base_dir):
            return []
        results = []
        for f in os.listdir(self.base_dir):
            if not f.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            path = os.path.join(self.base_dir, f)
            stat = os.stat(path)
            results.append({
                "key": f,
                "size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime),
            })
        results.sort(key=lambda x: x["last_modified"], reverse=True)
        return results[:50]


class S3StorageBackend(StorageBackend):
    def __init__(self):
        import boto3
        client_kwargs = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
        }
        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        self.client = boto3.client("s3", **client_kwargs)
        self.bucket = settings.S3_BUCKET_NAME
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
                logger.info(f"Created S3 bucket: {self.bucket}")
            except Exception as e:
                logger.error(f"Failed to create S3 bucket: {e}")

    def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info(f"Uploaded proof to S3: s3://{self.bucket}/{key}")
        return key

    def get_url(self, key: str) -> str:
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=3600,
        )
        return url

    def list_files(self, prefix: str = "") -> List[dict]:
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=50,
            )
            results = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if not key.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                results.append({
                    "key": key,
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                })
            results.sort(key=lambda x: x["last_modified"], reverse=True)
            return results[:50]
        except Exception as e:
            logger.error(f"Failed to list S3 objects: {e}")
            return []


def _get_proofs_base_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "uploads", "proofs"
    )


def get_storage_backend() -> StorageBackend:
    if settings.PROOF_STORAGE == "s3" and settings.AWS_ACCESS_KEY_ID:
        logger.info("Using S3 storage backend for proofs")
        return S3StorageBackend()
    logger.info("Using local filesystem storage backend for proofs")
    return LocalStorageBackend(_get_proofs_base_dir())


proof_storage = get_storage_backend()
