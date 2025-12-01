# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routers import activation, payment, support, auth, admin
from models.database import database, create_tables

app = FastAPI(
    title="CoolMath Pro Backend",
    version="2.0",
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

# Startup / Shutdown
@app.on_event("startup")
async def startup():
    await database.connect()
    await create_tables()
    print("Backend LIVE - MySQL Connected")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/")
def home():
    return {"message": "CoolMath Pro Backend LIVE", "admin": "/admin", "docs": "/docs"}