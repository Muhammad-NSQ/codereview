import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def chunk_code(source_code: str, file_path: str) -> list[dict]:
    """Parse Python code and split into function/class chunks."""
    chunks = []
    tree = parser.parse(bytes(source_code, "utf8"))
    root = tree.root_node

    for node in root.children:
        if node.type in ("function_definition", "class_definition"):
            chunk_text = source_code[node.start_byte:node.end_byte]
            chunks.append({
                "text": chunk_text,
                "file": file_path,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "type": node.type,
            })

    # If no functions/classes found, treat whole file as one chunk
    if not chunks:
        chunks.append({
            "text": source_code,
            "file": file_path,
            "start_line": 1,
            "end_line": source_code.count("\n") + 1,
            "type": "module",
        })

    return chunks