from pathlib import Path
import re
import tomllib
from urllib.parse import urlparse


REQUIRED_FIELDS = {
    "id",
    "title",
    "organization",
    "url",
    "kind",
    "topics",
    "language",
    "ingestion",
}
ALLOWED_INGESTION = {
    "allowed_with_attribution",
    "review_terms",
    "metadata_only_until_terms_review",
}


def load_catalog(path: Path) -> list[dict]:
    with path.open("rb") as file:
        catalog = tomllib.load(file)

    sources = catalog.get("sources", [])
    validate_catalog(sources)
    return sources


def validate_catalog(sources: list[dict]) -> None:
    if not isinstance(sources, list) or not sources:
        raise ValueError("O catálogo precisa conter uma lista não vazia em [[sources]].")

    seen_ids: set[str] = set()

    for number, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise ValueError(f"Fonte {number}: cada entrada precisa ser uma tabela TOML.")

        missing = REQUIRED_FIELDS - source.keys()
        if missing:
            fields = ", ".join(sorted(missing))
            raise ValueError(f"Fonte {number}: campos ausentes: {fields}")

        source_id = source["id"]
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", source_id):
            raise ValueError(f"Fonte {number}: id deve usar letras minúsculas, números, _ ou -.")
        if source_id in seen_ids:
            raise ValueError(f"ID de fonte repetido: {source_id}")
        seen_ids.add(source_id)

        for field in ("title", "organization", "url", "kind", "language"):
            if not isinstance(source[field], str) or not source[field].strip():
                raise ValueError(f"Fonte {source_id}: {field} precisa ser um texto não vazio.")

        parsed_url = urlparse(source["url"])
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(f"Fonte {source_id}: url deve ser um endereço HTTP ou HTTPS.")
        if not isinstance(source["ingestion"], str):
            raise ValueError(f"Fonte {source_id}: ingestion precisa ser um texto.")
        if source["ingestion"] not in ALLOWED_INGESTION:
            allowed = ", ".join(sorted(ALLOWED_INGESTION))
            raise ValueError(f"Fonte {source_id}: ingestion inválido. Use: {allowed}.")
        if not isinstance(source["topics"], list) or not all(
            isinstance(topic, str) for topic in source["topics"]
        ):
            raise ValueError(f"Fonte {source_id}: topics precisa ser uma lista de textos.")

        if source["ingestion"] == "allowed_with_attribution":
            ingest_fields = {"license", "license_url", "local_path", "include"}
            missing_ingest_fields = ingest_fields - source.keys()
            if missing_ingest_fields:
                fields = ", ".join(sorted(missing_ingest_fields))
                raise ValueError(f"Fonte {source_id}: faltam campos para ingestão: {fields}")
            if not isinstance(source["include"], list) or not source["include"]:
                raise ValueError(f"Fonte {source_id}: include precisa ter ao menos um padrão de arquivo.")
            if not all(isinstance(pattern, str) and pattern for pattern in source["include"]):
                raise ValueError(f"Fonte {source_id}: cada valor de include precisa ser um padrão de texto.")
            if any(Path(pattern).is_absolute() or ".." in Path(pattern).parts for pattern in source["include"]):
                raise ValueError(f"Fonte {source_id}: include não pode sair da pasta local da fonte.")
            if not isinstance(source["local_path"], str):
                raise ValueError(f"Fonte {source_id}: local_path precisa ser um caminho relativo em texto.")
            local_path = Path(source["local_path"])
            if local_path.is_absolute() or ".." in local_path.parts or local_path == Path("."):
                raise ValueError(f"Fonte {source_id}: local_path precisa ser relativo e permanecer no projeto.")
            for field in ("license", "license_url"):
                if not isinstance(source[field], str) or not source[field].strip():
                    raise ValueError(f"Fonte {source_id}: {field} precisa ser um texto não vazio.")
            license_url = urlparse(source["license_url"])
            if license_url.scheme not in {"http", "https"} or not license_url.netloc:
                raise ValueError(f"Fonte {source_id}: license_url deve ser HTTP ou HTTPS.")
            excluded = source.get("exclude", [])
            if not isinstance(excluded, list) or not all(
                isinstance(pattern, str) and pattern for pattern in excluded
            ):
                raise ValueError(f"Fonte {source_id}: exclude precisa ser uma lista de padrões de texto.")
        if "revision" in source and not isinstance(source["revision"], str):
            raise ValueError(f"Fonte {source_id}: revision precisa ser texto, como uma tag ou hash Git.")
