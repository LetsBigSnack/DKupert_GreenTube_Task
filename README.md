# GreenTube Promo Uplift

Measures whether a promotion moved stakes at a casino site by comparing total stakes during the promotion against the same number of days immediately before it.

## Documentation

| Document | Audience |
|---|---|
| [KAM Guide](docs/KAM_GUIDE.md) · [HTML version](docs/KAM_GUIDE.html) | Key Account Managers — how to read and use the dashboard |
| [API Reference](docs/api.md) | Developers — all endpoints, request/response schemas, auth |
| [Database Reference](docs/database.md) | Developers — PostgreSQL schema, column descriptions, useful queries |

## Prerequisites

- Docker and Docker Compose
- The `Data/` folder must be present in the repo root with both CSV files:
  ```
  Data/
  ├── stakes_delivery.csv
  └── promos.csv
  ```
  This folder is gitignored (treated as confidential source data).

## Run with Docker

```bash
docker compose up --build
```

- Frontend (KAM dashboard): http://localhost:5173
- Backend API: http://localhost:8000

On startup the backend:
1. Waits for PostgreSQL to be healthy
2. Runs the data pipeline against the mounted `Data/` folder
3. Persists results to PostgreSQL
4. Starts the API server

## Run without Docker

**Backend**
```bash
cd backend
pip install -r requirements.txt
python process.py                        # generates results.csv + results.json
uvicorn api:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

## Custom data paths

```bash
python backend/process.py \
  --stakes /path/to/stakes_delivery.csv \
  --promos /path/to/promos.csv \
  --out-csv results.csv \
  --out-json backend/results.json
```

## Internal upload endpoint

`POST /api/upload` re-runs the pipeline with fresh CSVs without touching the filesystem.
It is **not surfaced in the KAM UI** and requires an API key:

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "X-API-Key: change-me-before-deploying" \
  -F "stakes=@Data/stakes_delivery.csv" \
  -F "promos=@Data/promos.csv"
```

Set `UPLOAD_API_KEY` in your environment or `.env` file before deploying.

## Output

`results.csv` — one row per promo:

| Column | Description |
|--------|-------------|
| `promo_id` | Promo identifier |
| `before` | Total stakes (€) in the baseline window |
| `during` | Total stakes (€) during the promo |
| `uplift` | `(during − before) / before × 100`, one decimal (e.g. `12.3`). Empty if unmeasurable. |
