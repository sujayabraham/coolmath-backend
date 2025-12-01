# models/database.py
import databases
import sqlalchemy
from sqlalchemy import create_engine, MetaData
import os

# =============================================
# Database URL – Railway auto-upgrades to PostgreSQL
# =============================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./coolmath.db"  # Local dev fallback
)

# For Railway PostgreSQL: postgresql://user:pass@host:port/db
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

database = databases.Database(DATABASE_URL)
metadata = MetaData()

# =============================================
# 1. Devices Table – Core of your app
# =============================================
devices = sqlalchemy.Table(
    "devices",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String(64), primary_key=True),  # SHA256 device hash
    sqlalchemy.Column("email", sqlalchemy.String(255), nullable=True, unique=True, index=True),
    sqlalchemy.Column("password_hash", sqlalchemy.String(255), nullable=True),

    # Activation status
    sqlalchemy.Column("status", sqlalchemy.String(20), default="unregistered"),  # trial, active, expired
    sqlalchemy.Column("is_lifetime", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("trial_end", sqlalchemy.DateTime, nullable=True),

    # Timestamps
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime,
                      server_default=sqlalchemy.func.now(),
                      onupdate=sqlalchemy.func.now()),

    # Indexes for speed
    sqlalchemy.Index("ix_devices_email", "email"),
    sqlalchemy.Index("ix_devices_status", "status"),
)

# =============================================
# 2. Payments Table – Razorpay records
# =============================================
payments = sqlalchemy.Table(
    "payments",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String(50), primary_key=True),  # Razorpay payment_id
    sqlalchemy.Column("device_id", sqlalchemy.String(64),
                      sqlalchemy.ForeignKey("devices.id"), index=True),
    sqlalchemy.Column("amount", sqlalchemy.Integer),  # in rupees
    sqlalchemy.Column("currency", sqlalchemy.String(3), default="INR"),
    sqlalchemy.Column("status", sqlalchemy.String(20), default="captured"),  # captured, failed, etc.
    sqlalchemy.Column("method", sqlalchemy.String(20), nullable=True),  # UPI, card, etc.
    sqlalchemy.Column("razorpay_order_id", sqlalchemy.String(50), nullable=True),

    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),

    sqlalchemy.Index("ix_payments_device", "device_id"),
    sqlalchemy.Index("ix_payments_created", "created_at"),
)

# =============================================
# 3. Support Tickets Table
# =============================================
support_tickets = sqlalchemy.Table(
    "support_tickets",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("device_id", sqlalchemy.String(64),
                      sqlalchemy.ForeignKey("devices.id"), index=True),
    sqlalchemy.Column("name", sqlalchemy.String(100)),
    sqlalchemy.Column("email", sqlalchemy.String(255)),
    sqlalchemy.Column("phone", sqlalchemy.String(15), nullable=True),
    sqlalchemy.Column("message", sqlalchemy.Text),
    sqlalchemy.Column("status", sqlalchemy.String(20), default="pending"),  # pending, replied, resolved

    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column("replied_at", sqlalchemy.DateTime, nullable=True),

    sqlalchemy.Index("ix_tickets_status", "status"),
    sqlalchemy.Index("ix_tickets_email", "email"),
)

# =============================================
# Create Engine & Tables on Startup
# =============================================
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# This creates tables automatically on first deploy
metadata.create_all(engine)

# Optional: Print tables (dev only)
if os.getenv("ENV") == "development":
    print("Database tables ready: devices, payments, support_tickets")