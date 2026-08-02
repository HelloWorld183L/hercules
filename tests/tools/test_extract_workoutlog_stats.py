import json
from pathlib import Path

import pytest

from hercules.tools.extract_workoutlog_stats import extract_workoutlog_stats


@pytest.fixture
def workout_log_csv(tmp_path: Path) -> Path:
    log_file = tmp_path / "workout_log.csv"
    log_file.write_text(
        "Date,Exercise,Sets,Reps,Weight,Weight Unit\n"
        "2024-01-01T10:00:00,Squat,3,5,100,kg\n"
        "2024-01-02T10:00:00,Squat,3,5,105,kg\n",
        encoding="utf-8",
    )
    return log_file


@pytest.fixture
def tool_payload(workout_log_csv: Path) -> dict:
    return {
        "toolUseId": "test-tool-use",
        "input": {
            "log_file_path": str(workout_log_csv),
            "inferred_file_type": "fitnotes_csv",
            "start_datetime": "2024-01-01T00:00:00",
            "end_datetime": "2024-01-31T23:59:59",
            "days_in_gym": 2,
        },
    }


def test_extract_workoutlog_stats_returns_success_with_summary_payload(
    tool_payload: dict,
) -> None:
    result = extract_workoutlog_stats(tool_payload)

    assert result["status"] == "success"
    assert result["content"][0]["text"].startswith("")
    assert result["content"][1]["json"]["workout_consistency"] == 100

    exercise_summary_stats = json.loads(
        result["content"][1]["json"]["exercise_summary_stats"]
    )
    assert isinstance(exercise_summary_stats, list)
    assert len(exercise_summary_stats) == 1
    assert exercise_summary_stats[0]["exercise"] == "Squat"


def test_extract_workoutlog_stats_rejects_unsupported_file_type(
    workout_log_csv: Path,
) -> None:
    payload = {
        "toolUseId": "test-tool-use",
        "input": {
            "log_file_path": str(workout_log_csv),
            "inferred_file_type": "unsupported_format",
            "days_in_gym": 3,
        },
    }

    result = extract_workoutlog_stats(payload)

    assert result["status"] == "error"
    assert "Unsupported workout log format" in result["content"][0]["text"]


def test_extract_workoutlog_stats_rejects_invalid_days_in_gym(
    workout_log_csv: Path,
) -> None:
    payload = {
        "toolUseId": "test-tool-use",
        "input": {
            "log_file_path": str(workout_log_csv),
            "inferred_file_type": "fitnotes_csv",
            "days_in_gym": 0,
        },
    }

    result = extract_workoutlog_stats(payload)

    assert result["status"] == "error"
    assert "Invalid days_in_gym value" in result["content"][0]["text"]
