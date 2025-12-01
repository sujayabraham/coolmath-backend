# models/database.py
import databases
import sqlalchemy
from sqlalchemy import create_engine
import os

# =============================================
# MySQL Database URL – Railway / PlanetScale / Any MySQL
# =============================================
# Railway gives you this automatically → just leave DATABASE_URL empty
# Or set it manually for PlanetScale, AWS, etc.
DATABASE_URL = os.getenv("DATABASE_URL")

# Critical Fix: Railway gives "mysql://", but databases library needs "mysql+aiomysql"
if DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)

# If using PlanetScale (recommended for free tier)
# Example: mysql+aiomysql://user:pass@aws.connect.psdb.cloud/coolmath?ssl={"ca":"/etc/ssl/certs/ca-certificates.crt"}

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set! Add it in Railway Variables")

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

# =============================================
# 1. Devices Table (Activation + Auth)
# =============================================
devices = sqlalchemy.Table(
    "devices",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String(64), primary_key=True),  # SHA256 device hash
    sqlalchemy.Column("email", sqlalchemy.String(255), unique=True, nullable=True, index=True),
    sqlalchemy.Column("password_hash", sqlalchemy.String(255), nullable=True),
    
    # Activation
    sqlalchemy.Column("status", sqlalchemy.String(20), default="unregistered"),
    sqlalchemy.Column("is_lifetime", sqlalchemy.Boolean, default=False),
    sqlalchemy.Column("trial_end", sqlalchemy.DateTime, nullable=True),
    
    # Timestamps
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, 
                      server_default=sqlalchemy.func.now(), 
                      onupdate=sqlalchemy.func.now()),
)

# =============================================
# 2. Payments Table
# =============================================
payments = sqlalchemy.Table(
    "payments",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String(50), primary_key=True),  # Razorpay payment_id
    sqlalchemy.Column("device_id", sqlalchemy.String(64), 
                      sqlalchemy.ForeignKey("devices.id", ondelete="SET NULL"), index=True),
    sqlalchemy.Column("amount", sqlalchemy.Integer),
    sqlalchemy.Column("currency", sqlalchemy.String(3), default="INR"),
    sqlalchemy.Column("status", sqlalchemy.String(20), default="captured"),
    sqlalchemy.Column("method", sqlalchemy.String(20), nullable=True),
    sqlalchemy.Column("razorpay_order_id", sqlalchemy.String(50), nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
)

# =============================================
# 3. Support Tickets
# =============================================
support_tickets = sqlalchemy.Table(
    "support_tickets",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("device_id", sqlalchemy.String(64), 
                      sqlalchemy.ForeignKey("devices.id", ondelete="SET NULL"), index=True),
    sqlalchemy.Column("name", sqlalchemy.String(100)),
    sqlalchemy.Column("email", sqlalchemy.String(255)),
    sqlalchemy.Column("phone", sqlalchemy.String(15), nullable=True),
    sqlalchemy.Column("message", sqlalchemy.Text),
    sqlalchemy.Column("status", sqlalchemy.String(20), default="pending"),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column("replied_at", sqlalchemy.DateTime, nullable=True),
)

# =============================================
# Engine (with connection pool for MySQL)
# =============================================
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Auto-create tables on startup
metadata.create_all(engine)

print("MySQL Database connected & tables ready!")
