import datetime
import logging
from collections.abc import Callable
from enum import StrEnum

from pydantic import TypeAdapter
from strands.types.tools import ToolResult, ToolUse

from hercules.parsers import WorkoutLogEntry, parse_fitnotes_csv, parse_fitnotes_db
from hercules.workout_stats import (
    ExerciseSummaryStats,
    WorkoutLogSummaryStats,
    compute_workoutlog_stats,
)

logger = logging.getLogger("hercules")


class InferredFileType(StrEnum):
    FITNOTES_CSV = "fitnotes_csv"
    FITNOTES_DB = "fitnotes_db"


TOOL_SPEC = {
    "name": "extract_workoutlog_stats",
    "description": """
    Extract relevant statistics from a workout log to understand user rate of progression, progression consistency and for providing feedback on progress.
    The workout log can be filtered according to `start_datetime` and `end_datetime` to focus on a specific time range of interest.
    These could be exported workout logs from FitNotes or other fitness tracking apps. 
    The function computes summary statistics such as estimated one rep max progression (consistency + progression rate), tonnage progression, and workout consistency.
    Returns workout log statistics for any exercises with sufficient data points. Make sure to include consistency and progression rate statistics. Include percentages for the exercise summary stats except workout consistency.
    """,
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "log_file_path": {
                    "type": "string",
                    "description": "File path for the workout log. It must include the file extension.",
                },
                "inferred_file_type": {
                    "type": "string",
                    "description": "The inferred type of the workout log file. For example, 'fitnotes_csv' for a FitNotes CSV export or 'fitnotes_db' for a FitNotes database file. This is used to determine how to parse the file.",
                    "enum": [file_type.value for file_type in InferredFileType],
                },
                "start_datetime": {
                    "type": "string",
                    "description": "The start datetime for filtering workout log entries. Convert to ISO 8601 format (YYYY-MM-DDTHH:MM:SS) for consistency. If no start_datetime is provided, set to 'zero' date (e.g. 1970-01-01T00:00:00) to include all entries from the beginning of time.",
                },
                "end_datetime": {
                    "type": "string",
                    "description": "The end datetime for filtering workout log entries. Convert to ISO 8601 format (YYYY-MM-DDTHH:MM:SS) for consistency. If no start_datetime is provided, set to 'max' date (e.g. 2200-12-31T23:59:59) to include all entries from the beginning of time.",
                },
                "days_in_gym": {
                    "type": "integer",
                    "description": "The number of days in the week the user spent in the gym during the requested time range. When provided, workout consistency is calculated as a percentage of gym days attended. This MUST be between 1 and 7, inclusive. If not provided, workout consistency will not be calculated.",
                },
                "recent_bodyweight": {
                    "type": "number",
                    "description": "The user's most recent bodyweight in kilograms or pounds. This is used to calculate estimated one rep maxes for bodyweight exercises. If not provided, stats for bodyweight exercises will use a weight of 1.0. Multiply by bodyweight later if needed.",
                },
            },
            "required": ["log_file_path", "inferred_file_type"],
        }
    },
}

SUPPORTED_WORKOUTLOG_FORMATS: dict[
    tuple[str, str], Callable[[str], list[WorkoutLogEntry]]
] = {
    ("fitnotes_csv", "csv"): parse_fitnotes_csv,
    ("fitnotes_db", "fitnotes"): parse_fitnotes_db,
}


def extract_workoutlog_stats(tool: ToolUse, **kwargs) -> ToolResult:
    """
    Extract relevant statistics from a workout log to understand user rate of progression, progression consistency and for providing feedback on progress.
    These could be exported workout logs from FitNotes or other fitness tracking apps.
    The function computes summary statistics such as estimated one rep max progression (consistency + progression rate), tonnage progression, and workout consistency.
    Returns workout log statistics for any exercises with sufficient data points.
    """
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]
    log_file_path = tool_input["log_file_path"]

    inferred_file_type = tool_input["inferred_file_type"]
    start_datetime = tool_input.get("start_datetime")
    end_datetime = tool_input.get("end_datetime")
    days_in_gym = tool_input.get("days_in_gym")
    recent_bodyweight = tool_input.get("recent_bodyweight")

    is_valid, error_message = _validate_tool_input(tool_input)
    if not is_valid:
        logger.error(f"Invalid tool input: {error_message}")
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": error_message}],
        }

    logger.info(
        f"Received request to extract stats from workout log at {log_file_path} with inferred file type {inferred_file_type}, start_datetime {start_datetime}, end_datetime {end_datetime}, and days_in_gym {days_in_gym}"
    )

    file_extension = log_file_path.split(".")[-1].lower()
    try:
        workout_log_entries = SUPPORTED_WORKOUTLOG_FORMATS[
            (inferred_file_type, file_extension)
        ](log_file_path)
    except KeyError:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [
                {
                    "text": f"Unsupported workout log format: {file_extension}. Supported formats are: {', '.join([f'{k[0]} ({k[1]})' for k in SUPPORTED_WORKOUTLOG_FORMATS])}"
                }
            ],
        }

    try:
        date_range_str, workout_log_entries = _filter_workoutlog_entries_by_date_range(
            workout_log_entries, start_datetime, end_datetime
        )
    except ValueError:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [
                {
                    "text": f"Invalid date range: start_datetime {start_datetime} is after end_datetime {end_datetime}."
                }
            ],
        }

    if len(workout_log_entries) == 0:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [
                {
                    "text": f"No workout log entries found in {log_file_path} {date_range_str}."
                }
            ],
        }

    logger.info(
        f"Workout log loaded parsed from {log_file_path} into {len(workout_log_entries)} workout log entries."
    )

    workout_stats = compute_workoutlog_stats(
        workout_log_entries, days_in_gym=days_in_gym, bodyweight=recent_bodyweight
    )

    logger.info(f"Workout log stats computed successfully from {log_file_path}")

    # Use TypeAdapter for serializing WorkoutLogSummaryStats to JSON
    summary_stats_adapter = TypeAdapter(list[ExerciseSummaryStats])
    exercise_summary_stats_json = summary_stats_adapter.dump_json(
        workout_stats.exercise_summary_stats
    ).decode()

    output_dict: ToolResult = {
        "toolUseId": tool_use_id,
        "status": "success",
        "content": [
            {
                "text": f"{log_file_path} workout log stats have been computed successfully {date_range_str}."
            },
            {"json": {"exercise_summary_stats": exercise_summary_stats_json}},
        ],
    }

    output_dict = _add_workout_stat_caveats(
        workout_stats, recent_bodyweight, output_dict
    )
    return output_dict


