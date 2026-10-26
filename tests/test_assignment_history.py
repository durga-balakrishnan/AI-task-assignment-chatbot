import pandas as pd

import app


def test_latest_task_history_uses_latest_assignment_time():
    history = pd.DataFrame(
        [
            {
                "task_id": "T1",
                "assignment_time": "2026-10-26 09:00:00",
                "email_status": "Successful",
                "status": "Confirmed",
            },
            {
                "task_id": "T1",
                "assignment_time": "2026-10-26 10:00:00",
                "email_status": "Failed",
                "status": "Confirmed",
            },
        ]
    )

    latest = app.latest_task_history(history, "T1")

    assert latest is not None
    assert latest[1]["email_status"] == "Failed"
    assert app.is_assignment_complete(latest[1]) is False


def test_successful_or_completed_history_blocks_assignment():
    successful = pd.Series({"email_status": "Successful", "status": "Confirmed"})
    completed = pd.Series({"email_status": "Failed", "status": "Completed"})
    failed = pd.Series({"email_status": "Failed", "status": "Confirmed"})

    assert app.is_assignment_complete(successful) is True
    assert app.is_assignment_complete(completed) is True
    assert app.is_assignment_complete(failed) is False


def test_save_history_refuses_duplicate_task_record(tmp_path, monkeypatch):
    history_path = tmp_path / "assignment_history.csv"
    monkeypatch.setattr(app, "HISTORY_FILE", str(history_path))
    app.save_history(
        {
            "task_id": "T1",
            "status": "Confirmed",
            "email_status": "Failed",
            "assignment_time": "2026-10-26 10:00:00",
        }
    )

    saved = app.save_history(
        {
            "task_id": "T1",
            "status": "Confirmed",
            "email_status": "Failed",
            "assignment_time": "2026-10-26 10:01:00",
        }
    )

    assert saved is False
    assert len(pd.read_csv(history_path)) == 1


def test_update_history_row_records_retry_result_without_adding_row(tmp_path, monkeypatch):
    history_path = tmp_path / "assignment_history.csv"
    monkeypatch.setattr(app, "HISTORY_FILE", str(history_path))
    app.save_history(
        {
            "task_id": "T1",
            "status": "Confirmed",
            "email_status": "Failed",
            "email_error": "Connection unexpectedly closed",
            "assignment_time": "2026-10-26 10:00:00",
        }
    )
    history = app.load_history()
    latest = app.latest_task_history(history, "T1")
    assert latest is not None

    updated = app.update_history_row(
        latest[0],
        {"email_status": "Successful", "email_error": ""},
    )

    result = pd.read_csv(history_path)
    assert updated is True
    assert len(result) == 1
    assert result.iloc[0]["email_status"] == "Successful"
    assert pd.isna(result.iloc[0]["email_error"])
