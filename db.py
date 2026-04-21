"""
db.py — MySQL connection using PyMySQL.
Import `get_db()` anywhere in the app to get a (conn, cursor) context.
Supports both local env vars (DB_HOST, DB_PORT, etc.)
and Railway's DATABASE_URL (mysql://user:pass@host:port/dbname).
"""
import os
import pymysql
import pymysql.cursors
from contextlib import contextmanager
from urllib.parse import urlparse


def _parse_database_url(url: str) -> dict:
    """Parse a DATABASE_URL like mysql://user:pass@host:port/dbname into a config dict."""
    parsed = urlparse(url)
    return {
        "host":     parsed.hostname or "127.0.0.1",
        "port":     parsed.port or 3306,
        "user":     parsed.username or "root",
        "password": parsed.password or "",
        "database": (parsed.path or "/mood_wave").lstrip("/"),
    }


def get_connection():
    """Open and return a raw PyMySQL connection.

    Priority:
      1. DATABASE_URL  (set automatically by Railway MySQL plugin)
      2. Individual DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME vars
    """
    database_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if database_url:
        cfg = _parse_database_url(database_url)
    else:
        cfg = {
            "host":     os.getenv("DB_HOST", "127.0.0.1"),
            "port":     int(os.getenv("DB_PORT", 3306)),
            "user":     os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "mood_wave"),
        }

    DB_CONFIG = {
        **cfg,
        "charset":         "utf8mb4",
        "cursorclass":     pymysql.cursors.DictCursor,
        "autocommit":      False,
        "connect_timeout": 10,
    }
    return pymysql.connect(**DB_CONFIG)


@contextmanager
def get_db():
    """
    Context manager — yields a (conn, cursor) tuple.
    Auto-commits on success, rolls back on exception, always closes.

    Usage:
        with get_db() as (conn, cur):
            cur.execute("SELECT * FROM login_user_detail WHERE id = %s", (uid,))
            row = cur.fetchone()
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db():
    """
    Run schema.sql against the database on first startup.
    Call once from app.py before registering blueprints.
    """
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_path):
        print("[db] schema.sql not found — skipping init")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Remove comment lines before splitting
    lines = [line for line in raw.splitlines() if not line.strip().startswith("--")]
    cleaned = "\n".join(lines)

    # Split on semicolons, skip blank statements
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Allow multi-statement: run USE first
                for stmt in statements:
                    if stmt:
                        try:
                            cur.execute(stmt)
                        except Exception as e:
                            # Ignore "already exists" style errors gracefully
                            print(f"[db] stmt warning (ignored): {e}")
            conn.commit()
            print("[db] Schema applied")
        except Exception as e:
            conn.rollback()
            print(f"[db] Schema error: {e}")
        finally:
            conn.close()
    except Exception as e:
        print(f"[db] Could not connect to MySQL: {e}")
        print("[db] ⚠️  Make sure MySQL is running and .env DB credentials are correct.")
