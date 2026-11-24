# Anti-Copilot

Assistente de arquitetura design-first com recuperação semântica. A base vetorial é preparada por uma linha de ingestão explícita antes da conversa: fontes são catalogadas, documentos são extraídos e divididos, embeddings locais são calculados e os vetores com metadados são persistidos no ChromaDB.

## Primeira execução

Requer Python 3.14 e `uv`.

```bash
uv sync
uv run anti-copilot-knowledge sources
uv run anti-copilot-knowledge ingest
```

O primeiro uso baixa o modelo local `intfloat/multilingual-e5-small`. Para a geração de respostas, configure `GEMINI_API_KEY` no mesmo terminal e execute:

```bash
export GEMINI_API_KEY="sua-chave"
uv run streamlit run src/anti_copilot/app.py
```

## Aprender e ampliar o acervo

Leia [o guia documentado do acervo, da ingestão e dos embeddings](docs/GUIA_ACERVO_E_RAG.md). Ele explica os módulos, os metadados, o fluxo da informação e exemplos para registrar PDFs, documentação e repositórios Python/Java.

As fontes e regras de ingestão ficam em `data/catalog/sources.toml`; os materiais ficam em `data/raw/`; os vetores persistentes ficam em `data/chroma/`. Não coloque textos ou documentos dentro de arquivos Python.
