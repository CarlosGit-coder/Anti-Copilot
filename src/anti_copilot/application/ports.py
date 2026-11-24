"""Contratos mínimos entre o caso de uso e as integrações externas."""

from __future__ import annotations

from typing import Any, Protocol


class KnowledgeSearch(Protocol):
    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]: ...


class ResponseGenerator(Protocol):
    def generate(self, question: str, evidence: list[dict[str, Any]]) -> str: ...

