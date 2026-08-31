from datetime import UTC, datetime

from src.backend.models.sql_models import AuditLog


async def write_audit_log(
    db,
    actor_email,
    action,
    actor_role=None,
    target_user=None,
    details=None,
    ip_address=None,
    session_id=None,
):
    log = AuditLog(
        timestamp_utc=datetime.now(UTC),
        created_at=datetime.now(UTC),
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        target_user=target_user,
        details=details,
        ip_address=ip_address,
        session_id=session_id,
    )

    db.add(log)

    await db.commit()

    await db.refresh(log)

    return log