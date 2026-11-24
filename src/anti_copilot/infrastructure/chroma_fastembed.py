"""Ingestão e recuperação semântica local com FastEmbed e ChromaDB."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from typing import Any

import chromadb
from fastembed import TextEmbedding

from anti_copilot.config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, KNOWLEDGE_DIR


class ChromaFastEmbedKnowledge:
    """Adapta os arquivos Markdown a embeddings e consultas vetoriais."""

    def __init__(self) -> None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=None,
            metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL},
        )
        self._embedder = TextEmbedding(model_name=EMBEDDING_MODEL)

    def ingest(self, folder: Path = KNOWLEDGE_DIR, *, reset: bool = False) -> int:
        """Indexa Markdown local, guardando a seção e o link de origem como metadados."""
        files = sorted(folder.rglob("*.md"))
        if not files:
            raise FileNotFoundError(f"Nenhum arquivo Markdown encontrado em {folder}.")

        if reset:
            current_ids = self._collection.get(include=[])["ids"]
            if current_ids:
                self._collection.delete(ids=current_ids)

        rows: list[dict[str, Any]] = []
        for file_path in files:
            text = file_path.read_text(encoding="utf-8")
            frontmatter, body = _read_frontmatter(text)
            default_title = file_path.stem.replace("-", " ").title()
            title = str(frontmatter.get("title", default_title))
            source_url = str(frontmatter.get("source_url", ""))
            organization = str(frontmatter.get("organization", "Documentação local"))

            for index, section in enumerate(_split_sections(body), start=1):
                if not section.strip():
                    continue
                heading = _heading(section) or title
                stable_id = hashlib.sha256(
                    f"{file_path.relative_to(folder)}:{index}".encode("utf-8")
                ).hexdigest()
                rows.append(
                    {
                        "id": stable_id,
                        "text": section.strip(),
                        "metadata": {
                            "source_title": title,
                            "source_url": source_url,
                            "organization": organization,
                            "file_path": str(file_path.relative_to(folder)),
                            "section": heading,
                        },
                    }
                )

        if not rows:
            raise ValueError("Os arquivos Markdown não têm conteúdo indexável.")

        vectors = [
            vector.tolist()
            for vector in self._embedder.embed([row["text"] for row in rows], batch_size=32)
        ]
        self._collection.upsert(
            ids=[row["id"] for row in rows],
            documents=[row["text"] for row in rows],
            metadatas=[row["metadata"] for row in rows],
            embeddings=vectors,
        )
        return len(rows)

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        """Recupera as seções mais próximas semanticamente da pergunta."""
        total = self._collection.count()
        if total == 0:
            return []

        [query_vector] = self._embedder.embed([query], batch_size=1)
        result = self._collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        return [
            {"text": text, "metadata": metadata or {}, "distance": distance}
            for text, metadata, distance in zip(
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]


def _read_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Lê metadados TOML opcionais cercados por +++ no início do Markdown."""
    match = re.match(r"\A\+\+\+\s*\n(.*?)\n\+\+\+\s*\n(.*)\Z", text, re.DOTALL)
    if not match:
        return {}, text
    return tomllib.loads(match.group(1)), match.group(2)


def _split_sections(text: str, max_chars: int = 1800) -> list[str]:
    """Divide por títulos e mantém parágrafos curtos juntos para busca precisa."""
    sections = re.split(r"(?=^#{1,3}\s+)", text, flags=re.MULTILINE)
    chunks: list[str] = []
    for section in (part.strip() for part in sections if part.strip()):
        if len(section) <= max_chars:
            chunks.append(section)
            continue
        heading = _heading(section)
        body = re.sub(r"^#{1,3}\s+.+\n*", "", section, count=1)
        paragraphs = re.split(r"\n\s*\n", body)
        current = heading
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            if len(current) + len(paragraph) + 2 > max_chars and current.strip():
                chunks.append(current.strip())
                current = f"{heading}\n\n{paragraph}" if heading else paragraph
            else:
                current = f"{current}\n\n{paragraph}" if current else paragraph
        if current.strip():
            chunks.append(current.strip())
    return chunks


def _heading(section: str) -> str:
    match = re.search(r"^#{1,3}\s+(.+)$", section, re.MULTILINE)
    return match.group(1).strip() if match else ""

