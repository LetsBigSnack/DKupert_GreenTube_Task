"""
Data processing pipeline: load, clean, and compute promo uplift.
Can be run standalone or imported by the API.
"""

import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


def load_stakes(path: Path) -> tuple[list[dict], list[str]]:
    """
    Load stakes_delivery.csv, fixing the unquoted-comma site-name bug.
    Returns (rows, parse_warnings).
    """
    rows = []
    warnings = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        expected_cols = len(header)  # 5

        for lineno, raw in enumerate(reader, start=2):
            n = len(raw)

            if n > expected_cols and raw[0].isdigit():
                # Site name with one or more unquoted commas splits into extra fields.
                # The last three fields are always: game, date, stakes_eur.
                site_id = raw[0]
                stakes_str = raw[-1]
                date_str = raw[-2]
                game = raw[-3]
                site_name = ",".join(raw[1:-3])
            elif n == expected_cols:
                site_id, site_name, game, date_str, stakes_str = raw
            else:
                warnings.append(
                    f"Line {lineno}: unexpected {n} columns, skipped: {raw!r}"
                )
                continue

            # Normalise and validate the date so lookup keys are always ISO format.
            try:
                date = datetime.strptime(date_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                warnings.append(
                    f"Line {lineno}: unparseable date {date_str!r}, skipped"
                )
                continue

            try:
                stakes_eur = float(stakes_str)
            except ValueError:
                warnings.append(
                    f"Line {lineno}: non-numeric stakes {stakes_str!r}, skipped"
                )
                continue

            rows.append(
                {
                    "site_id": site_id.strip(),
                    "site_name": site_name.strip(),
                    "game": game.strip(),
                    "date": date,
                    "stakes_eur": stakes_eur,
                }
            )

    return rows, warnings


def clean_stakes(rows: list[dict]) -> tuple[dict, list[str]]:
    """
    Aggregate stakes by (site_id, game, date), summing correction rows.
    Returns (index, warnings) where index maps (site_id, game, date) -> stakes_eur.
    """
    accumulator: dict[tuple, float] = defaultdict(float)
    counts: dict[tuple, int] = defaultdict(int)

    for r in rows:
        key = (r["site_id"], r["game"], r["date"])
        accumulator[key] += r["stakes_eur"]
        counts[key] += 1

    warnings = []
    duplicates = {k for k, c in counts.items() if c > 1}
    if duplicates:
        warnings.append(
            f"{len(duplicates)} (site_id, game, date) combos had multiple rows "
            f"(assumed correction/reversal entries from the warehouse — summed to net). "
            f"Sample: {list(duplicates)[:3]}"
        )

    negatives = {k: v for k, v in accumulator.items() if v < 0}
    if negatives:
        warnings.append(
            f"{len(negatives)} (site_id, game, date) keys have a negative net stake "
            f"after summing correction rows. Treated as 0. Sample: {list(negatives.items())[:3]}"
        )
        for k in negatives:
            accumulator[k] = 0.0

    return dict(accumulator), warnings


def load_promos(path: Path) -> tuple[list[dict], list[str]]:
    rows = []
    warnings = []

    with open(path, newline="", encoding="utf-8") as f:
        for lineno, row in enumerate(csv.DictReader(f), start=2):
            promo_id = row["promo_id"].strip()
            try:
                start = datetime.strptime(row["start_date"].strip(), "%Y-%m-%d")
                end = datetime.strptime(row["end_date"].strip(), "%Y-%m-%d")
            except ValueError as e:
                warnings.append(f"{promo_id}: date parse error — {e}, skipped")
                continue

            if end < start:
                warnings.append(
                    f"{promo_id}: end_date {row['end_date']} is before start_date "
                    f"{row['start_date']} — cannot determine duration, marked unmeasurable"
                )

            rows.append(
                {
                    "promo_id": promo_id,
                    "site_id": row["site_id"].strip(),
                    "site_name": row["site_name"].strip(),
                    "games_raw": row["games"].strip(),
                    "start_date": start,
                    "end_date": end,
                }
            )

    return rows, warnings


def compute_uplift(
    promos: list[dict],
    stakes_index: dict[tuple, float],
) -> list[dict]:
    """
    For each promo compute before/during totals and uplift %.
    Unmeasurable promos get before=None, during=None, uplift=None, reason=<str>.
    """
    games_by_site: dict[str, set[str]] = defaultdict(set)
    for (site_id, game, _date) in stakes_index:
        games_by_site[site_id].add(game)

    results = []

    for p in promos:
        promo_id = p["promo_id"]
        site_id = p["site_id"]
        start: datetime = p["start_date"]
        end: datetime = p["end_date"]

        if end < start:
            results.append(
                {
                    "promo_id": promo_id,
                    "site_id": site_id,
                    "site_name": p["site_name"],
                    "games": p["games_raw"],
                    "start_date": start.date().isoformat(),
                    "end_date": end.date().isoformat(),
                    "before": None,
                    "during": None,
                    "uplift": None,
                    "measurable": False,
                    "reason": "Date entry error — end date is before start date",
                }
            )
            continue

        duration = (end - start).days + 1

        # Pre-compute date strings once per promo (not per game)
        before_dates = [
            (start - timedelta(days=duration - i)).strftime("%Y-%m-%d")
            for i in range(duration)
        ]
        during_dates = [
            (start + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(duration)
        ]

        games_raw = p["games_raw"]
        if games_raw.upper() == "ALL":
            games = list(games_by_site.get(site_id, []))
        else:
            games = [g.strip() for g in games_raw.split(";")]

        before_total = sum(
            stakes_index.get((site_id, game, d), 0.0)
            for game in games
            for d in before_dates
        )
        during_total = sum(
            stakes_index.get((site_id, game, d), 0.0)
            for game in games
            for d in during_dates
        )

        if before_total == 0:
            results.append(
                {
                    "promo_id": promo_id,
                    "site_id": site_id,
                    "site_name": p["site_name"],
                    "games": games_raw,
                    "start_date": start.date().isoformat(),
                    "end_date": end.date().isoformat(),
                    "before": 0.0,
                    "during": round(during_total, 2),
                    "uplift": None,
                    "measurable": False,
                    "reason": "No stakes in the baseline period — cannot divide by zero",
                }
            )
            continue

        uplift_pct = (during_total - before_total) / before_total * 100

        results.append(
            {
                "promo_id": promo_id,
                "site_id": site_id,
                "site_name": p["site_name"],
                "games": games_raw,
                "start_date": start.date().isoformat(),
                "end_date": end.date().isoformat(),
                "before": round(before_total, 2),
                "during": round(during_total, 2),
                "uplift": round(uplift_pct, 1),
                "measurable": True,
                "reason": None,
            }
        )

    return results


def run_pipeline(
    stakes_path: Path,
    promos_path: Path,
) -> tuple[list[dict], list[str]]:
    """Full pipeline: load → clean → compute. Returns (results, all_warnings)."""
    for p in (stakes_path, promos_path):
        if not p.exists():
            raise FileNotFoundError(f"Required file not found: {p}")

    all_warnings: list[str] = []

    stakes_rows, w = load_stakes(stakes_path)
    all_warnings.extend(w)

    stakes_index, w = clean_stakes(stakes_rows)
    all_warnings.extend(w)

    promos, w = load_promos(promos_path)
    all_warnings.extend(w)

    results = compute_uplift(promos, stakes_index)

    return results, all_warnings


def write_results_csv(results: list[dict], out_path: Path) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["promo_id", "before", "during", "uplift"])
        for r in results:
            uplift_str = f"{r['uplift']:.1f}" if r["uplift"] is not None else ""
            before_str = f"{r['before']:.2f}" if r["before"] is not None else ""
            during_str = f"{r['during']:.2f}" if r["during"] is not None else ""
            writer.writerow([r["promo_id"], before_str, during_str, uplift_str])


def write_results_json(results: list[dict], out_path: Path) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Default paths work when running from the repo root or from backend/.
    # The Dockerfile CMD passes explicit paths to avoid any ambiguity.
    _root = Path(__file__).parent.parent
    parser = argparse.ArgumentParser(description="Compute promo uplift from CSV data.")
    parser.add_argument(
        "--stakes",
        default=str(_root / "Data" / "stakes_delivery.csv"),
        help="Path to stakes_delivery.csv",
    )
    parser.add_argument(
        "--promos",
        default=str(_root / "Data" / "promos.csv"),
        help="Path to promos.csv",
    )
    parser.add_argument(
        "--out-csv",
        default=str(Path(__file__).parent / "results.csv"),
        help="Output path for results.csv",
    )
    parser.add_argument(
        "--out-json",
        default=str(Path(__file__).parent / "results.json"),
        help="Output path for results.json (consumed by the API when DATABASE_URL is not set)",
    )
    args = parser.parse_args()

    results, warnings = run_pipeline(Path(args.stakes), Path(args.promos))

    if warnings:
        print(f"\n{'='*60}")
        print(f"PARSE / DATA WARNINGS ({len(warnings)} total):")
        for w in warnings:
            print(f"  • {w}")
        print(f"{'='*60}\n")

    write_results_csv(results, Path(args.out_csv))

    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        from database import init_db, save_results
        init_db()
        save_results(results)
        print("Results written to PostgreSQL.")
    else:
        write_results_json(results, Path(args.out_json))
        print(f"Results written to {args.out_json}")

    measurable = sum(1 for r in results if r["measurable"])
    print(f"Done. {len(results)} promos processed, {measurable} measurable.")
    print(f"  → {args.out_csv}")
