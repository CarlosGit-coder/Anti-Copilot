"""Adaptador HTTP para o webhook local do n8n."""

from __future__ import annotations

from typing import Any

import requests

from anti_copilot.config import N8N_WEBHOOK_URL


class N8nResponseGenerator:
    """Envia pergunta e trechos recuperados ao workflow n8n."""

    def __init__(self, webhook_url: str = N8N_WEBHOOK_URL) -> None:
        self._webhook_url = webhook_url

    def generate(self, question: str, evidence: list[dict[str, Any]]) -> str:
        context = "\n\n---\n\n".join(item["text"] for item in evidence)
        sources = [
            {
                "title": item["metadata"].get("source_title", "Documento local"),
                "url": item["metadata"].get("source_url", ""),
                "file": item["metadata"].get("file_path", ""),
                "section": item["metadata"].get("section", ""),
            }
            for item in evidence
        ]
        response = requests.post(
            self._webhook_url,
            json={"pergunta": question, "contexto": context, "fontes": sources},
            timeout=240,
        )
        response.raise_for_status()
        return _extract_answer(response)


def _extract_answer(response: requests.Response) -> str:
    if "application/json" in response.headers.get("content-type", ""):
        try:
            payload = response.json()
        except ValueError:
            return ""
        if isinstance(payload, dict):
            for key in ("text", "response", "answer", "output"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return response.text.strip()
