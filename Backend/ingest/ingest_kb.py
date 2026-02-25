from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from supabase import create_client
from pathlib import Path
import httpx
import os

# Load .env from Backend folder
BASE = Path(__file__).parent.parent
load_dotenv(BASE / ".env", override=True)

RAW_DOC = BASE / "data" / "raw_policy.txt"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Debug: print to verify env loaded
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')[:30]}..." if os.getenv('SUPABASE_URL') else "SUPABASE_URL not found!")

# Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)


def get_openai_embedding(text: str) -> list:
    """Get embedding using OpenAI API"""
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
    """Get embeddings for multiple texts in one API call with retry"""
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
            return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait = (attempt + 1) * 10  # 10s, 20s, 30s
                print(f"  Rate limited, waiting {wait}s before retry...")
                time.sleep(wait)
            else:
                raise


# Read document
text = RAW_DOC.read_text(encoding="utf-8")

# Chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50
)
chunks = splitter.split_text(text)

print(f"Created {len(chunks)} chunks")
print("Getting OpenAI embeddings (batch)...")

# Get embeddings in batches of 100 (OpenAI limit is 2048)
batch_size = 100
all_embeddings = []
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i + batch_size]
    print(f"  Processing batch {i // batch_size + 1}...")
    embeddings = get_openai_embeddings_batch(batch)
    all_embeddings.extend(embeddings)

print("Inserting into Supabase...")

# Clear existing data
supabase.table("company_knowledge").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

# Insert into pgvector table
for chunk, embedding in zip(chunks, all_embeddings):
    supabase.table("company_knowledge").insert({
        "content": chunk,
        "embedding": embedding,
        "source": "raw_policy.txt"
    }).execute()

print("KB ingestion into pgvector complete")
print(f"Chunks stored: {len(chunks)}")
print("Embedding model: OpenAI text-embedding-3-small (1536 dimensions)")
