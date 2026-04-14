import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(anonymized_telemetry=False))

def get_or_create_collection(name: str = "codereview"):
    return client.get_or_create_collection(name=name)

def store_chunks(chunks: list[dict], collection_name: str = "codereview"):
    """Store embedded chunks in ChromaDB."""
    collection = get_or_create_collection(collection_name)
    
    ids = [f"{chunk['file']}:{chunk['start_line']}" for chunk in chunks]
    embeddings = [chunk["embedding"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [{
        "file": chunk["file"],
        "start_line": chunk["start_line"],
        "end_line": chunk["end_line"],
        "type": chunk["type"],
    } for chunk in chunks]

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

def retrieve_chunks(query_embedding: list[float], n_results: int = 5, collection_name: str = "codereview"):
    """Retrieve most relevant chunks for a query."""
    collection = get_or_create_collection(collection_name)
    results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    return results