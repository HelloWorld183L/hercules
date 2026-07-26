from pathlib import Path

from hercules.parsers import parse_fitnotes_csv


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
