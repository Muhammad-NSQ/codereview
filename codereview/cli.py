import typer
from pathlib import Path
from codereview.chunker import chunk_code
from codereview.embedder import embed_chunks, embed_query
from codereview.retriever import store_chunks, retrieve_chunks
from codereview.reviewer import review_chunks, check_ollama, list_models, DEFAULT_OLLAMA_URL, DEFAULT_MODEL

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
    source_code = Path(file_path).read_text()
    chunks = chunk_code(source_code, file_path)
    chunks = embed_chunks(chunks)
    store_chunks(chunks, COLLECTION)
    return len(chunks)

def run_review(n_results: int = 10, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_URL) -> str:
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

    return review_chunks(all_documents, model=model, base_url=base_url)

@app.command()
def review(
    path: str = typer.Argument(..., help="File or directory to review"),
    model: str = typer.Option(DEFAULT_MODEL, help="Ollama model (overrides CODEREVIEW_MODEL env var)"),
    ollama_url: str = typer.Option(DEFAULT_OLLAMA_URL, help="Ollama URL (overrides CODEREVIEW_OLLAMA_URL env var)"),
):
    """Review code using local LLM and RAG."""

    if not check_ollama(ollama_url):
        typer.echo(f"Error: Ollama is not running at {ollama_url}")
        typer.echo("Start it with: ollama serve")
        typer.echo(f"Or set a different URL: export CODEREVIEW_OLLAMA_URL=http://host:port")
        raise typer.Exit(1)

    available = list_models(ollama_url)
    if available and model not in available:
        typer.echo(f"Error: model '{model}' not found in Ollama.")
        typer.echo(f"Available models: {', '.join(available)}")
        typer.echo(f"Pull it with: ollama pull {model}")
        typer.echo(f"Or set a default: export CODEREVIEW_MODEL=<model-name>")
        raise typer.Exit(1)

    try:
        import chromadb
        from chromadb.config import Settings
        client = chromadb.Client(Settings(anonymized_telemetry=False))
        client.delete_collection(COLLECTION)
    except Exception:
        pass

    p = Path(path)

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
    result = run_review(model=model, base_url=ollama_url)
    typer.echo(result)

if __name__ == "__main__":
    app()