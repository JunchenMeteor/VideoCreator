/**
 * ADR0081 product authorization channel (workbench side).
 *
 * The engine advertises the channel on `GET /api/v1/health` through the
 * `X-VideoCreator-Authorization` response header. A restricted process exposes
 * only health and `/api/v1/authorization/*`; this module speaks the frozen
 * `product-authorization-ui-v1` view protocol.
 *
 * The authorization session secret is supplied by the trusted launcher for this
 * process only: R1 loopback injects a one-time URL fragment `#a=<secret>`, the
 * desktop shell may inject `window.__VIDEO_CREATOR_AUTHORIZATION_SECRET__`.
 * It lives in this module's closure only. It is never persisted to
 * localStorage/sessionStorage, written to the console, rendered, or copied to a
 * DOM attribute, and it is dropped as soon as a decision has been accepted.
 */

export const AUTHORIZATION_CHANNEL_HEADER = 'X-VideoCreator-Authorization';
export const AUTHORIZATION_UI_VERSION = 'product-authorization-ui-v1';

export type AuthorizationChannel = 'pending' | 'complete' | 'none';

export function readAuthorizationChannel(headers: Headers): AuthorizationChannel | undefined {
  const value = headers.get(AUTHORIZATION_CHANNEL_HEADER)?.trim().toLowerCase();
  return value === 'pending' || value === 'complete' || value === 'none' ? value : undefined;
}

export type ProductAuthorizationState =
  | 'pending'
  | 'approved'
  | 'applied'
  | 'denied'
  | 'expired'
  | 'superseded'
  | 'complete';

export type ProductAuthorizationScope = Readonly<Record<string, unknown>>;

/** Frozen `product-authorization-ui-v1` view (ADR0081 §9). */
export type ProductAuthorizationView = {
  readonly version: typeof AUTHORIZATION_UI_VERSION;
  readonly authorization_id: string;
  readonly kind: string;
  readonly scope: ProductAuthorizationScope;
  readonly scope_sha256: string;
  readonly created_at_us: number;
  readonly expires_at_us: number;
  readonly state: ProductAuthorizationState;
  readonly restart_required: boolean;
  readonly can_decide: boolean;
  /**
   * One-time value bound to this request. §4 makes it part of the approve/deny
   * body, but §9 does not list it among the view fields; it is read only when
   * the channel actually supplies it. A missing nonce is surfaced as a blocked
   * state instead of inventing a value the engine cannot verify.
   */
  readonly nonce: string | null;
};

const STATES: readonly ProductAuthorizationState[] = ['pending', 'approved', 'applied', 'denied', 'expired', 'superseded', 'complete'];
const ID_PATTERN = /^authorization-[A-Za-z0-9_-]{8,80}$/;
const HEX_DIGEST_PATTERN = /^[0-9a-f]{64}$/;
const NONCE_PATTERN = /^[A-Za-z0-9_-]{16,128}$/;
const SECRET_PATTERN = /^[A-Za-z0-9+/=_-]+$/;
// 128-bit secrets are 32 hex chars, but launchers may use token_urlsafe(16)
// (22 chars) or base64 (24). Accept the encodings without inventing entropy.
const SECRET_MIN_LENGTH = 16;
const SECRET_MAX_LENGTH = 256;

declare global {
  interface Window {
    /** Desktop-shell injection point; consumed once and removed. */
    __VIDEO_CREATOR_AUTHORIZATION_SECRET__?: unknown;
  }
}

let sessionSecret: string | null = null;
let initialized = false;

function isSecret(value: unknown): value is string {
  return typeof value === 'string' && value.length >= SECRET_MIN_LENGTH
    && value.length <= SECRET_MAX_LENGTH && SECRET_PATTERN.test(value);
}

