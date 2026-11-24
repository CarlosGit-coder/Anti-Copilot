"""Cria do zero o acervo vetorial a partir dos Markdown locais."""

from anti_copilot.infrastructure.chroma_fastembed import ChromaFastEmbedKnowledge


if __name__ == "__main__":
    sections = ChromaFastEmbedKnowledge().ingest(reset=True)
    print(f"Acervo reconstruído: {sections} seções em data/knowledge.")

