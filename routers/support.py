# routers/support.py
from fastapi import APIRouter, Header
from models.database import tickets, database

router = APIRouter()

@router.post("/submit-enquiry")
async def submit_support(
    name: str,
    email: str,
    phone: str,
    message: str,
    device_id: str = Header(..., alias="Device-ID")
):
    await database.execute(tickets.insert().values(
        device_id=device_id,
        name=name,
        email=email,
        phone=phone,
        message=message
    ))
    return {"message": "Thank you! We'll reply within 24 hours"}