function readFragmentSecret(): { secret?: string; present: boolean } {
  if (typeof window === 'undefined') return { present: false };
  const hash = window.location.hash;
  if (!hash.startsWith('#')) return { present: false };
  const raw = hash.slice(1);
  // R1 uses exactly `#a=<secret>`. A direct match keeps base64 '+' and '='
  // intact; URLSearchParams would turn '+' into a space.
  const direct = /^a=([A-Za-z0-9+/=_-]+)$/.exec(raw);
  const value = direct ? direct[1] : new URLSearchParams(raw).get('a');
  return { secret: isSecret(value) ? value : undefined, present: direct !== null || new URLSearchParams(raw).has('a') };
}

function scrubFragment(): void {
  // The fragment is transport only. Drop it before any render so it does not
  // linger in the address bar, history entry, screenshots or copied URLs.
  try { window.history.replaceState(null, '', window.location.pathname + window.location.search); } catch { /* Cosmetic only. */ }
}

/**
 * Capture the launcher-injected secret once, as early as possible. Called by
 * the workbench entry before React renders. Safe to call repeatedly.
 */
export function initializeProductAuthorization(): void {
  if (initialized || typeof window === 'undefined') return;
  initialized = true;
  const injected = window.__VIDEO_CREATOR_AUTHORIZATION_SECRET__;
  if (injected !== undefined) {
    // Remove the injected handle as soon as the closure owns the value.
    try { delete window.__VIDEO_CREATOR_AUTHORIZATION_SECRET__; } catch { /* Host-owned property; closure copy is still private. */ }
  }
  const fragment = readFragmentSecret();
  if (fragment.present) scrubFragment();
  const candidate = isSecret(injected) ? injected : fragment.secret;
  if (candidate && sessionSecret === null) sessionSecret = candidate;
}

/** True while this page still holds the per-process authorization secret. */
export function authorizationSessionSecretAvailable(): boolean {
  return sessionSecret !== null;
}

/** Drop the in-memory secret. Never called while a decision is in flight. */
export function clearAuthorizationSessionSecret(): void {
  sessionSecret = null;
}

export class AuthorizationFailure extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly retryability?: 'never' | 'safe' | 'reconcile',
  ) {
    super(code);
    this.name = 'AuthorizationFailure';
  }
}

export function asAuthorizationFailure(error: unknown): AuthorizationFailure {
  return error instanceof AuthorizationFailure ? error : new AuthorizationFailure(0, 'authorization_transport_failed');
}

