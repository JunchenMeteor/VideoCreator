"""Gate0 local HTTP API. Business operations share EngineService with other transports."""

import asyncio
import secrets
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi import Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, JSONResponse, StreamingResponse

from video_creator import __version__
from video_creator.api.development_marker import (
    DEVELOPMENT_INSTALLATION_HEADER,
    DEVELOPMENT_INSTALLATION_VALUE,
    is_development_host,
)
from video_creator.api.transport_contract import (
    content_metadata_for,
    install_transport_contract,
)
from video_creator.application.assets import AssetService
from video_creator.application.bundles import BundleService, InstancePrincipalRegistry
from video_creator.application.engine import EngineService, identity
from video_creator.application.product_authorization import (
    AUTHORIZATION_HEADER,
    HEALTH_HEADER,
    AuthorizationDecision,
    LocalEvidencePolicyRequest,
    ProductAuthorizationChannel,
)
from video_creator.application.worker import WorkerService
from video_creator.domain import contracts as c
from video_creator.domain import local_copy_input_scope as copy_contracts
from video_creator.domain.bundle import AccessContext, TrustedBundleValidators
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
    ProductionRequestAny,
    ProjectDraft,
    ProjectInput,
    ReviewDecision,
    StagedAsset,
)
from video_creator.domain.daily_project_authorization import (
    ProjectGoalAccepted,
    ProjectGoalInput,
    ProjectGoalReceiptAssociationV1,
    ProjectGoalReceiptQueryV1,
)
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.origins import startup_origins

# Domain failures and request validation share the existing public model.
# TrustedHost/CORS and malformed media Range requests may instead return text.
ERROR_RESPONSES = {
    400: {
        "model": ErrorEnvelope,
        "description": "Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text)",
        "content": {"text/plain": {"schema": {"type": "string"}}},
    },
    401: {"model": ErrorEnvelope, "description": "Installation session is invalid"},
    403: {"model": ErrorEnvelope, "description": "Installation permission or browser origin is denied"},
    404: {"model": ErrorEnvelope, "description": "Owned resource does not exist"},
    409: {"model": ErrorEnvelope, "description": "Version, idempotency or execution state conflicts; inspect retryability"},
    413: {"model": ErrorEnvelope, "description": "Asset upload exceeds the configured limit"},
    415: {"model": ErrorEnvelope, "description": "Identified media format or media reference is not supported by installation policy"},
    422: {"model": ErrorEnvelope, "description": "Request contract, content integrity or media decoding is invalid"},
    503: {"model": ErrorEnvelope, "description": "Required installation resource or media validator is unavailable"},
}


