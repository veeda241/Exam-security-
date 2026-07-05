"""V2 auth routes — wraps legacy AuthService."""
from __future__ import annotations

import sys
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status

_server_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from auth.schemas import AuthResponse, Token, TokenRefresh, UserCreate, UserLogin
from auth.service import AuthService
from auth.dependencies import get_client_ip
from deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, request: Request):
    service = AuthService()
    try:
        user = await service.register(user_data)
        login_data = UserLogin(username=user["username"], password=user_data.password)
        user, tokens = await service.authenticate(
            login_data,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
        from auth.schemas import UserResponse
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(login_data: UserLogin, request: Request):
    service = AuthService()
    try:
        user, tokens = await service.authenticate(
            login_data,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
        from auth.schemas import UserResponse
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=Token)
async def refresh(body: TokenRefresh):
    service = AuthService()
    try:
        return await service.refresh_tokens(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user
