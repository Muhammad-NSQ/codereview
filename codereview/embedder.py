import os
import torch
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

from sentence_transformers import SentenceTransformer

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Add embeddings to each chunk."""
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=False)
    
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()
    
    return chunks

def embed_query(query: str) -> list[float]:
    """Embed a natural language query string."""
    return model.encode(query).tolist()