# routers/auth.py
from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import random
import string
import os
from models.database import devices, database

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ==================== CONFIG ====================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
if SECRET_KEY == "dev-secret-key-change-in-production":
    print("WARNING: Using default SECRET_KEY! Set it in Railway Variables!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory OTP store (use Redis in production)
otp_store = {}  # {email: {"otp": "123456", "expires": datetime}}

# ==================== MODELS (NO EmailStr → NO email-validator needed!) ====================
class RegisterRequest(BaseModel):
    email: str        # ← Changed from EmailStr
    password: str

    # Optional: manual email validation
    def model_post_init(self, __context):
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise ValueError("Invalid email format")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool = False

class ResetPasswordRequest(BaseModel):
    email: str        # ← Changed from EmailStr

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str
    new_password: str

# ==================== HELPERS ====================
def hash_device(device_id: str) -> str:
    return hashlib.sha256(device_id.strip().lower().encode()).hexdigest()

def create_jwt(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))

async def get_current_user(authorization: str = Header(..., alias="Authorization")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token format")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        device_hash: str = payload.get("device")
        if not email or not device_hash:
            raise HTTPException(401, "Invalid token payload")

        row = await database.fetch_one(
            devices.select().where(devices.c.id == device_hash)
        )
        if not row or row.email != email:
            raise HTTPException(401, "Device not authorized")
        return {"email": email, "device": device_hash}
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

# ==================== ENDPOINTS ====================

@router.post("/register-or-login", response_model=Token)
async def register_or_login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        device_id: str = Header(..., alias="Device-ID")
):
    email = form_data.username
    password = form_data.password
    device_hash = hash_device(device_id)

    row = await database.fetch_one(
        devices.select().where(devices.c.id == device_hash)
    )

    if not row:
        raise HTTPException(404, "Device not activated. Complete purchase/trial first.")

    # Register new user
    if not row.email:
        hashed = pwd_context.hash(password)
        await database.execute(
            devices.update()
            .where(devices.c.id == device_hash)
            .values(email=email, password_hash=hashed)
        )
        token = create_jwt({"sub": email, "device": device_hash})
        return Token(access_token=token, is_new_user=True)

    # Login existing user
    if not pwd_context.verify(password, row.password_hash):
        raise HTTPException(401, "Invalid password")

    token = create_jwt({"sub": email, "device": device_hash})
    return Token(access_token=token, is_new_user=False)


@router.post("/request-reset")
async def request_password_reset(req: ResetPasswordRequest, background_tasks: BackgroundTasks):
    row = await database.fetch_one(
        devices.select().where(devices.c.email == req.email)
    )
    if not row:
        raise HTTPException(404, "Email not found")

    otp = generate_otp()
    otp_store[req.email] = {
        "otp": otp,
        "expires": datetime.utcnow() + timedelta(minutes=10)
    }

    background_tasks.add_task(send_otp_email, req.email, otp)
    return {"message": "OTP sent!", "dev_otp": otp}  # Remove dev_otp in production


@router.post("/reset-password")
async def reset_password(req: VerifyOTPRequest):
    if req.email not in otp_store:
        raise HTTPException(400, "No OTP request found")

    stored = otp_store[req.email]
    if datetime.utcnow() > stored["expires"]:
        del otp_store[req.email]
        raise HTTPException(400, "OTP expired")

    if stored["otp"] != req.otp:
        raise HTTPException(400, "Invalid OTP")

    hashed = pwd_context.hash(req.new_password)
    device_hash = (await database.fetch_one(
        devices.select(devices.c.id).where(devices.c.email == req.email)
    ))["id"]

    await database.execute(
        devices.update()
        .where(devices.c.id == device_hash)
        .values(password_hash=hashed)
    )

    del otp_store[req.email]
    return {"message": "Password reset successful!"}


@router.get("/me")
async def get_me(user = Depends(get_current_user)):
    return {"message": "Logged in!", "email": user["email"]}


def send_otp_email(email: str, otp: str):
    print(f"[DEV MODE] OTP for {email}: {otp} (Valid 10 mins)")