"""
FastAPI backend.
- GET  /api/results    → full results list (KAM-facing)
- GET  /api/health     → liveness check
- POST /api/upload     → internal endpoint (API-key protected); accepts fresh CSVs,
                         re-runs the pipeline, persists to PostgreSQL.
                         Not surfaced in the KAM UI.

NOTE on auth: the upload endpoint uses a single API key as a placeholder.
In production this must be replaced with OAuth/OIDC and role-based access control.
"""

import json
import logging
import os
import tempfile
import warnings as _warnings
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Header, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware

from database import DATABASE_URL, init_db, load_results, save_results
from process import run_pipeline, write_results_csv, write_results_json

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API key setup — warn loudly if using the insecure default
# ---------------------------------------------------------------------------
_UPLOAD_API_KEY = os.environ.get("UPLOAD_API_KEY", "")
_INSECURE_DEFAULT = "change-me-before-deploying"

if not _UPLOAD_API_KEY:
    _UPLOAD_API_KEY = _INSECURE_DEFAULT
    log.warning(
        "UPLOAD_API_KEY is not set. Using the insecure default '%s'. "
        "Set this environment variable before any real deployment.",
        _INSECURE_DEFAULT,
    )
elif _UPLOAD_API_KEY == _INSECURE_DEFAULT:
    log.warning(
        "UPLOAD_API_KEY is set to the known public default. "
        "Replace it with a strong secret before deploying."
    )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="GreenTube Promo Uplift API")

# Restrict CORS to the known frontend origin in production.
# Override ALLOWED_ORIGINS env var if you deploy behind a real domain.
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

_RESULTS_JSON = Path(__file__).parent / "results.json"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@app.on_event("startup")
def startup():
    if DATABASE_URL:
        init_db()
        log.info("Connected to PostgreSQL.")
    else:
        log.warning(
            "DATABASE_URL not set — serving results from results.json (dev mode). "
            "Set DATABASE_URL to enable PostgreSQL."
        )


# ---------------------------------------------------------------------------
# Auth dependency for the internal upload endpoint
# ---------------------------------------------------------------------------
def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != _UPLOAD_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def _get_results() -> list[dict]:
    if DATABASE_URL:
        return load_results()
    if _RESULTS_JSON.exists():
        with open(_RESULTS_JSON, encoding="utf-8") as f:
            return json.load(f)
    return []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    results = _get_results()
    return {"status": "ok", "promo_count": len(results)}


@app.get("/api/results")
def get_results():
    return _get_results()


@app.post("/api/upload", dependencies=[Depends(require_api_key)])
async def upload_csvs(
    stakes: UploadFile = File(..., description="stakes_delivery.csv"),
    promos: UploadFile = File(..., description="promos.csv"),
):
    """
    Internal endpoint — not visible in the KAM UI.
    Protected by X-API-Key header (env var UPLOAD_API_KEY).

    NOTE: In production replace with OAuth/OIDC + role-based access control.
    The API key here is a placeholder, not production-grade auth.
    """
    stakes_bytes = await stakes.read(MAX_UPLOAD_BYTES + 1)
    if len(stakes_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="stakes file exceeds 50 MB limit")

    promos_bytes = await promos.read(MAX_UPLOAD_BYTES + 1)
    if len(promos_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="promos file exceeds 50 MB limit")

    with tempfile.TemporaryDirectory() as tmpdir:
        stakes_path = Path(tmpdir) / "stakes_delivery.csv"
        promos_path = Path(tmpdir) / "promos.csv"
        stakes_path.write_bytes(stakes_bytes)
        promos_path.write_bytes(promos_bytes)

        try:
            new_results, warnings = run_pipeline(stakes_path, promos_path)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Pipeline error: {e}")

    if DATABASE_URL:
        save_results(new_results)
    else:
        write_results_json(new_results, _RESULTS_JSON)

    write_results_csv(new_results, Path(__file__).parent.parent / "results.csv")

    measurable = sum(1 for r in new_results if r["measurable"])
    return {
        "promo_count": len(new_results),
        "measurable": measurable,
        "warnings": warnings,
    }
