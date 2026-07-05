"""Authentication and admin risk-config routes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth.dependencies import get_client_ip
from auth.schemas import AuthResponse, Token, TokenRefresh, UserCreate, UserLogin, UserResponse
from auth.service import AuthService
from deps import get_admin_user, get_current_user, get_db
from schemas.risk import RiskConfigResponse, RiskConfigUpdate

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


@router.get("/admin/risk-config", response_model=List[RiskConfigResponse])
async def list_risk_configs(user=Depends(get_admin_user), db=Depends(get_db)):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
    res = db.table("risk_configs").select("*").order("version", desc=True).execute()
    return [RiskConfigResponse(**row) for row in (res.data or [])]


@router.put("/admin/risk-config", response_model=RiskConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_config(config_in: RiskConfigUpdate, user=Depends(get_admin_user), db=Depends(get_db)):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    latest = db.table("risk_configs").select("version").order("version", desc=True).limit(1).execute()
    next_version = (latest.data[0]["version"] + 1) if latest.data else 1

    db.table("risk_configs").update({"active": False}).eq("active", True).execute()

    row = {
        "version": next_version,
        "weights": config_in.weights,
        "thresholds": config_in.thresholds,
        "active": True,
    }
    res = db.table("risk_configs").insert(row).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create config")
    return RiskConfigResponse(**res.data[0])
