"""Caso de uso RAG, dependente apenas dos contratos da aplicação."""

from __future__ import annotations

from typing import Any

from anti_copilot.application.ports import KnowledgeSearch, ResponseGenerator


class MentorUnavailable(RuntimeError):
    """A recuperação ou a geração não conseguiu concluir a consulta."""


class ProjectMentor:
    """Recupera evidências e pede uma orientação baseada nelas."""

    def __init__(self, knowledge: KnowledgeSearch, generator: ResponseGenerator) -> None:
        self._knowledge = knowledge
        self._generator = generator

    def ask(self, question: str) -> tuple[str, list[dict[str, Any]]]:
        evidence = self._knowledge.search(question, top_k=4)
        if not evidence:
            raise MentorUnavailable("O acervo está vazio. Execute `uv run python seed.py` primeiro.")

        try:
            answer = self._generator.generate(question, evidence)
        except Exception as error:
            raise MentorUnavailable(
                "Não consegui gerar a resposta. Confira se n8n e Ollama estão ativos e se o workflow foi publicado."
            ) from error

        if not answer.strip():
            raise MentorUnavailable("O workflow não devolveu uma resposta de texto.")
        return answer.strip(), evidence
