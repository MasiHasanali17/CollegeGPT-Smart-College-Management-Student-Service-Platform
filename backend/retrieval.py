"""
retrieval.py

Production Retrieval Pipeline

Pipeline:
1. Spell Correction
2. Course Abbreviation Expansion
3. BGE Embedding
4. FAISS Search (Top 20)
5. CrossEncoder Re-ranking
6. Hostel Filtering
7. Return Best 5 Results
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import re
import math
from collections import Counter

import faiss
import numpy as np

from spellchecker import SpellChecker

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder,
)

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "model"
)

FAISS_INDEX_PATH = os.path.join(
    MODEL_DIR,
    "faiss_index.bin"
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
    "metadata.json"
)

EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"

RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

FAISS_TOP_K = 30
FINAL_TOP_K = 5

SIMILARITY_THRESHOLD = 0.18
MIN_CONFIDENCE_TO_ANSWER = 0.40

MAX_EDIT_DISTANCE = 3

MIN_ABBREVIATION_LENGTH = 3

DEBUG = True

TIEBREAK_BOOST_WORDS = [
    "gym",
    "fee",
    "fees",
    "hostel",
    "hostels",
    "admission",
    "admissions",
    "library",
    "canteen",
    "bus",
    "wifi",
    "mess",
    "faculty",
    "campus",
    "course",
    "courses",
    "placement",
    "placements",
    "scholarship",
    "scholarships",
    "exam",
    "exams",
]

TIEBREAK_BOOST_AMOUNT = 1000

# ---------------------------------------------------------
# LOAD MODELS
# ---------------------------------------------------------

print("[Retrieval] Loading BGE Embedder...")

_embedder = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)

print("[Retrieval] Loading CrossEncoder...")

_reranker = CrossEncoder(
    RERANK_MODEL_NAME
)

print("[Retrieval] Loading FAISS...")

_index = faiss.read_index(
    FAISS_INDEX_PATH
)

print("[Retrieval] Loading Metadata...")

with open(
    METADATA_PATH,
    "r",
    encoding="utf-8"
) as f:

    _metadata = json.load(f)

print(
    f"[Retrieval] Ready ({_index.ntotal} vectors)"
)

# ---------------------------------------------------------
# BUILD HOSTEL NAMES
# ---------------------------------------------------------

def _build_known_hostel_names():

    names = set()

    for entry in _metadata:

        if entry.get("category") != "hostel and residential life":
            continue

        match = re.search(
            r"for (.+?) under",
            entry["question"]
        )

        if not match:
            continue

        hostel = (
            match.group(1)
            .replace("*", "")
            .strip()
        )

        hostel = hostel.split(" - ")[0].strip().lower()

        if hostel:
            names.add(hostel)

    return names


_known_hostel_names = _build_known_hostel_names()

# Sorted (longest name first) for deterministic matching order.
# Using the raw set directly would make iteration order depend on
# Python's string hash seed, which can change the filtering result
# for ambiguous queries between runs.
_known_hostel_names_sorted = sorted(
    _known_hostel_names,
    key=len,
    reverse=True
)

print(
    f"[Retrieval] Hostels Loaded : {len(_known_hostel_names)}"
)

# ---------------------------------------------------------
# COURSE ABBREVIATIONS
# ---------------------------------------------------------

def _build_course_abbreviation_map():

    mapping = {}

    for entry in _metadata:

        if entry.get("category") != "faculties":
            continue

        question = entry["question"]

        course = None

        m = re.search(
            r"courses - (.+?) - specializations",
            question
        )

        if m:
            course = m.group(1).strip()

        else:

            m = re.search(
                r"for (.+?) under .+? - courses\?",
                question
            )

            if m:
                course = m.group(1).strip()

        if not course:
            continue

        if " " in course:
            continue

        key = re.sub(
            r"[^a-zA-Z0-9]",
            "",
            course
        ).lower()

        if (
            len(key) >= MIN_ABBREVIATION_LENGTH
            and key not in mapping
        ):
            mapping[key] = course

    return mapping


_course_abbreviation_map = (
    _build_course_abbreviation_map()
)

print(
    f"[Retrieval] Course Map : {len(_course_abbreviation_map)}"
)

# ---------------------------------------------------------
# COURSE ABBREVIATION EXPANSION
# ---------------------------------------------------------

def expand_course_abbreviations(text: str):

    words = text.split()

    expanded = []

    for word in words:

        key = re.sub(
            r"[^a-zA-Z0-9]",
            "",
            word
        ).lower()

        if (
            len(key) >= MIN_ABBREVIATION_LENGTH
            and key in _course_abbreviation_map
        ):
            expanded.append(
                _course_abbreviation_map[key]
            )
        else:
            expanded.append(word)

    return " ".join(expanded)


# ---------------------------------------------------------
# SPELL CHECKER
# ---------------------------------------------------------

_spell = SpellChecker()


def _build_domain_vocabulary():

    counts = Counter()

    for entry in _metadata:

        text = (
            entry["question"]
            + " "
            + entry["answer"]
        )

        spaced = re.sub(
            r"[^a-zA-Z\s]",
            " ",
            text
        )

        for word in spaced.split():

            word = word.lower()

            if len(word) > 2:
                counts[word] += 1

        for token in text.split():

            squashed = re.sub(
                r"[^a-zA-Z]",
                "",
                token
            ).lower()

            if len(squashed) > 2:
                counts[squashed] += 1

    for word in TIEBREAK_BOOST_WORDS:
        counts[word] += TIEBREAK_BOOST_AMOUNT

    return counts


_domain_vocab_counts = _build_domain_vocabulary()

_domain_vocab = set(
    _domain_vocab_counts.keys()
)

print(
    f"[Retrieval] Domain Vocabulary : {len(_domain_vocab)}"
)


# ---------------------------------------------------------
# LEVENSHTEIN DISTANCE
# ---------------------------------------------------------

def _levenshtein(a: str, b: str):

    if a == b:
        return 0

    la = len(a)
    lb = len(b)

    if la == 0:
        return lb

    if lb == 0:
        return la

    previous = list(range(lb + 1))

    for i, ca in enumerate(a, start=1):

        current = [i] + [0] * lb

        for j, cb in enumerate(b, start=1):

            cost = 0 if ca == cb else 1

            current[j] = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + cost,
            )

        previous = current

    return previous[lb]


# ---------------------------------------------------------
# DOMAIN SPELL MATCH
# ---------------------------------------------------------

def _find_best_domain_match(
    word,
    max_distance=MAX_EDIT_DISTANCE
):

    best_word = None
    best_distance = max_distance + 1
    best_frequency = -1

    for candidate in _domain_vocab:

        if abs(len(candidate) - len(word)) > max_distance:
            continue

        distance = _levenshtein(
            word,
            candidate
        )

        if distance > max_distance:
            continue

        frequency = _domain_vocab_counts[candidate]

        if (
            distance < best_distance
            or (
                distance == best_distance
                and frequency > best_frequency
            )
        ):
            best_distance = distance
            best_frequency = frequency
            best_word = candidate

    return (
        best_word
        if best_distance <= max_distance
        else None
    )


# ---------------------------------------------------------
# SPELL CORRECTION
# ---------------------------------------------------------

def correct_spelling(text: str):

    corrected = []

    for word in text.split():

        clean = word.strip(".,?!")

        if (
            not clean
            or not clean.isalpha()
        ):
            corrected.append(word)
            continue

        lower = clean.lower()

        if (
            lower in _domain_vocab
            or lower not in _spell.unknown([lower])
        ):
            corrected.append(word)
            continue

        domain = _find_best_domain_match(lower)

        if domain:
            corrected.append(domain)
            continue

        suggestion = _spell.correction(lower)

        corrected.append(
            suggestion if suggestion else word
        )

    return " ".join(corrected)


# ---------------------------------------------------------
# HOSTEL FILTER
# ---------------------------------------------------------

def filter_hostel_results(
    query: str,
    candidates: list
):

    query = query.lower()

    for hostel in _known_hostel_names_sorted:

        words = [
            w for w in hostel.split()
            if len(w) > 2
        ]

        if words and all(
            w in query for w in words
        ):

            filtered = []

            for item in candidates:

                text = (
                    item["question"]
                    + " "
                    + item["answer"]
                ).lower()

                if hostel in text:
                    filtered.append(item)

            if filtered:
                return filtered

            break

    return candidates


# ---------------------------------------------------------
# QUERY PREPROCESS
# ---------------------------------------------------------

def preprocess_query(query: str):

    corrected = correct_spelling(query)

    expanded = expand_course_abbreviations(
        corrected
    )

    if DEBUG and expanded != query:
        print(
            f"[DEBUG] '{query}' -> '{expanded}'"
        )

    return expanded


# ---------------------------------------------------------
# QUERY EMBEDDING
# ---------------------------------------------------------

def embed_query(query: str):

    vector = _embedder.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    return vector.astype("float32")


# ---------------------------------------------------------
# RERANKING (moved above `retrieve` — it must be defined
# before `retrieve()` calls it)
# ---------------------------------------------------------

def build_rerank_text(item):
    """
    Creates a richer document for the CrossEncoder.
    This gives better reranking than using only
    question + answer.
    """

    parts = []

    if item.get("category"):
        parts.append(f"Category: {item['category']}")

    if item.get("question"):
        parts.append(f"Question: {item['question']}")

    if item.get("answer"):
        parts.append(f"Answer: {item['answer']}")

    return "\n".join(parts)


def rerank_results(query: str, candidates: list):

    if not candidates:
        return []

    sentence_pairs = []

    for item in candidates:

        sentence_pairs.append(
            (
                query,
                build_rerank_text(item)
            )
        )

    scores = _reranker.predict(
        sentence_pairs,
        show_progress_bar=False
    )

    for item, score in zip(candidates, scores):

        item["rerank_score"] = float(score)

    candidates.sort(
        key=lambda x: (
            x["rerank_score"],
            x["similarity"]
        ),
        reverse=True
    )

    return candidates[:FINAL_TOP_K]


# ---------------------------------------------------------
# RETRIEVAL
# ---------------------------------------------------------

def retrieve(
    query: str,
    top_k: int = FINAL_TOP_K
):
    """
    Production Retrieval Pipeline

    Query
        ↓
    Spell Correction
        ↓
    Course Expansion
        ↓
    BGE Embedding
        ↓
    FAISS Top-20
        ↓
    Similarity Filter
        ↓
    Hostel Filter
        ↓
    CrossEncoder Rerank
        ↓
    Best 5
    """

    if not query or not query.strip():
        return []

    # -------------------------------------
    # Query preprocessing
    # -------------------------------------

    processed_query = preprocess_query(query)

    # -------------------------------------
    # Query embedding
    # -------------------------------------

    query_vector = embed_query(processed_query)

    # -------------------------------------
    # FAISS Search
    # -------------------------------------

    scores, indexes = _index.search(
        query_vector,
        FAISS_TOP_K
    )

    candidates = []

    for score, idx in zip(scores[0], indexes[0]):

        if idx == -1:
            continue

        if score < SIMILARITY_THRESHOLD:
            continue

        entry = _metadata[idx]

        candidates.append({

            "question": entry["question"],

            "answer": entry["answer"],

            "category": entry.get(
                "category",
                "General"
            ),

            "similarity": float(score)

        })

    if not candidates:
        return []

    # -------------------------------------
    # Hostel specific filtering
    # -------------------------------------

    candidates = filter_hostel_results(
        processed_query,
        candidates
    )

    # -------------------------------------
    # Cross Encoder Reranking
    # -------------------------------------

    candidates = rerank_results(
        processed_query,
        candidates
    )

    return candidates[:top_k]


# ---------------------------------------------------------
# CONFIDENCE CHECK
# ---------------------------------------------------------

def has_confident_match(results):
    """
    Returns True if retrieval found a usable answer.

    The CrossEncoder returns an unbounded logit, not a
    0-1 confidence score, so it's squashed through a
    sigmoid before being compared against the configured
    MIN_CONFIDENCE_TO_ANSWER threshold. (Previously this
    function ignored MIN_CONFIDENCE_TO_ANSWER entirely and
    just checked `rerank_score > 0`, which accepted almost
    any weakly-positive match.)
    """

    if not results:
        return False

    raw_score = results[0].get("rerank_score", None)

    if raw_score is None:
        return False

    confidence = 1 / (1 + math.exp(-raw_score))

    return confidence >= MIN_CONFIDENCE_TO_ANSWER


# ---------------------------------------------------------
# STARTUP BANNER
# ---------------------------------------------------------

print("\n======================================")
print(" Retrieval Pipeline Ready")
print("======================================")
print(f"Embedding Model : {EMBEDDING_MODEL_NAME}")
print(f"CrossEncoder    : {RERANK_MODEL_NAME}")
print(f"FAISS Vectors   : {_index.ntotal}")
print(f"Retrieve Top    : {FAISS_TOP_K}")
print(f"Return Top      : {FINAL_TOP_K}")
print("======================================\n")


# ---------------------------------------------------------
# DEBUG / MANUAL TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    while True:

        query = input("\nAsk something (or 'exit'): ")

        if query.lower() == "exit":
            break

        results = retrieve(query)

        if not has_confident_match(results):
            print("\nNo confident match found.")
            continue

        print("\nTop Results\n")

        for i, item in enumerate(results, start=1):

            print("-" * 80)

            print(f"Rank        : {i}")

            print(
                f"Similarity  : "
                f"{item['similarity']:.4f}"
            )

            if "rerank_score" in item:
                print(
                    f"Rerank Score: "
                    f"{item['rerank_score']:.4f}"
                )

            print(
                f"Category    : "
                f"{item['category']}"
            )

            print(
                f"Question    : "
                f"{item['question']}"
            )

            print(
                f"Answer      : "
                f"{item['answer']}"
            )

        print("-" * 80)