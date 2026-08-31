
# Push Notification Token Registration
from pydantic import BaseModel

class PushTokenRegistration(BaseModel):
    driver_id: str
    push_token: str

@app.post("/notifications/register-token")
async def register_token(payload: PushTokenRegistration):
    from services.notifications import register_driver_token
    register_driver_token(payload.driver_id, payload.push_token)
    return {"status": "success", "driver_id": payload.driver_id}

@app.post("/notifications/test-alert/{driver_id}")
async def test_alert(driver_id: str):
    from services.notifications import notify_driver_assignment
    res = await notify_driver_assignment(driver_id, "pkg-999", "123 N Michigan Ave, Chicago, IL")
    return {"status": "dispatched", "result": res}
