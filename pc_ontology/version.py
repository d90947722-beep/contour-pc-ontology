"""Identify the code and knowledge snapshot independently of hosting."""
import hashlib
from pathlib import Path

VERSION = "2.4"


def build_label():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    files = [root / "app.py", root / "cloud_app.py"]
    files += sorted((root / "pc_ontology").glob("*.py"))
    files += sorted((root / "ontology").glob("*"))
    for file in files:
        if file.is_file():
            digest.update(file.relative_to(root).as_posix().encode())
            digest.update(file.read_bytes().replace(b"\r\n", b"\n"))
    return f"{VERSION} · сборка {digest.hexdigest()[:10]}"