def _add_workout_stat_caveats(
    workout_stats: WorkoutLogSummaryStats, recent_bodyweight: float, output_dict: dict
) -> dict:
    """
    Add caveats to the workout stats output if certain conditions are met.
    For example, if `days_in_gym` is not provided, add a caveat about workout consistency not being computed.
    If `recent_bodyweight` is not provided, add a caveat about bodyweight exercises using a weight of 1.0.
    """
    if workout_stats.workout_consistency == -1:
        incomplete_consistency_msg = "Workout consistency has not been computed as `days_in_gym` was not provided."
        output_dict["content"][0]["text"] += f" {incomplete_consistency_msg}"
        logger.info(incomplete_consistency_msg)
    else:
        output_dict["content"][1]["json"]["workout_consistency"] = (
            workout_stats.workout_consistency
        )

    if not recent_bodyweight:
        no_bodyweight_msg = "No recent bodyweight was provided, so stats for bodyweight exercises will use a weight of 1.0. Multiply by bodyweight later if needed."
        output_dict["content"][0]["text"] += f" {no_bodyweight_msg}"
        logger.info(no_bodyweight_msg)

    return output_dict


def _validate_tool_input(tool_input: dict) -> tuple[bool, str]:
    """
    Validate the tool input for required fields and correct types.
    Returns a tuple of (is_valid, error_message).
    """
    required_fields = ["log_file_path", "inferred_file_type"]
    for field in required_fields:
        if field not in tool_input:
            return False, f"Missing required field: {field}"

    if "days_in_gym" in tool_input:
        days_in_gym = tool_input["days_in_gym"]
        if not isinstance(days_in_gym, int) or days_in_gym < 1 or days_in_gym > 7:
            return (
                False,
                f"Invalid days_in_gym value: {days_in_gym}. It must be an integer between 1 and 7.",
            )

    if "recent_bodyweight" in tool_input:
        recent_bodyweight = tool_input["recent_bodyweight"]
        if not isinstance(recent_bodyweight, (int, float)) or recent_bodyweight <= 0:
            return (
                False,
                f"Invalid recent_bodyweight value: {recent_bodyweight}. It must be a positive number.",
            )

    return True, ""


def _filter_workoutlog_entries_by_date_range(
    workout_log_entries: list[WorkoutLogEntry],
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
) -> tuple[str, list[WorkoutLogEntry]]:
    """
    Filter the workout log entries to only include entries within the specified date range.
    """
    if not start_datetime and not end_datetime:
        return "", workout_log_entries

    date_range_str = ""
    original_len = len(workout_log_entries)

    start_datetime = start_datetime.strip()
    end_datetime = end_datetime.strip()

    start_datetime = datetime.datetime.fromisoformat(start_datetime)
    end_datetime = datetime.datetime.fromisoformat(end_datetime)

    if start_datetime > end_datetime:
        raise ValueError(
            f"Invalid date range: start_datetime {start_datetime} is after end_datetime {end_datetime}."
        )

    filtered_workout_log_entries = [
        entry
        for entry in workout_log_entries
        if start_datetime <= entry.date <= end_datetime
    ]
    filtered_len = len(filtered_workout_log_entries)

    date_range_str = f"from {start_datetime.isoformat()} to {end_datetime.isoformat()}"
    logger.info(
        f"Filtered workout log entries from {original_len} to {filtered_len} entries {date_range_str}"
    )

    return date_range_str, filtered_workout_log_entries
