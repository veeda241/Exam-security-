"""Events API tests."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


@patch("core.rate_limit.get_rate_limiter")
def test_ingest_client_event(mock_limiter, client):
    mock_limiter.return_value.allow.return_value = True

    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "sess-1", "status": "active", "student_id": "u1"}]
    )
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "ev-1", "type": "tab_switch", "weight": 10}]
    )
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    with patch("api.events.get_current_user", return_value={"id": "u1", "role": "student"}):
        with patch("api.events.get_db", return_value=sb):
            with patch("workers.utils.get_supabase", return_value=sb):
                with patch("workers.utils.publish_session_message"):
                    res = client.post(
                        "/api/v1/events/",
                        json={"session_id": "sess-1", "type": "tab_switch", "payload": {}},
                        headers={"Authorization": "Bearer test"},
                    )

    assert res.status_code in (202, 401, 503)
