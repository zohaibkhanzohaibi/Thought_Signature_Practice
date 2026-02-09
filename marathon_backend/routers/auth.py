from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from typing import Optional

from marathon_backend.models.database import supabase
from marathon_backend.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# --- Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: str
    
# --- Dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    # Fetch user from DB
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    if not response.data:
        raise HTTPException(status_code=401, detail="User not found")
        
    return response.data[0]

# --- Endpoints ---

@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate):
    # 1. Check if email exists
    existing = supabase.table("users").select("id").eq("email", user.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Hash password
    hashed_password = get_password_hash(user.password)

    # 3. Create User
    user_data = {
        "email": user.email,
        "password_hash": hashed_password
    }
    response = supabase.table("users").insert(user_data).execute()
    new_user = response.data[0]

    # 4. Create Profile (Optional, but good for linking)
    profile_data = {
        "id": new_user["id"],
        "full_name": user.full_name or user.email.split("@")[0],
        "email": user.email
    }
    # Check if profile with same ID exists (unlikely given UUID generation but good practice)
    # Actually, we should upsert or just insert.
    supabase.table("profiles").insert(profile_data).execute()

    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Fetch user
    response = supabase.table("users").select("*").eq("email", form_data.username).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    user = response.data[0]

    # 2. Verify password
    if not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # 3. Generate Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

# --- Google Auth ---
class GoogleAuthRequest(BaseModel):
    token: str

@router.post("/google", response_model=Token)
async def google_login(request: GoogleAuthRequest):
    # 1. Verify Google Token
    from marathon_backend.auth import verify_google_token
    google_user = verify_google_token(request.token)
    
    if not google_user:
        raise HTTPException(status_code=400, detail="Invalid Google token")
    
    email = google_user.get("email")
    name = google_user.get("name")
    
    if not email:
        raise HTTPException(status_code=400, detail="Google token missing email")

    # 2. Check if user exists
    response = supabase.table("users").select("*").eq("email", email).execute()
    
    if response.data:
        # Login existing user
        user = response.data[0]
    else:
        # Register new user
        # Generate random password hash for Google users (they won't use it)
        import secrets
        random_password = secrets.token_urlsafe(16)
        hashed_password = get_password_hash(random_password)
        
        user_data = {
            "email": email,
            "password_hash": hashed_password
        }
        res = supabase.table("users").insert(user_data).execute()
        user = res.data[0]
        
        # Create Profile
        profile_data = {
            "id": user["id"],
            "full_name": name or email.split("@")[0],
            "email": email
        }
        supabase.table("profiles").insert(profile_data).execute()

    # 3. Generate Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
