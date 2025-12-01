# routers/payment.py
from fastapi import APIRouter, Request, Header
from datetime import datetime, timedelta
import razorpay
from models.database import devices, payments, database
import os

router = APIRouter()
client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))

@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    payload = await request.body()
    try:
        client.utility.verify_webhook_signature(payload.decode(), x_razorpay_signature, os.getenv("RAZORPAY_WEBHOOK_SECRET"))
    except:
        return {"status": "failed"}

    data = await request.json()
    if data["event"] == "payment.captured":
        payment_id = data["payload"]["payment"]["entity"]["id"]
        amount = data["payload"]["payment"]["entity"]["amount"] // 100  # paise → rupees
        notes = data["payload"]["payment"]["entity"].get("notes", {})
        device_id = notes.get("device_id")

        if not device_id:
            return {"status": "ignored"}

        device_hash = hashlib.sha256(device_id.strip().lower().encode()).hexdigest()

        # Mark as lifetime
        await database.execute(
            devices.update().where(devices.c.id == device_hash).values(
                status="active",
                is_lifetime=True
            )
        )

        # Save payment record
        await database.execute(payments.insert().values(
            id=payment_id,
            device_id=device_hash,
            amount=amount,
            status="captured"
        ))

    return {"status": "success"}