"""模块B（V2）：会议纪要自生长闭环。

工作流：源文件(上传 md/txt 或 MP3→MiMo ASR→md)
  → R1 清洗 → R2 三路提取(客户/项目/公司) → 人工确认 → 实体层入库 → 扫描闭环
"""
import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai import prompts
from app.ai.asr import transcribe_media
from app.ai.cards import render_entity_card
from app.ai.llm import llm
from app.config import settings
from app.database import get_db
from app.models import Entity, MeetingSource, PendingExtract

router = APIRouter(prefix="/api/meeting", tags=["meeting"])

# 扫描文件夹（闭环：放入新文件自动进流程）
SCAN_DIR = Path(__file__).resolve().parents[1] / "sample_meetings" / "待处理"
ALLOWED_TEXT = {".txt", ".md"}
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".flac", ".mov"}

ENTITY_TYPE_MAP = {"customers": "customer", "projects": "project", "companies": "company"}


class ExtractRequest(BaseModel):
    source_id: int


class ConfirmRequest(BaseModel):
    pending_id: int
    card: dict | None = None  # 人工修改后的卡片（可选）


class SkipRequest(BaseModel):
    pending_id: int


# ---------- 工具 ----------


def _to_md(filename: str, content: str) -> tuple[str, str]:
    """txt → md（统一 md 存储）。"""
    if filename.lower().endswith(".txt"):
        title = Path(filename).stem
        content = f"# {title}\n\n{content}"
        filename = f"{title}.md"
    return filename, content


