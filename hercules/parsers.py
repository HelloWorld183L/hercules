"""Module for parsing exercise logs into a standard format for Hercules to process."""

import datetime
from pathlib import Path
import csv

from pydantic import BaseModel

import sqlite3

import logging

logger = logging.getLogger("hercules")

class WorkoutLogEntry(BaseModel):
    """Represents a single workout log entry."""

    date: datetime.datetime
    exercise: str
    sets: int
    reps: int
    weight: float
    unit: str

def parse_fitnotes_csv(file_path: Path | str) -> list[WorkoutLogEntry]:
    """Parse the FitNotes CSV file and return a list of WorkoutLogEntry objects."""

    parsed_data = []
    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    fieldnames = set(reader.fieldnames or [])
    has_sets_column = 'Sets' in fieldnames

    if has_sets_column:
        for row in rows:
            workout_log_entry = WorkoutLogEntry(
                date=datetime.datetime.fromisoformat(row['Date'].strip()),
                exercise=row['Exercise'].strip(),
                sets=int((row.get('Sets') or '1').strip()),
                reps=int((row.get('Reps') or '0').strip()),
                weight=float((row.get('Weight') or '0').strip()),
                unit=(row.get('Weight Unit') or '').strip()
            )
            parsed_data.append(workout_log_entry)
        return parsed_data

    # Group rows by Date, Exercise, Reps, Weight, and Weight Unit to count sets
    grouped_rows = {}
    for row in rows:
        grouping_key = (
            (row['Date'].strip()),
            (row['Exercise'].strip()),
            (row['Reps'].strip()),
            (row['Weight'].strip()),
            (row['Weight Unit'].strip()),
        )
        grouped_rows.setdefault(grouping_key, []).append(row)

    # Create WorkoutLogEntry objects from grouped rows
    for grouped_row_list in grouped_rows.values():
        row = grouped_row_list[0]
        try:
            workout_log_entry = WorkoutLogEntry(
                date=datetime.datetime.fromisoformat(row['Date'].strip()),
                exercise=row['Exercise'].strip(),
                sets=len(grouped_row_list),
                reps=int((row.get('Reps') or '0').strip()),
                weight=float((row.get('Weight') or '0').strip()),
                unit=(row.get('Weight Unit') or '').strip()
            )
        except ValueError as e:
            logger.error(f"Skipping row. Error parsing row {row} in file {file_path}: {e}")
            continue
        parsed_data.append(workout_log_entry)

    return parsed_data

def parse_fitnotes_db(db_path: Path | str) -> list[WorkoutLogEntry]:
    """Parse the FitNotes database file (.fitnotes) and return a list of WorkoutLogEntry objects."""

    sqlite_connection = sqlite3.connect(db_path)
    cursor = sqlite_connection.cursor()

    log_entries = cursor.execute("""
        SELECT 
            tl._id, tl.date, ex.name, tl.reps, tl.metric_weight 
        FROM 
            training_log tl
        JOIN 
            exercise ex ON tl.exercise_id = ex._id
    """).fetchall()

    sqlite_connection.close()

    logger.warning(f"FitNotes measurement units are not properly referred to in the database. Assuming all weights are in kilograms. Please verify this assumption.")

    if len(log_entries) == 0:
        logger.warning(f"No workout log entries found in database {db_path}.")
        return []
    
    # Group rows by Date, Exercise, Reps, Weight, and Weight Unit to count sets
    grouped_rows = {}
    for row in log_entries:
        # FIXME: Row uses indices instead of column names; consider using a namedtuple or dict for clarity
        grouping_key = (
            (row[0]),
            (row[1].strip()),
            (row[2].strip()),
            (row[3]),
            (row[4]),
        )
        grouped_rows.setdefault(grouping_key, []).append(row)

    parsed_data = []
    # Create WorkoutLogEntry objects from grouped rows
    for grouped_row_list in grouped_rows.values():
        row = grouped_row_list[0]
        try:
            workout_log_entry = WorkoutLogEntry(
                date=datetime.datetime.fromisoformat(row[1].strip()),
                exercise=row[2].strip(),
                sets=len(grouped_row_list),
                reps=int((row[3] or '0')),
                weight=float((row[4] or '0')),
                unit='kgs'
            )
        except ValueError as e:
            logger.error(f"Skipping row. Error parsing row {row} in file {db_path}: {e}")
            continue
        parsed_data.append(workout_log_entry)

    if len(parsed_data) == 0:
        logger.warning(f"No valid workout log entries could be parsed from database {db_path}.")

    return parsed_data

