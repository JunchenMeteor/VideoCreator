import { bootstrapManagedWorkbench } from './engine';

/**
 * Runtime bootstrap for both dev and static production pages.
 *
 * The static installer serves the built workbench and the `/api` proxy on the
 * same loopback origin, so the trusted origin can be derived from the page
 * itself. A launcher may instead inject `window.__VIDEO_CREATOR_BOOT__`:
 * either a loopback origin string, or `{ mode: 'managed-proxy', origin }`.
 * Only the non-secret routing descriptor is read; any other field (including a
 * token) is ignored and never written to the DOM, storage or logs. The injected
 * descriptor is removed after capture so it cannot be read by later code.
 */
declare global {
  interface Window {
    __VIDEO_CREATOR_BOOT__?: unknown;
  }
}

function bootOrigin(value: unknown): string | undefined {
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined;
  const record = value as Record<string, unknown>;
  if (record.mode !== undefined && record.mode !== 'managed-proxy') return undefined;
  if (typeof record.origin === 'string') return record.origin;
  if (typeof record.base_url === 'string') return record.base_url;
  if (typeof record.baseUrl === 'string') return record.baseUrl;
  return undefined;
}

/** Same validation the generated client applies to a managed-proxy origin. */
function trustedLoopbackOrigin(origin: string): boolean {
  try {
    const url = new URL(origin);
    return url.protocol === 'http:' && url.hostname === '127.0.0.1'
      && !url.username && !url.password
      && url.pathname === '/' && !url.search && !url.hash;
  } catch {
    return false;
  }
}

export type WorkbenchLocation = Pick<Location, 'origin' | 'protocol' | 'hostname'>;

/**
 * Resolve the managed-proxy origin without any build-time constant. A boot
 * descriptor is used only when it names this exact loopback page origin; the
 * static fallback is the page's own origin (relative `/api/...` requests).
 */
export function resolveWorkbenchOrigin(location: WorkbenchLocation, boot: unknown): string | undefined {
  if (!trustedLoopbackOrigin(location.origin)) return undefined;
  const candidate = bootOrigin(boot);
  if (candidate !== undefined) {
    try {
      const url = new URL(candidate);
      // A boot descriptor may be a full URL with a trailing slash; only its
      // exact origin matters, and it must be this page's loopback origin.
      if (url.origin === location.origin && trustedLoopbackOrigin(url.origin)) return url.origin;
    } catch { /* Fall through to the same-origin static path. */ }
  }
  return location.origin;
}

/**
 * Install the workbench connection for the current page. Returns undefined when
 * the page is not a trusted loopback page, preserving the honest disconnected
 * state (no fake connection, no token, no storage writes).
 */
export function bootstrapWorkbenchFromRuntime(): (() => void) | undefined {
  if (typeof window === 'undefined') return undefined;
  const boot = window.__VIDEO_CREATOR_BOOT__;
  if (boot !== undefined) {
    try { delete window.__VIDEO_CREATOR_BOOT__; } catch { /* Host-owned property; we never read its other fields. */ }
  }
  const origin = resolveWorkbenchOrigin(window.location, boot);
  if (!origin) return undefined;
  try {
    return bootstrapManagedWorkbench(origin);
  } catch {
    return undefined;
  }
}
