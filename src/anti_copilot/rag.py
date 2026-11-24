"""Persistência Chroma e recuperação vetorial com embeddings explícitos."""

from typing import Any, Iterable

import chromadb

from anti_copilot.config import Settings
from anti_copilot.embeddings import MODEL_DIMENSIONS, LocalEmbedder
from anti_copilot.ingestion import PreparedChunk


UPSERT_BATCH_SIZE = 64


class KnowledgeBase:
    """Armazena trechos, vetores e metadados em uma coleção Chroma persistente."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self._embedder: LocalEmbedder | None = None
        dimensions = MODEL_DIMENSIONS.get(settings.embedding_model)
        if dimensions is None:
            raise ValueError(f"Não há dimensão registrada para o modelo {settings.embedding_model}.")
        client = chromadb.PersistentClient(path=str(settings.data_dir / "chroma"))
        self.collection = client.get_or_create_collection(
            name=settings.collection_name,
            embedding_function=None,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": self.embedding_model_id,
                "embedding_dimensions": dimensions,
            },
        )
        metadata = self.collection.metadata or {}
        actual_model = metadata.get("embedding_model")
        actual_dimensions = metadata.get("embedding_dimensions")
        if actual_model != self.embedding_model_id or actual_dimensions != dimensions:
            raise RuntimeError(
                f"A coleção {settings.collection_name} usa {actual_model!r}, mas a configuração pede "
                f"{self.embedding_model_id!r} com {dimensions} dimensões. Use outro nome de coleção "
                "antes de trocar o modelo ou as dimensões."
            )

    @property
    def embedding_model_id(self) -> str:
        return self.settings.embedding_model

    @property
    def embedder(self) -> LocalEmbedder:
        if self._embedder is None:
            self._embedder = LocalEmbedder(self.settings.embedding_model)
        return self._embedder

    def sync_source(self, source_id: str, chunks: Iterable[PreparedChunk]) -> int:
        """Indexa em lotes e remove IDs obsoletos após concluir a fonte sem erros."""
        previous = self.collection.get(where={"source_id": source_id}, include=[])
        previous_ids = set(previous["ids"])
        current_ids: set[str] = set()
        batch: list[PreparedChunk] = []
        indexed_count = 0

        def flush_batch() -> None:
            nonlocal indexed_count
            if not batch:
                return
            vectors = self.embedder.embed_documents([chunk.embedding_text for chunk in batch])
            self.collection.upsert(
                ids=[chunk.id for chunk in batch],
                documents=[chunk.text for chunk in batch],
                metadatas=[chunk.metadata for chunk in batch],
                embeddings=vectors,
            )
            indexed_count += len(batch)
            batch.clear()

        for chunk in chunks:
            current_ids.add(chunk.id)
            batch.append(chunk)
            if len(batch) >= UPSERT_BATCH_SIZE:
                flush_batch()
        flush_batch()

        if not current_ids:
            raise ValueError(f"A fonte {source_id} não produziu nenhum trecho para indexação.")

        stale_ids = previous_ids - current_ids
        if stale_ids:
            self.collection.delete(ids=sorted(stale_ids))
        return indexed_count

    def search(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Vetorializa a pergunta e devolve trechos com distâncias e proveniência."""
        total = self.collection.count()
        if total == 0:
            return []
        vector = self.embedder.embed_query(query)
        options: dict[str, Any] = {
            "query_embeddings": [vector],
            "n_results": min(limit, total),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            options["where"] = where
        result = self.collection.query(**options)
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        return [
            {
                "text": text,
                "metadata": metadata,
                "distance": distance,
                "similarity": 1.0 - distance,
            }
            for text, metadata, distance in zip(documents, metadatas, distances)
        ]

    def count(self) -> int:
        return self.collection.count()
