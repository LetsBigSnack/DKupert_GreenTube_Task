"""
PostgreSQL persistence layer.
All reads/writes go through this module; api.py and process.py never touch psycopg2 directly.
"""

import logging
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_pool: ThreadedConnectionPool | None = None


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Set it to a PostgreSQL DSN, e.g. "
                "postgresql://greentube:greentube@localhost:5432/greentube"
            )
        _pool = ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
    return _pool


@contextmanager
def _conn():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


_CREATE_TABLE = """
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
    )
"""


def init_db() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE)
    log.info("Database ready.")


def save_results(results: list[dict]) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE promo_results")
            cur.executemany(
                """
                INSERT INTO promo_results
                    (promo_id, site_id, site_name, games, start_date, end_date,
                     before_eur, during_eur, uplift, measurable, reason)
                VALUES
                    (%(promo_id)s, %(site_id)s, %(site_name)s, %(games)s,
                     %(start_date)s, %(end_date)s, %(before)s, %(during)s,
                     %(uplift)s, %(measurable)s, %(reason)s)
                """,
                results,
            )
    log.info("Saved %d promo results to database.", len(results))


def load_results() -> list[dict]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT promo_id, site_id, site_name, games, start_date, end_date,
                       before_eur, during_eur, uplift, measurable, reason
                FROM promo_results
                ORDER BY uplift DESC NULLS LAST
                """
            )
            cols = [d[0] for d in cur.description]
            rows = []
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                d["before"] = float(d.pop("before_eur")) if d["before_eur"] is not None else None
                d["during"] = float(d.pop("during_eur")) if d["during_eur"] is not None else None
                d["uplift"] = float(d["uplift"]) if d["uplift"] is not None else None
                rows.append(d)
    return rows
