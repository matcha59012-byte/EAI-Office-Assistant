"""文本向量化：中文 embedding 模型（bge-small-zh），本地推理，无额外 API 费用。"""
import os

# 国内镜像，避免 HuggingFace 下载失败
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from sentence_transformers import SentenceTransformer  # noqa: E402

_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化，返回归一化向量。"""
    if not texts:
        return []
    emb = get_model().encode(texts, normalize_embeddings=True)
    return emb.tolist()
