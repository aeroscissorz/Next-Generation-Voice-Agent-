import faiss, json, numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path

INDEX_PATH = Path("voice_agents_adk/data/kb.index")
CHUNKS_PATH = Path("voice_agents_adk/data/kb_chunks.json")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
index = faiss.read_index(str(INDEX_PATH))
chunks = json.load(open(CHUNKS_PATH))

def search_company_knowledge(query: str, k: int = 3):
    q_emb = model.encode([query])
    _, I = index.search(np.array(q_emb), k)
    return [chunks[i] for i in I[0]]
