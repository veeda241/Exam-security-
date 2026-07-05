from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ExamGuard Pro V2 API...")

    try:
        from core.event_bus import get_event_bus
        from app.api.v1.routes.ws import setup_ws_bus_listener

        bus = get_event_bus()
        setup_ws_bus_listener()
        await bus.start_listener()
        app.state.event_bus = bus
        logger.info("Event bus listener started")
    except Exception as e:
        logger.warning(f"Event bus unavailable (Redis may be down): {e}")
        app.state.event_bus = None

    yield

    logger.info("Shutting down ExamGuard Pro V2 API...")
    bus = getattr(app.state, "event_bus", None)
    if bus:
        await bus.disconnect()
