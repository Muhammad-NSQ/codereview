import typer
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from codereview.chunker import chunk_code
from codereview.embedder import embed_chunks, embed_query
from codereview.retriever import store_chunks, retrieve_chunks
from codereview.reviewer import review_chunks, check_ollama, list_models, DEFAULT_OLLAMA_URL, DEFAULT_MODEL

app = typer.Typer()
console = Console()

COLLECTION = "project_review"

REVIEW_QUERIES = [
    "security vulnerabilities SQL injection hardcoded credentials exposed secrets",
    "missing error handling no try except uncaught exceptions crashes",
    "resource leaks file handles not closed database connections not closed",
    "bad practices code smells inefficient logic poor structure",
    "input validation missing type checking no sanitization",
]

def index_file(file_path: str) -> int:
    """Index a file into ChromaDB for directory-wide RAG review."""
    try:
        source_code = Path(file_path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return 0

    if not source_code.strip():
        return 0

    chunks = chunk_code(source_code, file_path)
    chunks = embed_chunks(chunks)
    store_chunks(chunks, COLLECTION)
    return len(chunks)

def review_single_file(file_path: str, model: str, base_url: str) -> None:
    """Send entire file directly to LLM — no RAG needed for single files."""
    try:
        source_code = Path(file_path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        console.print(f"[red]Error:[/red] Could not read {file_path} — not a valid UTF-8 file.")
        return
    except PermissionError:
        console.print(f"[red]Error:[/red] Permission denied reading {file_path}.")
        return

    if not source_code.strip():
        console.print(f"[yellow]Skipping[/yellow] {file_path} — empty file.")
        return

    review_chunks([source_code], model=model, base_url=base_url)

def run_review(n_results: int = 10, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_URL) -> str:
    """RAG pipeline for directory-wide review."""
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
        console.print(f"[red]Error:[/red] Ollama is not running at {ollama_url}")
        console.print("Start it with: [bold]ollama serve[/bold]")
        console.print(f"Or set a different URL: [bold]export CODEREVIEW_OLLAMA_URL=http://host:port[/bold]")
        raise typer.Exit(1)

    available = list_models(ollama_url)
    if available and model not in available:
        console.print(f"[red]Error:[/red] model '[bold]{model}[/bold]' not found in Ollama.")
        console.print(f"Available models: [cyan]{', '.join(available)}[/cyan]")
        console.print(f"Pull it with: [bold]ollama pull {model}[/bold]")
        console.print(f"Or set a default: [bold]export CODEREVIEW_MODEL=<model-name>[/bold]")
        raise typer.Exit(1)

    p = Path(path)

    if p.is_file():
        # single file — skip RAG, send full file directly to LLM
        console.print(f"[blue]📂 Reading[/blue] {p}...")
        console.print("[blue]🤖 Reviewing with LLM...[/blue]\n")
        console.print(Rule("[bold blue]Code Review[/bold blue]"))
        review_single_file(str(p), model=model, base_url=ollama_url)
        console.print(Rule())

    elif p.is_dir():
        # directory — use full RAG pipeline
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.Client(Settings(anonymized_telemetry=False))
            client.delete_collection(COLLECTION)
        except Exception:
            pass

        files = list(p.rglob("*.py"))
        console.print(f"[blue]📂 Indexing[/blue] {len(files)} files...")
        total = 0
        for f in files:
            n = index_file(str(f))
            total += n
            console.print(f"   [dim]{f}[/dim] → [green]{n} chunks[/green]")
        console.print(f"   [bold]Total: {total} chunks indexed[/bold]\n")

        console.print("[blue]🔎 Running semantic retrieval...[/blue]")
        console.print("[blue]🤖 Reviewing with LLM...[/blue]\n")
        console.print(Rule("[bold blue]Code Review[/bold blue]"))
        run_review(model=model, base_url=ollama_url)
        console.print(Rule())

    else:
        console.print(f"[red]Error:[/red] {path} is not a valid file or directory")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()