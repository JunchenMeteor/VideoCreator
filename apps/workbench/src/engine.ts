import { ApiError, createApiClient } from '@video-creator/api-client';
import type { ApiResponse, components, RequestArguments, RouteKey } from '@video-creator/api-client';

export type Schemas = components['schemas'];
export type ProjectDraft = Schemas['ProjectDraft'];
export type ProjectInput = Schemas['ProjectInput'];
export type ProductionDetail = Schemas['ProductionDetail'];
export type ProductionAccepted = Schemas['ProductionAccepted'];
export type ProductionInput = RequestArguments<'POST /api/v1/productions'>['body'];
export type CreativeRevision = Schemas['CreativeRevision'];
export type EngineEvent = Schemas['EventEnvelope'];
export type AssetRecord = Schemas['AssetRecord'];
export type ErrorEnvelope = Schemas['ErrorEnvelope'];
export type ProjectGoalInput = Schemas['ProjectGoalInput'];
export type ProjectGoalAccepted = Schemas['ProjectGoalAccepted'];
export type SubmissionIdentity = { readonly instanceId: string; readonly principalId: string };
let submissionIdentity: SubmissionIdentity | undefined;
export function getSubmissionIdentity(): SubmissionIdentity | undefined { return submissionIdentity; }

// Installed by the trusted application bootstrap. No user/model key or fabricated
// bearer is accepted here. A missing bootstrap leaves delivery safely unavailable.
type EngineClient = ReturnType<typeof createApiClient>;
let configuredClient: EngineClient | undefined;
let configuredContent: (<K extends RouteKey>(key: K, args: RequestArguments<K>) => Promise<Response>) | undefined;
// Private UI lifetime association. A fresh object is issued even when the same
// client/instance returns; it conveys no instance permission or native authority.
export type EngineConnectionContext = Readonly<{ epoch: number; identity?: SubmissionIdentity }>;
let connectionEpoch = 0;
let connectionContext: EngineConnectionContext | null = null;
const connectionListeners = new Set<() => void>();
export const getEngineConnectionContext = () => connectionContext;
export const subscribeEngineConnection = (listener: () => void) => {
  connectionListeners.add(listener); return () => { connectionListeners.delete(listener); };
};
export function isEngineConnectionCurrent(context: EngineConnectionContext | null): context is EngineConnectionContext {
  return context !== null && context === connectionContext && configuredClient !== undefined;
}
function assertEngineConnection(context: EngineConnectionContext): void {
  if (!isEngineConnectionCurrent(context)) throw new RequestFailure(409, 'material_connection_changed', undefined, undefined, 'not_sent');
}
export function configureEngineConnection(client: EngineClient, content: NonNullable<typeof configuredContent>, identity?: SubmissionIdentity): () => void {
  submissionIdentity = identity ? Object.freeze({ ...identity }) : undefined;
  configuredClient = client; configuredContent = content;
  const installed = Object.freeze({ epoch: ++connectionEpoch, identity: submissionIdentity });
  connectionContext = installed; connectionListeners.forEach(listener => listener());
  return () => { if (connectionContext === installed) {
    configuredClient = undefined; configuredContent = undefined; submissionIdentity = undefined;
    connectionContext = null; connectionListeners.forEach(listener => listener());
  } };
}
// Called by the runtime bootstrap after it has validated that the origin is the
// exact loopback page origin (launcher boot descriptor or the page itself).
export function bootstrapManagedWorkbench(trustedOrigin: string): () => void {
  const client = createApiClient({ mode: 'managed-proxy', baseUrl: trustedOrigin, trustedOrigin });
  return configureEngineConnection(client, client.requestRaw);
}
function transportFailure(failure: unknown): unknown {
  if (!(failure instanceof ApiError)) return failure;
  const value = isErrorEnvelope(failure.payload) ? failure.payload : undefined;
  // A structured client rejection can prove non-acceptance. A gateway failure,
  // conflict, transport exception, incomplete ACK or reconcile cannot prove it.
  const rejectionStatuses: Record<string, readonly number[]> = {
    invalid_request: [400, 422], unauthorized: [401], local_proxy_denied: [403],
    input_asset_denied: [403], budget_unauthorized: [403], unsupported_bundle_version: [415],
  };
  const rejected = value?.retryability === 'never'
    && rejectionStatuses[value.code]?.includes(failure.status);
  return new RequestFailure(failure.status, value?.code ?? 'request_failed', value?.retryability, value?.request_id, rejected ? 'rejected' : 'unknown');
}
export async function engineRequest<K extends RouteKey>(key: K, args: RequestArguments<K>, context?: EngineConnectionContext): Promise<ApiResponse<K>> {
  if (context) assertEngineConnection(context);
  if (!configuredClient) throw new RequestFailure(503, 'trusted_connection_missing', undefined, undefined, 'not_sent');
  try { return await configuredClient.request(key, args); } catch (failure) { throw transportFailure(failure); }
}
export async function engineData<K extends RouteKey>(key: K, args: RequestArguments<K>, context?: EngineConnectionContext): Promise<NonNullable<ApiResponse<K>['data']>> {
  const response = await engineRequest(key, args, context);
  if (response.data === undefined) throw new RequestFailure(502, 'response_unavailable');
  return response.data as NonNullable<ApiResponse<K>['data']>;
}
export async function engineContent<K extends RouteKey>(key: K, args: RequestArguments<K>, context?: EngineConnectionContext): Promise<Response> {
  if (context) assertEngineConnection(context);
  if (!configuredContent) throw new RequestFailure(503, 'trusted_connection_missing');
  try {
    const response = await configuredContent(key, args);
    if (response.status === 200 && !response.headers.has('Content-Range')) return response;
    if (response.status === 206 || response.status === 304) throw new RequestFailure(response.status, 'complete_content_required');
    let envelope: ErrorEnvelope | undefined;
    const mime = response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
    if (mime === 'application/json' || mime?.endsWith('+json')) {
      try { const body: unknown = await response.json(); if (isErrorEnvelope(body)) envelope = body; } catch { /* Generic safe error below. */ }
    }
    throw new RequestFailure(response.status, envelope?.code ?? 'request_failed', envelope?.retryability, envelope?.request_id);
  } catch (failure) { throw transportFailure(failure); }
}

