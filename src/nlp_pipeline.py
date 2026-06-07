from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache
from typing import Iterable

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from .config import NEGATION_WORDS, NEGATIVE_WORDS, POSITIVE_WORDS, STOPWORDS, TOPIC_KEYWORDS, TOPIC_PROFILES, URGENT_WORDS
except ImportError:  # pragma: no cover - allows direct script execution
    from config import NEGATION_WORDS, NEGATIVE_WORDS, POSITIVE_WORDS, STOPWORDS, TOPIC_KEYWORDS, TOPIC_PROFILES, URGENT_WORDS

WORD_PATTERN = re.compile(r"[a-zA-Z\u00C0-\u024F]+")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
NEGATION_PATTERN = re.compile(r"\b(?:" + "|".join(sorted(NEGATION_WORDS)) + r")\b")


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.lower())
    if " " in term:
        return re.compile(rf"(?<!\w){escaped}(?!\w)")
    return re.compile(rf"\b{escaped}\b")


def _count_term_hits(text: str, term: str) -> int:
    return len(_term_pattern(term).findall(text))


@lru_cache(maxsize=128)
def _topic_profile_text(topic: str) -> str:
    keywords = " ".join(TOPIC_KEYWORDS.get(topic, []))
    profile = TOPIC_PROFILES.get(topic, "")
    return preprocess_text(f"{keywords} {profile}")


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        text = ""
    lowered = text.lower()
    lowered = URL_PATTERN.sub(" ", lowered)
    lowered = re.sub(r"[@#]\w+", " ", lowered)
    lowered = re.sub(r"[^a-zA-Z\u00C0-\u024F\s]", " ", lowered)
    tokens = [token for token in WORD_PATTERN.findall(lowered) if token not in STOPWORDS and len(token) > 1]
    return " ".join(tokens)


def classify_topic(text: str) -> tuple[str, float]:
    if not text:
        return "Lainnya", 0.0

    lower_text = text.lower()
    cleaned_text = preprocess_text(text)
    profile_texts = [_topic_profile_text(topic) for topic in TOPIC_PROFILES]
    corpus = [cleaned_text, *profile_texts]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    matrix = vectorizer.fit_transform(corpus)
    semantic_scores = cosine_similarity(matrix[0:1], matrix[1:]).ravel().tolist()

    scores: dict[str, float] = {}
    for index, topic in enumerate(TOPIC_PROFILES):
        keyword_hits = sum(1 for keyword in TOPIC_KEYWORDS.get(topic, []) if keyword in lower_text)
        keyword_score = keyword_hits / max(1, len(TOPIC_KEYWORDS.get(topic, [])))
        scores[topic] = semantic_scores[index] * 0.75 + keyword_score * 0.25

    best_topic = max(scores, key=scores.get, default="Lainnya")
    best_score = scores.get(best_topic, 0.0)

    if best_score == 0:
        return "Lainnya", 0.0
    return best_topic, min(1.0, best_score / 4.0)


def analyze_sentiment(text: str) -> tuple[str, float]:
    if not text:
        return "Netral", 0.0

    lower_text = text.lower()
    score = 0

    for term in POSITIVE_WORDS:
        hits = _count_term_hits(lower_text, term)
        if hits:
            score += hits
            negated_hits = len(re.findall(rf"\b(?:{'|'.join(sorted(NEGATION_WORDS))})\s+{re.escape(term.lower())}\b", lower_text))
            score -= negated_hits * 2

    for term in NEGATIVE_WORDS:
        hits = _count_term_hits(lower_text, term)
        if hits:
            score -= hits
            negated_hits = len(re.findall(rf"\b(?:{'|'.join(sorted(NEGATION_WORDS))})\s+{re.escape(term.lower())}\b", lower_text))
            score += negated_hits * 2

    if score == 0:
        return "Netral", 0.0

    label = "Positif" if score > 0 else "Negatif"
    confidence = min(1.0, abs(score) / 4.0)
    return label, confidence


def extract_keywords(corpus: list[str], top_n: int = 5) -> list[list[str]]:
    cleaned_corpus = [item if isinstance(item, str) else "" for item in corpus]
    if not any(cleaned_corpus):
        return [[] for _ in cleaned_corpus]

    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2), stop_words=list(STOPWORDS))
    matrix = vectorizer.fit_transform(cleaned_corpus)
    feature_names = vectorizer.get_feature_names_out()

    keywords_per_document: list[list[str]] = []
    for row_index in range(matrix.shape[0]):
        row = matrix.getrow(row_index)
        if row.nnz == 0:
            keywords_per_document.append([])
            continue
        row_scores = row.toarray().ravel()
        sorted_indices = row_scores.argsort()[::-1]
        keywords = []
        for index in sorted_indices:
            if row_scores[index] <= 0:
                break
            keyword = feature_names[index]
            if keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) == top_n:
                break
        keywords_per_document.append(keywords)
    return keywords_per_document


