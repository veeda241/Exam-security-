"""
ExamGuard Pro - API Router Registration
Helper for registering all API routers with FastAPI app
"""

from fastapi import FastAPI
from .endpoints import ROUTERS


def register_all_routers(app: FastAPI) -> None:
    """
    Register all API routers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    for router_config in ROUTERS:
        app.include_router(
            router_config["router"],
            prefix=router_config["prefix"],
            tags=router_config["tags"]
        )


def get_router_info() -> list:
    """
    Get information about all registered routers.
    
    Returns:
        List of router configurations
    """
    return [
        {
            "prefix": r["prefix"],
            "tags": r["tags"]
        }
        for r in ROUTERS
    ]