// Only bounded diagnostic fields from the generated contract cross the transport boundary.
// Server messages, credentials, raw response bodies and request inputs are never reflected.
export class RequestFailure extends Error {
  constructor(
    public status: number,
    public code: string,
    public retryability?: ErrorEnvelope['retryability'],
    public requestId?: ErrorEnvelope['request_id'],
    public submissionDisposition: 'not_sent' | 'rejected' | 'unknown' = 'unknown',
  ) { super(code); }
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  return Boolean(value && typeof value === 'object'
    && 'code' in value && typeof value.code === 'string' && /^[a-z0-9_]{1,80}$/.test(value.code)
    && 'message' in value && typeof value.message === 'string'
    && 'retryability' in value && (value.retryability === 'never' || value.retryability === 'safe' || value.retryability === 'reconcile')
    && 'request_id' in value && typeof value.request_id === 'string' && /^[A-Za-z0-9_.:-]{1,128}$/.test(value.request_id));
}

export function errorMessage(error: unknown): string {
  if (!(error instanceof RequestFailure)) return '暂时无法连接实例。当前输入和已有结果仍保留，请稍后重试。';
  const messages: Record<string, string> = {
    revision_conflict: '已有更新的保存版本。你的输入仍保留，请先比较或载入已保存版本。',
    idempotency_conflict: '这个请求已绑定另一份输入，请先读取原任务。',
    local_proxy_denied: '当前工作台连接不可用，请通过本机应用入口重新连接。',
    unauthorized: '实例会话已失效，请通过本机应用入口重新连接。',
    not_found: '这个项目或素材暂时不可用，请检查所属实例或重新载入。',
    invalid_request: '输入未通过实例检查，请核对目标、资料和来源。',
    media_validator_missing: '实例尚未接入媒体解码检查。文件已暂存，但没有登记为素材。',
    asset_integrity_failed: '素材大小或哈希不一致，未登记为可用素材。',
    object_integrity_failed: '素材内容校验失败，暂停播放。',
    media_invalid: '素材无法解码，未登记为可用素材。',
    text_asset_invalid: '文字素材格式无效或包含不允许的敏感内容，未登记。',
    preview_size_limit: '素材超过本次128MB预览上限。实例中的素材仍保留。',
    revision_limit: '已达到本次修订上限，原产物仍保留。',
    budget_unauthorized: '这次任务没有实例预算授权，请调整为已获授权的能力。',
    input_asset_denied: '这份素材未登记，或不在当前创作授权范围内。资料仍保留，请核对授权后再开始制作。',
    trusted_connection_missing: '作品连接尚未就绪。请通过应用入口重新连接，已有作品仍保留。',
    material_connection_changed: '素材连接已变化。原文件和暂存资料仍保留，请回到发起连接核实。',
    goal_submission_required: '新项目会随创作目标一次受理。请使用“开始创作”，无需先单独保存项目。',
    submission_identity_missing: '应用连接尚未提供当前提交身份。输入仍保留，请恢复应用连接后再提交。',
    daily_project_selection_required: '当前还没有可用的创作授权，或存在多份需要确认的授权。请在应用中核对创作范围，输入仍保留。',
    daily_project_authorization_unconfigured: '本机后续创作入口尚未接通。输入仍保留，尚不能开始新任务。',
    intent_storage_unavailable: '本机未能保留原请求信息，已暂停新的提交。请恢复本机存储后重试，已有结果仍保留。',
    submission_identity_mismatch: '原请求与当前实例或保存的输入不一致，已暂停提交。请回到发起实例核实。',
    bundle_version_mismatch: '作品版本与读取结果不一致，暂停预览。请重读原版本。',
    invalid_reference_descriptor: '来源版本描述格式不正确。请使用导出时保存的描述文件。',
    complete_content_required: '此次读取没有返回完整内容，暂停校验。请重新读取整个文件。',
    streaming_save_unavailable: '导出包已生成。当前入口尚未提供大文件流式保存，请通过具备该能力的应用入口保存。作品和导出包仍在实例中。',
    content_metadata_mismatch: '当前可读取内容与固定版本不一致，暂停预览。请重读原版本。',
  };
  if (!messages[error.code]) {
    if (error.status === 401) return '实例会话已失效。请重新连接，已有作品仍保留。';
    if (error.status === 403) return '当前身份没有这项使用权限。请核对授权范围。';
    if (error.status === 404) return '这个版本暂时不可用。请重读原任务或确认所属实例。';
    if (error.status === 415) return '实例尚不支持这种交付格式，请使用已支持的格式。';
    if (error.status === 503) return '实例所需资源暂时不可用。已有内容保留，请稍后重试。';
  }
  return messages[error.code] ?? `实例未能完成这次操作（${error.status}）。已有内容仍保留。`;
}

