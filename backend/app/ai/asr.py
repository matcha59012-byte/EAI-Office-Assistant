"""MiMo ASR 客户端（复用实习期 ASR 实现思路）。

- 鉴权：请求头 `api-key:`（MiMo 不是 Bearer）
- 模式：chat_completions（base64 input_audio）为主，audio_transcriptions（multipart）备选
- 仅支持 wav/mp3：其他音频/视频先用 ffmpeg 转 mp3（单声道 16kHz 64k）
- 大文件：按 300s 分段，段间等待 30s 防限流；429/5xx 指数退避重试
"""
import base64
import json
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings

SUPPORTED_EXTENSIONS = {".wav", ".mp3"}
SUPPORTED_MEDIA = SUPPORTED_EXTENSIONS | {".mp4", ".mov", ".m4a", ".ogg", ".flac", ".avi", ".wmv"}
MAX_RAW_BYTES = 7_000_000
SEGMENT_SECONDS = 300
SEGMENT_INTERVAL = 30.0


def _mime(path: Path) -> str:
    if path.suffix.lower() == ".wav":
        return "audio/wav"
    return "audio/mpeg"


def _data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{_mime(path)};base64,{encoded}"


def _asr_prompt(source_name: str) -> str:
    return (
        "Transcribe the audio verbatim. Output the original spoken words as faithfully as possible. "
        "Do not summarize, interpret, polish, or rewrite. Preserve repetitions, filler words, "
        "mixed Chinese/English, numbers, names, project terms, and uncertain words. "
        "If speech is unclear, write [unclear]. "
        "When speaker turns are obvious, use `[MM:SS] Speaker N: original words`; otherwise keep verbatim text. "
        f"file={source_name}"
    )


def _post(url: str, payload: dict, *, retries: int | None = None) -> dict:
    key = (settings.MIMO_ASR_API_KEYS or "").strip()
    if not key or key.startswith("***"):
        raise RuntimeError("未配置 MIMO_ASR_API_KEYS（MiMo ASR 密钥）")
    attempts = retries or max(1, int(settings.MIMO_ASR_RETRY_ATTEMPTS))
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last: str | None = None
    for attempt in range(1, attempts + 1):
        req = Request(
            url,
            data=body,
            method="POST",
            headers={"api-key": key, "content-type": "application/json"},
        )
        try:
            with urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError(
                    "MiMo API Key 无效或已过期（401），请在 backend/.env 配置有效的 MIMO_ASR_API_KEYS"
                ) from exc
            last = f"ASR HTTP {exc.code}"
            retryable = exc.code in {429, 500, 502, 503, 504}
            if not retryable or attempt >= attempts:
                raise RuntimeError(last) from exc
            time.sleep(min(2 ** (attempt - 1), 30))
        except (TimeoutError, URLError) as exc:
            last = f"ASR 网络失败: {exc}"
            if attempt >= attempts:
                raise RuntimeError(last) from exc
            time.sleep(min(2 ** (attempt - 1), 30))
    raise RuntimeError(last or "ASR 请求失败")


def _extract_text(raw: dict) -> str:
    for key in ("text", "transcript", "content"):
        v = raw.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def _transcribe_chat(path: Path, source_name: str) -> str:
    prompt = _asr_prompt(source_name)
    base = settings.MIMO_BASE_URL.rstrip("/")
    url = base + "/chat/completions"
    payload = {
        "model": settings.MIMO_ASR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "input_audio", "input_audio": {"data": _data_url(path)}},
                ],
            }
        ],
        "asr_options": {"language": "auto", "hotwords": prompt[:256]},
    }
    try:
        raw = _post(url, payload)
    except RuntimeError:
        # 400 时去掉 text prompt 重试
        payload["messages"][0]["content"] = payload["messages"][0]["content"][1:]
        raw = _post(url, payload)
    text = _extract_text(raw)
    if not text:
        raise RuntimeError("ASR 返回空文本")
    return text


def _transcribe_audio_endpoint(path: Path, source_name: str) -> str:
    """multipart /audio/transcriptions（备选模式）。"""
    import uuid

    boundary = f"----EAIASR{uuid.uuid4().hex}"
    url = settings.MIMO_BASE_URL.rstrip("/") + settings.MIMO_ASR_ENDPOINT_PATH
    parts = []
    for name, value in {
        "model": settings.MIMO_ASR_MODEL,
        "language": "auto",
        "prompt": _asr_prompt(source_name),
    }.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(str(value).encode("utf-8"))
        parts.append(b"\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {_mime(path)}\r\n\r\n".encode()
    )
    parts.append(path.read_bytes())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    key = settings.MIMO_ASR_API_KEYS
    req = Request(
        url,
        data=body,
        method="POST",
        headers={"api-key": key, "content-type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urlopen(req, timeout=180) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"ASR HTTP {exc.code}") from exc
    except (TimeoutError, URLError) as exc:
        raise RuntimeError(f"ASR 网络失败: {exc}") from exc
    text = _extract_text(raw)
    if not text:
        raise RuntimeError("ASR 返回空文本")
    return text


def _ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return "ffmpeg"


def _convert_to_mp3(path: Path) -> Path:
    """把非 mp3/wav 媒体转成 mp3（单声道 16kHz 64k）。"""
    target = Path(tempfile.gettempdir()) / f"eai_asr_{path.stem}-{time.time_ns()}.mp3"
    cmd = [
        _ffmpeg_bin(), "-y", "-i", str(path),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(target),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode != 0 or not target.exists() or target.stat().st_size == 0:
        raise RuntimeError(f"音频转换失败: {(r.stderr or r.stdout or '')[-300:]}")
    return target


def _split_segments(mp3_path: Path) -> list[Path]:
    """按 300s 分段。"""
    target_dir = Path(tempfile.gettempdir()) / f"eai_asr_seg_{mp3_path.stem}-{time.time_ns()}"
    target_dir.mkdir(parents=True, exist_ok=True)
    out_pattern = target_dir / "segment-%03d.mp3"
    cmd = [
        _ffmpeg_bin(), "-y", "-i", str(mp3_path),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
        "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
        "-reset_timestamps", "1", str(out_pattern),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"音频分段失败: {(r.stderr or r.stdout or '')[-300:]}")
    segs = sorted(p for p in target_dir.glob("segment-*.mp3") if p.stat().st_size > 0)
    if not segs:
        raise RuntimeError("音频分段为空")
    return segs


def transcribe_media(source_path: Path, source_name: str | None = None) -> str:
    """入口：MP3/MP4 等 → 转写文本（多段则按 ## Segment 拼接）。"""
    path = source_path
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_MEDIA:
        raise RuntimeError(f"不支持的音频格式: {suffix}")
    if suffix not in SUPPORTED_EXTENSIONS:
        path = _convert_to_mp3(path)

    mode = (settings.MIMO_ASR_MODE or "chat_completions").replace("-", "_").lower()
    display = source_name or path.name

    if path.stat().st_size <= MAX_RAW_BYTES:
        text = (
            _transcribe_chat(path, display)
            if mode in {"chat_completions", "chat", "omni", "asr"}
            else _transcribe_audio_endpoint(path, display)
        )
        return text.strip()

    segments = _split_segments(path)
    parts = []
    for i, seg in enumerate(segments, 1):
        if i > 1:
            time.sleep(SEGMENT_INTERVAL)
        t = (
            _transcribe_chat(seg, display)
            if mode in {"chat_completions", "chat", "omni", "asr"}
            else _transcribe_audio_endpoint(seg, display)
        )
        parts.append(f"## Segment {i}/{len(segments)}\n\n{t.strip()}")
    return "\n\n".join(parts)
