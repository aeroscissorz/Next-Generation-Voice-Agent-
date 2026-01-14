from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss, json, numpy as np
from pathlib import Path

BASE = Path(__file__).parent.parent
RAW_DOC = BASE / "data" / "raw_policy.txt"
OUT_CHUNKS = BASE / "data" / "kb_chunks.json"
OUT_INDEX = BASE / "data" / "kb.index"

text = RAW_DOC.read_text(encoding="utf-8")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50
)

chunks = splitter.split_text(text)

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = model.encode(chunks)

index = faiss.IndexFlatL2(len(embeddings[0]))
index.add(np.array(embeddings))

faiss.write_index(index, str(OUT_INDEX))
json.dump(chunks, open(OUT_CHUNKS, "w", encoding="utf-8"), indent=2)

print("KB chunking & indexing complete")
print(f"Chunks: {len(chunks)}")
