from datetime import datetime, timezone
from typing import Any, Dict


def app_status() -> Dict[str, Any]:
  """Returns the current application status and timestamp."""
  return {
      "status": "running",
      "timestamp": datetime.now(timezone.utc).isoformat(),
  }


def version() -> str:
  """Returns the current application version."""
  return "1.0.0"