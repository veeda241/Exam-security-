"""Worker utility tests."""
from unittest.mock import MagicMock, patch

from workers.utils import finalize_worker_result


@patch("workers.utils.recompute_and_update_session_risk")
@patch("workers.utils.publish_session_message")
@patch("workers.utils.insert_event")
def test_finalize_worker_result(mock_insert, mock_publish, mock_recompute):
    mock_insert.return_value = {"id": "ev-1", "type": "face_missing"}
    mock_recompute.return_value = {"score": 20, "level": "safe"}

    result = finalize_worker_result("sess-1", "face_missing", {"face_present": False})

    assert result["event"]["id"] == "ev-1"
    mock_publish.assert_called_once()
    mock_recompute.assert_called_once_with("sess-1")
