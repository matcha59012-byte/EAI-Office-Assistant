"""一次性数据修复：为 content 为空的文档回填全文。

优先从 sample_data 匹配；否则从 kb_chunks 拼接。
用法（backend 目录、激活 venv）：python scripts/repair_content.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Document, KbChunk  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"


def main() -> None:
    init_db()
    db = SessionLocal()
    fixed = 0
    for doc in db.query(Document).all():
        if doc.content:
            continue
        # 1) sample_data 同名文件
        sample = SAMPLE_DIR / doc.title
        if sample.exists():
            doc.content = sample.read_text(encoding="utf-8")
        else:
            # 2) kb_chunks 拼接兜底
            chunks = (
                db.query(KbChunk)
                .filter(KbChunk.doc_id == doc.id)
                .order_by(KbChunk.chunk_index.asc())
                .all()
            )
            doc.content = "\n\n".join(c.chunk_text for c in chunks)
        db.commit()
        fixed += 1
        print(f"已修复 doc#{doc.id} [{doc.title}] 长度={len(doc.content)}")
    db.close()
    print(f"完成，共修复 {fixed} 个文档")


if __name__ == "__main__":
    main()
