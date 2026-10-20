from datetime import datetime

import pytest

from tests.integration.conftest import int_db_seed_driver, int_db_seed_package


@pytest.mark.asyncio
async def test_package_workspace_updates_package_and_linked_job(
    int_client_manager, monkeypatch
):
    client, db, _manager = int_client_manager
    driver = await int_db_seed_driver(db, "Workspace Driver")
    package = await int_db_seed_package(db)
    create = await client.post(
        "/dispatch/jobs",
        json={
            "title": "Original delivery",
            "package_id": package.id,
            "scheduled_at": "2026-10-20T15:00:00Z",
        },
    )
    assert create.status_code == 200
    job_id = create.json()["id"]

    async def no_driver_alert(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "src.backend.api.routes.dispatch.alert_driver", no_driver_alert
    )
    scheduled_at = "2026-10-20T16:30:00Z"
    deliver_by = "2026-10-20T18:00:00Z"
    response = await client.patch(
        f"/dispatch/packages/{package.id}",
        json={
            "driver_id": driver.id,
            "scheduled_at": scheduled_at,
            "deliver_by": deliver_by,
            "recipient_name": "Test Recipient",
            "priority": "high",
            "job_title": "Updated delivery",
            "job_notes": "Use the side entrance",
        },
    )

    assert response.status_code == 200, response.text
    updated_package = response.json()
    assert updated_package["driver_id"] == driver.id
    assert updated_package["status"] == "assigned"
    assert updated_package["recipient_name"] == "Test Recipient"
    assert datetime.fromisoformat(updated_package["deliver_by"]).replace(
        tzinfo=None
    ) == datetime.fromisoformat(deliver_by).replace(tzinfo=None)

    job = await client.get(f"/dispatch/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["driver_id"] == driver.id
    assert job.json()["title"] == "Updated delivery"
    assert job.json()["notes"] == "Use the side entrance"
    assert datetime.fromisoformat(job.json()["scheduled_at"]).replace(
        tzinfo=None
    ) == datetime.fromisoformat(scheduled_at).replace(tzinfo=None)
    assert job.json()["priority"] == "high"


@pytest.mark.asyncio
async def test_package_workspace_cannot_reassign_delivered_package(int_client_manager):
    client, db, _manager = int_client_manager
    driver = await int_db_seed_driver(db, "Workspace Driver")
    package = await int_db_seed_package(db, status="delivered")

    response = await client.patch(
        f"/dispatch/packages/{package.id}",
        json={"driver_id": driver.id},
    )

    assert response.status_code == 409
