import datetime
import sqlite3
from pathlib import Path

from hercules.parsers import parse_fitnotes_csv, parse_fitnotes_db


def test_parse_fitnotes_csv_groups_duplicate_rows_into_sets(tmp_path: Path) -> None:
    csv_path = tmp_path / "fitnotes.csv"
    csv_path.write_text(
        "Date,Exercise,Reps,Weight,Weight Unit\n"
        "2024-01-01,Barbell Squat,5,100,kg\n"
        "2024-01-01,Barbell Squat,5,100,kg\n"
        "2024-01-01,Barbell Squat,5,100,kg\n",
        encoding="utf-8",
    )

    entries = parse_fitnotes_csv(csv_path)

    assert len(entries) == 1
    assert entries[0].exercise == "Barbell Squat"
    assert entries[0].sets == 3
    assert entries[0].reps == 5
    assert entries[0].weight == 100.0
    assert entries[0].unit == "kg"


def test_parse_fitnotes_csv_reads_sets_column(tmp_path: Path) -> None:
    """
    Test that the parser correctly reads the 'Sets' column when it is present in the CSV file.
    This test creates a temporary CSV file with the 'Sets' column and verifies that the parser
    correctly reads the number of sets for each workout log entry.
    """

    csv_path = tmp_path / "fitnotes_sets.csv"
    csv_path.write_text(
        "Date,Exercise,Sets,Reps,Weight,Weight Unit\n"
        "2024-01-01,Barbell Squat,2,5,100,kg\n"
        "2024-01-02,Barbell Squat,1,5,100,kg\n",
        encoding="utf-8",
    )

    entries = parse_fitnotes_csv(csv_path)

    assert len(entries) == 2
    assert entries[0].sets == 2
    assert entries[1].sets == 1
    assert entries[0].exercise == "Barbell Squat"
    assert entries[1].exercise == "Barbell Squat"


def test_parse_fitnotes_csv_skips_invalid_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "fitnotes_invalid.csv"
    csv_path.write_text(
        "Date,Exercise,Reps,Weight,Weight Unit\n"
        "2024-01-01,Barbell Squat,5,100,kg\n"
        "2024-01-02,Barbell Squat,5,not-a-number,kg\n"
        "2024-01-03,Barbell Squat,5,100,kg\n",
        encoding="utf-8",
    )

    entries = parse_fitnotes_csv(csv_path)

    assert len(entries) == 2
    assert entries[0].date == datetime.datetime(2024, 1, 1)
    assert entries[1].date == datetime.datetime(2024, 1, 3)


def test_parse_fitnotes_db_returns_empty_when_no_entries(tmp_path: Path) -> None:
    db_path = tmp_path / "fitnotes.fitnotes"
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        "CREATE TABLE training_log (_id INTEGER PRIMARY KEY, date TEXT, exercise_id INTEGER, reps INTEGER, metric_weight REAL)"
    )
    cursor.execute("CREATE TABLE exercise (_id INTEGER PRIMARY KEY, name TEXT)")
    connection.commit()
    connection.close()

    entries = parse_fitnotes_db(db_path)

    assert entries == []


def test_parse_fitnotes_db_reads_multiple_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "fitnotes.fitnotes"
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        "CREATE TABLE training_log (_id INTEGER PRIMARY KEY, date TEXT, exercise_id INTEGER, reps INTEGER, metric_weight REAL)"
    )
    cursor.execute("CREATE TABLE exercise (_id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute(
        "INSERT INTO exercise (_id, name) VALUES (?, ?)", (1, "Barbell Squat")
    )
    cursor.execute(
        "INSERT INTO training_log (date, exercise_id, reps, metric_weight) VALUES (?, ?, ?, ?)",
        ("2024-01-01", 1, 5, 100.0),
    )
    cursor.execute(
        "INSERT INTO training_log (date, exercise_id, reps, metric_weight) VALUES (?, ?, ?, ?)",
        ("2024-01-02", 1, 5, 100.0),
    )

    connection.commit()
    connection.close()

    entries = parse_fitnotes_db(db_path)

    assert len(entries) == 2
    assert entries[0].exercise == "Barbell Squat"
    assert entries[0].sets == 1
    assert entries[1].sets == 1
    assert entries[0].weight == 100.0
    assert entries[0].unit == "kgs"
