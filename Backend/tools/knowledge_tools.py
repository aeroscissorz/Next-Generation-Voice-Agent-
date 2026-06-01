"""
Knowledge Tools Module (RAG)
============================
Implements semantic search over the company knowledge base using
Retrieval-Augmented Generation (RAG) with pgvector.

Architecture:
  1. User asks a policy question (e.g., "what's your refund policy?")
  2. The agent calls search_company_knowledge(query)
  3. This module:
     a) Generates an embedding for the query using OpenAI's text-embedding-3-small
     b) Performs a vector similarity search against the 'company_knowledge' table
        in Supabase (which uses pgvector for cosine similarity)
     c) Falls back to keyword search (ILIKE) if vector search returns no results
  4. Returns the top-k matching knowledge chunks to the agent
  5. The agent synthesizes a natural-language answer from the chunks

Database:
  - Table: company_knowledge (content TEXT, embedding VECTOR(1536), source TEXT)
  - RPC: match_company_knowledge(query_embedding, match_count) — pgvector similarity search
  - Data is ingested via Backend/ingest/ingest_kb.py from raw_policy.txt

Caching:
  - Embedding cache: Avoids re-calling OpenAI for the same query text
  - Search result cache: 5-minute TTL, avoids redundant Supabase queries
  - Both caches are in-memory dicts with FIFO eviction at 200/500 entries

Performance:
  - OpenAI embedding: ~200-400ms (cached after first call)
  - Supabase vector search: ~100-300ms
  - Total: ~300-700ms first call, <50ms on cache hit
"""

from dotenv import load_dotenv
from supabase import create_client
from functools import lru_cache
import hashlib
import time
import httpx
import os

load_dotenv()

# ─── Supabase Client ─────────────────────────────────────────────────────────
# Unlike billing/support tools, this module initializes Supabase eagerly at import
# because it's needed immediately for the vector search RPC.
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Persistent HTTP client for connection reuse (avoids TCP handshake per request)
_http_client = httpx.Client(timeout=10.0)

# ─── Caches ──────────────────────────────────────────────────────────────────
# Embedding cache: query text → embedding vector (1536 floats)
# Avoids redundant OpenAI API calls for repeated/similar queries
_embedding_cache: dict[str, list] = {}

# Search result cache: "query::k" → (timestamp, results)
# Avoids redundant Supabase vector searches within a conversation
_search_cache: dict[str, tuple[float, list]] = {}
SEARCH_CACHE_TTL = 300  # 5 minutes


def get_embedding(text: str) -> list:
    """
    Generate a 1536-dimensional embedding vector for the given text
    using OpenAI's text-embedding-3-small model.

    Results are cached in-memory (keyed by lowercased text) to avoid
    redundant API calls. Cache evicts oldest entry at 500 items.

    Args:
        text: The query text to embed

    Returns:
        List of 1536 floats representing the text embedding
    """
    # Check cache first (case-insensitive)
    cache_key = text.strip().lower()
    if cache_key in _embedding_cache:
        print("⚡ Embedding cache hit")
        return _embedding_cache[cache_key]

    # Call OpenAI Embeddings API
    response = _http_client.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "text-embedding-3-small",
            "input": text
        },
    )
    response.raise_for_status()
    embedding = response.json()["data"][0]["embedding"]

    # Cache the result
    _embedding_cache[cache_key] = embedding
    # Evict oldest if cache gets too large
    if len(_embedding_cache) > 500:
        oldest_key = next(iter(_embedding_cache))
        del _embedding_cache[oldest_key]

    return embedding


def search_company_knowledge(query: str, k: int = 3):
    """
    Search the company knowledge base using semantic similarity.

    This is the main RAG tool called by the agent for policy questions,
    FAQ lookups, and general company information queries.

    Search Strategy:
      1. Generate embedding for the query (OpenAI text-embedding-3-small)
      2. Call Supabase RPC 'match_company_knowledge' for pgvector cosine similarity
      3. If no results: fall back to keyword search (ILIKE on content column)

    Args:
        query: Natural language question (e.g., "what is your refund policy?")
        k: Number of top results to return (default 3)

    Returns:
        List of matching knowledge chunks with content and similarity scores.
        On error, returns a generic fallback response.
    """
    try:
        start = time.time()

        # Check search result cache (keyed by normalized query + k)
        cache_key = f"{query.strip().lower()}::{k}"
        if cache_key in _search_cache:
            cached_time, cached_result = _search_cache[cache_key]
            if time.time() - cached_time < SEARCH_CACHE_TTL:
                print(f"⚡ Search cache hit ({time.time() - start:.3f}s)")
                return cached_result

        # Step 1: Get query embedding (may also be cached in _embedding_cache)
        query_embedding = get_embedding(query)
        embed_time = time.time() - start
        print(f"⏱️ OpenAI embedding took: {embed_time:.2f}s")

        # Step 2: Vector similarity search via Supabase RPC
        # The 'match_company_knowledge' function is a pgvector cosine similarity search
        # defined in Supabase as a PostgreSQL function
        start_search = time.time()
        response = supabase.rpc(
            "match_company_knowledge",
            {
                "query_embedding": query_embedding,
                "match_count": k
            }
        ).execute()
        search_time = time.time() - start_search
        print(f"⏱️ Vector search took: {search_time:.2f}s")

        if response.data:
            # Cache the successful result
            _search_cache[cache_key] = (time.time(), response.data)
            if len(_search_cache) > 200:
                oldest_key = next(iter(_search_cache))
                del _search_cache[oldest_key]
            return response.data

        # Step 3: Fallback to keyword search if vector search found nothing
        # Strips common filler words and does a case-insensitive LIKE search
        keyword = query.lower().replace("policy", "").strip()
        fallback = (
            supabase.table("company_knowledge")
            .select("content")
            .ilike("content", f"%{keyword}%")
            .limit(k)
            .execute()
        )

        result = fallback.data or []
        _search_cache[cache_key] = (time.time(), result)
        return result
    except Exception as e:
        print(f"Error searching knowledge base: {e}")
        # Fallback response so the agent doesn't crash
        return [{
            "content": "Our company offers 24/7 customer support. You can reach us via phone, email, or chat.",
            "similarity": 0.8
        }]
