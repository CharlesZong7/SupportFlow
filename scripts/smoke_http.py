"""Launch a temporary loopback server, verify HTTP, and save mock-only evidence."""
import importlib.metadata
import json
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
BASE = {"product": "nimbusdesk", "version": "1.1", "question": "导出 CSV 最多多少行？"}
CASES = [
    ("consultation", BASE, "dev-alice", 200, "answered"),
    ("troubleshooting", {**BASE, "question": "导出超时怎么办？", "symptom": "报表导出 30 秒后超时"},
     "dev-alice", 200, "answered"),
    ("missing_version", {"product": "nimbusdesk", "question": "导出 CSV 怎么用？"},
     "dev-alice", 200, "needs_info"),
    ("no_evidence", {**BASE, "question": "登录超时", "symptom": "登录十秒后超时"},
     "dev-alice", 200, "needs_human"),
    ("ticket_draft", {**BASE, "question": "请创建工单：导出报错"},
     "dev-alice", 200, "awaiting_confirmation"),
    ("forbidden_version", BASE, "dev-bob", 403, None),
    ("unauthenticated", BASE, None, 401, None),
]


def main() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    report = {
        "verified_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "scope": "local HTTP + mock fixtures; no model or external service calls",
        "python": sys.version.split()[0],
        "packages": {name: importlib.metadata.version(name) for name in (
            "fastapi", "pydantic", "uvicorn", "httpx",
        )},
        "cases": [],
    }
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as server_log:
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-m", "uvicorn", "support_app.main:app",
             "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--log-level", "warning"],
            cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2, trust_env=False) as client:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        health = client.get("/health")
                        health.raise_for_status()
                        break
                    except httpx.HTTPError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            server_log.seek(0)
                            raise RuntimeError("local server did not start: " + server_log.read())
                        time.sleep(0.05)
                report["health"] = health.json()
                assert report["health"]["mode"] == "mock"
                home = client.get("/")
                assert home.status_code == 200 and "support-form" in home.text
                assert "<script src=" not in home.text
                schema = client.get("/openapi.json")
                assert schema.status_code == 200 and "/api/support" in schema.json()["paths"]
                report["entrypoint"] = {"home_http": home.status_code, "openapi_http": schema.status_code}
                for name, payload, token, expected_http, expected_state in CASES:
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    response = client.post("/api/support", json=payload, headers=headers)
                    body = response.json()
                    assert response.status_code == expected_http, (name, response.status_code)
                    if expected_state:
                        assert body["status"] == expected_state, (name, body)
                        assert body["mode"] == "mock"
                    report["cases"].append({"case": name, "http_status": response.status_code, "response": body})
                    print(f"{name}: HTTP {response.status_code}, {body.get('status', 'rejected')}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    output = ROOT / "docs" / "validation" / "m0-http.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
