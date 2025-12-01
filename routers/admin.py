# routers/admin.py
from fastapi import APIRouter
from models.database import devices, payments, support_tickets, database

router = APIRouter()

@router.get("/stats")
async def admin_stats():
    # Total registered devices
    total = await database.fetch_val("SELECT COUNT(*) FROM devices") or 0

    # Active trial users (trial_end in future OR status may be "unregistered" during trial)
    trial_active = await database.fetch_val("""
        SELECT COUNT(*) FROM devices 
        WHERE trial_end IS NOT NULL 
          AND trial_end > NOW()
    """) or 0

    # Lifetime (paid) users
    lifetime = await database.fetch_val("""
        SELECT COUNT(*) FROM devices 
        WHERE is_lifetime = 1
    """) or 0

    # Total revenue in rupees
    revenue = await database.fetch_val("""
        SELECT COALESCE(SUM(amount), 0) FROM payments
    """) or 0

    return {
        "total_users": int(total),
        "trial_active": int(trial_active),
        "lifetime": int(lifetime),
        "revenue": int(revenue)  # Razorpay stores in rupees
    }