"""Gate0 local HTTP API. Business operations share EngineService with other transports."""

import asyncio
import secrets
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, JSONResponse, StreamingResponse

from video_creator import __version__
from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService, identity
from video_creator.domain.contracts import (
    AssetCandidate,
    AssetRecord,
    CreativeRevision,
    ErrorEnvelope,
    EventEnvelope,
    FeedbackRevision,
    InstanceHealth,
    MediaProbe,
    ProductionAccepted,
    ProductionDetail,
    ProductionRequest,
    ProjectDraft,
    ProjectInput,
    ReviewDecision,
    StagedAsset,
)
from video_creator.domain.errors import EngineError


def create_app(engine: EngineService, token: str, subject: str = "local-user",
               allowed_origins: tuple[str, ...] = (), allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost"),
               media_validator: Callable[[Path, str], MediaProbe] | None = None,
               worker_connected: bool = False, on_ready: Callable[[], None] | None = None) -> FastAPI:
    if len(token) < 32:
        raise EngineError("session_token_missing", "A session token of at least 32 characters is required", 503)
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine.recover()
        if on_ready:
            on_ready()
        yield

    app = FastAPI(title="VideoCreator Engine", version=__version__, docs_url=None, redoc_url=None, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))
    app.add_middleware(CORSMiddleware, allow_origins=list(allowed_origins), allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "If-Match", "Range", "Last-Event-ID"],
                       expose_headers=["ETag", "Accept-Ranges", "Content-Range"])
    assets = AssetService(engine)

    async def authenticate(request: Request, authorization: str | None = Header(default=None)) -> str:
        origin = request.headers.get("origin")
        if origin is not None and origin not in allowed_origins:
            raise EngineError("origin_denied", "Browser origin is not authorized", 403)
        supplied = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else ""
        if not secrets.compare_digest(supplied.encode(), token.encode()):
            raise EngineError("unauthorized", "A valid installation session is required", 401)
        return subject

    @app.exception_handler(EngineError)
    async def engine_error(request: Request, error: EngineError):
        envelope = ErrorEnvelope(code=error.code, message=error.message, retryability=error.retryability, request_id=identity("request"))
        return JSONResponse(envelope.model_dump(mode="json"), status_code=error.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # FastAPI's default error includes raw inputs. Do not reflect credentials or private source text.
        envelope = ErrorEnvelope(code="invalid_request", message="Request does not satisfy the published contract", retryability="never", request_id=identity("request"))
        return JSONResponse(envelope.model_dump(mode="json"), status_code=422)

    @app.get("/api/v1/health", response_model=InstanceHealth)
    def health(actor: str = Depends(authenticate)):
        return InstanceHealth(instance_id=engine.instance_id, engine_version=__version__, worker_connected=worker_connected)

    @app.get("/api/v1/projects", response_model=list[ProjectDraft])
    def projects(actor: str = Depends(authenticate)):
        return engine.list_projects(actor)

    @app.post("/api/v1/projects", response_model=ProjectDraft, status_code=201)
    def project_create(body: ProjectInput, key: str | None = Header(default=None, alias="Idempotency-Key", min_length=1, max_length=128), actor: str = Depends(authenticate)):
        return engine.create_project(actor, body, key)

    @app.get("/api/v1/projects/{project_id}", response_model=ProjectDraft)
    def project_get(project_id: str, response: Response, actor: str = Depends(authenticate)):
        draft = engine.get_project(actor, project_id)
        response.headers["ETag"] = f'"{draft.revision}"'
        return draft

    @app.put("/api/v1/projects/{project_id}", response_model=ProjectDraft)
    def project_update(project_id: str, body: ProjectInput, response: Response,
                       if_match: str = Header(alias="If-Match"), actor: str = Depends(authenticate)):
        try:
            revision = int(if_match.strip('"'))
        except ValueError:
            raise EngineError("invalid_revision", "If-Match must contain a numeric draft revision", 400) from None
        draft = engine.update_project(actor, project_id, revision, body)
        response.headers["ETag"] = f'"{draft.revision}"'
        return draft

    @app.get("/api/v1/productions", response_model=list[ProductionAccepted])
    def production_list(actor: str = Depends(authenticate)):
        return engine.list_productions(actor)

    @app.post("/api/v1/productions", response_model=ProductionAccepted, status_code=202)
    def production_create(body: ProductionRequest, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: str = Depends(authenticate)):
        return engine.accept_production(actor, key, body)

    @app.get("/api/v1/productions/{production_id}", response_model=ProductionDetail)
    def production_get(production_id: str, actor: str = Depends(authenticate)):
        return engine.get_production(actor, production_id)

    @app.post("/api/v1/productions/{production_id}/cancel", response_model=ProductionDetail)
    def production_cancel(production_id: str, actor: str = Depends(authenticate)):
        engine.cancel_production(actor, production_id)
        return engine.get_production(actor, production_id)

    @app.get("/api/v1/productions/{production_id}/revisions", response_model=list[CreativeRevision])
    def production_revisions(production_id: str, actor: str = Depends(authenticate)):
        return engine.creative_revisions(actor, production_id)

    @app.post("/api/v1/runs/{run_id}/decisions", response_model=ReviewDecision | FeedbackRevision)
    def decision_submit(run_id: str, body: ReviewDecision, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: str = Depends(authenticate)):
        return engine.submit_decision(actor, run_id, key, body)

    @app.post("/api/v1/runs/{run_id}/pause")
    def run_pause(run_id: str, actor: str = Depends(authenticate)):
        engine.set_paused(actor, run_id, True)
        return {"run_id": run_id, "paused": True}

    @app.post("/api/v1/runs/{run_id}/resume")
    def run_resume(run_id: str, actor: str = Depends(authenticate)):
        engine.set_paused(actor, run_id, False)
        return {"run_id": run_id, "paused": False}

    @app.get("/api/v1/runs/{run_id}/events", response_model=list[EventEnvelope])
    async def run_events(run_id: str, request: Request, after_sequence: int = Query(default=0, ge=0), actor: str = Depends(authenticate)):
        cursor_header = request.headers.get("last-event-id")
        if cursor_header:
            try:
                after_sequence = max(after_sequence, int(cursor_header))
            except ValueError:
                raise EngineError("invalid_cursor", "Event cursor must be numeric", 400) from None
        initial = engine.events(actor, run_id, after_sequence)
        if "text/event-stream" not in request.headers.get("accept", ""):
            return initial

        async def stream():
            sequence, pending = after_sequence, initial
            while not await request.is_disconnected():
                for event in pending:
                    sequence = event.sequence
                    yield f"id: {sequence}\nevent: {event.event_type}\ndata: {event.model_dump_json()}\n\n"
                if not pending:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(1)
                pending = engine.events(actor, run_id, sequence)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    @app.post("/api/v1/assets/staging", response_model=StagedAsset, status_code=201)
    async def asset_stage(request: Request, actor: str = Depends(authenticate)):
        data = bytearray()
        async for block in request.stream():
            data.extend(block)
            if len(data) > assets.max_bytes:
                raise EngineError("asset_size_denied", "Upload exceeds the configured limit", 413)
        return assets.stage_bytes(actor, bytes(data), request.headers.get("content-type", "application/octet-stream").split(";")[0])

    @app.post("/api/v1/assets/import", response_model=AssetRecord, status_code=201)
    def asset_import(body: AssetCandidate, actor: str = Depends(authenticate)):
        return assets.import_asset(actor, body, media_validator)

    @app.get("/api/v1/assets/{asset_id}", response_model=AssetRecord)
    def asset_get(asset_id: str, actor: str = Depends(authenticate)):
        return assets.get(actor, asset_id)

    @app.get("/api/v1/assets/{asset_id}/content")
    def asset_content(asset_id: str, actor: str = Depends(authenticate)):
        asset = assets.get(actor, asset_id)
        return FileResponse(assets.content_path(actor, asset_id), media_type=asset.media_type,
                            headers={"ETag": f'"{asset.sha256}"', "Cache-Control": "private, no-cache"})

    return app
