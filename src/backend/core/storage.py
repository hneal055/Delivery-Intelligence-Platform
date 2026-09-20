import os
import re
import time
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Safe component regex for file sanitization
_SAFE_COMPONENT = re.compile(r"[^a-zA-Z0-9_\.-]")


def sanitize_component(value: any) -> str:
    """Sanitize string components for safe filename usage."""
    if value is None:
        return "unknown"
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    return _SAFE_COMPONENT.sub("-", str(value).strip())


def is_safe_filename(filename: str) -> bool:
    """Validate that a filename is secure against path traversal."""
    if not filename:
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    return True


def build_proof_filename(package_id: str, driver_id: str) -> str:
    """Construct a unique, sanitized proof filename."""
    stamp = int(time.time())
    return f"{sanitize_component(package_id)}_{sanitize_component(driver_id)}_{stamp}.jpg"


class LocalProofStorage:
    """Local disk storage provider for proof-of-delivery images (dev/test mode)."""

    def __init__(self, upload_dir: str = "storage/proofs"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_proof(
        self,
        package_id: str,
        driver_id: str,
        file_bytes: bytes,
        filename: str = "proof.jpg",
    ) -> str:
        """Save proof bytes to disk and return the stored file path."""
        safe_filename = build_proof_filename(package_id, driver_id)
        file_path = self.upload_dir / safe_filename
        
        # Ensure asynchronous disk write compatibility
        file_path.write_bytes(file_bytes)
        logger.info(f"Proof saved to local disk: {file_path}")
        return str(file_path)

    async def get_proof_url(self, package_id: str, driver_id: str) -> Optional[str]:
        """Retrieve the local file path or URL for a stored proof."""
        prefix = f"{sanitize_component(package_id)}_{sanitize_component(driver_id)}"
        for p in self.upload_dir.glob(f"{prefix}_*.jpg"):
            return str(p)
        return None


# Global singleton instance
proof_storage = LocalProofStorage()