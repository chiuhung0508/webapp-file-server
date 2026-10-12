from fastapi import APIRouter, Response, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from app.database import has_users, create_user, get_user_by_username
from app.security import hash_password, verify_password, create_access_token, get_current_user, decode_access_token
from app.config import COOKIE_NAME, ACCESS_TOKEN_EXPIRE_MINUTES, USE_SSL

router = APIRouter(prefix="/api/auth", tags=["auth"])

class SetupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)

class LoginRequest(BaseModel):
    username: str
    password: str

@router.get("/status")
async def auth_status(request: Request):
    """Returns onboarding status and whether current client is authenticated."""
    configured = has_users()
    authenticated = False
    username = None

    if configured:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            payload = decode_access_token(token)
            if payload and "sub" in payload:
                user = get_user_by_username(payload["sub"])
                if user:
                    authenticated = True
                    username = user["username"]

    return {
        "configured": configured,
        "authenticated": authenticated,
        "username": username
    }

@router.post("/setup")
async def setup_admin(data: SetupRequest, response: Response):
    """Initial one-time onboarding wizard to configure the master administrator."""
    if has_users():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is already configured. Please log in."
        )

    pwd_hash = hash_password(data.password)
    created = create_user(data.username, pwd_hash)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create administrator account."
        )

    # Automatically log in the freshly created administrator
    token = create_access_token({"sub": data.username})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=USE_SSL,
        path="/"
    )
    return {"message": "Administrator account successfully configured.", "username": data.username}

@router.post("/login")
async def login(data: LoginRequest, response: Response):
    """Authenticate administrator and issue session cookie."""
    if not has_users():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server not initialized. Please complete setup first."
        )

    user = get_user_by_username(data.username)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    token = create_access_token({"sub": user["username"]})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=USE_SSL,
        path="/"
    )
    return {"message": "Login successful.", "username": user["username"]}

@router.post("/logout")
async def logout(response: Response):
    """Invalidate session cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "Logged out successfully."}

@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve logged in user information."""
    return {
        "username": current_user["username"],
        "created_at": current_user["created_at"]
    }
