# API Reference

Base URL: `http://localhost:8000` (Docker) or `http://localhost:8000` (local)

All responses are JSON. CORS is restricted to the frontend origin configured via `ALLOWED_ORIGINS`.

---

## GET /api/health

Liveness check. Returns the number of promo results currently loaded.

**Response**
```json
{
  "status": "ok",
  "promo_count": 120
}
```

---

## GET /api/results

Returns all promo uplift results. Results are pre-sorted by uplift descending (highest performing promos first) when served from PostgreSQL.

**Response** — array of promo result objects:

| Field | Type | Description |
|---|---|---|
| `promo_id` | string | Promo identifier, e.g. `"P01"` |
| `site_id` | string | Numeric site identifier |
| `site_name` | string | Human-readable site name |
| `games` | string | Semicolon-separated game names, or `"ALL"` |
| `start_date` | string | Promo start date, ISO 8601 (`"2026-08-17"`) |
| `end_date` | string | Promo end date, ISO 8601 (`"2026-08-23"`) |
| `before` | number \| null | Total stakes (€) in the baseline window |
| `during` | number \| null | Total stakes (€) during the promo |
| `uplift` | number \| null | `(during − before) / before × 100`, one decimal. `null` if unmeasurable |
| `measurable` | boolean | `false` if the uplift cannot be fairly calculated |
| `reason` | string \| null | Plain-language explanation when `measurable` is `false` |

**Example**
```json
[
  {
    "promo_id": "P07",
    "site_id": "1003",
    "site_name": "Casino Gamma HR",
    "games": "Lucky Lantern",
    "start_date": "2026-09-09",
    "end_date": "2026-09-15",
    "before": 936.99,
    "during": 9063.78,
    "uplift": 867.3,
    "measurable": true,
    "reason": null
  },
  {
    "promo_id": "P05",
    "site_id": "1001",
    "site_name": "Casino Alpha AT",
    "games": "Crystal Reel",
    "start_date": "2026-09-28",
    "end_date": "2026-09-22",
    "before": null,
    "during": null,
    "uplift": null,
    "measurable": false,
    "reason": "Date entry error — end date is before start date"
  }
]
```

---

## POST /api/upload

**Internal endpoint — not exposed in the KAM dashboard UI.**

Accepts a fresh pair of CSV files, re-runs the full processing pipeline, and persists the new results to PostgreSQL (or `results.json` in dev mode). Use this when the data warehouse produces an updated export.

**Authentication**

Requires `X-API-Key` header matching the `UPLOAD_API_KEY` environment variable.

```
X-API-Key: <your-key>
```

Returns `401 Unauthorized` if the key is missing or wrong.

> **Note:** This API key is a placeholder for a demo. In production, replace with OAuth/OIDC and role-based access control so only data-team members can trigger pipeline reruns.

**Request** — `multipart/form-data`

| Field | Required | Description |
|---|---|---|
| `stakes` | yes | `stakes_delivery.csv` — daily stakes per site and game |
| `promos` | yes | `promos.csv` — promo definitions |

Both files must be under 50 MB.

**Response**
```json
{
  "promo_count": 120,
  "measurable": 119,
  "warnings": [
    "51 (site_id, game, date) combos had multiple rows (assumed correction/reversal entries — summed to net).",
    "P05: end_date is before start_date — marked unmeasurable"
  ]
}
```

**Error responses**

| Status | Meaning |
|---|---|
| `401` | Missing or invalid API key |
| `413` | File exceeds 50 MB |
| `422` | Pipeline failed — malformed or missing CSV columns |

**Example (curl)**
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "X-API-Key: your-key-here" \
  -F "stakes=@Data/stakes_delivery.csv" \
  -F "promos=@Data/promos.csv"
```
