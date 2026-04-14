import os
import requests
import json

DEFAULT_OLLAMA_URL = os.environ.get("CODEREVIEW_OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("CODEREVIEW_MODEL", "qwen3-coder:latest")

def check_ollama(base_url: str = DEFAULT_OLLAMA_URL) -> bool:
    """Check if Ollama is running and reachable."""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=3)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False

def list_models(base_url: str = DEFAULT_OLLAMA_URL) -> list[str]:
    """List available models in Ollama."""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=3)
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []

def review_chunks(documents: list[str], model: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_URL) -> str:
    """Send retrieved code chunks to Ollama for review with streaming output."""

    combined_code = "\n\n---\n\n".join(documents)

    prompt = f"""You are an expert code reviewer. Review the following code and provide specific, actionable feedback.

Focus on:
1. Bugs and potential runtime errors
2. Security issues
3. Bad practices and code smells
4. Performance problems
5. Missing error handling

Be specific — mention line numbers or function names when possible.
Do not praise the code, only give constructive feedback.

Code to review:
{combined_code}

Review:"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
    }

    full_response = []

    try:
        with requests.post(f"{base_url}/api/generate", json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    print(token, end="", flush=True)
                    full_response.append(token)
                    if chunk.get("done", False):
                        break
        print()
        return "".join(full_response)

    except requests.exceptions.ConnectionError:
        return f"Error: Ollama is not running at {base_url}. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return "Error: Ollama timed out. The model may be overloaded."
    except Exception as e:
        return f"Error: {e}"