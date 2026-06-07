from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

DATABASE_FILENAME = "aspirations.db"


def get_database_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / DATABASE_FILENAME


def initialize_database() -> Path:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aspirations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal TEXT NOT NULL,
                sumber TEXT NOT NULL,
                nama TEXT NOT NULL,
                teks TEXT NOT NULL,
                clean_text TEXT,
                topik TEXT,
                topik_confidence REAL,
                sentimen TEXT,
                sentimen_confidence REAL,
                urgensi TEXT,
                urgency_score REAL,
                keywords_json TEXT,
                bulan TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    return database_path


def clear_records() -> None:
    database_path = initialize_database()
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM aspirations")
        connection.commit()


def save_analyzed_records(frame: pd.DataFrame, clear_existing: bool = False) -> int:
    if clear_existing:
        clear_records()

    if frame.empty:
        return 0

    database_path = initialize_database()
    columns = [
        "tanggal",
        "sumber",
        "nama",
        "teks",
        "clean_text",
        "topik",
        "topik_confidence",
        "sentimen",
        "sentimen_confidence",
        "urgensi",
        "urgency_score",
        "keywords_json",
        "bulan",
    ]

    records = []
    for _, row in frame.iterrows():
        keywords = row.get("keywords", [])
        records.append(
            (
                pd.to_datetime(row.get("tanggal"), errors="coerce").isoformat() if pd.notna(row.get("tanggal")) else pd.Timestamp.today().isoformat(),
                str(row.get("sumber", "Tidak Diketahui")),
                str(row.get("nama", "Anonim")),
                str(row.get("teks", "")),
                str(row.get("clean_text", "")),
                str(row.get("topik", "Lainnya")),
                float(row.get("topik_confidence", 0.0) or 0.0),
                str(row.get("sentimen", "Netral")),
                float(row.get("sentimen_confidence", 0.0) or 0.0),
                str(row.get("urgensi", "Rendah")),
                float(row.get("urgency_score", 0.0) or 0.0),
                json.dumps(keywords, ensure_ascii=False),
                str(row.get("bulan", "")),
            )
        )

    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            f"""
            INSERT INTO aspirations ({', '.join(columns)})
            VALUES ({', '.join(['?'] * len(columns))})
            """,
            records,
        )
        connection.commit()

    return len(records)


def load_records(limit: int | None = None, offset: int = 0) -> pd.DataFrame:
    database_path = initialize_database()
    query = "SELECT * FROM aspirations ORDER BY tanggal DESC, id DESC"
    params: list[object] = []
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    with sqlite3.connect(database_path) as connection:
        frame = pd.read_sql_query(query, connection, params=params)

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "tanggal",
                "sumber",
                "nama",
                "teks",
                "clean_text",
                "topik",
                "topik_confidence",
                "sentimen",
                "sentimen_confidence",
                "urgensi",
                "urgency_score",
                "keywords",
                "bulan",
                "created_at",
                "ringkasan_kata_kunci",
            ]
        )

    frame["tanggal"] = pd.to_datetime(frame["tanggal"], errors="coerce")
    frame["keywords"] = frame["keywords_json"].fillna("[]").map(json.loads)
    frame["ringkasan_kata_kunci"] = frame["keywords"].map(lambda items: ", ".join(items) if items else "-")
    return frame