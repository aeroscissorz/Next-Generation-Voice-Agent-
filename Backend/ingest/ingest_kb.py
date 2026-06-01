"""
Knowledge Base Ingestion Script
================================
One-time script to ingest company policy documents into the Supabase
pgvector-enabled 'company_knowledge' table for RAG (Retrieval-Augmented Generation).

Pipeline:
  1. Read raw policy text from Backend/data/raw_policy.txt
  2. Split into chunks using LangChain's RecursiveCharacterTextSplitter
     (400 chars per chunk, 50 char overlap for context continuity)
  3. Generate embeddings for all chunks using OpenAI text-embedding-3-small
     (batched in groups of 100 for efficiency)
  4. Clear existing data from the 'company_knowledge' table
  5. Insert all chunks with their embeddings into Supabase

The resulting table is queried at runtime by:
  - Backend/tools/knowledge_tools.py (search_company_knowledge)
  - Interceptor/services/tool_executor.py (knowledge_search fast-path)

Both use the 'match_company_knowledge' Supabase RPC function for
pgvector cosine similarity search.

Usage:
  cd Backend
  python ingest/ingest_kb.py

Prerequisites:
  - SUPABASE_URL and SUPABASE_SERVICE_KEY in Backend/.env
  - OPENAI_API_KEY in Backend/.env
  - 'company_knowledge' table with pgvector extension enabled in Supabase
  - 'match_company_knowledge' RPC function defined in Supabase
"""

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from supabase import create_client
from pathlib import Path
import httpx
import os

# Load .env from Backend folder (parent of ingest/)
BASE = Path(__file__).parent.parent
load_dotenv(BASE / ".env", override=True)

# Path to the raw policy document
RAW_DOC = BASE / "data" / "raw_policy.txt"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Debug: verify env loaded correctly
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')[:30]}..." if os.getenv('SUPABASE_URL') else "SUPABASE_URL not found!")

# ─── Supabase Client ─────────────────────────────────────────────────────────
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)


def get_openai_embedding(text: str) -> list:
    """
    Get a single embedding vector (1536 dims) for a text chunk.
    Uses OpenAI's text-embedding-3-small model.
    """
    response = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "text-embedding-3-small",
            "input": text
        },
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def get_openai_embeddings_batch(texts: list) -> list:
    """
    Get embeddings for multiple texts in a single API call.
    
    More efficient than calling get_openai_embedding() per chunk.
    Includes retry logic with exponential backoff for rate limiting (429).
    
    Args:
        texts: List of text strings to embed
    
    Returns:
        List of embedding vectors, ordered to match the input texts
    """
    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "text-embedding-3-small",
                    "input": texts
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()["data"]
            # Sort by index to ensure order matches input texts
            return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                # Rate limited — wait with exponential backoff (10s, 20s, 30s)
                wait = (attempt + 1) * 10
                print(f"  Rate limited, waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                raise


# ─── Main Ingestion Pipeline ─────────────────────────────────────────────────

# Step 1: Read the raw policy document
text = RAW_DOC.read_text(encoding="utf-8")

# Step 2: Split into chunks using LangChain's recursive splitter
# - chunk_size=400: Each chunk is ~400 characters (fits well in embedding context)
# - chunk_overlap=50: 50 chars of overlap between chunks for context continuity
splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50
)
chunks = splitter.split_text(text)

print(f"Created {len(chunks)} chunks")
print("Getting OpenAI embeddings (batch)...")

# Step 3: Generate embeddings in batches of 100 (OpenAI limit is 2048 per call)
batch_size = 100
all_embeddings = []
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i + batch_size]
    print(f"  Processing batch {i // batch_size + 1}...")
    embeddings = get_openai_embeddings_batch(batch)
    all_embeddings.extend(embeddings)

print("Inserting into Supabase...")

# Step 4: Clear existing data (delete all rows except a sentinel UUID)
supabase.table("company_knowledge").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

# Step 5: Insert all chunks with their embeddings
for chunk, embedding in zip(chunks, all_embeddings):
    supabase.table("company_knowledge").insert({
        "content": chunk,
        "embedding": embedding,
        "source": "raw_policy.txt"
    }).execute()

# ─── Summary ─────────────────────────────────────────────────────────────────
print("KB ingestion into pgvector complete")
print(f"Chunks stored: {len(chunks)}")
print("Embedding model: OpenAI text-embedding-3-small (1536 dimensions)")