def calculate_urgency(text: str, sentiment_label: str) -> tuple[str, float]:
    lower_text = text.lower()
    urgent_hits = sum(_count_term_hits(lower_text, term) for term in URGENT_WORDS)
    negative_bonus = 1.0 if sentiment_label == "Negatif" else 0.0
    score = urgent_hits * 0.7 + negative_bonus * 0.8

    if score >= 1.7:
        return "Tinggi", min(1.0, score / 3.0)
    if score >= 0.8:
        return "Sedang", min(1.0, score / 3.0)
    return "Rendah", min(1.0, score / 3.0)


def analyze_records(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    analyzed = frame.copy()
    analyzed["clean_text"] = analyzed["teks"].fillna("").astype(str).map(preprocess_text)

    topics = analyzed["teks"].fillna("").astype(str).map(classify_topic)
    analyzed["topik"] = [topic for topic, _ in topics]
    analyzed["topik_confidence"] = [confidence for _, confidence in topics]

    sentiments = analyzed["teks"].fillna("").astype(str).map(analyze_sentiment)
    analyzed["sentimen"] = [label for label, _ in sentiments]
    analyzed["sentimen_confidence"] = [confidence for _, confidence in sentiments]

    analyzed["keywords"] = extract_keywords(analyzed["clean_text"].tolist())

    urgency = [calculate_urgency(text, sentiment) for text, sentiment in zip(analyzed["teks"].fillna("").astype(str), analyzed["sentimen"])]
    analyzed["urgensi"] = [label for label, _ in urgency]
    analyzed["urgency_score"] = [score for _, score in urgency]

    analyzed["tanggal"] = pd.to_datetime(analyzed["tanggal"], errors="coerce")
    analyzed["bulan"] = analyzed["tanggal"].dt.to_period("M").astype(str)
    analyzed["ringkasan_kata_kunci"] = analyzed["keywords"].map(lambda items: ", ".join(items) if items else "-")
    return analyzed


def build_summary(analyzed: pd.DataFrame) -> dict:
    if analyzed.empty:
        return {
            "total_masuk": 0,
            "positif": 0,
            "netral": 0,
            "negatif": 0,
            "urgensi_tinggi": 0,
            "topik_utama": "-",
            "kata_kunci_utama": [],
        }

    sentiment_counts = analyzed["sentimen"].value_counts().to_dict()
    urgency_counts = analyzed["urgensi"].value_counts().to_dict()
    topic_counts = analyzed["topik"].value_counts().to_dict()

    keyword_counter = Counter()
    for keywords in analyzed["keywords"]:
        keyword_counter.update(keywords)

    return {
        "total_masuk": int(len(analyzed)),
        "positif": int(sentiment_counts.get("Positif", 0)),
        "netral": int(sentiment_counts.get("Netral", 0)),
        "negatif": int(sentiment_counts.get("Negatif", 0)),
        "urgensi_tinggi": int(urgency_counts.get("Tinggi", 0)),
        "topik_utama": max(topic_counts, key=topic_counts.get, default="-"),
        "kata_kunci_utama": [keyword for keyword, _ in keyword_counter.most_common(10)],
    }


def prioritize_policies(analyzed: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    if analyzed.empty:
        return pd.DataFrame(columns=["topik", "jumlah", "rata_rata_urgensi", "proporsi_negatif", "skor_prioritas"])

    grouped = (
        analyzed.groupby("topik")
        .agg(
            jumlah=("teks", "size"),
            rata_rata_urgensi=("urgency_score", "mean"),
            proporsi_negatif=("sentimen", lambda values: (values == "Negatif").mean()),
        )
        .reset_index()
    )
    grouped["skor_prioritas"] = grouped["jumlah"] * 0.35 + grouped["rata_rata_urgensi"] * 0.45 + grouped["proporsi_negatif"] * 0.2
    return grouped.sort_values("skor_prioritas", ascending=False).head(top_n).reset_index(drop=True)


if __name__ == "__main__":
    from data_loader import load_sample_data

    sample_frame = load_sample_data()
    analyzed_frame = analyze_records(sample_frame)
    summary = build_summary(analyzed_frame)
    print(f"rows={len(analyzed_frame)} topik_utama={summary['topik_utama']} negatif={summary['negatif']}")
