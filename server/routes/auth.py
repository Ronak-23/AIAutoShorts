"""
server/routes/auth.py
=====================
User authentication endpoints (register, login, me).
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional

from server.schemas import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
from server.auth.service import register_user, authenticate_user, get_user_from_token
from server.auth.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency extracting the authenticated user from the Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.split(" ")[1]
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@router.post("/register", response_model=TokenResponse)
async def register(req: UserRegisterRequest):
    try:
        user = register_user(req.username, req.password, req.email)
        token = create_access_token({"sub": user["id"], "username": user["username"]})
        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user.get("email"),
                role=user.get("role", "user"),
                created_at=user.get("created_at")
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["id"], "username": user["username"]})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user.get("email"),
            role=user.get("role", "user"),
            created_at=user.get("created_at")
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user.get("email"),
        role=current_user.get("role", "user"),
        created_at=current_user.get("created_at")
    )
