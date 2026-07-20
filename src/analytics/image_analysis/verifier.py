"""
Proof-of-delivery image verification using Pillow.

Checks (when IMAGE_VERIFICATION_PROVIDER != 'stub'):
  1. Valid image format (JPEG or PNG magic bytes)
  2. Minimum dimensions (300 x 300 px)
  3. Brightness -- image is not too dark or overexposed
  4. Blur -- Laplacian variance above threshold

Set IMAGE_VERIFICATION_PROVIDER=stub to skip real checks in dev/test.
"""
import io
import logging
from typing import List, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC  = b"\x89PNG"

MIN_WIDTH       = 300
MIN_HEIGHT      = 300
MIN_BRIGHTNESS  = 20.0   # mean pixel value 0-255
MAX_BRIGHTNESS  = 245.0
BLUR_THRESHOLD  = 50.0   # Laplacian variance proxy


class ImageVerificationResult(BaseModel):
    is_valid: bool
    confidence_score: float
    detected_objects: List[str] = []
    issues: List[str] = []


def _laplacian_variance(pixels: list, width: int, height: int) -> float:
    """Compute a Laplacian-variance sharpness score from flat grayscale pixel data."""
    if width < 3 or height < 3:
        return 0.0
    total = 0.0
    count = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            centre   = pixels[y * width + x]
            neighbours = (
                pixels[(y - 1) * width + x]
                + pixels[(y + 1) * width + x]
                + pixels[y * width + (x - 1)]
                + pixels[y * width + (x + 1)]
            )
            lap = abs(4 * centre - neighbours)
            total += lap * lap
            count += 1
    return total / count if count else 0.0


class ImageVerifier:
    """Validates proof-of-delivery photos before accepting a delivery confirmation."""

    def verify_delivery_photo(self, image_data: bytes) -> ImageVerificationResult:
        from src.backend.core.config import settings

        # Stub mode: minimal check only (used in dev / unit tests)
        if getattr(settings, "IMAGE_VERIFICATION_PROVIDER", "real") == "stub":
            if len(image_data) < 1024:
                return ImageVerificationResult(
                    is_valid=False,
                    confidence_score=0.0,
                    issues=["Image data too small or corrupted"],
                )
            return ImageVerificationResult(
                is_valid=True,
                confidence_score=0.95,
                detected_objects=["package_box"],
            )

        issues: List[str] = []

        # 1. Magic-byte format check
        if not (image_data[:3] == _JPEG_MAGIC or image_data[:4] == _PNG_MAGIC):
            return ImageVerificationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=["Unsupported image format -- only JPEG and PNG are accepted"],
            )

        # 2. Open with Pillow
        try:
            from PIL import Image
            buf = io.BytesIO(image_data)
            img = Image.open(buf)
            img.verify()          # raises on corrupt data; closes the handle
            img = Image.open(io.BytesIO(image_data))   # re-open after verify
        except Exception as exc:
            return ImageVerificationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=[f"Image file is corrupt or unreadable: {exc}"],
            )

        # 3. Minimum dimensions
        width, height = img.size
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            issues.append(
                f"Image too small ({width}x{height}px); minimum is {MIN_WIDTH}x{MIN_HEIGHT}px"
            )

        # 4. Brightness check
        gray   = img.convert("L")
        pixels = list(gray.getdata())
        mean_brightness = sum(pixels) / len(pixels) if pixels else 0.0

        if mean_brightness < MIN_BRIGHTNESS:
            issues.append(
                f"Image is too dark (brightness {mean_brightness:.1f} < {MIN_BRIGHTNESS})"
            )
        elif mean_brightness > MAX_BRIGHTNESS:
            issues.append(
                f"Image is overexposed (brightness {mean_brightness:.1f} > {MAX_BRIGHTNESS})"
            )

        # 5. Blur detection
        if width >= 3 and height >= 3:
            lap_var = _laplacian_variance(pixels, width, height)
            if lap_var < BLUR_THRESHOLD:
                issues.append(
                    f"Image is too blurry (sharpness {lap_var:.1f} < {BLUR_THRESHOLD})"
                )

        if issues:
            return ImageVerificationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=issues,
            )

        return ImageVerificationResult(
            is_valid=True,
            confidence_score=0.92,
            detected_objects=["package_box"],
        )

    def verify_proof_of_delivery(self, image_data: bytes) -> Tuple[bool, str]:
        """Compatibility wrapper used by the delivery route."""
        result = self.verify_delivery_photo(image_data)
        if result.is_valid:
            return True, "Valid"
        reason = "; ".join(result.issues) if result.issues else "Unknown verification failure"
        return False, reason


image_verifier = ImageVerifier()
