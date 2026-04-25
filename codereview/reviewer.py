import os
import requests
import json
from rich.console import Console
from rich.markdown import Markdown

DEFAULT_OLLAMA_URL = os.environ.get("CODEREVIEW_OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("CODEREVIEW_MODEL", "qwen3-coder:latest")

console = Console()

def colorize_line(line: str):
    stripped = line.strip()

    # section headers ## and ###
    if stripped.startswith("## "):
        text = stripped.replace("## ", "")
        console.print(f"\n[bold white on blue] {text.upper()} [/bold white on blue]")

    elif stripped.startswith("### "):
        text = stripped.replace("### ", "")
        console.print(f"\n[bold cyan]▶ {text}[/bold cyan]")

    # bold lines like **1. Missing error handling**
    elif stripped.startswith("**") and stripped.endswith("**"):
        text = stripped.strip("*")
        if any(word in text.lower() for word in ["critical", "security", "vulnerability"]):
            console.print(f"\n[bold red]● {text}[/bold red]")
        elif any(word in text.lower() for word in ["performance", "runtime", "error"]):
            console.print(f"\n[bold yellow]● {text}[/bold yellow]")
        elif any(word in text.lower() for word in ["smell", "practice", "bad"]):
            console.print(f"\n[bold magenta]● {text}[/bold magenta]")
        else:
            console.print(f"\n[bold yellow]● {text}[/bold yellow]")

    # fix lines
    elif "fix:" in stripped.lower() or "suggestion:" in stripped.lower():
        text = stripped.lstrip("- ")
        console.print(f"  [bold green]✔ {text}[/bold green]")

    # numbered recommendations
    elif stripped and stripped[0].isdigit() and ". " in stripped:
        console.print(f"  [cyan]{stripped}[/cyan]")

    # regular bullet points
    elif stripped.startswith("- ") or stripped.startswith("* "):
        text = stripped.lstrip("- *")
        # inline bold cleanup
        text = text.replace("**", "")
        console.print(f"  [white]• {text}[/white]")

    # divider
    elif stripped == "---":
        console.print("[dim]─────────────────────────────────[/dim]")

    # empty line
    elif stripped == "":
        console.print("")

    # everything else
    else:
        text = stripped.replace("**", "")
        console.print(f"[dim white]{text}[/dim white]")

def check_ollama(base_url: str = DEFAULT_OLLAMA_URL) -> bool:
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=3)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False

def list_models(base_url: str = DEFAULT_OLLAMA_URL) -> list[str]:
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=3)
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []

def review_chunks(documents: list[str], model: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_URL) -> str:
    combined_code = "\n\n---\n\n".join(documents)

    prompt = f"""You are an expert code reviewer. Review the following code and provide specific, actionable feedback.

Focus only on the most important issues:
1. Bugs and potential runtime errors
2. Security issues  
3. Bad practices and code smells
4. Performance problems
5. Missing error handling

Rules:
- Maximum 10 issues total
- Only report issues you can see directly in the provided code
- Do not report issues about missing imports or undefined variables that may be defined elsewhere
- Be specific — mention function names and line numbers
- Do not pad with generic advice like "add unit tests" or "add async support"
- Do not praise the code

Code to review:
{combined_code}

Review:"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
    }

    full_response = []
    current_line = []

    try:
        with requests.post(f"{base_url}/api/generate", json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("response", "")
                    full_response.append(token)

                    if "\n" in token:
                        parts = token.split("\n")
                        current_line.append(parts[0])
                        colorize_line("".join(current_line))
                        current_line = [parts[-1]] if parts[-1] else []
                    else:
                        current_line.append(token)

                    if chunk.get("done", False):
                        if current_line:
                            colorize_line("".join(current_line))
                        break

        return "".join(full_response)

    except requests.exceptions.ConnectionError:
        return f"Error: Ollama is not running at {base_url}. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return "Error: Ollama timed out. The model may be overloaded."
    except Exception as e:
        return f"Error: {e}"