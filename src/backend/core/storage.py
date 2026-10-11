"""
Proof-of-delivery photo storage.

Backends:
  - R2ProofStorage:    Cloudflare R2 (S3-compatible API). Used automatically
                       when all R2_* environment variables are set.
                       Survives redeploys. Production backend.
  - LocalProofStorage: Local disk under src/uploads/proofs. Development
                       fallback only -- ephemeral on Railway.

Filenames: {package_id}_{driver_id}_{utc_timestamp}-{random}.jpg
The timestamp plus a random suffix means no upload -- a redelivery attempt
or two in the same second -- ever overwrites earlier photographic evidence.
"""
import asyncio
import os
import re
import secrets
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


_EPOCH = datetime.fromtimestamp(0, timezone.utc)
# Current names end in _YYYYmmddTHHMMSSZ; older simulator names embed a Unix
# timestamp, e.g. PKG-D001-1770914907-5763_D001.jpg.
_STAMP_SUFFIX = re.compile(r"_(\d{8}T\d{6}Z)(?:-[0-9a-f]+)?\.\w+$")
_UNIX_STAMP = re.compile(r"-(\d{10})-")


def filename_timestamp(filename: str) -> Optional[datetime]:
    """Capture time encoded in a proof filename, or None if there is none."""
    match = _STAMP_SUFFIX.search(filename)
    if match:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    match = _UNIX_STAMP.search(filename)
    if match:
        return datetime.fromtimestamp(int(match.group(1)), timezone.utc)
    return None


def build_proof_filename(package_id: str, driver_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return "{0}_{1}_{2}-{3}.jpg".format(
        sanitize_component(package_id),
        sanitize_component(driver_id),
        stamp,
        secrets.token_hex(4),
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
        # "xb": never overwrite an existing proof, even on a name collision
        with open(path, "xb") as handle:
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
        return await asyncio.to_thread(self._list_recent, limit)

    def _list_recent(self, limit: int) -> List[dict]:
        # Sort by the time in the filename and stat only the files returned:
        # one stat per file is ~ms on a Docker-for-Windows bind mount, which
        # made this take >30s with ~90k simulator proofs on disk.
        if not os.path.isdir(self.base_dir):
            return []
        dated = []
        for name in os.listdir(self.base_dir):
            if name.lower().endswith(ALLOWED_EXTENSIONS):
                dated.append((filename_timestamp(name), name))
        dated.sort(key=lambda pair: pair[0] or _EPOCH, reverse=True)

        items = []
        for stamp, name in dated[:limit]:
            if stamp is None:
                stamp = datetime.fromtimestamp(
                    os.stat(os.path.join(self.base_dir, name)).st_mtime,
                    timezone.utc,
                )
            meta = parse_proof_meta(name)
            items.append(
                {
                    "packageId": meta["packageId"],
                    "driverId": meta["driverId"],
                    "timestamp": stamp.isoformat(),
                    "filename": name,
                    "url": "/delivery/proof/" + name,
                }
            )
        items.sort(key=lambda item: item["timestamp"], reverse=True)
        return items


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
