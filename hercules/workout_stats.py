"""Module for extracting statistics from workout logs."""

import datetime

from pydantic import BaseModel

from hercules.parsers import WorkoutLogEntry

from scipy import stats
import logging

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
    tonnages: list[float]  # List of total weights lifted for this exercise (sets * reps * weight)


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

def compute_progression_rate(dates: list[datetime.datetime], values: list[float]) -> float:
    """Compute the Theil-Sen slope of the values over time."""
    if len(dates) < NUM_SAMPLES_REQUIRED:
        logger.warning("Not enough data points to compute progression rate (Theil-Sen slope).")
        raise NoWorkoutLogEntriesError("Not enough data points to compute progression rate (Theil-Sen slope).")
    # Convert dates to ordinal for regression
    ordinals = [date.toordinal() for date in dates]
    result = stats.theilslopes(ordinals, values)
    return result.slope

def compute_progression_consistency(dates: list[datetime.datetime], values: list[float]) -> float:
    """Compute Kendall's tau correlation coefficient for the values over time."""
    if len(dates) < NUM_SAMPLES_REQUIRED:
        logger.warning("Not enough data points to compute progression consistency (Kendall's tau).")
        raise NoWorkoutLogEntriesError("Not enough data points to compute progression consistency (Kendall's tau).")
    # Convert dates to ordinal for correlation
    ordinals = [date.toordinal() for date in dates]
    tau, _ = stats.kendalltau(ordinals, values)
    return tau

def compute_workoutlog_stats(workout_log_entries: list[WorkoutLogEntry], days_in_gym: int | None = None) -> WorkoutLogSummaryStats:
    """Compute statistics from the workout log entries."""

    exercise_stats_dict: dict[str, list[WorkoutLogEntry]] = {}
    for entry in workout_log_entries:
        exercise_stats_dict.setdefault(entry.exercise, []).append(entry)

    logger.info(f"Exercise stats dictionary constructed for computing summary statistics: {exercise_stats_dict}")
    exercise_stats: list[ExerciseStatsEntry] = []
    for exercise, entries in exercise_stats_dict.items():
        sorted_entries = sorted(entries, key=lambda entry: entry.date)
        estimated_one_rep_maxes = [entry.weight * (1 + entry.reps / 30) for entry in sorted_entries]
        tonnages = [entry.sets * entry.reps * entry.weight for entry in sorted_entries]

        exercise_stats.append(
            ExerciseStatsEntry(
                dates=[entry.date for entry in sorted_entries],
                exercise=exercise,
                estimated_one_rep_maxes=estimated_one_rep_maxes,
                tonnages=tonnages,
            )
        )

    logger.info(f"Exercise stats computed for each exercise: {exercise_stats}")

    exercise_summary_stats: list[ExerciseSummaryStats] = []
    for exercise_stat in exercise_stats:
        try:
            estimated_one_rep_max_progression_rate = compute_progression_rate(exercise_stat.dates, exercise_stat.estimated_one_rep_maxes)
            estimated_one_rep_max_progression_consistency = compute_progression_consistency(exercise_stat.dates, exercise_stat.estimated_one_rep_maxes)
            tonnage_progression_rate = compute_progression_rate(exercise_stat.dates, exercise_stat.tonnages)
            tonnage_progression_consistency = compute_progression_consistency(exercise_stat.dates, exercise_stat.tonnages)
        # Skip summary stats for any exercise that doesn't have enough data points to compute meaningful statistics
        except NoWorkoutLogEntriesError:
            logger.warning(f"Insufficient data to compute statistics for exercise: {exercise_stat.exercise}")
            continue

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

    unique_dates = { entry.date for entry in workout_log_entries }
    if days_in_gym is not None:
        if days_in_gym <= 0:
            raise ValueError("days_in_gym must be greater than zero when provided.")
        workout_consistency = round((len(unique_dates) / days_in_gym) * 100)
    else:
        workout_consistency = len(unique_dates)

    logger.info(f"Workout consistency computed: {workout_consistency}")

    return WorkoutLogSummaryStats(
        exercise_summary_stats=exercise_summary_stats,
        workout_consistency=workout_consistency,
    )