def create_app(engine: EngineService, token: str, subject: str = "local-user",
               allowed_origins: tuple[str, ...] = (), allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost"),
               media_validator: Callable[[Path, str], MediaProbe] | None = None,
               worker_connected: bool = False, on_ready: Callable[[], None] | None = None,
               is_stopping: Callable[[], bool] | None = None,
               on_shutdown: Callable[[], None] | None = None,
               bundle_service: BundleService | None = None,
               principal_registry: InstancePrincipalRegistry | None = None,
               copy_input_service=None,
               authorization_channel: ProductAuthorizationChannel | None = None,
               authorization_state: str | None = None,
               restricted: bool = False) -> FastAPI:
    if len(token) < 32:
        raise EngineError("session_token_missing", "A session token of at least 32 characters is required", 503)
    if authorization_channel is not None and (
            type(authorization_channel) is not ProductAuthorizationChannel
            or authorization_channel.engine is not engine):
        raise EngineError('product_authorization_configuration_conflict',
                          'The authorization channel must belong to this exact Engine instance', 503)
    if authorization_state is not None and authorization_state != 'none':
        raise EngineError('product_authorization_configuration_conflict',
                          'The only externally fixed authorization state is none', 503)
    if type(restricted) is not bool or (restricted and authorization_channel is None):
        raise EngineError('product_authorization_configuration_conflict',
                          'A restricted process requires its actual authorization channel', 503)
    allowed_origins = startup_origins(allowed_origins)
    bundles = bundle_service or BundleService(engine, TrustedBundleValidators(media_validator=media_validator),
                      principal_registry or InstancePrincipalRegistry(engine.instance_id, subject))
    if bundles.engine is not engine or bundles.principals.instance_id != engine.instance_id or bundles.principals.owner_subject != subject:
        raise EngineError("bundle_configuration_conflict", "Bundle service must bind this exact engine and configured installation owner", 503)
    if copy_input_service is not None:
        if copy_input_service.bundle is not bundles:
            raise EngineError('local_copy_configuration_conflict', 'Management/source resolver must use this actual protected Bundle service', 503)
        engine.configure_local_copy_inputs(copy_input_service)
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # A restricted process has no execution capability: it neither recovers
        # run state nor starts bundle export work. Only the consent surface runs.
        if not restricted:
            engine.recover()
            bundles.start_exports()
        if on_ready:
            on_ready()
        yield
        if not restricted:
            bundles.stop_exports()
        if on_shutdown:
            # Only normal lifespan completion reaches this internal callback.
            on_shutdown()

    app = FastAPI(title="VideoCreator Engine", version=__version__, docs_url=None, redoc_url=None,
                  lifespan=lifespan, responses=ERROR_RESPONSES)
    if restricted:
        async def authorization_only(request: Request, call_next):
            # No Owner binding yet: only health and the authorization channel are
            # addressable. This is "not authorized" (403), not "unavailable".
            path = request.url.path
            if path == '/api/v1/health' or path.startswith('/api/v1/authorization/'):
                return await call_next(request)
            envelope = ErrorEnvelope(code='owner_authorization_required',
                                     message='This installation has no Owner authorization yet; only health and the '
                                             'authorization channel are available',
                                     retryability='never', request_id=identity('request'))
            return JSONResponse(envelope.model_dump(mode='json'), status_code=403)
        app.middleware('http')(authorization_only)
    app.add_middleware(CORSMiddleware, allow_origins=list(allowed_origins), allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "If-Match", "If-None-Match", "Range", "Last-Event-ID"],
                       expose_headers=["ETag", "Accept-Ranges", "Content-Range", "Content-Length", "Content-Disposition"])
    # Host validation also precedes a CORS preflight response.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))
    assets = AssetService(engine)
    app.state.bundle_service = bundles

    async def authenticate(request: Request, authorization: str | None = Header(default=None)) -> str:
        origin = request.headers.get("origin")
        if origin is not None and origin not in allowed_origins:
            raise EngineError("origin_denied", "Browser origin is not authorized", 403)
        supplied = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else ""
        if not secrets.compare_digest(supplied.encode(), token.encode()):
            raise EngineError("unauthorized", "A valid installation session is required", 401)
        return subject

    async def access(request: Request, authorization: str | None = Header(default=None)) -> AccessContext:
        origin = request.headers.get("origin")
        if origin is not None and origin not in allowed_origins:
            raise EngineError("origin_denied", "Browser origin is not authorized", 403)
        supplied = authorization.removeprefix("Bearer ") if authorization and authorization.startswith("Bearer ") else ""
        if secrets.compare_digest(supplied.encode(), token.encode()):
            return bundles.principals.owner()
        return bundles.principals.authenticate(supplied, engine.clock())

    access_dependency = Depends(access)

    def configured_copy_service():
        service = getattr(engine, 'local_copy_inputs', None)
        if service is None or service.bundle is not bundles:
            raise EngineError('local_copy_management_unconfigured', 'Trusted local copy management/source wiring is not configured', 503)
        return service

    async def management_access(request: Request, authorization: str | None = Header(default=None)):
        origin = request.headers.get('origin')
        if origin is not None and origin not in allowed_origins:
            raise EngineError('origin_denied', 'Browser origin is not authorized', 403)
        supplied = authorization.removeprefix('Bearer ') if authorization and authorization.startswith('Bearer ') else ''
        if not supplied or secrets.compare_digest(supplied.encode(), token.encode()):
            raise EngineError('production_management_denied', 'A distinct actual Owner management credential is required', 403)
        return configured_copy_service().authenticate_management(supplied.encode('utf-8'))

    management_dependency = Depends(management_access)

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
    def health(response: Response, actor: str = Depends(authenticate)):
        # A compatibility boolean is no longer evidence that a worker exists.
        if is_development_host():
            # Process-internal development binding only; not declared in OpenAPI.
            response.headers[DEVELOPMENT_INSTALLATION_HEADER] = DEVELOPMENT_INSTALLATION_VALUE
        if authorization_channel is not None and restricted:
            # Runtime-only fact; deliberately not part of the health model or OpenAPI.
            response.headers[HEALTH_HEADER] = authorization_channel.authorization_state
        elif authorization_channel is not None or authorization_state == 'none':
            # A normally assembled process is the stable `none` state; the
            # evidence-authorization channel does not change that fact.
            response.headers[HEALTH_HEADER] = 'none'
        return InstanceHealth(instance_id=engine.instance_id, schema_version=c.CONTRACT_SET_VERSION, engine_version=__version__,
                              worker_connected=WorkerService(engine).connected())

    if authorization_channel is not None:
        def authorization_origin(request: Request) -> str | None:
            origin = request.headers.get('origin')
            if origin is not None and origin not in allowed_origins:
                raise EngineError('origin_denied', 'Browser origin is not authorized', 403)
            fetch_site = request.headers.get('sec-fetch-site')
            if fetch_site is not None and fetch_site != 'same-origin':
                raise EngineError('origin_denied', 'Authorization requires a same-origin request', 403)
            return origin

        def authorization_secret(
                x_videocreator_authorization: str | None = Header(
                    default=None, alias=AUTHORIZATION_HEADER)) -> str:
            return x_videocreator_authorization or ''

        secret_dependency = Depends(authorization_secret)

        # Authorization routes are installation-session endpoints, not a published
        # contract: they stay out of OpenAPI and out of the CORS allowlist. Their
        # only decision methods are POST; no GET can decide anything.
        @app.get('/api/v1/authorization/pending', include_in_schema=False)
        def authorization_pending(request: Request, response: Response,
                                  actor: str = Depends(authenticate), secret: str = secret_dependency):
            authorization_origin(request)
            response.headers['Cache-Control'] = 'no-store'
            return authorization_channel.pending(secret=secret)

        @app.get('/api/v1/authorization/{authorization_id}', include_in_schema=False)
        def authorization_get(authorization_id: str, request: Request, response: Response,
                              actor: str = Depends(authenticate), secret: str = secret_dependency):
            authorization_origin(request)
            response.headers['Cache-Control'] = 'no-store'
            return authorization_channel.get(authorization_id, secret=secret)

        @app.post('/api/v1/authorization/{authorization_id}/approve', include_in_schema=False)
        def authorization_approve(authorization_id: str, body: AuthorizationDecision, request: Request,
                                  response: Response, actor: str = Depends(authenticate),
                                  secret: str = secret_dependency):
            origin = authorization_origin(request)
            response.headers['Cache-Control'] = 'no-store'
            return authorization_channel.approve(authorization_id, body, secret=secret, origin=origin,
                                                 fetch_site=request.headers.get('sec-fetch-site'))

        @app.post('/api/v1/authorization/{authorization_id}/deny', include_in_schema=False)
        def authorization_deny(authorization_id: str, body: AuthorizationDecision, request: Request,
                               response: Response, actor: str = Depends(authenticate),
                               secret: str = secret_dependency):
            origin = authorization_origin(request)
            response.headers['Cache-Control'] = 'no-store'
            return authorization_channel.deny(authorization_id, body, secret=secret, origin=origin,
                                              fetch_site=request.headers.get('sec-fetch-site'))

        @app.post('/api/v1/authorization/local-evidence-policy', include_in_schema=False)
        def authorization_local_evidence(body: LocalEvidencePolicyRequest, request: Request,
                                         response: Response, actor: str = Depends(authenticate),
                                         secret: str = secret_dependency):
            authorization_origin(request)
            response.headers['Cache-Control'] = 'no-store'
            return authorization_channel.request_local_evidence_policy(body.project_id, secret=secret)

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

    @app.post("/api/v1/productions", response_model=ProductionAccepted, status_code=202,
              description=(
                  "Accept a production or recover its original receipt by replaying the saved request and Idempotency-Key. "
                  "The key is scoped to this installation and the currently authenticated subject. For acceptances recorded "
                  "by this implementation, the same canonical Pydantic input returns the immutable original ProductionAccepted "
                  "with HTTP 202, including its original Run and acceptance-time status, even after feedback creates a new Run. "
                  "JSON whitespace, object-key order and serializer-equivalent omitted defaults do not change canonical input. "
                  "Different canonical input with the same key returns idempotency_conflict/409 and never replaces that receipt. "
                  "Historical acceptances without a receipt journal retain their original event-bound Run identity and return "
                  "that Run's current status; their original returned status is unavailable. Invalid or inconsistent acceptance "
                  "records return acceptance_record_invalid/422, never a new production. Current credential, operation, purpose "
                  "and project permissions are required on every replay. A revoked or expired credential or denied scope cannot "
                  "recover a receipt, and its error does not prove that a prior request was never accepted. Replaying a committed "
                  "acceptance does not resume execution, approve a revision, resolve unknown provider acceptance/cost, create an "
                  "Operation or reset a budget. First acceptance commits the production, original Run, event and receipt in one "
                  "transaction; replay after an uncommitted failure may perform that first acceptance. Use status_path to read "
                  "current production progress; the acceptance snapshot is not current execution permission. Task-list similarity "
                  "is not recovery evidence."
              ))
    def production_create(body: ProductionRequestAny, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: AccessContext = access_dependency):
        return bundles.create_production(actor, key, body)

    @app.post('/api/v1/project-goals', response_model=ProjectGoalAccepted, status_code=202,
              operation_id='create_project_goal',
              description='Accept one canonical Goal under an actual previously installed bounded Owner creation delegation. '
              'Creates the real Project, exact child scope and original Production/Run atomically. Same authenticated principal, '
              'key and canonical Goal replay the immutable original receipt; a different Goal conflicts. Disconnect does not '
              'cancel production. A locator, ordinary token or Goal never installs a delegation or resource qualification.')
    def create_project_goal(body: ProjectGoalInput, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=128),
                            actor: AccessContext = access_dependency):
        return bundles.create_project_goal(actor, key, body, entry='api')

    @app.post('/api/v1/project-goals/receipt-lookup', response_model=ProjectGoalReceiptAssociationV1,
              status_code=200, operation_id='lookup_project_goal_receipt',
              description='Read the original authenticated principal/key/canonical Goal association without accepting, recovering or reserving production.')
    def lookup_project_goal_receipt(body: ProjectGoalReceiptQueryV1, response: Response,
                                    actor: AccessContext = access_dependency):
        result = bundles.lookup_project_goal_receipt(actor, body)
        response.headers['Cache-Control'] = 'no-store'
        return result

    @app.get("/api/v1/productions/{production_id}", response_model=ProductionDetail)
    def production_get(production_id: str, actor: AccessContext = access_dependency):
        return bundles.production(actor, production_id)

    @app.post("/api/v1/productions/{production_id}/cancel", response_model=ProductionDetail)
    def production_cancel(production_id: str, actor: str = Depends(authenticate)):
        engine.cancel_production(actor, production_id)
        return engine.get_production(actor, production_id)

    @app.get("/api/v1/productions/{production_id}/revisions", response_model=list[CreativeRevision])
    def production_revisions(production_id: str, actor: str = Depends(authenticate)):
        return engine.creative_revisions(actor, production_id)

    @app.post("/api/v1/runs/{run_id}/decisions", response_model=ReviewDecision | FeedbackRevision)
    def decision_submit(run_id: str, body: ReviewDecision, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: AccessContext = access_dependency):
        return bundles.decision(actor, run_id, key, body)

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
            while not (is_stopping and is_stopping()) and not await request.is_disconnected():
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

    def metadata_input(request, purpose=False):
        allowed = {"purpose"} if purpose else set()
        if (set(request.query_params) - allowed or len(request.query_params.getlist("purpose")) > 1
                or any(name in request.headers for name in ("range", "if-range", "if-none-match", "if-modified-since"))
                or request.headers.get("content-length", "0") != "0" or "transfer-encoding" in request.headers):
            raise EngineError("metadata_request_invalid", "Metadata accepts only its exact declared IDs and effective purpose; no body, range or condition", 400)

    def actual_asset(actor, asset_id):
        record = assets.get(actor, asset_id)
        path = assets.content_path(actor, asset_id)
        if path.stat().st_size != record.size:
            raise EngineError("object_unavailable", "Content object changed after its checked Asset record", 503)
        return record, path

    def bundle_metadata(method, *values):
        # Stage gap: the current expiry/license fact resolution requires the
        # independent Architecture decision. This is explicitly unavailable,
        # never a ready record or null expiry inferred from missing facts.
        callback = getattr(bundles, method, None)
        if callback is None:
            raise EngineError("delivery_metadata_facts_unavailable", "Current authorized expiry and license fact resolution is not implemented", 503)
        return callback(*values)

    @app.get("/api/v1/assets/{asset_id}/content", responses={
        416: {"description": "Requested byte range is not satisfiable (Starlette transport response)",
              "content": {"text/plain": {"schema": {"type": "string"}}}},
    })
    def asset_content(asset_id: str, actor: str = Depends(authenticate)):
        asset, path = actual_asset(actor, asset_id)
        return FileResponse(path, media_type=asset.media_type,
                            headers={"ETag": f'"{asset.sha256}"', "Cache-Control": "private, no-cache"})

    @app.get("/api/v1/assets/{asset_id}/content/metadata", response_model=c.DeliveryContentMetadata)
    @content_metadata_for(asset_content)
    def asset_content_metadata(asset_id: str, request: Request, actor: str = Depends(authenticate)):
        metadata_input(request)
        record, _path = actual_asset(actor, asset_id)
        return c.DeliveryContentMetadata(local_instance_id=engine.instance_id,
            locator=c.AssetContentLocator(asset_id=record.asset_id), sha256=record.sha256,
            size=record.size, media_type=record.media_type,
            purpose_binding=c.InstallationOwnerPurpose(), checked_at_us=engine.clock(), authorization_expires_at_us=None)

    def protected_file(handle, request):
        headers = {"ETag": f'"{handle.sha256}"', "Cache-Control": "private, no-cache"}
        # Authorization and actual integrity ran before conditional/range handling.
        if request.headers.get("if-none-match") == headers["ETag"]:
            return Response(status_code=304, headers=headers)
        return FileResponse(handle.path, media_type=handle.media_type, headers=headers)

    range_responses = {416: {"description": "Unsatisfiable byte range (plain-text transport response)", "content": {"text/plain": {"schema": {"type": "string"}}}}}

    @app.get("/api/v1/bundles/{revision_id}/manifest", response_model=c.BundleManifestAny, responses=range_responses)
    def bundle_get(revision_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        return protected_file(bundles.manifest_content(actor, revision_id, purpose), request)

    @app.get("/api/v1/bundles/{revision_id}/manifest/metadata", response_model=c.DeliveryContentMetadata)
    @content_metadata_for(bundle_get)
    def bundle_manifest_metadata(revision_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        metadata_input(request, True)
        return bundle_metadata("manifest_metadata", actor, revision_id, purpose)

    @app.get("/api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content", responses=range_responses)
    def bundle_content(revision_id: str, artifact_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        return protected_file(bundles.content(actor, revision_id, artifact_id, purpose), request)

    @app.get("/api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content/metadata", response_model=c.DeliveryContentMetadata)
    @content_metadata_for(bundle_content)
    def bundle_artifact_metadata(revision_id: str, artifact_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        metadata_input(request, True)
        return bundles.content_metadata(actor, revision_id, artifact_id, purpose)

    @app.get("/api/v1/bundles/{revision_id}/semantic-segments", response_model=c.SemanticPage)
    def bundle_semantic(revision_id: str, cursor: str | None = None, limit: int = Query(default=50, ge=1, le=100), actor: AccessContext = access_dependency):
        return bundles.semantic_page(actor, revision_id, cursor, limit)

    @app.post("/api/v1/bundles/{revision_id}/exports", response_model=c.BundleExportAccepted, status_code=202)
    def bundle_export(revision_id: str, body: c.BundleExportRequest, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: AccessContext = access_dependency):
        return bundles.request_export(actor, revision_id, key, body)

    @app.get("/api/v1/bundle-exports/{export_id}", response_model=c.BundleExportAccepted)
    def bundle_export_status(export_id: str, actor: AccessContext = access_dependency):
        return bundles.export_status(actor, export_id)

    @app.get("/api/v1/bundle-exports/{export_id}/content", responses=range_responses)
    def bundle_export_content(export_id: str, request: Request, actor: AccessContext = access_dependency):
        return protected_file(bundles.export_content(actor, export_id), request)

    @app.get("/api/v1/bundle-exports/{export_id}/content/metadata", response_model=c.DeliveryContentMetadata)
    @content_metadata_for(bundle_export_content)
    def bundle_export_metadata(export_id: str, request: Request, actor: AccessContext = access_dependency):
        metadata_input(request)
        return bundle_metadata("export_metadata", actor, export_id)

    @app.post("/api/v1/bundles/{revision_id}/grants", response_model=c.BundleReferenceGrant, status_code=201)
    def bundle_grant(revision_id: str, body: c.BundleGrantRequest, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: AccessContext = access_dependency):
        return bundles.create_grant(actor, revision_id, key, body)

    @app.post("/api/v1/bundle-grants/{grant_id}/revoke", response_model=c.BundleReferenceGrant)
    def bundle_revoke(grant_id: str, actor: AccessContext = access_dependency):
        return bundles.revoke_grant(actor, grant_id)

    @app.post("/api/v1/bundle-imports", response_model=c.BundleImportReceiptAny, status_code=201)
    def bundle_import(body: c.BundleImportRequest, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: AccessContext = access_dependency):
        return bundles.import_bundle(actor, key, body)

    @app.get("/api/v1/bundle-imports/{import_id}", response_model=c.BundleImportReceiptAny)
    def bundle_import_get(import_id: str, actor: AccessContext = access_dependency):
        return bundles.import_status(actor, import_id)

    @app.get("/api/v1/bundle-imports/{import_id}/manifest", response_model=c.BundleManifestAny, responses=range_responses)
    def bundle_import_manifest(import_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        return protected_file(bundles.import_manifest_content(actor, import_id, purpose), request)

    @app.get("/api/v1/bundle-imports/{import_id}/manifest/metadata", response_model=c.DeliveryContentMetadata)
    @content_metadata_for(bundle_import_manifest)
    def bundle_import_manifest_metadata(import_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        metadata_input(request, True)
        return bundle_metadata("import_manifest_metadata", actor, import_id, purpose)

    @app.get("/api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content", responses=range_responses)
    def bundle_import_content(import_id: str, artifact_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        return protected_file(bundles.import_content(actor, import_id, artifact_id, purpose), request)

    @app.get("/api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content/metadata", response_model=c.DeliveryContentMetadata)
    @content_metadata_for(bundle_import_content)
    def bundle_import_artifact_metadata(import_id: str, artifact_id: str, request: Request, purpose: c.UsePurpose = "playback", actor: AccessContext = access_dependency):
        metadata_input(request, True)
        return bundle_metadata("import_content_metadata", actor, import_id, artifact_id, purpose)

    @app.post("/api/v1/bundle-imports/{import_id}/exports", response_model=c.BundleExportAccepted, status_code=202)
    def bundle_import_export(import_id: str, body: c.BundleExportRequest, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128), actor: AccessContext = access_dependency):
        return bundles.request_import_export(actor, import_id, key, body)

    @app.post('/api/v1/local-copy-input-scopes/preview', response_model=copy_contracts.LocalCopyInputScope)
    def local_copy_scope_preview(body: copy_contracts.PreviewLocalCopyInputScope, capability=management_dependency):
        return configured_copy_service().preview(capability, body)

    @app.post('/api/v1/local-copy-input-scopes/install', response_model=copy_contracts.LocalCopyInputActionReceipt)
    def local_copy_scope_install(body: copy_contracts.InstallLocalCopyInputScope,
            key: str = Header(alias='Idempotency-Key', min_length=1, max_length=128), capability=management_dependency):
        return configured_copy_service().install_scope(capability, key, body)

    @app.post('/api/v1/local-copy-input-scopes/select', response_model=copy_contracts.LocalCopyInputActionReceipt)
    def local_copy_scope_select(body: copy_contracts.SelectLocalCopyInputScope,
            key: str = Header(alias='Idempotency-Key', min_length=1, max_length=128), capability=management_dependency):
        return configured_copy_service().select_scope(capability, key, body)

    @app.post('/api/v1/local-copy-input-scopes/revoke', response_model=copy_contracts.LocalCopyInputActionReceipt)
    def local_copy_scope_revoke(body: copy_contracts.RevokeLocalCopyInputScope,
            key: str = Header(alias='Idempotency-Key', min_length=1, max_length=128), capability=management_dependency):
        return configured_copy_service().revoke_scope(capability, key, body)

    @app.get('/api/v1/local-copy-input-scopes/{scope_id}/revisions/{revision}', response_model=copy_contracts.LocalCopyInputScopeRecord)
    def local_copy_scope_get(scope_id: c.Identifier, content_sha256: c.Sha256,
            revision: int = ApiPath(gt=0), capability=management_dependency):
        ref = copy_contracts.LocalCopyInputScopeRef(scope_id=scope_id, revision=revision, content_sha256=content_sha256)
        return configured_copy_service().get_scope(capability, ref)

    @app.post('/api/v1/local-copy-input-scopes/bind-request', response_model=copy_contracts.LocalCopyInputActionReceipt)
    def local_copy_scope_bind(body: copy_contracts.BindLocalCopyInputScope,
            key: str = Header(alias='Idempotency-Key', min_length=1, max_length=128), capability=management_dependency):
        return configured_copy_service().bind_existing(capability, key, body)

    install_transport_contract(app, allowed_hosts=allowed_hosts, allowed_origins=allowed_origins,
                               upload_max_bytes=assets.max_bytes)
    return app