// This is a UI memory bound, never the installation's upload or export limit.
export const PREVIEW_BUFFER_BYTES = 128 * 1024 * 1024;
export const ARCHIVE_BUFFER_BYTES = 64 * 1024 * 1024;

export function verifyContentMetadata(metadata: Schemas['DeliveryContentMetadata'], expected: { instanceId: string; size: number; sha256: string; media_type: string }): void {
  if (metadata.state !== 'ready' || metadata.local_instance_id !== expected.instanceId
    || metadata.size !== expected.size || metadata.sha256 !== expected.sha256
    || metadata.media_type.toLowerCase() !== expected.media_type.toLowerCase()) {
    throw new RequestFailure(409, 'content_metadata_mismatch');
  }
  if (metadata.authorization_expires_at_us !== null && metadata.authorization_expires_at_us <= Date.now() * 1000) {
    throw new RequestFailure(403, 'authorization_expired');
  }
}

// Read the original response exactly once. Incremental counting bounds both a
// misleading Content-Length and chunked responses before allocating the Blob.
export async function verifiedContentBlob(response: Response, expected: { size: number; sha256: string; media_type: string }, limit = PREVIEW_BUFFER_BYTES, limitCode = 'preview_size_limit'): Promise<Blob> {
  const reader = response.body?.getReader();
  try {
    if (response.status !== 200 || response.headers.has('Content-Range')) throw new RequestFailure(response.status, 'complete_content_required');
    if (!Number.isSafeInteger(expected.size) || expected.size < 0 || expected.size > limit) throw new RequestFailure(413, limitCode);
    const mime = response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
    const length = response.headers.get('Content-Length');
    if (mime !== expected.media_type.split(';')[0].trim().toLowerCase()
      || (length !== null && (!/^\d+$/.test(length) || Number(length) !== expected.size))) throw new RequestFailure(422, 'object_integrity_failed');
    if (!reader) throw new RequestFailure(502, 'response_unavailable');
    const chunks: ArrayBuffer[] = []; let size = 0;
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      size += next.value.byteLength;
      if (size > expected.size || size > limit) throw new RequestFailure(422, 'object_integrity_failed');
      chunks.push(next.value.slice().buffer);
    }
    if (size !== expected.size) throw new RequestFailure(422, 'object_integrity_failed');
    const blob = new Blob(chunks, { type: expected.media_type });
    const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
    const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
    if (hash !== expected.sha256) throw new RequestFailure(422, 'object_integrity_failed');
    return blob;
  } catch (failure) {
    await reader?.cancel().catch(() => {});
    throw failure;
  } finally { reader?.releaseLock(); }
}

export function storedLocator(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}

export function rememberLocator(key: string, id: string): void {
  try { localStorage.setItem(key, id); } catch { /* Instance data remains saved even if this convenience locator is unavailable. */ }
}

export async function inputHash(input: unknown): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(input)));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}
