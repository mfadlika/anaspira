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
    source_mode = st.selectbox("Mode input", ["Data contoh", "Unggah CSV atau Excel", "Google Sheets / Form responses"])
    uploaded_file = None
    google_sheet_url = ""
    if source_mode == "Unggah CSV atau Excel":
        uploaded_file = st.file_uploader("Unggah CSV atau Excel", type=["csv", "xlsx", "xls"])
    elif source_mode == "Google Sheets / Form responses":
        google_sheet_url = st.text_input("Tempel URL Google Sheets")
        with st.expander("ℹ️ Panduan Singkat"):
            st.markdown(
                """
                1. Buka spreadsheet jawaban Google Form Anda.
                2. Klik **Bagikan (Share)** di pojok kanan atas.
                3. Ubah Akses Umum menjadi **Siapa saja yang memiliki link (Anyone with the link)**.
                4. Salin URL di browser & tempelkan di atas.
                """
            )
    st.caption("Kolom yang disarankan: tanggal, sumber, nama, teks")
    st.divider()
    top_n = st.slider("Tampilkan prioritas topik", min_value=3, max_value=10, value=5)
    st.caption("Analisis ini memakai pipeline hybrid semantic + leksikon agar tetap ringan, tapi lebih adaptif pada variasi bahasa.")

if source_mode == "Unggah CSV atau Excel":
    if uploaded_file is None:
        st.info("Unggah file untuk memulai analisis.")
        st.stop()
    try:
        raw_frame = load_uploaded_file(uploaded_file)
        data_source = f"File diunggah: {uploaded_file.name}"
    except Exception as exc:
        st.error(f"Gagal membaca file: {exc}")
        st.stop()
elif source_mode == "Google Sheets / Form responses":
    if not google_sheet_url.strip():
        st.info("Masukkan URL Google Sheets di sidebar untuk memulai analisis.")
        
        st.markdown("### 🏘️ Panduan Integrasi Google Form")
        tab_sheets, tab_webhook = st.tabs(["📋 Metode A: Tautan Google Sheets (Paling Mudah)", "⚡ Metode B: Webhook Apps Script (Real-time)"])
        
        with tab_sheets:
            st.markdown(
                """
                #### Sinkronisasi Lewat Google Sheets
                Metode ini membaca data dari Google Sheets tempat Google Form menyimpan jawabannya secara otomatis.
                
                **Langkah-langkah:**
                1. **Buat Google Sheets dari Form**:
                   - Buka Google Form Anda.
                   - Masuk ke tab **Jawaban / Responses**.
                   - Klik tombol hijau **Tautkan ke Sheets / Link to Sheets** di kanan atas untuk membuat spreadsheet baru.
                2. **Ubah Hak Akses Google Sheets**:
                   - Buka spreadsheet tersebut.
                   - Klik tombol **Bagikan / Share** di pojok kanan atas.
                   - Pada bagian *Akses umum*, ubah dari *Dibatasi* menjadi **Siapa saja yang memiliki link (Anyone with the link)**.
                   - Pastikan perannya tetap sebagai **Pelihat (Viewer)**.
                3. **Salin & Tempel Link**:
                   - Salin URL spreadsheet yang ada di address bar browser Anda (misalnya: `https://docs.google.com/spreadsheets/d/xxx/edit#gid=0`).
                   - Tempelkan URL tersebut ke kolom input **Tempel URL Google Sheets** di sidebar sebelah kiri.
                """
            )
            
        with tab_webhook:
            st.markdown(
                """
                #### Sinkronisasi Real-time Menggunakan Webhook (Google Apps Script)
                Metode ini langsung mengirimkan setiap data aspirasi baru yang masuk dari Google Form ke server API secara real-time.
                
                > ⚠️ **Catatan**: Metode ini membutuhkan server API Anda dapat diakses dari internet (misalnya menggunakan port-forwarding atau **ngrok**).
                
                **Langkah-langkah:**
                1. Buka Google Form Anda.
                2. Klik ikon tiga titik di pojok kanan atas, pilih **Editor Skrip / Script Editor**.
                3. Hapus semua kode bawaan, lalu tempel kode JavaScript berikut:
                """
            )
            st.code(
                """function kirimAspirasiKeAPI(e) {
  // Ganti dengan URL backend Anda (misal menggunakan alamat ngrok publik Anda)
  var url = "URL_API_BACKEND_ANDA/ingest/records"; 
  
  var response = e.response;
  var itemResponses = response.getItemResponses();
  var email = response.getRespondentEmail();
  
  var nama = email || "Anonim";
  var teks = "";
  var tanggal = response.getTimestamp().toISOString();
  
  // Mencari nama dan teks aspirasi dari field form secara dinamis
  for (var i = 0; i < itemResponses.length; i++) {
    var title = itemResponses[i].getItem().getTitle().toLowerCase();
    var value = itemResponses[i].getResponse();
    
    if (title.includes("nama")) {
      nama = value;
    } else if (title.includes("aspirasi") || title.includes("keluhan") || title.includes("masukan") || title.includes("pesan") || title.includes("teks")) {
      teks = value;
    }
  }
  
  // Jika kolom spesifik tidak ditemukan, gunakan jawaban pertama sebagai teks aspirasi
  if (!teks && itemResponses.length > 0) {
    teks = itemResponses[0].getResponse();
  }
  
  var payload = {
    "records": [
      {
        "tanggal": tanggal,
        "sumber": "Google Form Webhook",
        "nama": nama,
        "teks": teks
      }
    ],
    "replace_existing": false
  };
  
  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };
  
  try {
    var res = UrlFetchApp.fetch(url, options);
    Logger.log("Response Code: " + res.getResponseCode());
  } catch(err) {
    Logger.log("Error: " + err.toString());
  }
}""",
                language="javascript"
            )
            st.markdown(
                """
                4. Klik ikon disket (**Simpan proyek**).
                5. Klik menu **Pemicu / Triggers** (ikon jam di menu bilah sisi kiri).
                6. Klik tombol **Tambahkan Pemicu / Add Trigger** di kanan bawah.
                7. Konfigurasi pemicu:
                   - Pilih fungsi yang dijalankan: `kirimAspirasiKeAPI`
                   - Pilih sumber acara: **Dari formulir (From form)**
                   - Pilih jenis acara: **Saat mengirim formulir (On form submit)**
                8. Klik **Simpan** dan izinkan otorisasi akun Google Anda jika muncul pop-up.
                """
            )
        st.stop()
    try:
        raw_frame = load_google_sheets_source(google_sheet_url)
        data_source = "Google Sheets / Google Form"
    except Exception as exc:
        st.error(f"Gagal membaca Google Sheets: {exc}")
        st.stop()
else:
    raw_frame = load_sample_data()
    data_source = "Dataset contoh bawaan"

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
