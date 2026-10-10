"""
Proof-of-delivery photo storage.

Backends:
  - R2ProofStorage:    Cloudflare R2 (S3-compatible API). Used automatically
                       when all R2_* environment variables are set.
                       Survives redeploys. Production backend.
  - LocalProofStorage: Local disk under src/uploads/proofs. Development
                       fallback only -- ephemeral on Railway.

Filenames: {package_id}_{driver_id}_{utc_timestamp}.jpg
The timestamp suffix means a redelivery attempt NEVER overwrites the
photographic evidence of a prior attempt.
"""
import asyncio
import os
import re
from datetime import datetime, timezone
from typing import List, Optional

from src.backend.core.config import settings

ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")

_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9\-]")


def sanitize_component(value: str) -> str:
    """Make an ID safe for use inside a filename/object key."""
    cleaned = _SAFE_COMPONENT.sub("-", (value or "").strip())
    return cleaned[:64] or "unknown"


def is_safe_filename(filename: str) -> bool:
    """Reject path traversal and unexpected extensions."""
    if not filename:
        return False
    if "/" in filename or "\\" in filename or ".." in filename:
        return False
    return filename.lower().endswith(ALLOWED_EXTENSIONS)


def parse_proof_meta(filename: str) -> dict:
    parts = filename.rsplit(".", 1)[0].split("_")
    return {
        "packageId": parts[0] if len(parts) > 0 else "Unknown",
        "driverId": parts[1] if len(parts) > 1 else "Unknown",
    }


def build_proof_filename(package_id: str, driver_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return "{0}_{1}_{2}.jpg".format(
        sanitize_component(package_id), sanitize_component(driver_id), stamp
    )


class LocalProofStorage:
    """Development fallback. Ephemeral on Railway -- do not rely on in prod."""

    def __init__(self) -> None:
        self.base_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "uploads",
            "proofs",
        )

    async def save_proof(
        self, package_id: str, driver_id: str, content: bytes
    ) -> str:
        filename = build_proof_filename(package_id, driver_id)
        os.makedirs(self.base_dir, exist_ok=True)
        path = os.path.join(self.base_dir, filename)
        with open(path, "wb") as handle:
            handle.write(content)
        return filename

    async def get_proof(self, filename: str) -> Optional[bytes]:
        if not is_safe_filename(filename):
            return None
        path = os.path.join(self.base_dir, filename)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as handle:
            return handle.read()

    async def list_recent(self, limit: int = 50) -> List[dict]:
        if not os.path.isdir(self.base_dir):
            return []
        items = []
        for name in os.listdir(self.base_dir):
            if not name.lower().endswith(ALLOWED_EXTENSIONS):
                continue
            path = os.path.join(self.base_dir, name)
            stat = os.stat(path)
            meta = parse_proof_meta(name)
            items.append(
                {
                    "packageId": meta["packageId"],
                    "driverId": meta["driverId"],
                    "timestamp": datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(),
                    "filename": name,
                    "url": "/delivery/proof/" + name,
                }
            )
        items.sort(key=lambda item: item["timestamp"], reverse=True)
        return items[:limit]


class R2ProofStorage:
    """Cloudflare R2 via the S3-compatible API (boto3)."""

    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = settings.R2_BUCKET_NAME
        self._client = boto3.client(
            "s3",
            endpoint_url="https://{0}.r2.cloudflarestorage.com".format(
                settings.R2_ACCOUNT_ID
            ),
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    async def save_proof(
        self, package_id: str, driver_id: str, content: bytes
    ) -> str:
        filename = build_proof_filename(package_id, driver_id)

        def _put() -> None:
            self._client.put_object(
                Bucket=self.bucket,
                Key=filename,
                Body=content,
                ContentType="image/jpeg",
            )

        await asyncio.to_thread(_put)
        return filename

    async def get_proof(self, filename: str) -> Optional[bytes]:
        if not is_safe_filename(filename):
            return None

        def _get() -> Optional[bytes]:
            try:
                response = self._client.get_object(
                    Bucket=self.bucket, Key=filename
                )
                return response["Body"].read()
            except self._client.exceptions.NoSuchKey:
                return None
            except Exception:
                return None

        return await asyncio.to_thread(_get)

    async def list_recent(self, limit: int = 50) -> List[dict]:
        def _list() -> List[dict]:
            response = self._client.list_objects_v2(
                Bucket=self.bucket, MaxKeys=1000
            )
            contents = response.get("Contents", [])
            contents.sort(key=lambda obj: obj["LastModified"], reverse=True)
            items = []
            for obj in contents[:limit]:
                name = obj["Key"]
                if not name.lower().endswith(ALLOWED_EXTENSIONS):
                    continue
                meta = parse_proof_meta(name)
                items.append(
                    {
                        "packageId": meta["packageId"],
                        "driverId": meta["driverId"],
                        "timestamp": obj["LastModified"].isoformat(),
                        "filename": name,
                        "url": "/delivery/proof/" + name,
                    }
                )
            return items

        return await asyncio.to_thread(_list)


def _build_storage():
    if settings.r2_configured:
        print("[storage] Using Cloudflare R2 backend (bucket: {0})".format(
            settings.R2_BUCKET_NAME
        ))
        return R2ProofStorage()
    print("[storage] R2 not configured -- using LOCAL DISK (dev only).")
    return LocalProofStorage()


proof_storage = _build_storage()