/** Cancellation is not a decision failure; callers ignore it. */
export function isAuthorizationAbort(error: unknown): boolean {
  return Boolean(error && typeof error === 'object' && 'name' in error && (error as { name?: unknown }).name === 'AbortError');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isTimestamp(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
}

/**
 * Validate a view before it reaches the UI. Unknown/malformed payloads are not
 * partially rendered: the caller shows an honest blocked state instead.
 */
export function parseAuthorizationView(value: unknown): ProductAuthorizationView | null {
  if (!isRecord(value)) return null;
  if (value.version !== AUTHORIZATION_UI_VERSION) return null;
  const authorizationId = value.authorization_id;
  const scopeSha256 = value.scope_sha256;
  const nonce = value.nonce;
  if (typeof authorizationId !== 'string' || !ID_PATTERN.test(authorizationId)) return null;
  if (typeof value.kind !== 'string' || !value.kind || value.kind.length > 80) return null;
  if (!isRecord(value.scope)) return null;
  if (typeof scopeSha256 !== 'string' || !HEX_DIGEST_PATTERN.test(scopeSha256)) return null;
  if (!isTimestamp(value.created_at_us) || !isTimestamp(value.expires_at_us)) return null;
  if (typeof value.state !== 'string' || !STATES.includes(value.state as ProductAuthorizationState)) return null;
  return Object.freeze({
    version: AUTHORIZATION_UI_VERSION,
    authorization_id: authorizationId,
    kind: value.kind,
    scope: value.scope,
    scope_sha256: scopeSha256,
    created_at_us: value.created_at_us,
    expires_at_us: value.expires_at_us,
    state: value.state as ProductAuthorizationState,
    restart_required: value.restart_required === true,
    can_decide: value.can_decide === true,
    nonce: typeof nonce === 'string' && NONCE_PATTERN.test(nonce) ? nonce : null,
  });
}

function envelopeCode(value: unknown): string | undefined {
  if (!isRecord(value)) return undefined;
  return typeof value.code === 'string' && /^[a-z0-9_]{1,80}$/.test(value.code) ? value.code : undefined;
}

async function readJson(response: Response): Promise<unknown> {
  try { return await response.json(); } catch { return undefined; }
}

async function failureFromResponse(response: Response): Promise<AuthorizationFailure> {
  const body = await readJson(response);
  const code = envelopeCode(body) ?? 'authorization_request_failed';
  const bodyRecord = isRecord(body) ? body : undefined;
  const retryability = bodyRecord?.retryability;
  return new AuthorizationFailure(
    response.status,
    code,
    retryability === 'never' || retryability === 'safe' || retryability === 'reconcile' ? retryability : undefined,
  );
}

/**
 * Same-origin, same-session request. The managed proxy owns the installation
 * bearer; this page only adds the channel marker and (for decisions) the
 * launcher-injected authorization secret. No credential ever appears in the
 * URL, storage, console or the DOM.
 */
async function authorizationRequest(
  path: string,
  init: { method: 'GET' | 'POST'; body?: string; secret?: string; signal?: AbortSignal },
): Promise<Response> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-Video-Creator-Client': 'workbench',
  };
  if (init.body !== undefined) headers['Content-Type'] = 'application/json';
  if (init.secret !== undefined) headers[AUTHORIZATION_CHANNEL_HEADER] = init.secret;
  try {
    return await fetch(path, {
      method: init.method,
      headers,
      body: init.body,
      signal: init.signal,
      credentials: 'omit',
      redirect: 'error',
      cache: 'no-store',
    });
  } catch (error) {
    if (isAuthorizationAbort(error)) throw error;
    throw new AuthorizationFailure(0, 'authorization_transport_failed');
  }
}

/**
 * Read the single pending request. `null` means the channel has no pending
 * request (404 `authorization_not_found`), which the caller may retry briefly
 * during startup before treating it as a dead end.
 */
export async function readPendingAuthorization(signal?: AbortSignal): Promise<ProductAuthorizationView | null> {
  // The channel only returns the one-time nonce to a reader that presents the
  // same launcher secret (ADR0081 §4/§9). Without a secret the view stays
  // readable but carries `nonce: null`, which the UI surfaces as blocked.
  const response = await authorizationRequest('/api/v1/authorization/pending', {
    method: 'GET', signal, secret: sessionSecret ?? undefined,
  });
  if (response.status === 404) return null;
  if (!response.ok) throw await failureFromResponse(response);
  const view = parseAuthorizationView(await readJson(response));
  if (!view) throw new AuthorizationFailure(502, 'authorization_response_invalid');
  return view;
}

/**
 * Submit the one-time decision. The body is exactly the frozen shape:
 * `{scope_sha256, nonce}`. The secret is cleared only after the engine accepted
 * the decision; a retryable failure keeps it for a same-page retry.
 */
export async function decideAuthorization(
  view: ProductAuthorizationView,
  decision: 'approve' | 'deny',
  signal?: AbortSignal,
): Promise<ProductAuthorizationView> {
  if (view.nonce === null) throw new AuthorizationFailure(0, 'authorization_nonce_missing');
  if (sessionSecret === null) throw new AuthorizationFailure(403, 'authorization_session_missing');
  if (!ID_PATTERN.test(view.authorization_id)) throw new AuthorizationFailure(0, 'authorization_response_invalid');
  const response = await authorizationRequest(
    `/api/v1/authorization/${encodeURIComponent(view.authorization_id)}/${decision}`,
    {
      method: 'POST',
      body: JSON.stringify({ scope_sha256: view.scope_sha256, nonce: view.nonce }),
      secret: sessionSecret,
      signal,
    },
  );
  if (!response.ok) throw await failureFromResponse(response);
  const result = parseAuthorizationView(await readJson(response));
  if (!result) throw new AuthorizationFailure(502, 'authorization_response_invalid');
  clearAuthorizationSessionSecret();
  return result;
}

