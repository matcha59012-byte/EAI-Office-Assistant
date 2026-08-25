"""SQLAlchemy 数据模型（地基卡锁定）。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    """模块A：知识库文档。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(20), default="md")
    library: Mapped[str] = mapped_column(String(100), default="默认资料库")
    content: Mapped[str] = mapped_column(Text, default="")  # 全文（供查看）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KbChunk(Base):
    """模块A：文档切片（向量存 chromadb，这里存文本与归属）。"""

    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chunk_text: Mapped[str] = mapped_column(Text)


class Meeting(Base):
    """模块B：会议纪要。"""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="未命名会议")
    transcript: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[str] = mapped_column(Text, default="")
    todos: Mapped[str] = mapped_column(Text, default="")
    highlights: Mapped[str] = mapped_column(Text, default="")
    markdown: Mapped[str] = mapped_column(Text, default="")  # 完整四段纪要
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Customer(Base):
    """模块C：客户数据。"""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    source: Mapped[str] = mapped_column(String(50), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatSession(Base):
    """对话会话（可被多个模块复用：kb/meeting/customer）。"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(20), default="kb")
    title: Mapped[str] = mapped_column(String(255), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    """会话消息。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MeetingSource(Base):
    """模块B：会议纪要源文件（统一 md 存储）。"""

    __tablename__ = "meeting_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="未命名会议")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(20), default="upload")  # upload / asr
    content: Mapped[str] = mapped_column(Text, default="")  # md 内容
    # 状态：raw → transcribing → ready → extracted → pending → confirmed / skipped
    status: Mapped[str] = mapped_column(String(20), default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Entity(Base):
    """模块B/C：实体卡片（客户 / 项目 / 公司），来源可追溯。"""

    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))  # customer / project / company
    name: Mapped[str] = mapped_column(String(255))
    card_json: Mapped[str] = mapped_column(Text, default="{}")
    card_md: Mapped[str] = mapped_column(Text, default="")  # 实体卡片格式 md 卡片
    # 跟进字段（客户数据管理用）
    status: Mapped[str] = mapped_column(String(20), default="新")  # 新/跟进中/静默/已关闭
    last_contact: Mapped[str] = mapped_column(String(20), default="")  # YYYY-MM-DD
    source_meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meeting_sources.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PendingExtract(Base):
    """模块B：待人工确认的提取结果（闭环扫描后生成）。"""

    __tablename__ = "pending_extracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("meeting_sources.id"))
    entity_type: Mapped[str] = mapped_column(String(20))
    card_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / confirmed / skipped
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
