from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from supabase import create_client
from pathlib import Path
import os
load_dotenv()
BASE = Path(__file__).parent.parent
RAW_DOC = BASE / "data" / "raw_policy.txt"

# Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

# Read document
text = RAW_DOC.read_text(encoding="utf-8")

# Chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50
)
chunks = splitter.split_text(text)

# Embeddings
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = model.encode(chunks)

# Insert into pgvector table
for chunk, embedding in zip(chunks, embeddings):
    supabase.table("company_knowledge").insert({
        "content": chunk,
        "embedding": embedding.tolist(),
        "source": "raw_policy.txt"
    }).execute()

print("KB ingestion into pgvector complete")
print(f"Chunks stored: {len(chunks)}")
