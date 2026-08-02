"""Module for extracting statistics from workout logs."""

import datetime
import logging

from pydantic import BaseModel
from scipy import stats

from hercules.parsers import WorkoutLogEntry

logger = logging.getLogger("hercules")

# Minimum number of samples required to compute meaningful statistics
NUM_SAMPLES_REQUIRED = 2


class NoWorkoutLogEntriesError(Exception):
    """Raised when there are not enough workout log entries to compute meaningful statistics from."""


class ExerciseStatsEntry(BaseModel):
    """Statistics for a specific exercise."""

    dates: list[datetime.datetime]
    exercise: str
    estimated_one_rep_maxes: list[float]
    tonnages: list[float]
    """List of total weights lifted for this exercise (sets * reps * weight) over time."""


class ExerciseSummaryStats(BaseModel):
    """Summary statistics for a specific exercise."""

    exercise: str

    estimated_one_rep_max_progression_rate: float
    """Theil-Sen slope of the estimated one rep max over time, indicating strength progression."""

    estimated_one_rep_max_progression_consistency: float
    """Kendall's tau correlation coefficient for estimated one rep max progression consistency, indicating consistency of strength progression."""

    tonnage_progression_rate: float
    """Theil-Sen slope of the tonnage over time, indicating volume progression."""

    tonnage_progression_consistency: float
    """Kendall's tau correlation coefficient for tonnage over time, indicating consistency of volume progression."""


class WorkoutLogSummaryStats(BaseModel):
    """Summary statistics for a workout log."""

    exercise_summary_stats: list[ExerciseSummaryStats]
    """Summary stats per exercise that provide details on progression and consistency."""

    workout_consistency: int
    """Workout consistency as a percentage of gym days attended, or the number of workout days when no gym-day count is provided."""


def compute_workoutlog_stats(
    workout_log_entries: list[WorkoutLogEntry],
    days_in_gym: int | None = None,
    bodyweight: float | None = None,
) -> WorkoutLogSummaryStats:
    """Compute statistics from the workout log entries."""

    if len(workout_log_entries) == 0:
        raise NoWorkoutLogEntriesError("No workout log entries provided.")

    if days_in_gym is None:
        workout_consistency = -1  # Indicate that workout consistency was not computed
    else:
        if days_in_gym and (days_in_gym < 1 or days_in_gym > 7):
            raise ValueError("`days_in_gym` must be between 1 and 7 when provided.")

        workout_consistency = _compute_workout_consistency(
            workout_log_entries, days_in_gym
        )

    logger.info(f"Workout consistency computed: {workout_consistency}")

    exercise_stats = _compute_exercise_stat_entries(workout_log_entries, bodyweight)
    logger.info(f"Exercise stats computed for each exercise: {exercise_stats}")

    exercise_summary_stats: list[ExerciseSummaryStats] = []
    for exercise_stat in exercise_stats:
        if len(exercise_stat.dates) < NUM_SAMPLES_REQUIRED:
            logger.warning(
                f"Not enough data points to compute summary statistics for exercise: {exercise_stat.exercise}. Required: {NUM_SAMPLES_REQUIRED}, Found: {len(exercise_stat.dates)}"
            )
            continue

        estimated_one_rep_max_progression_rate = _compute_progression_rate(
            exercise_stat.dates, exercise_stat.estimated_one_rep_maxes
        )
        estimated_one_rep_max_progression_consistency = (
            _compute_progression_consistency(
                exercise_stat.dates, exercise_stat.estimated_one_rep_maxes
            )
        )
        tonnage_progression_rate = _compute_progression_rate(
            exercise_stat.dates, exercise_stat.tonnages
        )
        tonnage_progression_consistency = _compute_progression_consistency(
            exercise_stat.dates, exercise_stat.tonnages
        )

        exercise_summary_stats.append(
            ExerciseSummaryStats(
                exercise=exercise_stat.exercise,
                estimated_one_rep_max_progression_rate=estimated_one_rep_max_progression_rate,
                estimated_one_rep_max_progression_consistency=estimated_one_rep_max_progression_consistency,
                tonnage_progression_rate=tonnage_progression_rate,
                tonnage_progression_consistency=tonnage_progression_consistency,
            )
        )

    logger.info(f"Exercise summary statistics computed: {exercise_summary_stats}")

    return WorkoutLogSummaryStats(
        exercise_summary_stats=exercise_summary_stats,
        workout_consistency=workout_consistency,
    )


