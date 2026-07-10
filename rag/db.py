import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://rag:rag@localhost:5432/rag")

_conn = None


def connect(register=True):
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DATABASE_URL)
        if register:
            register_vector(_conn)
    return _conn


def ensure_schema():
    schema = Path(__file__).resolve().parent.parent / "schema.sql"
    # create extension before registering the vector type with psycopg
    conn = connect(register=False)
    with conn.cursor() as cur:
        cur.execute(schema.read_text())
    conn.commit()
    register_vector(conn)


def execute(sql, params=None):
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        conn.commit()


def fetchall(sql, params=None):
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def executemany(sql, rows):
    conn = connect()
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
        conn.commit()
