# routers/auth.py
from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import random
import string
from models.database import devices, database

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ==================== CONFIG ====================
SECRET_KEY = "your-super-secret-256-bit-key-change-in-railway-env-1234567890"  # SET IN RAILWAY ENV
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory OTP store (use Redis in production)
otp_store = {}  # {email: {"otp": "123456", "expires": datetime}}

# ==================== MODELS ====================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool = False

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
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
            raise HTTPException(401, "Invalid token")
        # Verify device still exists
        row = await database.fetch_one(devices.select().where(devices.c.id == device_hash))
        if not row or row.email != email:
            raise HTTPException(401, "Device not authorized")
        return {"email": email, "device": device_hash}
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

# ==================== ENDPOINTS ====================

# 1. Register OR Login (same endpoint)
@router.post("/register-or-login", response_model=Token)
async def register_or_login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        device_id: str = Header(..., alias="Device-ID")
):
    email = form_data.username  # using username field for email
    password = form_data.password
    device_hash = hash_device(device_id)

    row = await database.fetch_one(
        devices.select().where(devices.c.id == device_hash)
    )

    if not row:
        raise HTTPException(404, "Device not registered. Complete activation first.")

    # New user: register
    if not row.email:
        hashed = pwd_context.hash(password)
        await database.execute(
            devices.update().where(devices.c.id == device_hash).values(
                email=email,
                password_hash=hashed
            )
        )
        token = create_jwt({"sub": email, "device": device_hash})
        return Token(access_token=token, is_new_user=True)

    # Existing user: login
    if not row.password_hash or not pwd_context.verify(password, row.password_hash):
        raise HTTPException(401, "Invalid email or password")

    token = create_jwt({"sub": email, "device": device_hash})
    return Token(access_token=token, is_new_user=False)


# 2. Request Password Reset (Send OTP)
@router.post("/request-reset")
async def request_password_reset(req: ResetPasswordRequest, background_tasks: BackgroundTasks):
    row = await database.fetch_one(
        "SELECT id, email FROM devices WHERE email = :email", {"email": req.email}
    )
    if not row:
        raise HTTPException(404, "Email not registered")

    otp = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=10)
    otp_store[req.email] = {"otp": otp, "expires": expires}

    # Send email (replace with your email util)
    background_tasks.add_task(send_otp_email, req.email, otp)

    return {"message": "OTP sent to your email", "dev_otp": otp}  # Remove dev_otp in prod


# 3. Verify OTP & Reset Password
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
        "SELECT id FROM devices WHERE email = :email", {"email": req.email}
    ))["id"]

    await database.execute(
        devices.update().where(devices.c.id == device_hash).values(
            password_hash=hashed
        )
    )

    del otp_store[req.email]
    return {"message": "Password reset successful!"}


# 4. Get Current User (Protected)
@router.get("/me")
async def get_me(user = Depends(get_current_user)):
    return {
        "message": "Authenticated!",
        "email": user["email"],
        "device_bound": True
    }


# Dummy email function — replace with real one
def send_otp_email(email: str, otp: str):
    print(f"[EMAIL] To: {email} | OTP: {otp} | Valid 10 mins")
    # Integrate with your utils/email.py or Resend/Brevo