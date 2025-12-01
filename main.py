# main.py — MODERN FastAPI 0.115+ style (zero warnings)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers import activation, payment, support, auth, admin
from models.database import database, create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ───── Startup ─────
    await database.connect()
    await create_tables()
    print("CoolMath Pro Backend STARTED — MySQL Connected")
    yield
    # ───── Shutdown ─────
    await database.disconnect()
    print("Database disconnected — Bye!")

# Create app with lifespan
app = FastAPI(
    title="CoolMath Pro Backend",
    version="2.0",
    lifespan=lifespan,
    docs_url="/docs"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(activation.router, prefix="/api")
app.include_router(payment.router,   prefix="/api")
app.include_router(support.router,   prefix="/api")
app.include_router(auth.router,      prefix="/api/auth")
app.include_router(admin.router,     prefix="/api/admin")

# Admin Panel
app.mount("/admin", StaticFiles(directory="admin_panel", html=True))

# Root
@app.get("/")
async def root():
    return {"message": "CoolMath Pro Backend LIVE", "admin": "/admin", "docs": "/docs"}