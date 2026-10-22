# Database Reference

The application uses **PostgreSQL 16** as its persistence layer. The schema is created automatically at startup via `database.init_db()` — no manual migrations needed.

---

## Connection

Configured via the `DATABASE_URL` environment variable:

```
postgresql://<user>:<password>@<host>:<port>/<dbname>
```

Docker Compose default:
```
postgresql://greentube:greentube@postgres:5432/greentube
```

The API falls back to `backend/results.json` when `DATABASE_URL` is not set (local development without Docker).

---

## Table: `promo_results`

Stores one row per promotion. The table is **truncated and repopulated** on each pipeline run — there is no version history. See "What I'd do with more time" in `NOTES.md` for an audit-log approach.

```sql
CREATE TABLE IF NOT EXISTS promo_results (
    promo_id     TEXT PRIMARY KEY,
    site_id      TEXT NOT NULL,
    site_name    TEXT NOT NULL,
    games        TEXT NOT NULL,
    start_date   TEXT NOT NULL,
    end_date     TEXT NOT NULL,
    before_eur   NUMERIC,
    during_eur   NUMERIC,
    uplift       NUMERIC,
    measurable   BOOLEAN NOT NULL,
    reason       TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Column descriptions

| Column | Type | Nullable | Description |
|---|---|---|---|
| `promo_id` | TEXT | no | Primary key; matches the promo_id in the source CSV |
| `site_id` | TEXT | no | Numeric site identifier from the source data |
| `site_name` | TEXT | no | Human-readable site name (with comma-split fix applied) |
| `games` | TEXT | no | Raw games field: semicolon-separated names or `ALL` |
| `start_date` | TEXT | no | Promo start date as ISO 8601 string |
| `end_date` | TEXT | no | Promo end date as ISO 8601 string |
| `before_eur` | NUMERIC | yes | Total stakes (€) in the baseline period. `NULL` if unmeasurable |
| `during_eur` | NUMERIC | yes | Total stakes (€) during the promo. `NULL` if unmeasurable |
| `uplift` | NUMERIC | yes | `(during − before) / before × 100`. `NULL` if unmeasurable |
| `measurable` | BOOLEAN | no | `false` when uplift cannot be fairly calculated |
| `reason` | TEXT | yes | Plain-language explanation for `measurable = false` |
| `processed_at` | TIMESTAMPTZ | no | Timestamp of the pipeline run that produced this row |

### API field mapping

The API layer renames the DB columns to match the original contract:

| DB column | API field |
|---|---|
| `before_eur` | `before` |
| `during_eur` | `during` |

---

## Useful queries

**All measurable promos sorted by uplift:**
```sql
SELECT promo_id, site_name, games, uplift
FROM promo_results
WHERE measurable = true
ORDER BY uplift DESC;
```

**Promos with a low baseline (potentially unreliable uplift):**
```sql
SELECT promo_id, site_name, before_eur, uplift
FROM promo_results
WHERE measurable = true AND before_eur < 5000
ORDER BY before_eur;
```

**Unmeasurable promos:**
```sql
SELECT promo_id, site_name, reason
FROM promo_results
WHERE measurable = false;
```

**Last pipeline run timestamp:**
```sql
SELECT MAX(processed_at) FROM promo_results;
```
