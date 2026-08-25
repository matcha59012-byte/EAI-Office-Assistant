"""模块A冒烟测试：对运行中的后端做 3 轮完整 API 验证（测试3遍铁律）。

前置：后端已在 127.0.0.1:8000 运行（开发环境 APP_IS_ADMIN=true）。
用法（在 backend 目录、激活 venv 后）：
    python scripts/smoke_test.py
"""
import sys
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
SAMPLE = BACKEND / "sample_data" / "财务报销流程.md"
ROUNDS = 3


def round_test() -> tuple[int, int]:
    passed = 0
    total = 0
    doc_id = None
    session_id = None
    with httpx.Client(base_url=BASE, timeout=180) as c:
        # 1 健康检查
        total += 1
        r = c.get("/api/health")
        if r.status_code == 200 and r.json().get("status") == "ok":
            passed += 1
        else:
            print(f"[health] FAIL {r.status_code}")

        # 2 上传
        total += 1
        r = c.post(
            "/api/kb/upload",
            files={"file": ("报销流程.md", SAMPLE.read_bytes(), "text/markdown")},
        )
        up = r.json()
        if r.status_code == 200 and up.get("id"):
            passed += 1
            doc_id = up["id"]
        else:
            print(f"[upload] FAIL {r.status_code} {up}")

        # 3 文档列表
        total += 1
        r = c.get("/api/kb/documents")
        if r.status_code == 200 and len(r.json()) >= 1:
            passed += 1
        else:
            print(f"[list] FAIL {r.status_code}")

        # 4 文档内容（只读查看）
        total += 1
        r = c.get(f"/api/kb/documents/{doc_id}/content")
        body = r.json()
        if r.status_code == 200 and "发票" in body.get("content", ""):
            passed += 1
        else:
            print(f"[content] FAIL {r.status_code}")

        # 5 新建会话
        total += 1
        r = c.post("/api/kb/sessions", json={"title": "测试会话"})
        s = r.json()
        if r.status_code == 200 and s.get("id"):
            passed += 1
            session_id = s["id"]
        else:
            print(f"[session-create] FAIL {r.status_code} {s}")

        # 6 会话内提问（合法）
        total += 1
        r = c.post(
            f"/api/kb/sessions/{session_id}/messages",
            json={"question": "报销需要提供什么材料？"},
        )
        a = r.json()
        if r.status_code == 200 and not a.get("rejected") and len(a.get("sources", [])) > 0:
            passed += 1
        else:
            print(f"[session-ask] FAIL {r.status_code} {a}")

        # 7 基于当前文档提问（来源必须限定该文档）
        total += 1
        r = c.post(
            f"/api/kb/sessions/{session_id}/messages",
            json={"question": "报销多久内提交？", "doc_id": doc_id},
        )
        a = r.json()
        ok_scope = (
            r.status_code == 200
            and not a.get("rejected")
            and all(s["doc_id"] == doc_id for s in a.get("sources", []))
        )
        if ok_scope:
            passed += 1
        else:
            print(f"[doc-scoped] FAIL {r.status_code} {a}")

        # 8 消息历史
        total += 1
        r = c.get(f"/api/kb/sessions/{session_id}/messages")
        msgs = r.json()
        roles = [m["role"] for m in msgs]
        if r.status_code == 200 and "user" in roles and "assistant" in roles:
            passed += 1
        else:
            print(f"[messages] FAIL {r.status_code} {roles}")

        # 9 无关问题拒答
        total += 1
        r = c.post(f"/api/kb/sessions/{session_id}/messages", json={"question": "今天天气怎么样？"})
        a = r.json()
        if r.status_code == 200 and a.get("rejected") is True:
            passed += 1
        else:
            print(f"[reject] FAIL {a}")

        # 10 单次问答兼容旧接口
        total += 1
        r = c.post("/api/kb/ask", json={"question": "报销需要提供什么材料？"})
        a = r.json()
        if r.status_code == 200 and not a.get("rejected"):
            passed += 1
        else:
            print(f"[ask] FAIL {r.status_code}")

        # 11 删除会话
        total += 1
        r = c.delete(f"/api/kb/sessions/{session_id}")
        if r.status_code == 200 and r.json().get("ok"):
            passed += 1
        else:
            print(f"[session-delete] FAIL {r.text}")

        # 12 删除文档
        total += 1
        r = c.delete(f"/api/kb/documents/{doc_id}")
        if r.status_code == 200 and r.json().get("ok"):
            passed += 1
        else:
            print(f"[delete] FAIL {r.text}")

    return passed, total


def main() -> int:
    all_ok = True
    for i in range(1, ROUNDS + 1):
        passed, total = round_test()
        ok = passed == total
        all_ok = all_ok and ok
        print(f"第{i}轮: {passed}/{total} {'[PASS]' if ok else '[FAIL]'}")
    print("总结果:", "3/3 轮全部通过 [PASS]" if all_ok else "存在失败 [FAIL]")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
