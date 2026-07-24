"""Fast structural validation for the submitted project."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.retention import calculate_retention  # noqa: E402


REQUIRED_FILES = [
    "README.md",
    "notebooks/final_project_variant_1.ipynb",
    "reports/final_report.md",
    "src/retention.py",
    "tests/test_retention.py",
    "data/raw/ab_test.csv",
]


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    if missing:
        raise SystemExit(f"Не найдены обязательные файлы: {', '.join(missing)}")

    with (PROJECT_ROOT / "notebooks/final_project_variant_1.ipynb").open(
        encoding="utf-8"
    ) as notebook_file:
        notebook = json.load(notebook_file)
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    saved_errors = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    if saved_errors:
        raise SystemExit("В ноутбуке сохранены ошибки выполнения")

    registrations = pd.DataFrame(
        {"reg_ts": [1704067200, 1704067200], "uid": [1, 2]}
    )
    authorizations = pd.DataFrame(
        {"auth_ts": [1704067200, 1704153600, 1704067200], "uid": [1, 1, 2]}
    )
    smoke_result = calculate_retention(
        registrations, authorizations, max_days=1, as_percent=True
    )
    if smoke_result.iloc[0].tolist() != [100.0, 50.0]:
        raise SystemExit("Smoke-тест retention вернул неожиданный результат")

    ab_data = pd.read_csv(PROJECT_ROOT / "data/raw/ab_test.csv", sep=";")
    if tuple(ab_data.columns) != ("user_id", "revenue", "testgroup"):
        raise SystemExit("Неожиданная схема датасета A/B-теста")
    if len(ab_data) != 404_770:
        raise SystemExit("Неожиданное число строк в датасете A/B-теста")

    print("Project validation passed")
    print(f"Notebook: {len(code_cells)} code cells, {len(saved_errors)} saved errors")
    print(f"A/B dataset: {len(ab_data):,} rows")


if __name__ == "__main__":
    main()
