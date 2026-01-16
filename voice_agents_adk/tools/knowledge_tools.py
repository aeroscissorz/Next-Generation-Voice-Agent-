from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer
import os
import threading

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

# Lazy-loaded embedding model
_embedder = None
_embedder_lock = threading.Lock()

def get_embedder():
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:  
                print("🔄 Loading embedding model (first KB request)...")
                _embedder = SentenceTransformer(
                    "sentence-transformers/all-MiniLM-L6-v2"
                )
    return _embedder


def search_company_knowledge(query: str, k: int = 3):
    embedder = get_embedder() 

    query_embedding = embedder.encode(query).tolist()

    response = supabase.rpc(
        "match_company_knowledge",
        {
            "query_embedding": query_embedding,
            "match_count": k
        }
    ).execute()

    print("DEBUG KB RESPONSE:", response.data)

    if response.data:
        return response.data

    keyword = query.lower().replace("policy", "").strip()
    fallback = (
        supabase.table("company_knowledge")
        .select("content")
        .ilike("content", f"%{keyword}%")
        .limit(k)
        .execute()
    )

    return fallback.data or []