// --- Readable presentation -------------------------------------------------

const KIND_LABELS: Readonly<Record<string, string>> = {
  owner_initialize: '初始化本机 Owner（首次授权）',
  owner_renew: '续期本机 Owner 授权',
  owner_revoke: '撤销本机 Owner 授权',
  policy_install: '安装创作策略',
  policy_select: '选择创作策略',
  policy_revoke: '撤销创作策略',
  budget_authorize: '授权创作预算',
  daily_creation_install: '登记日常创作授权',
  daily_creation_revoke: '撤销日常创作授权',
  local_evidence_policy: '登记本机自签证据策略',
};

export function describeAuthorizationKind(kind: string): string {
  return KIND_LABELS[kind] ?? `本机授权动作（${kind}）`;
}

const SCOPE_LABELS: Readonly<Record<string, string>> = {
  owner_subject: '授权对象',
  project_ids: '涉及项目',
  expires_at_us: '授权有效期',
  created_at_us: '创建时间',
  amount_limit: '金额上限',
  amount_limit_cny: '金额上限（CNY）',
  amount_cap: '金额上限',
  budget_limit: '预算上限',
  budget_limit_cny: '预算上限（CNY）',
  budget_authorize_amount: '预算上限',
  purpose: '用途',
  target: '目标对象',
  target_ref: '目标对象',
  target_kind: '目标类型',
  kind: '范围类型',
  label: '范围',
  summary: '范围说明',
  description: '范围说明',
};
const SCOPE_ORDER = [
  'owner_subject', 'project_ids', 'purpose', 'target', 'target_ref', 'target_kind',
  'amount_limit', 'amount_limit_cny', 'amount_cap', 'budget_limit', 'budget_limit_cny', 'budget_authorize_amount',
  'expires_at_us', 'created_at_us', 'summary', 'description', 'label', 'kind',
];
// Defense in depth: scope is specified never to carry credentials or paths, but
// nothing credential-shaped is ever rendered if a server violates that.
const HIDDEN_KEY = /(secret|token|password|passwd|credential|nonce|private_key|api_key|authorization)/i;

export type AuthorizationScopeRow = { readonly label: string; readonly value: string };

