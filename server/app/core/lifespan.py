from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info("Starting ExamGuard Pro API...")
    
    # Load AI models here
    try:
        from app.services.ml.face_detection import get_face_service
        from app.services.ml.object_detection import get_object_service
        
        # Trigger initialization
        get_face_service()
        get_object_service()
        
        logger.info("AI models preloaded successfully")
    except Exception as e:
        logger.error(f"Failed to preload AI models: {e}")
    
    # Initialize services
    from app.services.realtime import get_realtime_manager
    app.state.realtime = get_realtime_manager()
    
    # Start analysis pipeline if needed
    # from server.app.services.pipeline import get_pipeline
    # app.state.pipeline = get_pipeline()
    # await app.state.pipeline.start()
    
    logger.info("Application startup complete")
    
    yield
    
    # SHUTDOWN
    logger.info("Shutting down ExamGuard Pro API...")
    # Clean up resources
    # await app.state.pipeline.stop()
    logger.info("Application shutdown complete")
