import datetime

import pytest

from hercules.parsers import WorkoutLogEntry
from hercules.workout_stats import NoWorkoutLogEntriesError, compute_workoutlog_stats

@pytest.fixture
def sample_workout_entries() -> list[WorkoutLogEntry]:
    """
    Fixture that provides a sample list of inconsistent workout log entries for testing.
    The entries are inconsistent in terms of dates and exercises.
    """
    return [
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
            exercise="Bench Press",
            sets=3,
            reps=5,
            weight=80.0,
            unit="kg",
        ),
        WorkoutLogEntry(
            date=datetime.datetime(2024, 1, 3),
            exercise="Deadlift",
            sets=3,
            reps=5,
            weight=120.0,
            unit="kg",
        ),
    ]

@pytest.fixture
def sample_bodyweight_entries() -> list[WorkoutLogEntry]:
    """
    Fixture that provides a sample list of consistent workout log entries for testing.
    The entries are consistent in terms of dates and exercises, and include bodyweight adjustments.
    """
    return [
        WorkoutLogEntry(
            date=datetime.datetime(2024, 1, 1),
            exercise="Pull Up",
            sets=3,
            reps=10,
            weight=0.0,  # Bodyweight exercise
            unit="kg",
        ),
        WorkoutLogEntry(
            date=datetime.datetime(2024, 1, 2),
            exercise="Push Up",
            sets=3,
            reps=15,
            weight=0.0,  # Bodyweight exercise
            unit="kg",
        ),
        WorkoutLogEntry(
            date=datetime.datetime(2024, 1, 3),
            exercise="Squat",
            sets=3,
            reps=12,
            weight=0.0,  # Bodyweight exercise
            unit="kg",
        ),
    ]

def test_compute_workoutlog_stats_uses_days_in_gym_for_workout_consistency(sample_workout_entries: list[WorkoutLogEntry]) -> None:
    """
    Test that compute_workoutlog_stats correctly computes workout consistency using the provided days_in_gym parameter.
    The workout consistency should be calculated as (actual_days_in_gym / days_in_gym) * 100, where actual_days_in_gym is the number of unique days in the workout log entries.
    """

    stats = compute_workoutlog_stats(sample_workout_entries, days_in_gym=3)
    assert stats.workout_consistency == len(sample_workout_entries) / 3 * 100

def test_compute_workoutlog_stats_without_days_in_gym(sample_workout_entries: list[WorkoutLogEntry]) -> None:
    """
    Test that compute_workoutlog_stats returns -1 for workout consistency when days_in_gym is not provided.
    This indicates that workout consistency was not computed.
    """

    stats = compute_workoutlog_stats(sample_workout_entries)
    assert stats.workout_consistency == -1

def test_compute_workoutlog_stats_with_invalid_days_in_gym_raises_value_error(sample_workout_entries: list[WorkoutLogEntry]) -> None:
    """
    Test that compute_workoutlog_stats raises a ValueError when days_in_gym is provided as zero.
    This is to ensure that the function handles invalid input for days_in_gym correctly.
    """

    with pytest.raises(ValueError):
        compute_workoutlog_stats(sample_workout_entries, days_in_gym=0)

    with pytest.raises(ValueError):
        compute_workoutlog_stats(sample_workout_entries, days_in_gym=8)
    
    with pytest.raises(ValueError):
        compute_workoutlog_stats(sample_workout_entries, days_in_gym=-5)

def test_compute_workoutlog_stats_with_no_entries_raises_error() -> None:
    """
    Test that compute_workoutlog_stats raises a NoWorkoutLogEntriesError when no workout log entries are provided.
    This is to ensure that the function handles the case of empty input correctly.
    """

    with pytest.raises(NoWorkoutLogEntriesError):
        compute_workoutlog_stats([])

@pytest.mark.parametrize("bodyweight", [70.0, 80.0, 90.0])
def test_compute_workoutlog_stats_with_bodyweight_adjustment(sample_bodyweight_entries: list[WorkoutLogEntry], bodyweight: float) -> None:
    """
    Test that compute_workoutlog_stats correctly adjusts bodyweight entries when a bodyweight parameter is provided.
    This test checks that the function processes the entries and computes statistics accordingly.
    """

    stats = compute_workoutlog_stats(sample_bodyweight_entries, days_in_gym=3, bodyweight=bodyweight)
    assert stats.workout_consistency == len(sample_bodyweight_entries) / 3 * 100

    assert stats.exercise_summary_stats is not None and all(
        entry.estimated_one_rep_max_progression_rate != None and entry.estimated_one_rep_max_progression_rate != None for entry in stats.exercise_summary_stats
    )