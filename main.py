# main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import activation, payment, support, auth, admin
from models.database import database, engine, metadata

# ===================================
# FastAPI App Setup
# ===================================
app = FastAPI(
    title="CoolMath Pro Backend",
    description="Activation • Payments • Auth • Support • Admin Panel",
    version="2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ===================================
# CORS (Allow your Android/Web app)
# ===================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================================
# Database Connection
# ===================================
@app.on_event("startup")
async def startup():
    await database.connect()
    metadata.create_all(engine)  # Auto-creates tables if missing

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ===================================
# Include All Routers
# ===================================
app.include_router(activation.router, prefix="/api")
app.include_router(payment.router,   prefix="/api")
app.include_router(support.router,   prefix="/api")
app.include_router(auth.router,      prefix="/api/auth")
app.include_router(admin.router,     prefix="/api/admin")

# ===================================
# Serve Beautiful Admin Panel
# ===================================
# Make sure you have folder: admin_panel/index.html
app.mount("/admin", StaticFiles(directory="admin_panel", html=True), name="admin")

# ===================================
# Health & Root
# ===================================
@app.get("/")
async def root():
    return {
        "app": "CoolMath Pro Backend",
        "status": "LIVE",
        "version": "2.0",
        "admin_panel": "/admin",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}