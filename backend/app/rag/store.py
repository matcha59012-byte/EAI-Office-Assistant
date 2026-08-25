"""向量检索：numpy 余弦相似度 + SQLite 持久化（BLOB）。

背景决策：chromadb 在 Windows 上大量写入后跨进程加载 HNSW 索引异常
（本机实测 1.5.9 / 0.5.23 均复现 "Error loading hnsw index"）。为可靠性，
改为轻量自实现：数千切片 × 512 维，numpy 毫秒级、零外部依赖。
数据量增大后可平滑迁移 chromadb / Milvus（本文件是唯一改动点）。
"""
import numpy as np
from sqlalchemy import text

from app.database import engine
from app.rag.embedder import embed_texts

TABLE = "kb_vectors"


def _ensure() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""CREATE TABLE IF NOT EXISTS {TABLE} (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id INTEGER,
                    chunk_index INTEGER,
                    dim INTEGER,
                    chunk_text TEXT,
                    vector BLOB)"""
            )
        )


def add_document(doc_id: int, chunks: list[str]) -> None:
    """把文档切片向量化后写入。"""
    _ensure()
    vecs = embed_texts(chunks)
    with engine.begin() as conn:
        for i, (chunk, vec) in enumerate(zip(chunks, vecs)):
            blob = np.asarray(vec, dtype=np.float32).tobytes()
            conn.execute(
                text(
                    f"INSERT OR REPLACE INTO {TABLE} "
                    "(chunk_id, doc_id, chunk_index, dim, chunk_text, vector) "
                    "VALUES (:cid, :did, :ci, :dim, :ct, :vec)"
                ),
                {
                    "cid": f"doc{doc_id}-chunk{i}",
                    "did": doc_id,
                    "ci": i,
                    "dim": len(vec),
                    "ct": chunk,
                    "vec": blob,
                },
            )


def delete_document(doc_id: int) -> None:
    _ensure()
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {TABLE} WHERE doc_id=:did"), {"did": doc_id})


def search(
    query: str,
    top_k: int = 5,
    doc_id: int | None = None,
    doc_ids: list[int] | None = None,
) -> list[dict]:
    """检索最相似切片，按相似度降序。doc_id 限单文档，doc_ids 限资料库范围。"""
    _ensure()
    sql = f"SELECT chunk_id, doc_id, chunk_index, chunk_text, vector FROM {TABLE}"
    params: dict = {}
    if doc_id is not None:
        sql += " WHERE doc_id=:did"
        params["did"] = doc_id
    elif doc_ids:
        ph = ",".join(f":id{i}" for i in range(len(doc_ids)))
        sql += f" WHERE doc_id IN ({ph})"
        params.update({f"id{i}": v for i, v in enumerate(doc_ids)})

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    if not rows:
        return []

    q = np.asarray(embed_texts([query])[0], dtype=np.float32)
    qn = np.linalg.norm(q) + 1e-9

    ids = [r[0] for r in rows]
    docs = [r[1] for r in rows]
    idxs = [r[2] for r in rows]
    texts = [r[3] for r in rows]
    mat = np.stack([np.frombuffer(r[4], dtype=np.float32) for r in rows])

    sims = (mat @ q) / (np.linalg.norm(mat, axis=1) + 1e-9) / qn
    top = np.argsort(-sims)[:top_k]

    return [
        {
            "chunk_id": ids[i],
            "doc_id": docs[i],
            "chunk_index": idxs[i],
            "text": texts[i],
            "similarity": round(float(sims[i]), 4),
        }
        for i in top
    ]
