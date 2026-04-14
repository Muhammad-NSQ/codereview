import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3-coder:latest"

def review_chunks(documents: list[str], model: str = DEFAULT_MODEL) -> str:
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
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    import json
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    print(token, end="", flush=True)
                    full_response.append(token)
                    if chunk.get("done", False):
                        break
        print()
        return "".join(full_response)

    except requests.exceptions.ConnectionError:
        return "Error: Ollama is not running. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return "Error: Ollama timed out. The model may be overloaded."
    except Exception as e:
        return f"Error: {e}"