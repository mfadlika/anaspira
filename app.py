from __future__ import annotations

from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import ensure_required_text, load_google_sheets_source, load_sample_data, load_uploaded_file
from src.nlp_pipeline import analyze_records, build_summary, prioritize_policies

st.set_page_config(
    page_title="Sistem Analisis Aspirasi Warga",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f4f7fb 0%, #ffffff 45%, #eef4ff 100%);
        }
        .hero {
            padding: 1.5rem 1.75rem;
            border-radius: 24px;
            background: linear-gradient(135deg, #12355b 0%, #1d6f73 100%);
            color: white;
            box-shadow: 0 20px 40px rgba(18, 53, 91, 0.18);
            margin-bottom: 1.5rem;
        }
        .hero h1 {
            margin-bottom: 0.4rem;
            font-size: 2.1rem;
        }
        .hero p {
            margin: 0;
            opacity: 0.9;
            max-width: 850px;
            line-height: 1.5;
        }
        .metric-card {
            background: white;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 22px rgba(12, 35, 64, 0.08);
            border: 1px solid rgba(18, 53, 91, 0.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>Sistem Analisis Aspirasi Warga</h1>
        <p>
            Platform NLP untuk mengolah aspirasi, keluhan, dan masukan warga dari Google Form,
            formulir digital, atau media sosial menjadi informasi terstruktur yang membantu desa
            memahami sentimen, mengidentifikasi masalah utama, dan memprioritaskan kebijakan lebih cepat.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Sumber Data")
    google_sheet_url = st.text_input(
        "Tautan Google Sheets (Form Responses)",
        value="https://docs.google.com/spreadsheets/d/1qgIr5xDX5fCura7aqYI6plDzEft174fpOkQDmi4N9GI/edit?resourcekey=&gid=2117530252#gid=2117530252"
    )
    st.caption("Kolom yang disarankan di Google Form: Nama Lengkap, Aspirasi/Keluhan")
    st.divider()
    top_n = st.slider("Tampilkan prioritas topik", min_value=3, max_value=10, value=5)
    st.caption("Analisis ini memakai pipeline hybrid semantic + leksikon agar tetap ringan, tapi lebih adaptif pada variasi bahasa.")

if not google_sheet_url.strip():
    st.info("Masukkan URL Google Sheets di sidebar untuk memulai analisis.")
    st.stop()

try:
    raw_frame = load_google_sheets_source(google_sheet_url)
    data_source = "Google Sheets / Google Form"
except Exception as exc:
    st.error(f"Gagal membaca Google Sheets: {exc}")
    st.stop()

raw_frame = ensure_required_text(raw_frame)
if raw_frame.empty:
    st.warning("Tidak ada teks yang bisa dianalisis dari sumber data yang dipilih.")
    st.stop()

analyzed = analyze_records(raw_frame)
summary = build_summary(analyzed)
priorities = prioritize_policies(analyzed, top_n=top_n)

st.caption(data_source)

metric_columns = st.columns(5)
metric_items = [
    ("Total Aspirasi", summary["total_masuk"]),
    ("Negatif", summary["negatif"]),
    ("Netral", summary["netral"]),
    ("Positif", summary["positif"]),
    ("Urgensi Tinggi", summary["urgensi_tinggi"]),
]
for column, (label, value) in zip(metric_columns, metric_items):
    with column:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="font-size: 0.85rem; color: #5b6b7f;">{label}</div>
                <div style="font-size: 2rem; font-weight: 700; color: #12355b;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

left_column, right_column = st.columns((1.2, 1))
with left_column:
    st.subheader("Tren Sentimen")
    sentiment_counts = analyzed["sentimen"].value_counts().reset_index()
    sentiment_counts.columns = ["sentimen", "jumlah"]
    fig_sentiment = px.bar(
        sentiment_counts,
        x="sentimen",
        y="jumlah",
        color="sentimen",
        color_discrete_map={"Positif": "#2f9e44", "Netral": "#6c757d", "Negatif": "#e03131"},
        text="jumlah",
    )
    fig_sentiment.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), height=340)
    st.plotly_chart(fig_sentiment, use_container_width=True)

with right_column:
    st.subheader("Distribusi Topik")
    topic_counts = analyzed["topik"].value_counts().reset_index()
    topic_counts.columns = ["topik", "jumlah"]
    fig_topic = px.pie(topic_counts, names="topik", values="jumlah", hole=0.45)
    fig_topic.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
    st.plotly_chart(fig_topic, use_container_width=True)

priority_column, keyword_column = st.columns((1.15, 0.85))
with priority_column:
    st.subheader("Prioritas Kebijakan")
    if priorities.empty:
        st.info("Belum ada topik yang cukup kuat untuk diprioritaskan.")
    else:
        st.dataframe(
            priorities.rename(
                columns={
                    "topik": "Topik",
                    "jumlah": "Jumlah Aduan",
                    "rata_rata_urgensi": "Rata-rata Urgensi",
                    "proporsi_negatif": "Proporsi Negatif",
                    "skor_prioritas": "Skor Prioritas",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

with keyword_column:
    st.subheader("Kata Kunci Dominan")
    keyword_list = summary["kata_kunci_utama"][:10]
    if keyword_list:
        st.write(", ".join(keyword_list))
    else:
        st.write("-")
    st.subheader("Topik Utama")
    st.write(summary["topik_utama"])

st.subheader("Detail Aspirasi")
filter_columns = st.columns(4)
selected_source = filter_columns[0].selectbox("Sumber", options=["Semua"] + sorted(analyzed["sumber"].dropna().unique().tolist()))
selected_sentiment = filter_columns[1].selectbox("Sentimen", options=["Semua", "Positif", "Netral", "Negatif"])
selected_topic = filter_columns[2].selectbox("Topik", options=["Semua"] + sorted(analyzed["topik"].dropna().unique().tolist()))
selected_urgency = filter_columns[3].selectbox("Urgensi", options=["Semua", "Tinggi", "Sedang", "Rendah"])

filtered = analyzed.copy()
if selected_source != "Semua":
    filtered = filtered[filtered["sumber"] == selected_source]
if selected_sentiment != "Semua":
    filtered = filtered[filtered["sentimen"] == selected_sentiment]
if selected_topic != "Semua":
    filtered = filtered[filtered["topik"] == selected_topic]
if selected_urgency != "Semua":
    filtered = filtered[filtered["urgensi"] == selected_urgency]

st.dataframe(
    filtered[
        [
            "tanggal",
            "sumber",
            "nama",
            "teks",
            "topik",
            "sentimen",
            "urgensi",
            "ringkasan_kata_kunci",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

csv_buffer = StringIO()
filtered.to_csv(csv_buffer, index=False)
st.download_button(
    "Unduh hasil analisis CSV",
    data=csv_buffer.getvalue().encode("utf-8"),
    file_name="hasil_analisis_aspirasi.csv",
    mime="text/csv",
)
