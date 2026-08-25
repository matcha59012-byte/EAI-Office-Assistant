"""知识库问答核心逻辑：检索 + 拒答 + LLM。

供 /api/kb/ask（单次）与会话提问（带历史）共用，避免逻辑重复。
"""
from app.ai import prompts
from app.ai.llm import llm
from app.config import settings
from app.rag import store

# 强制检索拒答阈值：低于该相似度直接拒答，不靠 LLM 自觉（确定性规则）
MIN_SIMILARITY = 0.45

# 拼入提示词的历史条数（2条=1轮对话）
HISTORY_MAX_ITEMS = 6

# 来源最多展示条数
MAX_SOURCES = 3


def format_history(messages: list[dict]) -> str:
    """把最近的会话消息拼成【对话历史】块。"""
    if not messages:
        return ""
    recent = messages[-HISTORY_MAX_ITEMS:]
    lines = []
    for m in recent:
        role = "用户" if m.get("role") == "user" else "AI"
        lines.append(f"{role}: {(m.get('content') or '')[:200]}")
    return prompts.HISTORY_BLOCK_TEMPLATE.format(history="\n".join(lines))


def answer_question(
    question: str,
    doc_id: int | None = None,
    doc_ids: list[int] | None = None,
    messages: list[dict] | None = None,
) -> dict:
    """检索 + 拒答 + LLM 回答。messages 为最近会话消息 [{role, content}]。"""
    results = store.search(question, top_k=5, doc_id=doc_id, doc_ids=doc_ids)

    if not results or results[0]["similarity"] < MIN_SIMILARITY:
        return {
            "answer": "未检索到相关文档，请换个问法，或先上传相关文档后再提问。",
            "sources": [],
            "rejected": True,
        }

    top = [r for r in results if r["similarity"] >= MIN_SIMILARITY] or results[:3]
    top = top[:MAX_SOURCES]
    sources_text = "\n\n".join(
        f"[来源{i + 1}]\n{r['text']}" for i, r in enumerate(top)
    )

    if not settings.llm_configured:
        fallback = (
            "（后端尚未配置 DeepSeek API Key，以下展示检索到的相关内容；配置 Key 后可获得 AI 综合回答）\n\n"
            + "\n\n".join(f"[来源{i + 1}] {r['text']}" for i, r in enumerate(top))
        )
        return {"answer": fallback, "sources": [_to_source(r) for r in top], "rejected": False}

    history_block = format_history(messages) if messages else ""
    user_prompt = prompts.KB_QA_USER_TEMPLATE.format(
        history_block=history_block,
        sources=sources_text,
        question=question,
    )
    answer = llm.chat(prompts.KB_QA_SYSTEM, user_prompt)
    return {"answer": answer, "sources": [_to_source(r) for r in top], "rejected": False}


def _to_source(r: dict) -> dict:
    return {
        "doc_id": r["doc_id"],
        "chunk_index": r["chunk_index"],
        "text": r["text"],
        "similarity": r["similarity"],
    }


def append_sources_footer(answer: str, sources: list[dict], titles: dict) -> str:
    """在回答末尾附上来源（最多 MAX_SOURCES 条），带可跳转的 doc:// 链接。

    来源随回答一起存入消息内容，切换会话后仍保留。
    """
    if not sources:
        return answer
    lines = ["\n\n---\n**来源：**"]
    for i, s in enumerate(sources[:MAX_SOURCES], 1):
        doc_id = s.get("doc_id")
        title = titles.get(doc_id) or f"文档#{doc_id}"
        lines.append(f"{i}. [{title}](doc://{doc_id}) · 相似度 {s.get('similarity')}")
    return answer + "\n".join(lines)
