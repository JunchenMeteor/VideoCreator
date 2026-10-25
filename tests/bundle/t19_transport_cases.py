"""Actual loopback HTTP, no TestClient/ASGI mock or product top-level import."""
import http.client
import json
import secrets
import socket
import threading
import time


def run_actual_http_negative(ctx):
    from video_creator.api.app import create_app
    import uvicorn

    token = secrets.token_urlsafe(32)  # New own instance session, never logged.
    app = create_app(ctx.engine, token, bundle_service=ctx.bundle)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(64)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False, lifespan="on"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, name="T19-owned-uvicorn")
    thread.start()
    rows = []
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline and thread.is_alive():
            time.sleep(0.01)
        assert server.started and thread.is_alive()
        for authorized, expected in ((False, 401), (True, 404)):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            try:
                headers = {"Authorization": "Bearer " + token} if authorized else {}
                connection.request("GET", "/api/v1/bundles/absent/manifest", headers=headers)
                response = connection.getresponse()
                raw = response.read(65537)
                assert response.status == expected and len(raw) <= 65536
                envelope = ctx.contracts.ErrorEnvelope.model_validate(json.loads(raw))
                assert token.encode() not in raw and envelope.code == ("unauthorized" if not authorized else "not_found")
                rows.append({"status": response.status, "code": envelope.code})
            finally:
                connection.close()
    finally:
        server.should_exit = True
        thread.join(10)
        listener.close()
    assert not thread.is_alive(), "real API thread still owns its listener"
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", port)) != 0
    return {"actual_port": port, "responses": rows, "thread_closed": True, "scope": "real socket HTTP only; not CLI/native/MCP lifecycle"}
