/**
 * BYOK credential endpoints (list/create/delete).
 *
 * The workbench never reads an instance token: these are same-origin requests
 * through the managed proxy, which injects the instance session. Only the
 * whitelisted summary fields of a response are copied out, so a secret echoed
 * by a misbehaving server still never reaches UI state, the DOM or web storage.
 */

export const CREDENTIAL_PROVIDERS = ['deepseek', 'openai', 'anthropic', 'custom'] as const;
export type CredentialProvider = (typeof CREDENTIAL_PROVIDERS)[number];

export type CredentialSummary = Readonly<{
  credential_ref: string;
  fingerprint: string;
  provider: string;
  label: string;
  created_at_us: number;
}>;

export const EMPTY_CREDENTIALS_TEXT = '尚未配置模型凭证';
export const CREDENTIAL_IN_USE_TEXT = '该凭证仍被路由引用，无法删除';
export const VAULT_UNAVAILABLE_TEXT = '本机保险库不可用，无法保存凭证';
export const CREDENTIAL_RESPONSE_INVALID_TEXT = '实例返回的凭证信息无法识别';
/** The engine has no connection-test endpoint; say so instead of faking a pass. */
export const CREDENTIAL_TEST_NOTE = '连接测试需先配置模型路由（尚未实现）';

const ERROR_TEXT: Readonly<Record<string, string>> = {
  vault_unavailable: VAULT_UNAVAILABLE_TEXT,
  credential_in_use: CREDENTIAL_IN_USE_TEXT,
  credential_external_reference_denied: '密钥不能引用外部环境变量，请直接输入密钥值',
  credential_store_failed: '本机保险库未能保存该凭证',
  credential_not_found: '该凭证不存在或已被删除',
  credential_ref_invalid: '凭证编号无效，未发送删除请求',
  credential_response_invalid: CREDENTIAL_RESPONSE_INVALID_TEXT,
  credential_request_failed: '凭证请求未完成',
};

export class CredentialApiFailure extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly references: readonly string[] = [],
    message = '',
  ) {
    super(message || code);
    this.name = 'CredentialApiFailure';
  }
}

/** A named message for every failure; never a bare "something went wrong". */
export function credentialFailureText(failure: unknown): string {
  if (!(failure instanceof CredentialApiFailure)) return '凭证操作未完成';
  if (failure.status === 0) return '无法连接本机实例，凭证操作未完成';
  const known = ERROR_TEXT[failure.code];
  if (known) return known;
  return failure.message && failure.message !== failure.code
    ? failure.message
    : `凭证操作失败（${failure.code}）`;
}

/** Only the first 12 characters of the fingerprint are ever shown. */
export function fingerprintPrefix(fingerprint: string): string {
  const value = typeof fingerprint === 'string' ? fingerprint : '';
  return value.length > 12 ? value.slice(0, 12) + '…' : value;
}

export function createdAtText(createdAtUs: number): string {
  if (!Number.isFinite(createdAtUs)) return '时间未知';
  const date = new Date(Math.floor(createdAtUs / 1000));
  if (Number.isNaN(date.getTime())) return '时间未知';
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

async function request(
  path: string,
  init: { method: 'GET' | 'POST' | 'DELETE'; body?: unknown; signal?: AbortSignal },
): Promise<Response> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Video-Creator-Client': 'workbench',
  };
  if (init.body !== undefined) headers['Content-Type'] = 'application/json';
  try {
    return await fetch(path, {
      method: init.method,
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      signal: init.signal,
      credentials: 'omit',
      redirect: 'error',
      cache: 'no-store',
    });
  } catch {
    throw new CredentialApiFailure(0, 'credential_transport_unavailable');
  }
}

async function responseFailure(response: Response): Promise<CredentialApiFailure> {
  const value: unknown = await response.json().catch(() => undefined);
  const record = isRecord(value) ? value : {};
  const code = typeof record.code === 'string' && record.code ? record.code : 'credential_request_failed';
  const message = typeof record.message === 'string' ? record.message : '';
  const references = Array.isArray(record.references)
    ? record.references.filter((item): item is string => typeof item === 'string')
    : [];
  return new CredentialApiFailure(response.status, code, references, message);
}

/** Copy only the documented summary fields; everything else is dropped. */
function summary(value: unknown): CredentialSummary | null {
  if (!isRecord(value)) return null;
  const { credential_ref, fingerprint, provider, label, created_at_us } = value;
  if (typeof credential_ref !== 'string' || !/^vault:[A-Za-z0-9_-]{1,120}$/.test(credential_ref)) return null;
  if (typeof fingerprint !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(fingerprint)) return null;
  if (typeof provider !== 'string' || !provider || provider.length > 80) return null;
  if (typeof label !== 'string' || !label || label.length > 200) return null;
  if (typeof created_at_us !== 'number' || !Number.isFinite(created_at_us) || created_at_us < 0) return null;
  return { credential_ref, fingerprint, provider, label, created_at_us };
}

/**
 * The published contract (OpenAPI `CredentialListV1`) is
 * `{"credentials":[...]}`. Anything else is a contract failure: report it,
 * never silently render it as an empty list.
 */
export async function readCredentials(signal?: AbortSignal): Promise<CredentialSummary[]> {
  const response = await request('/api/v1/credentials', { method: 'GET', signal });
  if (!response.ok) throw await responseFailure(response);
  const value: unknown = await response.json().catch(() => undefined);
  if (!isRecord(value) || !Array.isArray(value.credentials)) {
    throw new CredentialApiFailure(502, 'credential_response_invalid');
  }
  const items = value.credentials.map(summary);
  if (items.some(item => item === null)) throw new CredentialApiFailure(502, 'credential_response_invalid');
  return items as CredentialSummary[];
}

/**
 * The secret lives only in this request body. The response is expected to carry
 * no secret; even if it did, only the summary fields above are retained.
 */
export async function createCredential(
  input: { provider: CredentialProvider; label: string; secret: string },
  signal?: AbortSignal,
): Promise<CredentialSummary> {
  if (!CREDENTIAL_PROVIDERS.includes(input.provider)) {
    throw new CredentialApiFailure(400, 'credential_provider_invalid');
  }
  if (!input.label.trim() || !input.secret) {
    throw new CredentialApiFailure(400, 'credential_input_invalid');
  }
  const response = await request('/api/v1/credentials', {
    method: 'POST',
    body: { provider: input.provider, label: input.label.trim(), secret: input.secret },
    signal,
  });
  if (!response.ok) throw await responseFailure(response);
  const item = summary(await response.json().catch(() => undefined));
  if (!item) throw new CredentialApiFailure(502, 'credential_response_invalid');
  return item;
}

/** 204 removes it; 409 carries `references` so the page can name the blockers. */
export async function deleteCredential(ref: string, signal?: AbortSignal): Promise<void> {
  if (!/^vault:[A-Za-z0-9_-]{1,120}$/.test(ref)) {
    throw new CredentialApiFailure(400, 'credential_ref_invalid');
  }
  const response = await request(`/api/v1/credentials/${ref}`, { method: 'DELETE', signal });
  if (!response.ok) throw await responseFailure(response);
}
