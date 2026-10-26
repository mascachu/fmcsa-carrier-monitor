
from unittest.mock import MagicMock, patch

from app.repository import list_runs


def test_list_runs_returns_latest_runs_with_limit():
    expected = [
        {
            "id": 4,
            "run_key": "demo-run-4",
            "status": "completed",
            "rows_matched": 0,
            "events_created": 0,
            "errors": [],
        }
    ]

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = expected

    with patch("app.repository.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn

        result = list_runs(1)

    assert result == expected
    mock_conn.execute.assert_called_once()
    assert mock_conn.execute.call_args.args[1] == (1,)
