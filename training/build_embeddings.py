"""
build_embeddings.py

Builds embeddings and a FAISS index from knowledge_base.json

Run:
    python build_embeddings.py
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ==========================================================
# Paths
# ==========================================================

KB_FILE = "data/knowledge_base.json"
MODEL_DIR = "../model"

FAISS_INDEX_PATH = os.path.join(MODEL_DIR, "faiss_index.bin")
EMBEDDINGS_PATH = os.path.join(MODEL_DIR, "embeddings.npy")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")

# ==========================================================
# Embedding Model
# ==========================================================

EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"


def build_document(entry):
    """
    Convert one knowledge base entry into a rich searchable document.
    """

    return f"""
Category:
{entry.get("category", "")}

Question:
{entry.get("question", "")}

Alternate Questions:
{' '.join(entry.get("alternate_questions", []))}

Keywords:
{' '.join(entry.get("keywords", []))}

Answer:
{entry.get("answer", "")}

Source:
{entry.get("source_file", "")}
""".strip()


def main():

    if not os.path.exists(KB_FILE):
        print(f"\n❌ Knowledge base not found:\n{KB_FILE}")
        return

    print("\nLoading knowledge base...")

    with open(KB_FILE, "r", encoding="utf-8") as f:
        knowledge_base = json.load(f)

    print(f"✅ Loaded {len(knowledge_base)} entries")

    documents = []

    for entry in knowledge_base:
        documents.append(build_document(entry))

    print("\nLoading embedding model...")
    print(EMBEDDING_MODEL_NAME)

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("\nGenerating embeddings...")

    embeddings = model.encode(
        documents,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    print("✅ Embeddings generated")

    dimension = embeddings.shape[1]

    print(f"Embedding Dimension : {dimension}")

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"FAISS vectors : {index.ntotal}")

    os.makedirs(MODEL_DIR, exist_ok=True)

    faiss.write_index(index, FAISS_INDEX_PATH)
    np.save(EMBEDDINGS_PATH, embeddings)

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)

    print("\n========================================")
    print("✅ Embedding Generation Completed")
    print("========================================")
    print(f"Knowledge Entries : {len(knowledge_base)}")
    print(f"Embedding Size    : {dimension}")
    print(f"FAISS Index       : {FAISS_INDEX_PATH}")
    print(f"Embeddings File   : {EMBEDDINGS_PATH}")
    print(f"Metadata File     : {METADATA_PATH}")
    print("========================================")


if __name__ == "__main__":
    main()