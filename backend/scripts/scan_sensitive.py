"""敏感词扫描：部署/推送前检查仓库是否存在真实企业标识（防数据泄露）。

用法（仓库根目录、任意 Python 3.11）：
    python backend/scripts/scan_sensitive.py
退出码：0=通过（无敏感词）；1=发现敏感词（阻止推送）。

说明：会跳过 `.git/.venv/node_modules/dist/reference` 与二进制文件。
仅允许的例外：docs/ 下的个人简历 HTML（含本人真实就业公司，属个人履历）。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "__pycache__", "reference"}
SKIP_EXT = {".pyc", ".jpg", ".png", ".xlsx", ".db", ".lock"}
# 例外文件：简历 HTML（含本人真实就业单位，属个人履历）、扫描器自身（含敏感词定义）
ALLOWED_FILES = {
    "梁政_简历_求职版.html",
    "梁政_简历_求职版_带项目.html",
    "scan_sensitive.py",
}

PATTERNS = [
    r"博路德", r"SpecWise|SPECWISE|Specwise", r"东篱",
    r"Obsidian-Claude", r"工作经历\.zip",
    r"\bShak\b", r"\bAlex\b", r"\bHarvey\b", r"\bEmilyRz\b", r"\bEmily\b",
    r"\bJackyLin\b", r"\bJacky\b", r"\bDorisLi\b", r"\bDoris\b", r"\bNicole\b",
    r"\bDaisyNie\b", r"\bDaisy\b", r"\bZack\b", r"\bGary\b", r"\bYoung\b",
    r"\bGladys\b", r"\bQueenie\b", r"\bQueenche\b", r"\bJoe\b", r"\bFrank\b",
    r"\bEsther\b", r"\bAndy\b", r"\bSteven\b", r"\bZia\b", r"\bFranco\b",
    r"\bNadi\b", r"\bStephanieYang\b", r"\bRock\b", r"\bLiNa\b", r"\bDanny\b",
    r"\bEddie\b", r"\bDulux\b", r"\bMatrak\b", r"\bAlimak\b", r"\bBlueBeam\b",
    r"\bBG8001\b", r"\bBG0607\b", r"\bBG01\b", r"\bArcherSt\b", r"\bBaiYun\b",
    r"\bMidwater\b", r"\bH202\b", r"\bAURA\b", r"\bBFI\b", r"\bSYNOVA\b",
    r"\bSCCH\b", r"\bTBR\b", r"Mermaid Plaza", r"\bPMU\b", r"\bVMU\b",
    r"\bFIDIC\b", r"\bTrn\b", r"\bProject_R\b",
]
compiled = [re.compile(p) for p in PATTERNS]


def scan_file(path: str) -> list[tuple[int, str]]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(content.splitlines(), 1):
        for rx in compiled:
            m = rx.search(line)
            if m:
                hits.append((i, m.group(0)))
    return hits


def main() -> int:
    hits: list[tuple[str, int, str]] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            if fn == ".env" or fn.startswith(".env."):
                continue
            if fn in ALLOWED_FILES:
                continue
            p = os.path.join(dirpath, fn)
            for ln, token in scan_file(p):
                hits.append((os.path.relpath(p, ROOT), ln, token))
    if hits:
        print(f"FAIL: 发现 {len(hits)} 处敏感词，禁止推送：")
        for rel, ln, token in sorted(set(hits)):
            print(f"  {rel}:{ln}  [{token}]")
        return 1
    print("OK: 未发现敏感词，可以推送")
    return 0


if __name__ == "__main__":
    sys.exit(main())
