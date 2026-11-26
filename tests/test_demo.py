"""Demo database seeding (budget-ai seed-demo) and budget-ai-api --db."""
import os
from datetime import date
from unittest.mock import patch

import pytest

from budget_ai.api import launch
from budget_ai.budgets import budget_report
from budget_ai.cli import main
from budget_ai.db.database import Database
from budget_ai.demo import seed_demo
from budget_ai.insights import spending_insights


def open_db(path):
    return Database(str(path))


def all_dates(db):
    return [row["date"] for row in db.list_activity(limit=500) if row["date"]]


def test_seed_demo_matches_the_design(tmp_path):
    path = tmp_path / "demo.db"
    today = date(2026, 11, 18)
    seed_demo(str(path), today=today)

    db = open_db(path)
    report = budget_report(db, month="2026-11", today=today)
    assert report["total_budget"] == 4000
    assert len(report["budgets"]) == 7
    assert [g["icon"] for g in report["goals"]] == ["shield", "sun", "laptop"]
    assert sum(g["saved_amount"] for g in report["goals"]) == 7200

    titles = [row["title"] for row in db.list_activity(limit=500)]
    assert "Payday" in titles and "Coffee break" in titles and "Whole Foods" in titles

    insights = spending_insights(db, today=today)
    assert insights["spent"] > 0 and insights["previous"]["spent"] > 0
    assert insights["last_7_days_total"] > 0
    db.close()


@pytest.mark.parametrize("today", [date(2026, 11, 18), date(2026, 12, 1), date(2027, 1, 31)])
def test_seed_demo_dates_stay_in_this_and_last_month(tmp_path, today):
    path = tmp_path / "demo.db"
    seed_demo(str(path), today=today)
    db = open_db(path)
    dates = all_dates(db)
    db.close()
    prev_first = date(today.year - (today.month == 1), (today.month - 2) % 12 + 1, 1)
    assert dates and all(prev_first.isoformat() <= d <= today.isoformat() for d in dates)


def test_seed_demo_refuses_to_overwrite_without_force(tmp_path):
    path = tmp_path / "demo.db"
    path.write_text("not a database")
    with pytest.raises(FileExistsError):
        seed_demo(str(path))
    assert path.read_text() == "not a database"

    seed_demo(str(path), force=True)
    db = open_db(path)
    assert len(db.list_budgets()) == 7
    db.close()


def test_cli_seed_demo_never_touches_database_path(tmp_path, monkeypatch, capsys):
    real = tmp_path / "budget.db"
    demo = tmp_path / "demo.db"
    monkeypatch.setenv("DATABASE_PATH", str(real))

    main(["seed-demo", "--db", str(demo)])
    assert demo.exists() and not real.exists()
    assert "budget-ai-api --db" in capsys.readouterr().out

    with pytest.raises(SystemExit) as exit_info:
        main(["seed-demo", "--db", str(demo)])
    assert exit_info.value.code == 1

    main(["seed-demo", "--db", str(demo), "--force"])
    assert not real.exists()


def test_api_launch_db_option_sets_database_path(monkeypatch):
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    with patch.object(launch.uvicorn, "run") as run:
        launch.main(["--db", "data/demo.db"])
    assert os.environ["DATABASE_PATH"] == "data/demo.db"
    run.assert_called_once()
