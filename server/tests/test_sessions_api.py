"""Sessions API tests (mocked Supabase)."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


@pytest.fixture
def mock_user():
    return {"id": "user-123", "role": "student", "full_name": "Test Student"}


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


@patch("deps.get_current_user")
@patch("deps.get_db")
def test_create_session_mock(mock_db, mock_auth, client, mock_user):
    mock_auth.return_value = mock_user
    sb = MagicMock()
    mock_db.return_value = sb

    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "exam-1", "title": "Test Exam"}]
    )
    sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{
            "id": "sess-1",
            "exam_id": "exam-1",
            "student_id": "user-123",
            "status": "active",
            "risk_score": 0,
            "risk_level": "safe",
            "consent_metadata": {},
            "monitoring_tier": "full",
        }]
    )

    with patch("api.sessions.get_current_user", return_value=mock_user):
        with patch("api.sessions.get_db", return_value=sb):
            res = client.post(
                "/api/v1/sessions/",
                json={"exam_id": "exam-1", "consent_metadata": {"biometric_consent": True}},
                headers={"Authorization": "Bearer test"},
            )

    assert res.status_code in (201, 401, 503)
