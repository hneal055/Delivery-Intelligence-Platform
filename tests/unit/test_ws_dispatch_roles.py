import pytest
from src.backend.api.routes.websocket import _can_manage_jobs


@pytest.mark.parametrize("role,allowed", [
    ("dispatcher", True),
    ("manager", True),
    ("admin", True),
    ("driver", False),
    ("nonsense", False),
    (None, False),
])
def test_dispatch_feed_follows_manage_jobs_permission(role, allowed):
    assert _can_manage_jobs(role) is allowed