export function formatMicroseconds(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '未提供';
  const date = new Date(Math.floor(value / 1000));
  if (Number.isNaN(date.getTime())) return '未提供';
  const pad = (part: number) => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatAuthorizationRemaining(expiresAtUs: number, nowMs: number): string {
  // Timestamps are integer microseconds; now is the page's millisecond clock.
  const total = Math.max(0, Math.ceil((expiresAtUs - nowMs * 1000) / 1_000_000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

export function isAuthorizationExpired(view: Pick<ProductAuthorizationView, 'expires_at_us'>, nowMs: number): boolean {
  return view.expires_at_us <= nowMs * 1000;
}

const TARGET_LABELS: Readonly<Record<string, string>> = {
  'local-owner-binding-v1': '本机 Owner 绑定',
  'owner-binding': '本机 Owner 绑定',
};

function formatScopeValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return '未指定';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return String(value);
    if (key.endsWith('_us') || key.endsWith('_at_us')) return formatMicroseconds(value);
    if (/cny/i.test(key)) return `¥${value.toLocaleString('zh-CN')}`;
    return value.toLocaleString('zh-CN');
  }
  if (typeof value === 'string') {
    const text = value.trim();
    if (!text) return '未指定';
    return text.length > 400 ? `${text.slice(0, 400)}…` : text;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '未指定';
    const primitives = value.filter(item => ['string', 'number', 'boolean'].includes(typeof item));
    if (primitives.length === value.length) {
      const joined = primitives.map(item => String(item)).join('、');
      return joined.length > 400 ? `${joined.slice(0, 400)}…` : joined;
    }
    return `${value.length} 项`;
  }
  if (isRecord(value)) {
    // Structured target references stay readable: their discriminator is the
    // human-facing fact, not "1 项".
    if (typeof value.kind === 'string') return TARGET_LABELS[value.kind] ?? value.kind;
    return `${Object.keys(value).length} 项`;
  }
  return String(value);
}

export function describeAuthorizationScope(scope: ProductAuthorizationScope): AuthorizationScopeRow[] {
  const keys = Object.keys(scope).filter(key => !HIDDEN_KEY.test(key));
  const ordered = [
    ...SCOPE_ORDER.filter(key => keys.includes(key)),
    ...keys.filter(key => !SCOPE_ORDER.includes(key)).sort(),
  ];
  return ordered.map(key => ({
    label: SCOPE_LABELS[key] ?? key.replace(/_/g, ' '),
    value: formatScopeValue(key, scope[key]),
  }));
}

/** Bounded, credential-redacted JSON for the optional raw-scope disclosure. */
export function serializeAuthorizationScope(scope: ProductAuthorizationScope): string {
  try {
    const text = JSON.stringify(scope, (key, value) => (key && HIDDEN_KEY.test(key) ? '[已隐藏]' : value), 2);
    if (text === undefined) return '{}';
    return text.length > 4_096 ? `${text.slice(0, 4_096)}\n…` : text;
  } catch {
    return '{}';
  }
}

const FAILURE_MESSAGES: Readonly<Record<string, string>> = {
  authorization_not_found: '没有可确认的待授权请求（可能已过期，或被新的请求替代）。没有写入任何内容。',
  authorization_expired: '这次授权请求已过期（有效期不超过 10 分钟），没有写入任何内容。',
  authorization_already_decided: '这个请求已经被确认过，不会重复写入。请重新检查状态或重启应用。',
  authorization_conflict: '这个请求与已记录的范围或决定不一致，本次提交没有生效。请重新打开应用再发起。',
  authorization_instance_conflict: '这个请求不属于当前安装实例，本次提交没有生效。',
  authorization_nonce_denied: '一次性确认凭据已被使用或不匹配，本次提交没有生效。请重新打开工作台再确认新的请求。',
  authorization_session_denied: '本机授权会话凭据无效或已轮换，本次提交没有生效。请从启动器重新打开工作台。',
  authorization_session_missing: '当前页面没有拿到启动器注入的授权会话凭据，无法提交确认。请从启动器重新打开工作台。',
  authorization_session_unavailable: '启动实例时没有注入授权会话密钥，当前进程只能显示待授权请求，无法批准。请从启动器重新启动实例后再试。',
  authorization_nonce_missing: '授权通道没有提供这次确认所需的一次性凭据，当前页面无法提交。请更新启动器或引擎；在此之前可继续使用终端兜底。',
  authorization_audit_unwritten: '本机审计记录未能写入，因此授权没有生效（Owner 授权未写入）。请确认实例数据目录可写后重试。',
  authorization_response_invalid: '授权通道返回了无法识别的结果。为避免误批，本次没有提交或显示任何凭据，请重新打开应用。',
  authorization_transport_failed: '暂时无法连接授权通道，本次提交的结果未知。请先重新检查状态；重复提交同一个决定不会产生第二份授权。',
  origin_denied: '请求来源未通过本机准入检查，没有写入任何内容。请从工作台正常入口打开。',
  owner_authorization_required: '实例仍处于受限模式，这个操作需要先完成本机授权。',
  unauthorized: '实例会话已失效，没有写入任何内容。请从启动器重新打开工作台。',
};

export function authorizationFailureMessage(failure: AuthorizationFailure): string {
  return FAILURE_MESSAGES[failure.code] ?? `授权通道未能完成这次操作（${failure.code}）。没有显示或写入任何新凭据。`;
}
