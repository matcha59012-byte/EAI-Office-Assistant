"""通用对话会话 API（模块路径参数：kb / meeting / customer）。

- kb 模块：问答走 RAG 检索（可限定资料库 library / 单文档 doc_id）
- 其他模块（meeting/customer）：普通对话，不检索知识库
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.llm import llm
from app.database import get_db
from app.models import ChatMessage, ChatSession, Document
from app.rag import qa

router = APIRouter(prefix="/api/{module}/sessions", tags=["chat"])


class CreateSessionRequest(BaseModel):
    title: str = "新会话"


class RenameSessionRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    question: str
    doc_id: int | None = None
    library: str | None = None


def _get_session(module: str, session_id: int, db: Session) -> ChatSession:
    s = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.module == module)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="会话不存在")
    return s


@router.get("")
def list_sessions(module: str, db: Session = Depends(get_db)):
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.module == module)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [
        {"id": s.id, "title": s.title, "created_at": s.created_at} for s in rows
    ]


@router.post("")
def create_session(
    module: str, req: CreateSessionRequest, db: Session = Depends(get_db)
):
    s = ChatSession(module=module, title=req.title or "新会话")
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "title": s.title}


@router.delete("/{session_id}")
def delete_session(module: str, session_id: int, db: Session = Depends(get_db)):
    s = _get_session(module, session_id, db)
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.put("/{session_id}")
def rename_session(
    module: str,
    session_id: int,
    req: RenameSessionRequest,
    db: Session = Depends(get_db),
):
    s = _get_session(module, session_id, db)
    s.title = req.title.strip() or "新会话"
    db.commit()
    return {"id": s.id, "title": s.title}


@router.get("/{session_id}/messages")
def list_messages(module: str, session_id: int, db: Session = Depends(get_db)):
    _get_session(module, session_id, db)
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
        for m in rows
    ]


@router.post("/{session_id}/messages")
def send_message(
    module: str,
    session_id: int,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
):
    s = _get_session(module, session_id, db)
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 记录用户问题
    db.add(ChatMessage(session_id=session_id, role="user", content=question))
    db.commit()

    # 取最近历史（供上下文续聊）
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(6)
        .all()
    )
    history = [
        {"role": m.role, "content": m.content} for m in reversed(history_rows)
    ]

    if module == "kb":
        # 知识库模块：走 RAG 检索
        try:
            doc_ids = None
            if req.library:
                doc_ids = [
                    d.id
                    for d in db.query(Document)
                    .filter(Document.library == req.library)
                    .all()
                ]
            result = qa.answer_question(
                question, doc_id=req.doc_id, doc_ids=doc_ids, messages=history
            )
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {e}")

        # 来源附在回答末尾（带可跳转链接，随消息持久化）
        source_ids = {s["doc_id"] for s in result["sources"] if s.get("doc_id")}
        titles: dict = {}
        if source_ids:
            rows = db.query(Document).filter(Document.id.in_(source_ids)).all()
            titles = {d.id: d.title for d in rows}
        final_answer = qa.append_sources_footer(
            result["answer"], result["sources"], titles
        )
    else:
        # 非知识库模块（会议纪要/客户数据）：普通对话，不检索知识库
        try:
            history_block = qa.format_history(history)
            user_prompt = (
                f"{history_block}【问题】{question}" if history_block else question
            )
            answer = llm.chat(
                "你是企业AI办公助手。请用中文简洁、准确地回答用户问题，并基于对话历史理解上下文。",
                user_prompt,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {e}")
        result = {"answer": answer, "sources": [], "rejected": False}
        final_answer = answer

    db.add(ChatMessage(session_id=session_id, role="assistant", content=final_answer))
    if s.title == "新会话":
        s.title = question[:20]
    db.commit()
    return result
