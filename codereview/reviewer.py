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

    if stripped.startswith("▶ Issue"):
        text = stripped.replace("▶ ", "").replace("**", "")
        console.print(f"\n[bold cyan]▶ {text}[/bold cyan]")

    elif stripped.startswith("File:"):
        text = stripped.replace("File:", "").strip().replace("`", "")
        console.print(f"  [dim]📄 File:[/dim] [white]{text}[/white]")

    elif stripped.startswith("Function:"):
        text = stripped.replace("Function:", "").strip().replace("`", "")
        console.print(f"  [dim]⚙ Function:[/dim] [white]{text}[/white]")

    elif stripped.startswith("Line:"):
        text = stripped.replace("Line:", "").strip()
        console.print(f"  [dim]📍 Line:[/dim] [white]{text}[/white]")

    elif stripped.startswith("● Description:"):
        text = stripped.replace("● Description:", "").strip()
        console.print(f"\n  [red]● Description:[/red] {text}")

    elif stripped.startswith("● Suggestion:"):
        text = stripped.replace("● Suggestion:", "").strip()
        console.print(f"\n  [green]● Suggestion:[/green] {text}")

    elif stripped.startswith("```"):
        console.print(f"  [dim]{stripped}[/dim]")

    elif stripped.startswith("─────"):
        console.print(f"\n[dim]─────────────────────────────────[/dim]")

    elif stripped == "":
        console.print("")

    else:
        text = stripped.replace("**", "")
        console.print(f"  [dim white]{text}[/dim white]")

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

Note: The code below may consist of extracted chunks from multiple files, not complete files.
Do not flag syntax errors or incomplete functions based on missing context —
assume the rest of the code is correctly implemented elsewhere.

Focus only on the most important issues:
1. Bugs and potential runtime errors
2. Security issues
3. Bad practices and code smells
4. Performance problems
5. Missing error handling

Rules:
- Report only real issues you can directly see in the provided code
- Do not invent issues or speculate about code not shown
- Do not report issues about missing imports or undefined variables that may be defined elsewhere
- Do not flag incomplete functions — they may be truncated chunks
- Be specific — mention function names and line numbers
- Do not pad with generic advice like "add unit tests", "add async support", or "add logging"
- Do not force issues — if you only find 2 real problems, report 2. Quality over quantity.
- A clean function with minor style issues is not worth reporting
- Only report issues that would cause real problems in production: crashes, security holes, data loss, or significant performance degradation
- Do not report theoretical or speculative issues
- Do not praise the code
- If the code is clean, say so briefly
- Do not make assumptions about code inside imported functions — only review what is directly visible

Format each issue exactly like this — use these exact symbols and labels:
▶ Issue N: **Title**
File: `filename`
Function: `function_name`
Line: line_number
● Description: what is wrong and why it matters
● Suggestion: how to fix it, with a code example if helpful
─────────────────────────────────

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