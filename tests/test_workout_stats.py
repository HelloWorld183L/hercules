import datetime

from hercules.parsers import WorkoutLogEntry
from hercules.workout_stats import compute_workoutlog_stats


def test_compute_workoutlog_stats_uses_days_in_gym_for_workout_consistency() -> None:
    entries = [
        WorkoutLogEntry(
            date=datetime.datetime(2024, 1, 1),
            exercise="Squat",
            sets=3,
            reps=5,
            weight=100.0,
            unit="kg",
        ),
        WorkoutLogEntry(
            date=datetime.datetime(2024, 1, 2),
            exercise="Squat",
            sets=3,
            reps=5,
            weight=100.0,
            unit="kg",
        ),
        WorkoutLogEntry(
            date=datetime.datetime(2024, 1, 4),
            exercise="Squat",
            sets=3,
            reps=5,
            weight=100.0,
            unit="kg",
        ),
    ]

    stats = compute_workoutlog_stats(entries, days_in_gym=5)

    assert stats.workout_consistency == 60
