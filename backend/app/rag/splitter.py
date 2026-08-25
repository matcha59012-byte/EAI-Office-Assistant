"""文档切片：按段落切，超长再按句子切。"""
import re


def split_text(text: str, max_len: int = 400, min_len: int = 30) -> list[str]:
    """把长文档切成可检索的片段。"""
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= max_len:
            chunks.append(para)
        else:
            chunks.extend(_split_long(para, max_len))

    # 过滤过短片段
    result = [c for c in chunks if len(c) >= min_len]
    return result or chunks


def _split_long(text: str, max_len: int) -> list[str]:
    """按句子切长段落。"""
    sentences = re.split(r"(?<=[。！？.!?])", text)
    parts: list[str] = []
    buf = ""
    for s in sentences:
        if len(buf) + len(s) <= max_len:
            buf += s
        else:
            if buf:
                parts.append(buf)
            buf = s
    if buf:
        parts.append(buf)
    return parts
