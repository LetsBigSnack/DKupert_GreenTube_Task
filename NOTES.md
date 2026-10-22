# Notes

## Data problems found

Findings were identified through automated analysis (Claude Code) and then manually verified by DKupert before acceptance.

### 1. Unquoted comma in site name — `stakes_delivery.csv`
`Casino Beta, DE` (site 1002) contains a comma but was not quoted in the CSV export.
Standard CSV parsers split it into two fields, producing 6 columns instead of 5.
This affects all 2,562 rows for that site.
**Fix:** when a row has 6 fields and field 0 is numeric, merge fields 1 and 2 back into the site name.

### 2. Duplicate rows with negative stakes — `stakes_delivery.csv`
51 `(site_id, game, date)` combinations appear twice — once with a positive value and once with a negative value.
**Assumption:** these are correction/reversal entries from the data warehouse (a common pattern when a day's figure is adjusted after the initial export).
**Fix:** sum both rows to a net value. Cases where the net is still negative are treated as 0 for the uplift calculation and flagged.

### 3. Inverted dates — `promos.csv`, promo P05
P05 has `start_date = 2026-09-28` and `end_date = 2026-09-22` — the end is before the start.
The promo duration cannot be determined.
**Fix:** P05 is marked as unmeasurable with reason "Date entry error — end date is before start date".

### 4. Sites with stakes data but no promotions
Sites 1036 and 1012 appear in `stakes_delivery.csv` but have no entries in `promos.csv`.
No fix needed — they simply never ran a measured promotion.

---

## What I would do with more time

- **PostgreSQL is in place; Redis is the next step.** Results are persisted to PostgreSQL via `DATABASE_URL`. Redis would sit in front as a read cache once query times become a problem — but there is no point adding it before the read path is measurably slow. Order matters: DB first, cache second.
- **Upload audit log.** Record who uploaded what, when, how many rows were parsed, and any warnings. Essential for traceability in a production data pipeline.
- **Proper authentication.** The `/api/upload` endpoint is protected by a single API key (env var) as a placeholder. In production this should be replaced with OAuth/OIDC and role-based access control: KAMs get read-only access; only data-team members can trigger a new upload.
- **Statistical significance.** A 5% uplift on 10 days of data is very different from one on 28 days. Bootstrap confidence intervals or a paired t-test per promo would let KAMs distinguish real signal from noise.
- **Seasonal and day-of-week normalisation.** The current baseline is the N days immediately before the promo. If the promo spans a weekend and the baseline is all weekdays (or vice versa), the comparison is unfair. A day-of-week-adjusted baseline would be more reliable.
- **Overlapping promo detection.** If two promos at the same site run concurrently, or if one promo's baseline window falls within another promo's active window, the uplift figure is contaminated. Automated detection and flagging of these cases would reduce false positives.
- **dbt models.** Move the cleaning and aggregation logic into warehouse-native dbt models so the data is already clean before it reaches this service.

---

## AI tools used

- **Claude Code (Anthropic)** — used throughout the entire task: exploratory data analysis, identifying data quality issues, discussing and challenging architectural decisions, writing and reviewing all code. All findings were manually verified before being accepted.

- **Claude Code sub-agents** — after the initial implementation, three specialised sub-agents were spun up in parallel to review the work independently:
  - *KAM / UX agent* — adopted the perspective of a Key Account Manager to assess whether the dashboard surfaced the right information and flagged usability gaps (missing € impact column, unmeasurable promo explanation too technical, default filter state).
  - *Code review agent* — reviewed the backend and frontend for correctness, security, and robustness (found the broken Docker volume mount, unbounded upload size, invalid locale tag).
  - *QA / testing agent* — identified untested edge cases and wrote concrete pytest cases for the core processing logic.

  Findings from all three agents were reviewed and discussed before being applied.

- **Second sub-agent review round** — after adding the KAM guide, database docs, and HTML guide to the repo, a second parallel review was run:
  - *KAM / UX agent (round 2)* — identified that "Before (€)" / "During (€)" column labels would be misread as revenue (GGR/NGR) rather than stakes, flagged that Days and Impact (€) sort columns were silently broken, and noted the missing date column and export functionality.
  - *Code review agent (round 2)* — confirmed the sort bug (`_duration` / `_impact` keys missing from row objects), flagged the hardcoded PostgreSQL password exposed on host port 5432, and noted the deprecated FastAPI `on_event` startup hook.
  - *QA / testing agent (round 2)* — verified the before-period date formula by hand, found that NOTES.md described the P05 reason text incorrectly, and wrote a full pytest suite covering all critical pipeline paths.

  Applied from this round: renamed Before/During columns to "Stakes Before (€)" / "Stakes During (€)"; fixed the Days and Impact sort; corrected the P05 reason text in these notes; added `backend/tests/test_process.py`.

- **Manual end-to-end testing** — after all code changes were complete, the full application was run via `docker compose up --build` and every dashboard feature was tested manually in the browser: table loading, sorting on all columns, promo ID search, site filter, game filter, uplift direction segmented control, measurable toggle, low-baseline warnings, N/A badge hover tooltip, and the summary stats in the header. All features behaved as expected.