def _parse_llm_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON。"""
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        text = m.group(0)
    return json.loads(text)


def _merge_cards(old: dict, new: dict) -> dict:
    """增量不覆盖：已有字段有值就保留，只补空缺。"""
    merged = dict(old)
    for k, v in new.items():
        if k not in merged or not merged.get(k):
            merged[k] = v
    return merged


def _merge_cards_edited(existing: dict, edited: dict) -> dict:
    """人工编辑优先：编辑卡片中非空字段覆盖已有，空字段保留已有。"""
    merged = dict(existing)
    for k, v in edited.items():
        if v not in (None, "", [], {}):
            merged[k] = v
    return merged


def _update_source_status(db: Session, source_id: int) -> None:
    remaining = (
        db.query(PendingExtract)
        .filter(PendingExtract.source_id == source_id, PendingExtract.status == "pending")
        .count()
    )
    source = db.get(MeetingSource, source_id)
    if not source:
        return
    if remaining == 0:
        skipped = (
            db.query(PendingExtract)
            .filter(PendingExtract.source_id == source_id, PendingExtract.status == "skipped")
            .count()
        )
        total = (
            db.query(PendingExtract)
            .filter(PendingExtract.source_id == source_id)
            .count()
        )
        source.status = "skipped" if (total and skipped == total) else "confirmed"


# ---------- ① 源文件（上传 md/txt / 音频 ASR） ----------


@router.post("/sources")
def upload_source(file: UploadFile = File(...), db: Session = Depends(get_db)):
    name = file.filename or ""
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_TEXT:
        raise HTTPException(status_code=400, detail="源文件仅支持 txt/md")
    content = file.file.read().decode("utf-8", errors="ignore")
    if not content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")
    title, content_md = _to_md(name, content)
    src = MeetingSource(title=Path(title).stem, file_name=title, source_type="upload", content=content_md)
    db.add(src)
    db.commit()
    db.refresh(src)
    return {"id": src.id, "title": src.title, "status": src.status}


@router.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """MP3/MP4 → MiMo ASR → 会议纪要 md（工作流第①步）。"""
    name = file.filename or ""
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_AUDIO:
        raise HTTPException(status_code=400, detail=f"不支持的音频格式: {suffix}")
    # 先建待转写记录
    src = MeetingSource(
        title=Path(name).stem,
        file_name=name,
        source_type="asr",
        content="",
        status="transcribing",
    )
    db.add(src)
    db.commit()
    db.refresh(src)

    tmp = Path(__file__).resolve().parents[1] / "uploads"
    tmp.mkdir(exist_ok=True)
    tmp_path = tmp / f"asr_{src.id}{suffix}"
    tmp_path.write_bytes(file.file.read())

    try:
        transcript = transcribe_media(tmp_path, source_name=name)
    except RuntimeError as e:
        src.status = "ready"
        src.content = f"# ASR 失败\n\n{e}"
        db.commit()
        raise HTTPException(status_code=502, detail=f"ASR 转写失败: {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    # 对齐实习期 ASR 精炼后格式（Speaker Map + 逐句转写）
    md_content = f"# {Path(name).stem} 会议纪要转写\n\n## Speaker Map / 说话人映射\n\n## 转写正文\n\n{transcript}\n"
    src.title = Path(name).stem
    src.file_name = f"{Path(name).stem}-transcript.md"
    src.content = md_content
    src.status = "ready"
    db.commit()
    return {"id": src.id, "title": src.title, "status": src.status}


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(MeetingSource).order_by(MeetingSource.created_at.desc()).all()
    return [
        {"id": s.id, "title": s.title, "file_name": s.file_name, "source_type": s.source_type, "status": s.status, "created_at": s.created_at}
        for s in rows
    ]


@router.get("/sources/{source_id}")
def get_source(source_id: int, db: Session = Depends(get_db)):
    s = db.get(MeetingSource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="源文件不存在")
    return {"id": s.id, "title": s.title, "content": s.content, "status": s.status, "source_type": s.source_type}


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    s = db.get(MeetingSource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="源文件不存在")
    db.query(PendingExtract).filter(PendingExtract.source_id == source_id).delete()
    db.query(Entity).filter(Entity.source_meeting_id == source_id).update({"source_meeting_id": None})
    db.delete(s)
    db.commit()
    return {"ok": True}


# ---------- ③ 实体提取（R1+R2 → 待确认） ----------


@router.post("/extract")
def extract_entities(req: ExtractRequest, db: Session = Depends(get_db)):
    s = db.get(MeetingSource, req.source_id)
    if not s:
        raise HTTPException(status_code=404, detail="源文件不存在")
    if not s.content.strip():
        raise HTTPException(status_code=400, detail="源文件内容为空")

    if not settings.llm_configured:
        raise HTTPException(status_code=502, detail="未配置 DeepSeek API Key，无法提取实体")

    try:
        cleaned = llm.chat(prompts.MEETING_R1_CLEAN_SYSTEM, s.content)
        raw = llm.chat(prompts.MEETING_R2_EXTRACT_SYSTEM, cleaned)
        parsed = _parse_llm_json(raw)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"提取失败: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI 返回非 JSON: {e}")

    # 清掉旧的待确认，重新生成
    db.query(PendingExtract).filter(PendingExtract.source_id == s.id).delete()
    items = []
    for group, etype in ENTITY_TYPE_MAP.items():
        for card in parsed.get(group, []):
            if not isinstance(card, dict) or not card.get("name"):
                continue
            # 准入预筛：C 级客户/公司仅提名，不建档
            if card.get("level", "").strip().upper() == "C" and etype in ("customer", "company"):
                continue
            pe = PendingExtract(
                source_id=s.id,
                entity_type=etype,
                card_json=json.dumps(card, ensure_ascii=False),
            )
            db.add(pe)
            db.commit()
            db.refresh(pe)
            md = render_entity_card(etype, card, s.id)
            existing = (
                db.query(Entity)
                .filter(Entity.entity_type == etype, Entity.name == card.get("name"))
                .first()
            )
            diff = "🔄 更新" if existing else "🆕 新增"
            items.append(
                {"pending_id": pe.id, "entity_type": etype, "card": card, "card_md": md, "diff": diff}
            )

    s.status = "pending"
    db.commit()
    return {"source_id": s.id, "cleaned": cleaned, "items": items}


# ---------- ④ 人工确认 / 跳过 → 实体层入库 ----------


@router.post("/confirm")
def confirm_entity(req: ConfirmRequest, db: Session = Depends(get_db)):
    pe = db.get(PendingExtract, req.pending_id)
    if not pe:
        raise HTTPException(status_code=404, detail="待确认项不存在")
    if pe.status != "pending":
        raise HTTPException(status_code=400, detail="该项已处理")

    # 使用人工修改后的卡片（未改则用提取结果）
    card = req.card if req.card is not None else json.loads(pe.card_json or "{}")
    pe.card_json = json.dumps(card, ensure_ascii=False)

    existing = (
        db.query(Entity)
        .filter(Entity.entity_type == pe.entity_type, Entity.name == card.get("name"))
        .first()
    )
    if existing:
        merged = _merge_cards_edited(json.loads(existing.card_json or "{}"), card)
        existing.card_json = json.dumps(merged, ensure_ascii=False)
        existing.card_md = render_entity_card(pe.entity_type, merged, pe.source_id)
        final_name = merged.get("name") or existing.name
    else:
        md = render_entity_card(pe.entity_type, card, pe.source_id)
        db.add(
            Entity(
                entity_type=pe.entity_type,
                name=card.get("name") or "未命名",
                card_json=pe.card_json,
                card_md=md,
                source_meeting_id=pe.source_id,
            )
        )
        final_name = card.get("name") or "未命名"

    pe.status = "confirmed"
    db.commit()
    _update_source_status(db, pe.source_id)
    db.commit()
    return {"ok": True, "entity_type": pe.entity_type, "name": final_name}


@router.post("/skip")
def skip_entity(req: SkipRequest, db: Session = Depends(get_db)):
    pe = db.get(PendingExtract, req.pending_id)
    if not pe:
        raise HTTPException(status_code=404, detail="待确认项不存在")
    if pe.status != "pending":
        raise HTTPException(status_code=400, detail="该项已处理")
    pe.status = "skipped"
    db.commit()
    _update_source_status(db, pe.source_id)
    db.commit()
    return {"ok": True}


# ---------- 待确认队列 / 实体库 / 扫描闭环 ----------


@router.get("/pending")
def list_pending(db: Session = Depends(get_db)):
    rows = (
        db.query(PendingExtract)
        .filter(PendingExtract.status == "pending")
        .order_by(PendingExtract.created_at.asc())
        .all()
    )
    return [
        {
            "pending_id": p.id,
            "source_id": p.source_id,
            "entity_type": p.entity_type,
            "card": json.loads(p.card_json or "{}"),
        }
        for p in rows
    ]


@router.get("/entities")
def list_entities(entity_type: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Entity)
    if entity_type:
        q = q.filter(Entity.entity_type == entity_type)
    rows = q.order_by(Entity.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "name": e.name,
            "card": json.loads(e.card_json or "{}"),
            "card_md": e.card_md,
            "source_meeting_id": e.source_meeting_id,
            "created_at": e.created_at,
        }
        for e in rows
    ]


@router.get("/entities/{entity_id}")
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    e = db.get(Entity, entity_id)
    if not e:
        raise HTTPException(status_code=404, detail="实体不存在")
    return {
        "id": e.id,
        "entity_type": e.entity_type,
        "name": e.name,
        "card": json.loads(e.card_json or "{}"),
        "card_md": e.card_md,
        "source_meeting_id": e.source_meeting_id,
    }


@router.post("/scan")
def scan_sources(db: Session = Depends(get_db)):
    """扫描源文件夹：新文件 → 生成源记录 → 自动提取 → 待确认（闭环）。"""
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    imported = 0
    results = []
    for f in sorted(SCAN_DIR.iterdir()):
        if not f.is_file() or f.suffix.lower() not in ALLOWED_TEXT:
            continue
        exists = db.query(MeetingSource).filter(MeetingSource.file_name == f.name).first()
        if exists:
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        title, content_md = _to_md(f.name, content)
        src = MeetingSource(title=Path(title).stem, file_name=title, source_type="upload", content=content_md, status="ready")
        db.add(src)
        db.commit()
        db.refresh(src)
        imported += 1
        results.append({"source_id": src.id, "file": f.name, "title": src.title})
    return {"imported": imported, "sources": results}


# ---------- V1 兼容：旧接口保留 ----------


class ParseRequest(BaseModel):
    transcript: str
    title: str = "未命名会议"


@router.post("/parse")
def parse(req: ParseRequest):
    if not settings.llm_configured:
        return {"title": req.title, "markdown": f"## 原始会议记录\n{req.transcript[:2000]}"}
    md = llm.chat(prompts.MEETING_SYSTEM, req.transcript)
    return {"title": req.title, "markdown": md}


@router.get("/records")
def old_records(db: Session = Depends(get_db)):
    from app.models import Meeting

    rows = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    return [{"id": m.id, "title": m.title, "summary": (m.summary or "")[:60]} for m in rows]
