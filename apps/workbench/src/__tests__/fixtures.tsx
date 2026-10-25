import type { ComponentProps } from 'react';
import { expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import { Workbench } from '../Workbench';
import { ProductAuthorizationGate } from '../ProductAuthorizationGate';
import type { ProductAuthorizationView } from '../productAuthorization';

// Test-only authorization session secret. It is never a real launcher value.
export const SECRET = 'a1b2c3d4e5f60718293a4b5c6d7e8f90';

export const NOW_US = Date.now() * 1000;

export const pendingView: ProductAuthorizationView = {
  version: 'product-authorization-ui-v1',
  authorization_id: 'authorization-' + 'd'.repeat(40),
  kind: 'owner_initialize',
  scope: {
    owner_subject: '本机用户',
    project_ids: ['project-a'],
    expires_at_us: NOW_US + 365 * 24 * 60 * 60 * 1_000_000,
    amount_cap: null,
    target: { kind: 'local-owner-binding-v1' },
    purpose: '首次初始化本机 Owner',
    summary: 'Authorize this installation Owner for 1 project(s)',
  },
  scope_sha256: 'e'.repeat(64),
  created_at_us: NOW_US,
  expires_at_us: NOW_US + 10 * 60 * 1_000_000,
  state: 'pending',
  restart_required: false,
  can_decide: true,
  nonce: 'f'.repeat(32),
};

export const completeView: ProductAuthorizationView = {
  ...pendingView, state: 'complete', restart_required: true, can_decide: false, nonce: null,
};

export const deniedView: ProductAuthorizationView = {
  ...pendingView, state: 'denied', restart_required: false, can_decide: false, nonce: null,
};

export const health = {
  instance_id: 'instance-verify',
  schema_version: '0.2.0-candidate',
  engine_version: '0.0.0-verify',
  mode: 'local',
  worker_connected: false,
};

type Reply = { status: number; body?: unknown; headers?: Record<string, string> };

/** Minimal Response facade; the app only reads status/ok/headers/json(). */
export function reply({ status, body, headers = {} }: Reply): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json', ...headers }),
    json: async () => body,
  } as unknown as Response;
}

export type ApiMock = {
  fetchMock: ReturnType<typeof vi.fn>;
  calls: { url: string; init?: RequestInit }[];
};

/** Mock the installation API for one health-channel state. */
export function mockApi(channel: 'pending' | 'complete' | 'none' | 'error', pending: ProductAuthorizationView = pendingView): ApiMock {
  const calls: { url: string; init?: RequestInit }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    if (url.includes('/api/v1/health')) {
      if (channel === 'error') {
        return reply({ status: 403, body: { code: 'unauthorized', message: 'denied', retryability: 'never', request_id: 'r-1' } });
      }
      return reply({ status: 200, body: health, headers: { 'X-VideoCreator-Authorization': channel } });
    }
    if (url.includes('/api/v1/authorization/pending')) return reply({ status: 200, body: pending });
    if (url.endsWith('/approve')) return reply({ status: 200, body: completeView });
    if (url.endsWith('/deny')) return reply({ status: 200, body: deniedView });
    if (url.endsWith('/api/v1/projects') || url.endsWith('/api/v1/productions')) return reply({ status: 200, body: [] });
    return reply({ status: 404, body: { code: 'not_found', message: 'missing', retryability: 'never', request_id: 'r-404' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock, calls };
}

export function renderWorkbench() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
  return render(<QueryClientProvider client={client}><Workbench /></QueryClientProvider>);
}

export function renderGate(props: Partial<ComponentProps<typeof ProductAuthorizationGate>> = {}) {
  return render(<Theme><ProductAuthorizationGate channel="pending" reachable instanceId="instance-verify" onRecheck={() => {}} {...props} /></Theme>);
}

/** The secret must never appear in rendered text, attributes or web storage. */
export function expectNoSecretStored() {
  expect(document.body.innerHTML).not.toContain(SECRET);
  expect(JSON.stringify(localStorage)).not.toContain(SECRET);
  expect(JSON.stringify(sessionStorage)).not.toContain(SECRET);
}
