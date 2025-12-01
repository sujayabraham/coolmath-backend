# routers/admin.py
from fastapi import APIRouter
from models.database import devices, payments, tickets, database
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/admin/stats")
async def admin_stats():
    total = await database.fetch_val("SELECT COUNT(*) FROM devices")
    active_trial = await database.fetch_val("SELECT COUNT(*) FROM devices WHERE status='trial'")
    lifetime = await database.fetch_val("SELECT COUNT(*) FROM devices WHERE is_lifetime=1")
    revenue = await database.fetch_val("SELECT COALESCE(SUM(amount), 0) FROM payments") or 0

    return {
        "total_users": total or 0,
        "trial_active": active_trial or 0,
        "lifetime": lifetime or 0,
        "revenue": revenue
    }