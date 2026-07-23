import subprocess
from pypdf import PdfReader
from pathlib import Path
from tools.file_index import jarvis_file_index, INDEXED_ROOT
from rag import client, get_embedding
import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)
# Give JARVIS file access

JARVIS_FOLDER = Path.home() / "Desktop" / "PhongDinh" / "Side Project" / "JARVIS_Files"
JARVIS_FOLDER.mkdir(exist_ok=True)
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache"}
JARVIS_SEARCHABLE_DIRS = [
    Path.home()/"Desktop",
    Path.home()/"Documents",
    Path.home()/"Downloads"
]
def path_safe(requested_path: str, base_dir: Path) -> bool: # Check whether a path is safe to access or not, guarded against hallucinated paths
    try:
        resolved = (base_dir / requested_path).resolve()
        return resolved.is_relative_to(base_dir.resolve())
    except Exception as e:
        return False

def find_file(query:str, max_results: int = 6) -> str:
    if max_results in (None, "null", "none", ""):
        max_results = 6
    else:
        try:
            max_results = int(max_results)
        except (ValueError, TypeError):
            max_results = 6

    if jarvis_file_index.count() == 0:
        return "File index is empty - no files indexed yet."
    query_embedding = get_embedding(query)
    
    query = query.lower()
    if not query_embedding:
        return "Can't process the search."
    
    results = jarvis_file_index.query(
        query_embeddings=[query_embedding],
        n_results=min(max_results, jarvis_file_index.count())
    )

    if not results["documents"][0]:
        return "No matching files."

    return "\n".join(results["documents"][0])

def open_file(path: str):
    file = Path(path).resolve()
    try:
        if not file.is_relative_to(INDEXED_ROOT.resolve()):
            return f"Access denied - File is not within allowed folders."
    except Exception:
        return "Access denied."
    if not file.exists():
        return "File not found."
    try:
        subprocess.run(["open", path])
        return f"Opened file {file.name}"
    except Exception as e:
        return f"Couldn't open {file.name}: e"

MAX_READ_CHARS = 2000
def read_file(path: str) -> str:
    file = Path(path).resolve()
    try:
        if not file.is_relative_to(INDEXED_ROOT.resolve()):
            return "Access denied - file not within allowed folder."
    except Exception:
        return "Access denied."
    if not file.exists():
        return "File not found."
    try:
        if file.suffix.lower() == ".pdf":
            reader = PdfReader(str(file))
            text = ""
            for page in reader.pages[:5]:
                text += page.extract_text() or ""
                if len(page) >= MAX_READ_CHARS:
                    break
        else:
            text = file.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Couldn't read file {file.name}: {e}"
    
    if len(text) >= MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + "\n\n...[file truncated]..."
    return text

MAX_WRITE_CHARS = 10000
SAFE_EXTENSIONS = {".md", ".txt"} # Current allowed extension
def create_file(filename: str, content: str = "") -> str:
    file = (JARVIS_FOLDER / filename).resolve()
    if not path_safe(file, JARVIS_FOLDER):
        return "Access denied."
    if file.suffix.lower() not in SAFE_EXTENSIONS:
        return f"Currently unsupported file type: {file.suffix}"
    if len(content) > MAX_WRITE_CHARS:
        return f"Content too long ({len(content)} chars) — max is {MAX_WRITE_CHARS}."
    if file.exists():
        return f"'{filename}' already exists. Use a different name, or explicitly ask to overwrite it."
    try:
        file.write_text(data=content, encoding="utf-8")
        return f"Created {file.name}"
    except Exception as e:
        return f"Couldn't create file {e}"
    