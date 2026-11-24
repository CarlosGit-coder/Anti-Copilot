"""Leitura, divisão e enriquecimento de documentos antes da vetorização."""

from dataclasses import dataclass
import ast
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterator

from langchain_text_splitters import Language, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pypdf import PdfReader


CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf", ".py", ".java"}
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "target",
    "coverage",
}


@dataclass(frozen=True)
class PreparedChunk:
    """Trecho original, texto com contexto para embedding, ID e metadados."""

    id: str
    text: str
    embedding_text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RawDocument:
    text: str
    page_number: int | None = None


def discover_source_files(project_root: Path, source: dict[str, Any]) -> list[Path]:
    """Expande os padrões include sem sair da pasta local declarada pela fonte."""
    source_root = (project_root / source["local_path"]).resolve()
    root = project_root.resolve()
    if root not in source_root.parents:
        raise ValueError(f"Fonte {source['id']}: local_path precisa ficar dentro do projeto.")
    if not source_root.is_dir():
        raise FileNotFoundError(f"Pasta local não encontrada para {source['id']}: {source_root}")

    excluded_patterns = source.get("exclude", [])
    files: set[Path] = set()
    for pattern in source["include"]:
        for path in source_root.glob(pattern):
            if not path.is_file():
                continue
            resolved_path = path.resolve()
            if source_root != resolved_path and source_root not in resolved_path.parents:
                raise ValueError(f"Arquivo da fonte aponta para fora da pasta local: {path}")
            relative = path.relative_to(source_root)
            if any(part in IGNORED_DIRECTORY_NAMES or part.startswith(".") for part in relative.parts):
                continue
            if any(relative.match(excluded) for excluded in excluded_patterns):
                continue
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                raise ValueError(
                    f"Formato não suportado em {path}. Formatos aceitos: "
                    f"{', '.join(sorted(SUPPORTED_SUFFIXES))}."
                )
            files.add(path)

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo compatível foi encontrado para {source['id']}. "
            "Confira local_path e include em sources.toml."
        )
    return sorted(files)


def iter_raw_documents(path: Path) -> Iterator[RawDocument]:
    """Extrai PDF página a página ou lê um arquivo textual em UTF-8."""
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        pages = reader.pages
        found_text = False
        for index, page in enumerate(pages, 1):
            text = page.extract_text() or ""
            found_text = found_text or bool(text.strip())
            yield RawDocument(text, page_number=index)
        if not found_text:
            raise ValueError(
                f"O PDF {path.name} não contém texto extraível. PDFs digitalizados precisam de OCR, "
                "que ainda não está habilitado."
            )
        return

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        # Arquivos __init__.py vazios são marcadores válidos de pacote e comuns
        # em projetos Python. Não há conteúdo para indexar, então apenas pulamos.
        return
    yield RawDocument(text)


def _splitter_for(path: Path) -> RecursiveCharacterTextSplitter:
    common = {
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "add_start_index": True,
    }
    if path.suffix.lower() == ".py":
        return RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON, **common)
    if path.suffix.lower() == ".java":
        return RecursiveCharacterTextSplitter.from_language(language=Language.JAVA, **common)
    return RecursiveCharacterTextSplitter(**common)


def _split_markdown(text: str) -> list[Any]:
    """Mantém o título das seções nos metadados antes de dividir os parágrafos."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    sections = header_splitter.split_text(text)
    if not sections:
        from langchain_core.documents import Document

        sections = [Document(page_content=text, metadata={})]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )
    return splitter.split_documents(sections)


def _code_symbols(path: Path, text: str) -> tuple[str, str]:
    """Extrai símbolos de topo para enriquecer o contexto dos chunks de código."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return "", ""
        classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
        functions = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        symbols = classes + functions
        return (classes[0] if classes else ""), ", ".join(symbols[:12])
    if suffix == ".java":
        declarations = re.findall(r"\b(?:class|interface|enum|record)\s+([A-Za-z_$][\w$]*)", text)
        return (declarations[0] if declarations else ""), ", ".join(declarations[:12])
    return "", ""


def prepare_file_chunks(
    path: Path,
    source: dict[str, Any],
    project_root: Path,
) -> Iterator[PreparedChunk]:
    """Transforma uma fonte em trechos com origem, seção e contexto global."""
    relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
    with path.open("rb") as file:
        file_digest = hashlib.file_digest(file, "sha256").hexdigest()
    source_revision = str(source.get("revision", "working-copy"))
    global_context = f"{source['title']} | {source['organization']} | {relative_path} | revisão {source_revision}"
    chunk_number = 0

    for raw_document in iter_raw_documents(path):
        primary_symbol, symbols = _code_symbols(path, raw_document.text)
        symbol_context = f" | símbolo principal {primary_symbol}" if primary_symbol else ""
        if path.suffix.lower() == ".md":
            split_documents = _split_markdown(raw_document.text)
        else:
            split_documents = _splitter_for(path).create_documents([raw_document.text])

        for split_document in split_documents:
            content = split_document.page_content.strip()
            if not content:
                continue
            section = " > ".join(
                str(split_document.metadata[key])
                for key in ("h1", "h2", "h3")
                if split_document.metadata.get(key)
            )
            enriched_context = global_context + symbol_context + (f" | {section}" if section else "")
            chunk_id_text = f"{source['id']}\0{relative_path}\0{raw_document.page_number}\0{chunk_number}"
            chunk_id = hashlib.sha256(chunk_id_text.encode("utf-8")).hexdigest()
            metadata: dict[str, Any] = {
                "source_id": source["id"],
                "source_title": source["title"],
                "organization": source["organization"],
                "source_url": source["url"],
                "source_revision": source_revision,
                "license": source["license"],
                "license_url": source["license_url"],
                "kind": source["kind"],
                "language": source["language"],
                "topics": json.dumps(source["topics"], ensure_ascii=False),
                "file_path": relative_path,
                "file_sha256": file_digest,
                "chunk_index": chunk_number,
                "start_index": int(split_document.metadata.get("start_index", 0)),
                "context_global": enriched_context,
            }
            if primary_symbol:
                metadata["primary_symbol"] = primary_symbol
            if symbols:
                metadata["symbols"] = symbols
            if raw_document.page_number is not None:
                metadata["page_number"] = raw_document.page_number
            if section:
                metadata["section"] = section

            yield PreparedChunk(
                id=chunk_id,
                text=content,
                embedding_text=f"{enriched_context}\n\n{content}",
                metadata=metadata,
            )
            chunk_number += 1
