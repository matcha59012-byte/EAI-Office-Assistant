"""演示数据初始化：重置数据库并导入纯虚构通用制度文档到知识库。

用途：本地开发/公网演示前的标准动作。数据全部来自 `sample_data/`（虚构的
XX科技有限公司通用制度文档，不含任何真实公司/人名/项目信息）。

用法（backend 目录、激活 venv）：
    python scripts/seed_demo_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import (  # noqa: E402
    ChatMessage,
    ChatSession,
    Customer,
    Document,
    Entity,
    KbChunk,
    Meeting,
    MeetingSource,
    PendingExtract,
)
from app.rag import splitter, store  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"
LIBRARY = "演示知识库"


def reset_all(db) -> None:
    """清空全部业务数据，保证干净起点。"""
    for m in [
        Document,
        KbChunk,
        Meeting,
        Customer,
        ChatSession,
        ChatMessage,
        MeetingSource,
        Entity,
        PendingExtract,
    ]:
        db.query(m).delete()
    db.commit()
    store._ensure()
    from sqlalchemy import text
    from app.database import engine

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM kb_vectors"))
    print("[reset] 全部业务数据与向量已清空")


def import_kb(db) -> list[str]:
    """导入 sample_data/ 全部 md 文档到「演示知识库」。"""
    docs = sorted(SAMPLE_DIR.glob("*.md"))
    imported: list[str] = []
    for p in docs:
        text = p.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            print(f"[skip] 空文档: {p.name}")
            continue
        chunks = splitter.split_text(text)
        if not chunks:
            print(f"[skip] 无可检索文本: {p.name}")
            continue
        doc = Document(
            title=p.name,
            file_type="md",
            library=LIBRARY,
            content=text,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        store.add_document(doc.id, chunks)
        for i, c in enumerate(chunks):
            db.add(KbChunk(doc_id=doc.id, chunk_index=i, chunk_text=c))
        db.commit()
        imported.append(p.name)
        print(f"[ok] {p.name} -> {len(chunks)} 切片")
    return imported


def main() -> None:
    init_db()
    db = SessionLocal()
    reset_all(db)
    imported = import_kb(db)
    print(f"\n[完成] 演示知识库共导入 {len(imported)} 篇文档:")
    for name in imported:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
