"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import chat, customer, kb, meeting


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="E-AI Office Assistant",
    description="企业AI智能办公助手：知识库问答 / 会议纪要 / 客户数据管理",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "E-AI Office Assistant",
        "version": "0.1.0",
        "llm_configured": settings.llm_configured,
        "is_admin": settings.is_admin,
    }


app.include_router(kb.router)
app.include_router(chat.router)
app.include_router(meeting.router)
app.include_router(customer.router)
