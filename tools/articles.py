#!/usr/bin/env python3
# ============================================================
#  tools/articles.py — article fetcher + RAG pipeline
#  Step 1: fetch_article  (no extra deps)
#  Step 2: embed_article, query_knowledge (needs chromadb)
# ============================================================
# ── sqlite3 version fix for ChromaDB on Ubuntu ───────────────
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import os
import json
import hashlib
import datetime
import requests
from langchain.tools import tool
from config import OUTPUT_DIR, AGENT_DIR

ARTICLES_DIR = os.path.join(AGENT_DIR, "knowledge", "articles")
DB_DIR       = os.path.join(AGENT_DIR, "knowledge", "chromadb")
os.makedirs(ARTICLES_DIR, exist_ok=True)
os.makedirs(DB_DIR,       exist_ok=True)


def _url_to_slug(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _fetch_text(url: str) -> str:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded, include_comments=False,
                                   include_tables=False)
        if text and len(text) > 200:
            return text
    except Exception:
        pass
    try:
        from lxml import etree
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = etree.fromstring(resp.content, etree.HTMLParser())
        for bad in root.xpath("//script|//style|//nav|//footer|//header"):
            bad.getparent().remove(bad)
        return " ".join(root.xpath("//body//text()")).split()[:3000].__str__()
    except Exception as e:
        return f"[fetch failed: {e}]"


@tool
def fetch_article(url: str, save: bool = True) -> str:
    """
    Fetch the full text of a travel/points article from a URL.
    Saves to knowledge/articles/ so it can be embedded later.
    Returns the text so the model can reason over it immediately.

    Args:
        url:  Article URL (from fetch_deals results or any travel blog)
        save: Whether to save to disk for later RAG embedding (default True)
    """
    text = _fetch_text(url)
    if text.startswith("[fetch failed"):
        return text

    words = text.split()
    trimmed = " ".join(words[:4000])
    if len(words) > 4000:
        trimmed += f"\n\n[... truncated at 4000 words, {len(words)} total]"

    if save:
        slug = _url_to_slug(url)
        record = {
            "url":        url,
            "fetched_at": datetime.datetime.now().isoformat(),
            "slug":       slug,
            "word_count": len(words),
            "text":       trimmed,
        }
        path = os.path.join(ARTICLES_DIR, f"{slug}.json")
        with open(path, "w") as f:
            json.dump(record, f, indent=2)

    return f"[Article text — {len(words)} words]\n\n{trimmed}"


@tool
def list_knowledge() -> str:
    """
    List all articles saved in the local knowledge base.
    Shows URL, date fetched, and word count.
    """
    files = sorted(os.listdir(ARTICLES_DIR))
    if not files:
        return "Knowledge base is empty. Use fetch_article to add articles."

    lines = [f"Knowledge base: {len(files)} articles\n"]
    for fname in files:
        path = os.path.join(ARTICLES_DIR, fname)
        try:
            with open(path) as f:
                rec = json.load(f)
            date = rec.get("fetched_at", "?")[:10]
            words = rec.get("word_count", "?")
            url = rec.get("url", "?")
            lines.append(f"  [{date}] {words}w  {url}")
        except Exception:
            lines.append(f"  {fname} (unreadable)")
    return "\n".join(lines)


@tool
def embed_articles(reembed_all: bool = False) -> str:
    """
    Embed all saved articles into a local ChromaDB vector store
    using nomic-embed-text (already pulled on floorBoard).
    Run this after fetch_article to make articles queryable.

    Requires: pip install chromadb
    Requires: ollama pull nomic-embed-text (already done)

    Args:
        reembed_all: Re-embed even articles already in the DB
    """
    try:
        import chromadb
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
    except ImportError:
        return "Run: pip install chromadb"

    emb_fn = OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text",
    )

    client     = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(
        name="nomadex_knowledge",
        embedding_function=emb_fn,
    )

    existing_ids = set(collection.get()["ids"])
    files        = sorted(os.listdir(ARTICLES_DIR))
    embedded     = []
    skipped      = []

    for fname in files:
        path = os.path.join(ARTICLES_DIR, fname)
        try:
            with open(path) as f:
                rec = json.load(f)
        except Exception:
            continue

        slug = rec.get("slug", fname.replace(".json", ""))
        if slug in existing_ids and not reembed_all:
            skipped.append(slug)
            continue

        text  = rec.get("text", "")
        url   = rec.get("url", "")
        date  = rec.get("fetched_at", "")

        words  = text.split()
        chunks = [" ".join(words[i:i+500]) for i in range(0, len(words), 500)]

        for i, chunk in enumerate(chunks):
            chunk_id = f"{slug}_chunk{i}"
            if chunk_id in existing_ids and not reembed_all:
                continue
            collection.upsert(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[{"url": url, "date": date, "chunk": i}],
            )
        embedded.append(url)

    lines = [f"Embedded {len(embedded)} articles into ChromaDB"]
    if skipped:
        lines.append(f"Skipped {len(skipped)} already embedded")
    lines.append(f"DB path: {DB_DIR}")
    return "\n".join(lines)


@tool
def query_knowledge(question: str, n_results: int = 5) -> str:
    """
    Query the local ChromaDB knowledge base for relevant article chunks.
    Use this to answer questions about points, miles, and travel deals
    using your saved article library rather than training data.

    Args:
        question:  Natural language question
        n_results: Number of chunks to retrieve (default 5)
    """
    try:
        import chromadb
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
    except ImportError:
        return "Run: pip install chromadb"

    emb_fn = OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text",
    )

    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        collection = client.get_collection(
            name="nomadex_knowledge",
            embedding_function=emb_fn,
        )
    except Exception:
        return "Knowledge base not yet built. Run embed_articles first."

    results = collection.query(
        query_texts=[question],
        n_results=min(n_results, collection.count()),
    )

    if not results["documents"] or not results["documents"][0]:
        return "No relevant results found in knowledge base."

    lines = [f"Knowledge base results for: '{question}'\n"]
    for i, (doc, meta) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
    )):
        url  = meta.get("url", "?")
        date = meta.get("date", "?")[:10]
        lines.append(f"── Source {i+1} [{date}] {url}")
        lines.append(doc[:600])
        lines.append("")

    return "\n".join(lines)
