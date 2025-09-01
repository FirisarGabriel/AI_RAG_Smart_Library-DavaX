
"""
RAG utilities for Smart Library (Chroma + OpenAI embeddings).

What this module does:
- Loads local books from data/book_summaries.json
- Builds embeddings with OpenAI (text-embedding-3-small)
- Persists a Chroma collection on disk
- Provides `retrieve(query, k)` to fetch the most relevant books

"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any, Dict, List, Tuple

from openai import OpenAI
import chromadb

# -----------------------------
# Config & singletons
# -----------------------------

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]  
DATA_DIR = pathlib.Path(__file__).parent / "data"
BOOKS_JSON = DATA_DIR / "book_summaries.json"
CHROMA_DIR = pathlib.Path(os.getenv("CHROMA_DIR", str(DATA_DIR / "vector_store")))
COLLECTION_NAME = "books"

CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_openai_client: OpenAI | None = None
_chroma_client: chromadb.PersistentClient | None = None
_collection: chromadb.api.models.Collection.Collection | None = None


def get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI() 
    return _openai_client


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _chroma_client


def get_collection() -> chromadb.api.models.Collection.Collection:
    """
    Get or create the persistent 'books' collection.
    We DO NOT register an embedding function with Chroma because
    we compute embeddings ourselves with OpenAI (so we can also use them elsewhere).
    """
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  
        )
    return _collection


# -----------------------------
# Data loading & preprocessing
# -----------------------------

def _load_books() -> List[Dict[str, Any]]:
    """
    Expected JSON structure per item (flexible, but recommended):
    {
      "title": "The Hobbit",
      "authors": ["J.R.R. Tolkien"],
      "tags": ["fantasy", "friendship", "adventure"],
      "summary": "..."
    }
    """
    if not BOOKS_JSON.exists():
        raise FileNotFoundError(f"books file not found: {BOOKS_JSON}")
    with open(BOOKS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("book_summaries.json must contain a list of books")
    return data


def _slugify(title: str) -> str:
    return (
        "".join(ch if ch.isalnum() else "-" for ch in title.lower())
        .strip("-")
        .replace("--", "-")
    )


def _compose_document(book: Dict[str, Any]) -> str:
    """
    Keep a compact but information-rich string for embedding.
    """
    title = str(book.get("title", "")).strip()
    authors = ", ".join(book.get("authors", []) or [])
    tags = ", ".join(book.get("tags", []) or [])
    summary = str(book.get("summary", "")).strip()
    parts = [
        f"Title: {title}",
        f"Authors: {authors}" if authors else "",
        f"Tags: {tags}" if tags else "",
        f"Summary: {summary}",
    ]
    return "\n".join(p for p in parts if p)


# -----------------------------
# Embeddings
# -----------------------------

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Uses OpenAI embeddings API (batched by API).
    Returns list of float vectors in the same order as `texts`.
    """
    if not texts:
        return []
    client = get_openai()
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in resp.data]  


# -----------------------------
# Indexing
# -----------------------------

def index_books(force: bool = False) -> Tuple[int, int]:
    """
    Build / refresh the Chroma index from local JSON.
    Returns (added, skipped).
    If force=True, re-adds all docs (dedup by id first).
    """
    books = _load_books()
    col = get_collection()

    existing_count = col.count() or 0
    if existing_count and not force:
        return (0, int(existing_count))

    if force and existing_count:
        col.delete(ids=col.get()["ids"]) 

    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict[str, Any]] = []

    for book in books:
        title = str(book.get("title", "")).strip()
        if not title:
            continue
        bid = _slugify(title)
        ids.append(bid)
        docs.append(_compose_document(book))
        metas.append(
            {
                "title": title,
                "authors": ", ".join(book.get("authors", [])), 
                "tags": ", ".join(book.get("tags", [])),  
                "summary": book.get("summary", ""),
            }
        )

    BATCH = 64
    added = 0
    for i in range(0, len(docs), BATCH):
        batch_ids = ids[i : i + BATCH]
        batch_docs = docs[i : i + BATCH]
        batch_meta = metas[i : i + BATCH]
        vectors = embed_texts(batch_docs)
        col.add(ids=batch_ids, documents=batch_docs, embeddings=vectors, metadatas=batch_meta)
        added += len(batch_ids)

    return (added, len(docs) - added)


# -----------------------------
# Retrieval
# -----------------------------

def retrieve(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """
    Returns top-k matches as a list of dicts:
    [
      {
        "title": "...",
        "summary": "...",
        "authors": [...],
        "tags": [...],
        "distance": 0.12,   # cosine distance (lower is better)
        "document": "raw embedded text"
      },
      ...
    ]
    """
    query = (query or "").strip()
    if not query:
        return []

    col = get_collection()

    q_emb = embed_texts([query])[0]
    res = col.query(query_embeddings=[q_emb], n_results=max(1, k))

    out: List[Dict[str, Any]] = []
    ids = res.get("ids", [[]])[0]
    dists = res.get("distances", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]

    for i in range(len(ids)):
        meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
        out.append(
            {
                "title": meta.get("title"),
                "summary": meta.get("summary"),
                "authors": meta.get("authors", []),
                "tags": meta.get("tags", []),
                "distance": dists[i] if i < len(dists) else None,
                "document": docs[i] if i < len(docs) else None,
                "id": ids[i],
            }
        )
    return out


# -----------------------------
# Convenience init on import 
# -----------------------------

def init_store(force: bool = False) -> Tuple[int, int]:
    """
    Ensure the store exists and is populated.
    Call this once at app startup (e.g., in FastAPI lifespan event).
    """
    get_collection() 
    return index_books(force=force)

