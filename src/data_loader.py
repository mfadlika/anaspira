from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import Iterable

import pandas as pd

REQUIRED_COLUMNS = ["tanggal", "sumber", "nama", "teks"]
COLUMN_ALIASES = {
    "timestamp": "tanggal",
    "date": "tanggal",
    "waktu": "tanggal",
    "asal": "sumber",
    "channel": "sumber",
    "platform": "sumber",
    "pengirim": "nama",
    "nama_warga": "nama",
    "nama_lengkap": "nama",
    "nama_anda": "nama",
    "warga": "nama",
    "isi": "teks",
    "keluhan": "teks",
    "aspirasi": "teks",
    "masukan": "teks",
    "pesan": "teks",
    "uraian": "teks",
    "deskripsi": "teks",
    "isi_laporan": "teks",
}


def _normalize_column_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: COLUMN_ALIASES.get(_normalize_column_name(column), _normalize_column_name(column)) for column in frame.columns}
    frame = frame.rename(columns=renamed)

    if "tanggal" not in frame.columns:
        frame["tanggal"] = pd.Timestamp.today().normalize()
    if "sumber" not in frame.columns:
        frame["sumber"] = "Tidak Diketahui"
    if "nama" not in frame.columns:
        frame["nama"] = "Anonim"

    text_column = None
    for candidate in ["teks", "isi", "aspirasi", "keluhan", "masukan", "pesan", "uraian"]:
        if candidate in frame.columns:
            text_column = candidate
            break

    if text_column is None:
        object_columns = [column for column in frame.columns if frame[column].dtype == "object"]
        if object_columns:
            text_column = object_columns[0]
            frame = frame.rename(columns={text_column: "teks"})
        else:
            frame["teks"] = ""
    elif text_column != "teks":
        frame = frame.rename(columns={text_column: "teks"})

    frame["tanggal"] = pd.to_datetime(frame["tanggal"], errors="coerce").fillna(pd.Timestamp.today().normalize())
    frame["sumber"] = frame["sumber"].fillna("Tidak Diketahui").astype(str)
    frame["nama"] = frame["nama"].fillna("Anonim").astype(str)
    frame["teks"] = frame["teks"].fillna("").astype(str)

    return frame[[column for column in REQUIRED_COLUMNS if column in frame.columns] + [column for column in frame.columns if column not in REQUIRED_COLUMNS]]


def load_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(uploaded_file)
    else:
        frame = pd.read_csv(uploaded_file)
    return normalize_columns(frame)


def resolve_google_sheets_csv_url(source_url: str) -> str:
    cleaned_source = source_url.strip()
    if "export?format=csv" in cleaned_source:
        return cleaned_source

    parsed = urlparse(cleaned_source)
    if "docs.google.com" not in parsed.netloc:
        return cleaned_source

    match = None
    parts = parsed.path.split("/")
    if "d" in parts:
        try:
            sheet_id = parts[parts.index("d") + 1]
            match = sheet_id
        except (ValueError, IndexError):
            match = None

    if match is None:
        return cleaned_source

    query = parse_qs(parsed.query)
    gid = query.get("gid", ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{match}/export?format=csv&gid={gid}"


def load_google_sheets_source(source_url: str) -> pd.DataFrame:
    csv_url = resolve_google_sheets_csv_url(source_url)
    frame = pd.read_csv(csv_url)
    return normalize_columns(frame)


def load_sample_data() -> pd.DataFrame:
    sample_path = Path(__file__).resolve().parents[1] / "data" / "sample_aspirasi.csv"
    frame = pd.read_csv(sample_path)
    return normalize_columns(frame)


def ensure_required_text(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_columns(frame.copy())
    normalized = normalized[normalized["teks"].str.strip() != ""].reset_index(drop=True)
    return normalized
