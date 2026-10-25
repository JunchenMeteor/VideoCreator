"""Run the real engine CLI over loopback HTTP, without any model request."""

from __future__ import annotations

import argparse
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
from pathlib import Path

import httpx


def probe(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=False)
    token = secrets.token_urlsafe(48)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("VIDEO_CREATOR_SECRET_")}
    environment["VIDEO_CREATOR_API_TOKEN"] = token
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "services" / "engine" / "src")
    command = [sys.executable, "-m", "video_creator.cli.main", "serve", "--data-dir", str(root),
               "--port", "0", "--allowed-origin", "http://127.0.0.1:1420"]
    process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding="utf-8")
    lines = queue.Queue()
    reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
    reader.start()
    output = {"transport": "real_cli_loopback_http", "provider_calls": 0, "media_generated": False}
    try:
        line = lines.get(timeout=20)
        ready = json.loads(line)
        if ready.get("event") != "ready":
            raise AssertionError("CLI did not return actual ready handshake")
        output["ready"] = ready["event"]
        with httpx.Client(base_url=ready["base_url"], timeout=10, trust_env=False,
                          headers={"Authorization": "Bearer " + token}) as client:
            output["health_status"] = client.get("/api/v1/health").status_code
            payload = {"goal": "测试资料：只验证任务受理，不调用模型", "inputs": {"source_text": "公开自造样本"}}
            first = client.post("/api/v1/productions", json=payload, headers={"Idempotency-Key": "runtime-one"})
            second = client.post("/api/v1/productions", json=payload, headers={"Idempotency-Key": "runtime-one"})
            conflict = client.post("/api/v1/productions", json={"goal": "不同输入"}, headers={"Idempotency-Key": "runtime-one"})
            output["production_status"] = first.status_code
            output["repeat_status"] = second.status_code
            output["same_production_and_run"] = (first.json()["production_id"], first.json()["run_id"]) == (second.json()["production_id"], second.json()["run_id"])
            output["different_input_status"] = conflict.status_code
            output["state"] = first.json()["status"]
            output["bad_origin_status"] = client.get("/api/v1/health", headers={"Origin": "https://unauthorized.invalid"}).status_code
            output["bad_host_status"] = client.get("/api/v1/health", headers={"Host": "unauthorized.invalid"}).status_code
            fake = "sk-" + "T1FakeSecretOnly" * 4
            invalid = client.post("/api/v1/productions", json={"goal": fake, "api_key": fake}, headers={"Idempotency-Key": "invalid-secret"})
            output["invalid_secret_status"] = invalid.status_code
            output["invalid_response_contains_fake_secret"] = fake in invalid.text
            event_response = client.get(first.json()["events_path"])
            output["event_count"] = len(event_response.json())
        with httpx.Client(base_url=ready["base_url"], timeout=10, trust_env=False) as client:
            output["unauthorized_status"] = client.get("/api/v1/health").status_code
        expected = {"health_status": 200, "production_status": 202, "repeat_status": 202,
                    "same_production_and_run": True, "different_input_status": 409,
                    "bad_origin_status": 403, "bad_host_status": 400, "invalid_secret_status": 422,
                    "invalid_response_contains_fake_secret": False, "unauthorized_status": 401, "state": "queued"}
        for key, value in expected.items():
            if output.get(key) != value:
                raise AssertionError(f"Actual CLI HTTP check failed: {key}")
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
        output["session_token_in_stdout_or_stderr"] = token in stdout or token in stderr
        output["child_stopped"] = process.poll() is not None
    if output["session_token_in_stdout_or_stderr"]:
        raise AssertionError("Session credential leaked into child logs")
    (root.parent / (root.name + "Receipt.json")).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.data_dir), ensure_ascii=False))
