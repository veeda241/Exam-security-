"""
ExamGuard Pro - Logger Utility
Centralized logging configuration
"""

import logging
import sys
from datetime import datetime
import os

# Create logs directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create and configure a logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # File handler
    log_file = os.path.join(LOG_DIR, f"examguard_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger


# Pre-configured loggers
main_logger = setup_logger("examguard")
api_logger = setup_logger("examguard.api")
analysis_logger = setup_logger("examguard.analysis")
task_logger = setup_logger("examguard.tasks")


def log_event(event_type: str, session_id: str, data: dict = None):
    """Log an event with structured data"""
    main_logger.info(f"EVENT | {event_type} | Session: {session_id} | Data: {data}")


def log_analysis(analysis_type: str, session_id: str, result: dict):
    """Log analysis result"""
    analysis_logger.info(f"ANALYSIS | {analysis_type} | Session: {session_id} | Result: {result}")


def log_error(error: Exception, context: str = ""):
    """Log an error with context"""
    main_logger.error(f"ERROR | {context} | {type(error).__name__}: {str(error)}")
