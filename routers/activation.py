# routers/activation.py
from fastapi import APIRouter, Header
from datetime import datetime, timedelta
import hashlib
from models.database import devices, database

router = APIRouter()

def hash_device(device_id: str) -> str:
    return hashlib.sha256(device_id.strip().lower().encode()).hexdigest()

@router.get("/check-activation")
async def check_activation(device_id: str = Header(..., alias="Device-ID")):
    device_hash = hash_device(device_id)

    row = await database.fetch_one(
        devices.select().where(devices.c.id == device_hash)
    )

    if not row:
        return {
            "status": "unregistered",
            "activation_url": f"https://coolmath.in/activate?device={device_id}"
        }

    if row.is_lifetime:
        return {"status": "active"}

    if row.trial_end:
        if datetime.utcnow() < row.trial_end:
            days_left = (row.trial_end - datetime.utcnow()).days + 1
            return {"status": "trial", "days_left": days_left}
        else:
            return {
                "status": "expired",
                "activation_url": f"https://coolmath.in/activate?device={device_id}"
            }

    return {
        "status": "unregistered",
        "activation_url": f"https://coolmath.in/activate?device={device_id}"
    }