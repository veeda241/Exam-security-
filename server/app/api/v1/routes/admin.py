"""Admin risk configuration API."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from deps import get_admin_user, get_db
from schemas.risk import RiskConfigResponse, RiskConfigUpdate

router = APIRouter()


@router.get("/", response_model=List[RiskConfigResponse])
async def list_risk_configs(
    user=Depends(get_admin_user),
    db=Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
    res = db.table("risk_configs").select("*").order("version", desc=True).execute()
    return [RiskConfigResponse(**row) for row in (res.data or [])]


@router.put("/", response_model=RiskConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_config(
    config_in: RiskConfigUpdate,
    user=Depends(get_admin_user),
    db=Depends(get_db),
):
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