def _compute_workout_consistency(
    workout_log_entries: list[WorkoutLogEntry], days_in_gym: int
) -> int:
    """Compute workout consistency as a percentage of gym days attended."""
    if len(workout_log_entries) == 0:
        raise NoWorkoutLogEntriesError("No workout log entries provided.")
    if days_in_gym <= 0:
        raise ValueError("`days_in_gym` must be greater than zero when provided.")

    # Use date-only values so multiple entries on the same day count as one workout day
    unique_dates = {entry.date.date() for entry in workout_log_entries}

    # Compute date range covered by the entries
    start_date = min(unique_dates)
    end_date = max(unique_dates)
    total_days = (end_date - start_date).days + 1

    # Maximum possible workout days in the range given `days_in_gym` per week.
    full_weeks = total_days // 7
    remainder_days = total_days % 7
    max_possible_workout_days = full_weeks * days_in_gym + min(
        remainder_days, days_in_gym
    )

    # Actual attended workout days (unique calendar days with entries)
    actual_days_in_gym = len(unique_dates)

    # Compute consistency as a percentage of actual attended days over maximum possible
    workout_consistency = (
        round((actual_days_in_gym / max_possible_workout_days) * 100)
        if max_possible_workout_days > 0
        else 0
    )

    logger.info(f"Workout consistency computed: {workout_consistency}")

    return workout_consistency


def _compute_exercise_stat_entries(
    workout_log_entries: list[WorkoutLogEntry], bodyweight: float | None
) -> list[ExerciseStatsEntry]:
    exercise_stats_dict: dict[str, list[WorkoutLogEntry]] = {}
    for entry in workout_log_entries:
        exercise_stats_dict.setdefault(entry.exercise, []).append(entry)

    logger.info(
        f"Exercise stats dictionary constructed for computing summary statistics: {exercise_stats_dict}"
    )
    exercise_stats: list[ExerciseStatsEntry] = []
    for exercise, entries in exercise_stats_dict.items():
        fixed_entries = _fix_bodyweight_entries(entries, bodyweight)
        sorted_entries = sorted(fixed_entries, key=lambda entry: entry.date)

        estimated_one_rep_maxes = [
            entry.weight * (1 + entry.reps / 30) for entry in sorted_entries
        ]
        tonnages = [entry.sets * entry.reps * entry.weight for entry in sorted_entries]

        exercise_stats.append(
            ExerciseStatsEntry(
                dates=[entry.date for entry in sorted_entries],
                exercise=exercise,
                estimated_one_rep_maxes=estimated_one_rep_maxes,
                tonnages=tonnages,
            )
        )

    return exercise_stats


def _fix_bodyweight_entries(
    workout_log_entries: list[WorkoutLogEntry], bodyweight: float | None
) -> list[WorkoutLogEntry]:
    """Replace weight of 0.0 with bodyweight in workout log entries."""

    if bodyweight is None:
        logger.warning(
            "No bodyweight provided. Weight of 0.0 will be replaced with 1.0 for all exercises."
        )
        for entry in workout_log_entries:
            if entry.weight == 0.0:
                entry.weight = 1.0
    else:
        for entry in workout_log_entries:
            if entry.weight == 0.0:
                logger.info(
                    f"Replacing weight of 0.0 with bodyweight {bodyweight} for exercise {entry.exercise} on {entry.date}."
                )
                entry.weight = bodyweight

    return workout_log_entries


def _compute_progression_rate(
    dates: list[datetime.datetime], values: list[float]
) -> float:
    """Compute the Theil-Sen slope of the values over time."""
    # Convert dates to ordinal for regression
    ordinals = [date.toordinal() for date in dates]
    result = stats.theilslopes(ordinals, values)
    return result.slope


def _compute_progression_consistency(
    dates: list[datetime.datetime], values: list[float]
) -> float:
    """Compute Kendall's tau correlation coefficient for the values over time."""
    # Convert dates to ordinal for correlation
    ordinals = [date.toordinal() for date in dates]
    tau, _ = stats.kendalltau(ordinals, values)
    return tau
