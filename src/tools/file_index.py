from pypdf import PdfReader
import chromadb
from rag import client, get_embedding
from pathlib import Path
from datetime import datetime, timedelta

jarvis_file_index = client.get_or_create_collection("jarvis_file_index")

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    "dist",
    "build",
    "data",
    "datasets",
    "dataset",
    "models",
}
INDEXED_ROOT = Path.home() / "Desktop" / "PhongDinh"
INDEXABLE_EXTENSIONS = {".pdf", ".md"}
PREVIEW_CHARS = 1000 # How much text permitted to extract
MAX_FILE_SIZE = 50*1024*1024 #20MB
MAX_FILE_AGE_DAYS = 730

def extract_preview(file: Path) -> str:
    try:
        # Avoid huge files
        if file.stat().st_size > MAX_FILE_SIZE:
            print(f"Skipping large file: {file.name}")
            return ""
        
        if file.suffix.lower() == ".pdf":
            reader = PdfReader(str(file))
            text = ""
            for page in reader.pages[:3]:
                text += page.extract_text() or ""
                if len(text) >= PREVIEW_CHARS:
                    break
            return text[:PREVIEW_CHARS]
        else:  # .md, .txt
            text = file.read_text(encoding="utf-8", errors="ignore")
        return text[:PREVIEW_CHARS]
    except Exception as e:
        print(f"Skipping PDF {file.name}: {e}")
        return ""
    
def build_file_index(root: Path=INDEXED_ROOT):
    existing = {doc_id: meta for doc_id, meta in
                zip(jarvis_file_index.get()["ids"], jarvis_file_index.get()["metadatas"])} if jarvis_file_index.count() > 0 else {}
    for file in INDEXED_ROOT.rglob("*"):
        # Ignore metadatas
        if file.name.startswith("._"):
            continue
        # Ignore unwanted directories
        if any(part in SKIP_DIRS for part in file.parts):
            continue
        # Ignore unsupported files
        if not file.is_file() or file.suffix.lower() not in INDEXABLE_EXTENSIONS:
            continue
        
        # Check modification date
        modified_time = datetime.fromtimestamp(file.stat().st_mtime)

        if datetime.now() - modified_time > timedelta(days=MAX_FILE_AGE_DAYS):
            continue
        
        file_id = str(file)
        mtime = file.stat().st_mtime # Modified Time

        # Skip unchanged file
        if file_id in existing and existing[file_id].get("mtime") == mtime:
            continue

        preview = extract_preview(file)
        if not preview.strip():
            continue

        embed_text = f"{file.name}\n{preview}"
        embedding = get_embedding(text=embed_text)
        if not embedding:
            continue

        jarvis_file_index.upsert(
            documents=[str(file)],
            embeddings=[embedding],
            metadatas=[{"filename": file.name, "mtime": mtime}],
            ids=[file_id]
        )

    print(f"File Index built: {jarvis_file_index.count()} files indexed.")

