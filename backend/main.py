from __future__ import annotations

from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.data_loader import ensure_required_text, load_google_sheets_source, load_sample_data, load_uploaded_file
from src.nlp_pipeline import analyze_records, build_summary, prioritize_policies
from src.storage import clear_records, initialize_database, load_records, save_analyzed_records


class RecordInput(BaseModel):
    tanggal: Optional[str] = None
    sumber: str = Field(default="Tidak Diketahui")
    nama: str = Field(default="Anonim")
    teks: str


class GoogleSheetsInput(BaseModel):
    url: str
    replace_existing: bool = True


class RecordsInput(BaseModel):
    records: List[RecordInput]
    replace_existing: bool = True


app = FastAPI(title="Sistem Analisis Aspirasi Warga API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    initialize_database()


def _analyze_and_store(frame: pd.DataFrame, replace_existing: bool = False) -> dict:
    prepared = ensure_required_text(frame)
    if prepared.empty:
        raise HTTPException(status_code=400, detail="Tidak ada teks valid yang bisa dianalisis.")

    analyzed = analyze_records(prepared)
    saved_count = save_analyzed_records(analyzed, clear_existing=replace_existing)
    return {
        "records": saved_count,
        "summary": build_summary(analyzed),
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest/sample")
def ingest_sample(replace_existing: bool = True) -> dict:
    frame = load_sample_data()
    return _analyze_and_store(frame, replace_existing=replace_existing)


@app.post("/ingest/file")
def ingest_file(file: UploadFile = File(...), replace_existing: bool = True) -> dict:
    frame = load_uploaded_file(file)
    return _analyze_and_store(frame, replace_existing=replace_existing)


@app.post("/ingest/google-sheets")
def ingest_google_sheets(payload: GoogleSheetsInput) -> dict:
    frame = load_google_sheets_source(payload.url)
    return _analyze_and_store(frame, replace_existing=payload.replace_existing)


@app.post("/ingest/records")
def ingest_records(payload: RecordsInput) -> dict:
    frame = pd.DataFrame([item.model_dump() for item in payload.records])
    return _analyze_and_store(frame, replace_existing=payload.replace_existing)


@app.delete("/records")
def delete_records() -> dict:
    clear_records()
    return {"status": "cleared"}


@app.get("/records")
def get_records(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    sumber: Optional[str] = None,
    sentimen: Optional[str] = None,
    topik: Optional[str] = None,
    urgensi: Optional[str] = None,
) -> dict:
    frame = load_records(limit=limit, offset=offset)
    if frame.empty:
        return {"items": [], "total": 0}

    filtered = frame.copy()
    if sumber:
        filtered = filtered[filtered["sumber"] == sumber]
    if sentimen:
        filtered = filtered[filtered["sentimen"] == sentimen]
    if topik:
        filtered = filtered[filtered["topik"] == topik]
    if urgensi:
        filtered = filtered[filtered["urgensi"] == urgensi]

    return {
        "items": filtered.drop(columns=["keywords_json"], errors="ignore").to_dict(orient="records"),
        "total": int(filtered.shape[0]),
    }


@app.get("/summary")
def get_summary() -> dict:
    frame = load_records()
    if frame.empty:
        return build_summary(pd.DataFrame())
    return build_summary(frame)


@app.get("/priorities")
def get_priorities(top_n: int = Query(default=5, ge=1, le=20)) -> dict:
    frame = load_records()
    priorities = prioritize_policies(frame, top_n=top_n)
    return {"items": priorities.to_dict(orient="records")}
