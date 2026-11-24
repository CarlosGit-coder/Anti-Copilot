"""Comandos para inventariar fontes, indexar documentos e inspecionar buscas."""

import argparse
import sys
from pathlib import Path
from typing import Any, Iterator

from anti_copilot.catalog import load_catalog
from anti_copilot.config import settings
from anti_copilot.ingestion import PreparedChunk, discover_source_files, prepare_file_chunks
from anti_copilot.rag import KnowledgeBase


def _source_by_id(sources: list[dict[str, Any]], source_id: str) -> dict[str, Any]:
    for source in sources:
        if source["id"] == source_id:
            return source
    raise ValueError(f"Fonte '{source_id}' não existe em {settings.catalog_path}.")


def _list_sources(sources: list[dict[str, Any]]) -> None:
    for source in sources:
        status = source["ingestion"]
        print(f"{source['id']}: {source['title']} [{status}]")
        print(f"  origem: {source['url']}")
        if "license" in source:
            print(f"  licença: {source['license']} ({source.get('license_url', 'sem URL')})")
        if status == "allowed_with_attribution":
            try:
                files = discover_source_files(settings.project_root, source)
                print(f"  {len(files)} arquivo(s) local(is) pronto(s) para ingestão")
            except (FileNotFoundError, ValueError) as error:
                print(f"  pendente: {error}")
        else:
            print("  não indexada: a fonte ainda não foi liberada no catálogo")


def _ingest(sources: list[dict[str, Any]], requested_ids: list[str] | None) -> None:
    if requested_ids:
        selected = [_source_by_id(sources, source_id) for source_id in requested_ids]
    else:
        selected = [source for source in sources if source["ingestion"] == "allowed_with_attribution"]

    pending = [source["id"] for source in selected if source["ingestion"] != "allowed_with_attribution"]
    if pending:
        raise ValueError(
            "Estas fontes não estão liberadas para ingestão no catálogo: " + ", ".join(pending)
        )
    if not selected:
        raise ValueError("Nenhuma fonte liberada. Revise ingestion em data/catalog/sources.toml.")

    source_files: list[tuple[dict[str, Any], list[Path]]] = []
    for source in selected:
        files = discover_source_files(settings.project_root, source)
        source_files.append((source, files))
        print(f"{source['id']}: {len(files)} arquivo(s) encontrado(s)")

    # O modelo só é carregado depois de encontrarmos arquivos locais autorizados.
    knowledge = KnowledgeBase(settings)
    for source, files in source_files:
        def chunk_stream() -> Iterator[PreparedChunk]:
            for path in files:
                print(f"  lendo {path.relative_to(settings.project_root)}")
                yield from prepare_file_chunks(path, source, settings.project_root)

        count = knowledge.sync_source(source["id"], chunk_stream())
        print(f"{source['id']}: {count} trecho(s) gravados; coleção tem {knowledge.count()} no total")


def _search(knowledge: KnowledgeBase, query: str, limit: int) -> None:
    if limit < 1:
        raise ValueError("--limit precisa ser maior que zero.")
    results = knowledge.search(query, limit=limit)
    if not results:
        print("A coleção está vazia. Execute primeiro: uv run anti-copilot-knowledge ingest")
        return
    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]
        location = metadata["file_path"]
        if "page_number" in metadata:
            location += f": página {metadata['page_number']}"
        print(
            f"\n[{rank}] similaridade={result['similarity']:.3f} | "
            f"{metadata['source_title']} | {location}"
        )
        print(f"URL: {metadata['source_url']}")
        print(result["text"][:900].replace("\n", " "))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="anti-copilot-knowledge")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sources", help="Lista fontes e informa quais podem ser indexadas")

    ingest = commands.add_parser("ingest", help="Extrai, divide, vetorializa e indexa fontes liberadas")
    ingest.add_argument("--source", action="append", dest="source_ids", help="ID de fonte; pode repetir")

    search = commands.add_parser("search", help="Busca trechos na coleção vetorial")
    search.add_argument("query", help="Pergunta ou conceito para recuperar")
    search.add_argument("--limit", type=int, default=5)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        sources = load_catalog(settings.catalog_path)
        if args.command == "sources":
            _list_sources(sources)
        elif args.command == "ingest":
            _ingest(sources, args.source_ids)
        elif args.command == "search":
            _search(KnowledgeBase(settings), args.query, args.limit)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
