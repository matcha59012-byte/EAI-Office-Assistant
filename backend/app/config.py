"""E-AI Office Assistant 后端配置（读 .env）。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（锚定路径，避免受当前工作目录影响）
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 数据库（默认锚定 backend/app.db）
    DATABASE_URL: str = ""

    # 向量库（默认锚定 backend/chroma_data）
    CHROMA_PATH: str = ""

    # 服务
    BACKEND_PORT: int = 8000
    FRONTEND_ORIGIN: str = "http://127.0.0.1:5173"

    # 角色控制：true=管理员（可上传/删除文档），false=员工只读
    APP_IS_ADMIN: bool = False

    # LLM 调用参数
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT: int = 30
    LLM_MAX_RETRIES: int = 2

    # MiMo ASR 配置
    MIMO_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    MIMO_ASR_API_KEYS: str = ""
    MIMO_ASR_MODEL: str = "mimo-v2.5-asr"
    MIMO_ASR_MODE: str = "chat_completions"
    MIMO_ASR_ENDPOINT_PATH: str = "/audio/transcriptions"
    MIMO_ASR_RETRY_ATTEMPTS: int = 3
    MIMO_ASR_TEMPERATURE: float = 0.0
    MIMO_ASR_ALLOWED_MODELS: str = "mimo-v2.5-asr,mimo-v2.5"
    SPEECH_TRANSCRIPTION_PROFILE: str = "mimo-v2.5-audio"

    def model_post_init(self, __context) -> None:
        # 相对路径一律锚定到 backend/，避免因启动目录不同而各建一套数据
        url = self.DATABASE_URL
        if not url:
            self.DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'app.db').as_posix()}"
        elif url.startswith("sqlite:///"):
            rel = url[len("sqlite:///"):]
            p = Path(rel)
            if not p.is_absolute():
                self.DATABASE_URL = f"sqlite:///{(BACKEND_DIR / p).as_posix()}"
        cp = Path(self.CHROMA_PATH)
        if not self.CHROMA_PATH:
            self.CHROMA_PATH = str(BACKEND_DIR / "chroma_data")
        elif not cp.is_absolute():
            self.CHROMA_PATH = str(BACKEND_DIR / cp)

    @property
    def llm_configured(self) -> bool:
        key = self.DEEPSEEK_API_KEY or ""
        return bool(key and key != "sk-xxxx")

    @property
    def is_admin(self) -> bool:
        return bool(self.APP_IS_ADMIN)


settings = Settings()
