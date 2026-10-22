import csv
import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from process import load_stakes, clean_stakes, load_promos, compute_uplift


# ── helpers ───────────────────────────────────────────────────────────────────

def write_stakes_csv(path: Path, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site_id", "site_name", "game", "date", "stakes_eur"])
        w.writerows(rows)


def _promo(start: str, end: str, games: str = "Slots", site_id: str = "1001") -> dict:
    return {
        "promo_id": "PX",
        "site_id": site_id,
        "site_name": "Test Site",
        "games_raw": games,
        "start_date": datetime.strptime(start, "%Y-%m-%d"),
        "end_date": datetime.strptime(end, "%Y-%m-%d"),
    }


# ── load_stakes ───────────────────────────────────────────────────────────────

def test_load_stakes_normal_row():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.csv"
        write_stakes_csv(p, [["1001", "Casino Alpha", "Slots", "2026-01-01", "1000.00"]])
        rows, warnings = load_stakes(p)
    assert len(rows) == 1
    assert rows[0]["site_name"] == "Casino Alpha"
    assert rows[0]["stakes_eur"] == 1000.0
    assert warnings == []


def test_load_stakes_repairs_unquoted_comma_in_site_name():
    """'Casino Beta, DE' unquoted produces 6 raw fields — must be rejoined."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            f.write("site_id,site_name,game,date,stakes_eur\n")
            f.write("1002,Casino Beta, DE,Slots,2026-01-01,500.00\n")
        rows, warnings = load_stakes(p)
    assert len(rows) == 1
    assert rows[0]["site_name"] == "Casino Beta, DE"
    assert rows[0]["stakes_eur"] == 500.0
    assert warnings == []


def test_load_stakes_bad_date_skipped_with_warning():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.csv"
        write_stakes_csv(p, [["1001", "Alpha", "Slots", "not-a-date", "100.00"]])
        rows, warnings = load_stakes(p)
    assert rows == []
    assert len(warnings) > 0


def test_load_stakes_non_numeric_stakes_skipped_with_warning():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.csv"
        write_stakes_csv(p, [["1001", "Alpha", "Slots", "2026-01-01", "N/A"]])
        rows, warnings = load_stakes(p)
    assert rows == []
    assert len(warnings) > 0


# ── clean_stakes ──────────────────────────────────────────────────────────────

def test_clean_stakes_sums_correction_pair():
    rows = [
        {"site_id": "1001", "game": "Slots", "date": "2026-01-01", "stakes_eur": 500.0, "site_name": "Alpha"},
        {"site_id": "1001", "game": "Slots", "date": "2026-01-01", "stakes_eur": -200.0, "site_name": "Alpha"},
    ]
    index, _ = clean_stakes(rows)
    assert index[("1001", "Slots", "2026-01-01")] == pytest.approx(300.0)


def test_clean_stakes_negative_net_clamped_to_zero():
    rows = [
        {"site_id": "1001", "game": "Slots", "date": "2026-01-01", "stakes_eur": 100.0, "site_name": "Alpha"},
        {"site_id": "1001", "game": "Slots", "date": "2026-01-01", "stakes_eur": -200.0, "site_name": "Alpha"},
    ]
    index, _ = clean_stakes(rows)
    assert index[("1001", "Slots", "2026-01-01")] == 0.0


# ── compute_uplift ────────────────────────────────────────────────────────────

def test_compute_uplift_basic_calculation():
    """before=100, during=150 → +50.0%"""
    promo = _promo("2026-01-04", "2026-01-06")  # 3-day promo; before window: Jan 1–3
    index = {
        ("1001", "Slots", "2026-01-01"): 100.0,
        ("1001", "Slots", "2026-01-02"): 0.0,
        ("1001", "Slots", "2026-01-03"): 0.0,
        ("1001", "Slots", "2026-01-04"): 50.0,
        ("1001", "Slots", "2026-01-05"): 50.0,
        ("1001", "Slots", "2026-01-06"): 50.0,
    }
    r = compute_uplift([promo], index)[0]
    assert r["measurable"] is True
    assert r["uplift"] == pytest.approx(50.0, abs=0.1)
    assert r["before"] == pytest.approx(100.0, abs=0.01)
    assert r["during"] == pytest.approx(150.0, abs=0.01)


def test_compute_uplift_inverted_dates_unmeasurable():
    promo = _promo("2026-01-10", "2026-01-05")  # end < start
    r = compute_uplift([promo], {})[0]
    assert r["measurable"] is False
    assert r["uplift"] is None
    assert r["before"] is None
    assert "end date is before start date" in r["reason"].lower()


def test_compute_uplift_zero_baseline_unmeasurable():
    """No stakes in baseline window → cannot divide by zero."""
    promo = _promo("2026-01-04", "2026-01-04")  # 1-day promo
    index = {("1001", "Slots", "2026-01-04"): 200.0}  # during only, no before
    r = compute_uplift([promo], index)[0]
    assert r["measurable"] is False
    assert r["uplift"] is None


def test_compute_uplift_all_games_sums_every_game_at_site():
    """games='ALL' must aggregate every game at that site."""
    promo = _promo("2026-01-04", "2026-01-04", games="ALL")
    index = {
        ("1001", "Slots", "2026-01-03"): 100.0,
        ("1001", "Roulette", "2026-01-03"): 100.0,
        ("1001", "Slots", "2026-01-04"): 120.0,
        ("1001", "Roulette", "2026-01-04"): 130.0,
    }
    r = compute_uplift([promo], index)[0]
    assert r["before"] == pytest.approx(200.0, abs=0.01)
    assert r["during"] == pytest.approx(250.0, abs=0.01)
    assert r["uplift"] == pytest.approx(25.0, abs=0.1)
