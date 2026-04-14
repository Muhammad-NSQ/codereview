import typer
from pathlib import Path
from codereview.chunker import chunk_code
from codereview.embedder import embed_chunks, embed_query
from codereview.retriever import store_chunks, retrieve_chunks, get_or_create_collection
from codereview.reviewer import review_chunks

app = typer.Typer()

COLLECTION = "project_review"

REVIEW_QUERIES = [
    "security vulnerabilities SQL injection hardcoded credentials exposed secrets",
    "missing error handling no try except uncaught exceptions crashes",
    "resource leaks file handles not closed database connections not closed",
    "bad practices code smells inefficient logic poor structure",
    "input validation missing type checking no sanitization",
]

def index_file(file_path: str):
    """Chunk and embed a file and store in the shared collection."""
    source_code = Path(file_path).read_text()
    chunks = chunk_code(source_code, file_path)
    chunks = embed_chunks(chunks)
    store_chunks(chunks, COLLECTION)
    return len(chunks)

def run_review(n_results: int = 10) -> str:
    """Query the shared collection with semantic queries and review results."""
    seen_ids = set()
    all_documents = []

    for query in REVIEW_QUERIES:
        query_embedding = embed_query(query)
        results = retrieve_chunks(query_embedding, n_results=n_results, collection_name=COLLECTION)
        for doc, id_ in zip(results["documents"][0], results["ids"][0]):
            if id_ not in seen_ids:
                seen_ids.add(id_)
                all_documents.append(doc)

    if not all_documents:
        return "No chunks retrieved."

    return review_chunks(all_documents)

@app.command()
def review(
    path: str = typer.Argument(..., help="File or directory to review"),
    model: str = typer.Option("qwen3-coder:latest", help="Ollama model to use"),
):
    """Review code using local LLM and RAG."""
    p = Path(path)

    # reset collection for each run
    try:
        import chromadb
        from chromadb.config import Settings
        client = chromadb.Client(Settings(anonymized_telemetry=False))
        client.delete_collection(COLLECTION)
    except Exception:
        pass

    if p.is_file():
        typer.echo(f"📂 Indexing {p}...")
        n = index_file(str(p))
        typer.echo(f"   {n} chunks indexed")

    elif p.is_dir():
        files = list(p.rglob("*.py"))
        typer.echo(f"📂 Indexing {len(files)} files...")
        total = 0
        for f in files:
            n = index_file(str(f))
            total += n
            typer.echo(f"   {f} → {n} chunks")
        typer.echo(f"   Total: {total} chunks indexed\n")

    else:
        typer.echo(f"Error: {path} is not a valid file or directory")
        raise typer.Exit(1)

    typer.echo("🔎 Running semantic retrieval...")
    typer.echo("🤖 Reviewing with LLM...\n")
    result = run_review()
    typer.echo(result)

if __name__ == "__main__":
    app()