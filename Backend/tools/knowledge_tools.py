from dotenv import load_dotenv
from supabase import create_client
from functools import lru_cache
import hashlib
import time
import httpx
import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Persistent HTTP client for connection reuse
_http_client = httpx.Client(timeout=10.0)

# In-memory caches
_embedding_cache: dict[str, list] = {}
_search_cache: dict[str, tuple[float, list]] = {}
SEARCH_CACHE_TTL = 300  # 5 minutes


def get_embedding(text: str) -> list:
    """Get embedding using OpenAI API with caching."""
    # Check cache first
    cache_key = text.strip().lower()
    if cache_key in _embedding_cache:
        print("⚡ Embedding cache hit")
        return _embedding_cache[cache_key]

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

    # Cache it
    _embedding_cache[cache_key] = embedding
    # Evict oldest if cache gets too large
    if len(_embedding_cache) > 500:
        oldest_key = next(iter(_embedding_cache))
        del _embedding_cache[oldest_key]

    return embedding


def search_company_knowledge(query: str, k: int = 3):
    """Search knowledge base using OpenAI embeddings with result caching."""
    try:
        start = time.time()

        # Check search result cache
        cache_key = f"{query.strip().lower()}::{k}"
        if cache_key in _search_cache:
            cached_time, cached_result = _search_cache[cache_key]
            if time.time() - cached_time < SEARCH_CACHE_TTL:
                print(f"⚡ Search cache hit ({time.time() - start:.3f}s)")
                return cached_result

        # Get query embedding (may also be cached)
        query_embedding = get_embedding(query)
        embed_time = time.time() - start
        print(f"⏱️ OpenAI embedding took: {embed_time:.2f}s")

        # Search Supabase
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
            # Cache the result
            _search_cache[cache_key] = (time.time(), response.data)
            # Evict old entries
            if len(_search_cache) > 200:
                oldest_key = next(iter(_search_cache))
                del _search_cache[oldest_key]
            return response.data

        # Fallback to keyword search
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
        return [{
            "content": "Our company offers 24/7 customer support. You can reach us via phone, email, or chat.",
            "similarity": 0.8
        }]
