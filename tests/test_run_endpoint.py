from dataclasses import replace
from fastapi.testclient import TestClient

import app.main as main
from app.main import app


client = TestClient(app)


def test_run_daily_rejects_missing_token():
    response = client.post("/run/daily")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing X-Run-Token"
    }


def test_run_daily_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, run_token="test-secret-token"),
    )

    response = client.post(
        "/run/daily",
        headers={"X-Run-Token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or missing X-Run-Token"
    }
def test_run_daily_returns_409_when_lock_is_busy(monkeypatch):
    from contextlib import contextmanager

    @contextmanager
    def fake_busy_lock():
        yield False

    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, run_token="test-secret-token"),
    )
    monkeypatch.setattr(main, "daily_run_lock", fake_busy_lock)

    response = client.post(
        "/run/daily",
        headers={"X-Run-Token": "test-secret-token"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A daily run is already in progress"
    }


def test_run_daily_marks_failed_if_report_writing_fails(monkeypatch):
    from contextlib import contextmanager

    @contextmanager
    def fake_lock():
        yield True

    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, run_token="test-secret-token"),
    )
    monkeypatch.setattr(main, "daily_run_lock", fake_lock)
    monkeypatch.setattr(main, "start_run", lambda run_key: 999)
    monkeypatch.setattr(
        main.FMCSAClient,
        "fetch_daily_datasets",
        lambda self: {},
    )
    monkeypatch.setattr(
        main,
        "write_daily_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated report failure")
        ),
    )

    finish_calls = []

    def fake_finish_run(
        run_id,
        status,
        source_counts,
        rows_matched,
        events_created,
        errors,
        report_path,
    ):
        finish_calls.append(
            {
                "status": status,
                "errors": errors,
                "report_path": report_path,
            }
        )

    monkeypatch.setattr(main, "finish_run", fake_finish_run)

    response = client.post(
        "/run/daily",
        headers={"X-Run-Token": "test-secret-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["errors_count"] == 1
    assert len(finish_calls) == 1
    assert finish_calls[0]["status"] == "failed"
    assert "Report generation failed" in finish_calls[0]["errors"][0]
