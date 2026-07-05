"""Pytest configuration."""
import os
import sys

import pytest

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(SERVER_DIR)

if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)
# Avoid importing repo-root main.py instead of server/main.py
if REPO_ROOT in sys.path:
    sys.path.remove(REPO_ROOT)


@pytest.fixture
def risk_config():
    from core.risk_engine import RiskConfig
    return RiskConfig.default()


@pytest.fixture
def sample_events():
    from core.risk_engine import Event
    return [
        Event(type="tab_switch", weight=10),
        Event(type="face_missing", weight=20),
    ]
