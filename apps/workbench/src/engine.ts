import type { components } from '@video-creator/api-client';

export type Schemas = components['schemas'];
export type ProjectDraft = Schemas['ProjectDraft'];
export type ProjectInput = Schemas['ProjectInput'];
export type ProductionDetail = Schemas['ProductionDetail'];
export type ProductionAccepted = Schemas['ProductionAccepted'];
export type ProductionInput = Schemas['ProductionRequest-Input'];
export type CreativeRevision = Schemas['CreativeRevision'];
export type EngineEvent = Schemas['EventEnvelope'];
export type AssetRecord = Schemas['AssetRecord'];
export type ErrorEnvelope = Schemas['ErrorEnvelope'];

// Only bounded diagnostic fields from the generated contract cross the transport boundary.
// Server messages, credentials, raw response bodies and request inputs are never reflected.
export class RequestFailure extends Error {
  constructor(
    public status: number,
    public code: string,
    public retryability?: ErrorEnvelope['retryability'],
    public requestId?: ErrorEnvelope['request_id'],
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
    input_asset_denied: '输入素材不属于当前用户或尚未登记，未开始制作。',
  };
  return messages[error.code] ?? `实例未能完成这次操作（${error.status}）。已有内容仍保留。`;
}

export async function engineFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith('/api/v1/') || path.startsWith('//') || path.includes('\\')) {
    throw new RequestFailure(400, 'invalid_path');
  }
  const headers = new Headers(init.headers);
  headers.set('X-Video-Creator-Client', 'workbench');
  const response = await fetch(path, { ...init, headers, credentials: 'omit', cache: 'no-store', mode: 'same-origin' });
  if (!response.ok) {
    let envelope: ErrorEnvelope | undefined;
    try {
      const mediaType = response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
      if (mediaType === 'application/json' || mediaType?.endsWith('+json')) {
        const body: unknown = await response.json();
        if (isErrorEnvelope(body)) envelope = body;
      }
    } catch { /* Plain Host/Range errors, framework detail and malformed JSON stay generic. */ }
    throw new RequestFailure(response.status, envelope?.code ?? 'request_failed', envelope?.retryability, envelope?.request_id);
  }
  return response;
}

export async function engineJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await engineFetch(path, init);
  return await response.json() as T;
}

export function jsonWrite(method: 'POST' | 'PUT', body: unknown, extraHeaders: Record<string, string> = {}): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json', ...extraHeaders }, body: JSON.stringify(body) };
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
