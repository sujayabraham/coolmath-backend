# models/database.py
import databases
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+aiomysql://", 1)

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set!")

database = databases.Database(DATABASE_URL)
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

metadata = sqlalchemy.MetaData()

# Tables
devices = sqlalchemy.Table("devices", metadata,
                           sqlalchemy.Column("id", sqlalchemy.String(64), primary_key=True),
                           sqlalchemy.Column("email", sqlalchemy.String(255), unique=True, nullable=True),
                           sqlalchemy.Column("password_hash", sqlalchemy.String(255), nullable=True),
                           sqlalchemy.Column("status", sqlalchemy.String(20), default="unregistered"),
                           sqlalchemy.Column("is_lifetime", sqlalchemy.Boolean, default=False),
                           sqlalchemy.Column("trial_end", sqlalchemy.DateTime, nullable=True),
                           sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
                           sqlalchemy.Column("updated_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now()),
                           )

payments = sqlalchemy.Table("payments", metadata,
                            sqlalchemy.Column("id", sqlalchemy.String(50), primary_key=True),
                            sqlalchemy.Column("device_id", sqlalchemy.String(64), index=True),
                            sqlalchemy.Column("amount", sqlalchemy.Integer),
                            sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
                            )

support_tickets = sqlalchemy.Table("support_tickets", metadata,
                                   sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
                                   sqlalchemy.Column("device_id", sqlalchemy.String(64), index=True),
                                   sqlalchemy.Column("name", sqlalchemy.String(100)),
                                   sqlalchemy.Column("email", sqlalchemy.String(255)),
                                   sqlalchemy.Column("message", sqlalchemy.Text),
                                   sqlalchemy.Column("status", sqlalchemy.String(20), default="pending"),
                                   sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
                                   )

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)