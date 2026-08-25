"""金标评估集：验证「企业管理」资料库检索命中率（命中率需 >= 0.8）。

从资料库抽取规则类文档，以其标题构造问题，检查 Top1 来源是否为该文档。

用法（backend 目录、激活 venv）：python scripts/eval_kb.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Document  # noqa: E402
from app.rag import store  # noqa: E402

LIBRARY = "演示知识库"
MAX_CASES = 12


def is_rule_doc(title: str) -> bool:
    """规则/制度类文档：不含训练日期码、不为索引。"""
    if re.match(r"^\d{6}\s", title):  # 训练/培训日期码
        return False
    if "List" in title or "说明" in title or "Tags" in title:
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", title))


def clean_title(title: str) -> str:
    return re.sub(r"\.md$", "", title).strip()


def run_eval() -> float:
    init_db()
    db = SessionLocal()
    docs = (
        db.query(Document)
        .filter(Document.library == LIBRARY)
        .all()
    )
    cases = [d for d in docs if is_rule_doc(d.title)][:MAX_CASES]
    db.close()

    hits = 0
    total = len(cases)
    print(f"{'问题':<30} 命中 期望文档")
    print("-" * 70)
    for d in cases:
        q = f"{clean_title(d.title)}有哪些主要内容？"
        results = store.search(q, top_k=1, doc_ids=[x.id for x in cases])
        hit = bool(results) and results[0]["doc_id"] == d.id
        if hit:
            hits += 1
        mark = "[OK]" if hit else "[NO]"
        print(f"{q[:28]:<30} {mark:<4} {d.title[:20]}")
    rate = hits / total
    print("-" * 70)
    print(f"命中率: {hits}/{total} = {rate:.1%}  (要求 >= 80%)")
    return rate


if __name__ == "__main__":
    rate = run_eval()
    sys.exit(0 if rate >= 0.8 else 1)
