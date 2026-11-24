"""Embeddings locais E5 via ONNX Runtime, sem dependência de PyTorch/CUDA."""

from functools import lru_cache
from typing import Any, Sequence


MODEL_DIMENSIONS = {"intfloat/multilingual-e5-small": 384}


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> Any:
    """Registra e carrega o modelo uma vez por processo."""
    from fastembed import TextEmbedding
    from fastembed.common.model_description import ModelSource, PoolingType

    registered = {item["model"] for item in TextEmbedding.list_supported_models()}
    if model_name not in registered:
        if model_name not in MODEL_DIMENSIONS:
            raise ValueError(f"Modelo {model_name!r} não está registrado neste projeto.")
        TextEmbedding.add_custom_model(
            model=model_name,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf=model_name),
            dim=MODEL_DIMENSIONS[model_name],
            model_file="onnx/model.onnx",
            license="mit",
        )
    return TextEmbedding(model_name=model_name)


class LocalEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model_id = model_name
        self.model = _load_model(model_name)

    @property
    def dimensions(self) -> int:
        try:
            return MODEL_DIMENSIONS[self.model_name]
        except KeyError as error:
            raise RuntimeError(f"Dimensão não configurada para {self.model_name}.") from error

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        passages = [f"passage: {text}" for text in texts]
        return [vector.tolist() for vector in self.model.embed(passages, batch_size=32)]

    def embed_query(self, text: str) -> list[float]:
        [vector] = list(self.model.embed([f"query: {text}"], batch_size=1))
        return vector.tolist()
