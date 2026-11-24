from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Configuração da aplicação, ingestão e persistência vetorial."""

    project_root: Path = PROJECT_ROOT
    data_dir: Path = Path(os.getenv("ANTI_COPILOT_DATA_DIR", str(PROJECT_ROOT / "data")))
    catalog_path: Path = PROJECT_ROOT / "data" / "catalog" / "sources.toml"
    collection_name: str = "anti_copilot_e5_small_v1"
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    api_key: str | None = os.getenv("GEMINI_API_KEY")


settings = Settings()
