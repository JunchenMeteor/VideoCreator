import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import { CredentialsPanel } from '../CredentialsPanel';
import {
  CREDENTIAL_IN_USE_TEXT, CREDENTIAL_RESPONSE_INVALID_TEXT, CREDENTIAL_TEST_NOTE,
  EMPTY_CREDENTIALS_TEXT, VAULT_UNAVAILABLE_TEXT,
  fingerprintPrefix, type CredentialSummary,
} from '../credentialApi';

// Test-only value; it never belongs to a real provider.
const SECRET = 'sk-test-should-never-be-echoed-1234567890';
const FINGERPRINT = 'ab12cd34ef567890';
const NOW_US = Date.UTC(2026, 9, 26, 9, 16) * 1000;

type ApiCall = { method: string; path: string; body?: Record<string, unknown> };

function reply(status: number, body?: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  } as unknown as Response;
}

function credential(overrides: Partial<CredentialSummary> = {}): CredentialSummary {
  return {
    credential_ref: 'vault:' + 'b'.repeat(32),
    fingerprint: FINGERPRINT,
    provider: 'openai',
    label: '主账号',
    created_at_us: NOW_US,
    ...overrides,
  };
}

function installApi(options: {
  items?: CredentialSummary[];
  listBody?: unknown;
  createFailure?: { status: number; body: unknown };
  deleteFailure?: { status: number; body: unknown };
} = {}) {
  const items = [...(options.items ?? [])];
  const calls: ApiCall[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), window.location.origin);
    const method = init?.method ?? 'GET';
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) as Record<string, unknown> : undefined;
    calls.push({ method, path: url.pathname, body });
    if (url.pathname === '/api/v1/credentials' && method === 'GET') {
      return reply(200, options.listBody ?? { credentials: items });
    }
    if (url.pathname === '/api/v1/credentials' && method === 'POST') {
      if (options.createFailure) return reply(options.createFailure.status, options.createFailure.body);
      const created = credential({
        credential_ref: 'vault:' + 'c'.repeat(32),
        provider: String(body?.provider ?? ''),
        label: String(body?.label ?? ''),
      });
      items.push(created);
      return reply(201, created);
    }
    const target = pathnameRef(url.pathname);
    if (target !== null) {
      if (options.deleteFailure) return reply(options.deleteFailure.status, options.deleteFailure.body);
      const index = items.findIndex(item => item.credential_ref === target);
      if (index >= 0) items.splice(index, 1);
      return reply(204);
    }
    return reply(404, { code: 'not_found', message: 'probe' });
  });
  vi.stubGlobal('fetch', fetchMock);
  return { calls, items };
}

function pathnameRef(pathname: string): string | null {
  const prefix = '/api/v1/credentials/';
  return pathname.startsWith(prefix) ? decodeURIComponent(pathname.slice(prefix.length)) : null;
}

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
  return render(<Theme><QueryClientProvider client={client}><CredentialsPanel connected instanceId="instance-verify" /></QueryClientProvider></Theme>);
}

async function fillForm(label = '主账号', secret = SECRET) {
  await userEvent.type(screen.getByLabelText('名称'), label);
  await userEvent.type(screen.getByLabelText('密钥'), secret);
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('lists provider, label, the first 12 fingerprint characters and the creation time only', async () => {
  installApi({ items: [credential()] });
  renderPanel();
  const list = await screen.findByRole('list', { name: '已配置的模型凭证' });
  expect(within(list).getByText('openai')).toBeInTheDocument();
  expect(within(list).getByText('主账号')).toBeInTheDocument();
  expect(within(list).getByText(fingerprintPrefix(FINGERPRINT))).toBeInTheDocument();
  expect(fingerprintPrefix(FINGERPRINT)).toBe('ab12cd34ef56…');
  expect(within(list).getByText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)).toBeInTheDocument();
  expect(document.body.innerHTML).not.toContain(FINGERPRINT);
});

it('shows the empty state when no credential exists', async () => {
  installApi({ items: [] });
  renderPanel();
  expect(await screen.findByText(EMPTY_CREDENTIALS_TEXT)).toBeInTheDocument();
});

it('reports a contract failure instead of showing an empty list when the envelope is missing', async () => {
  installApi({ listBody: [credential()] });
  renderPanel();
  expect(await screen.findByText(CREDENTIAL_RESPONSE_INVALID_TEXT)).toBeInTheDocument();
  expect(screen.queryByText(EMPTY_CREDENTIALS_TEXT)).not.toBeInTheDocument();
  expect(screen.queryByRole('list', { name: '已配置的模型凭证' })).not.toBeInTheDocument();
});

it('rejects a malformed credential entry instead of silently dropping it', async () => {
  installApi({ listBody: { credentials: [credential({ fingerprint: 'not a fingerprint!' })] } });
  renderPanel();
  expect(await screen.findByText(CREDENTIAL_RESPONSE_INVALID_TEXT)).toBeInTheDocument();
  expect(screen.queryByText('主账号')).not.toBeInTheDocument();
  expect(screen.queryByText(EMPTY_CREDENTIALS_TEXT)).not.toBeInTheDocument();
});

it('offers exactly the supported providers', async () => {
  installApi({ items: [] });
  renderPanel();
  await screen.findByText(EMPTY_CREDENTIALS_TEXT);
  await userEvent.click(screen.getByRole('combobox'));
  const options = await screen.findAllByRole('option');
  expect(options.map(option => option.textContent)).toEqual(['deepseek', 'openai', 'anthropic', 'custom']);
});

it('clears the password field and keeps the secret out of the page after saving', async () => {
  const api = installApi({ items: [] });
  renderPanel();
  await screen.findByText(EMPTY_CREDENTIALS_TEXT);
  const secretInput = screen.getByLabelText('密钥');
  expect(secretInput).toHaveAttribute('type', 'password');
  await fillForm();
  expect(secretInput).toHaveValue(SECRET);

  await userEvent.click(screen.getByRole('button', { name: '保存' }));

  expect(await screen.findByText(`已保存，指纹 ${fingerprintPrefix(FINGERPRINT)}`)).toBeInTheDocument();
  expect(secretInput).toHaveValue('');
  expect(document.body.innerHTML).not.toContain(SECRET);
  expect(window.location.href).not.toContain(SECRET);
  expect(JSON.stringify(localStorage)).not.toContain(SECRET);
  expect(JSON.stringify(sessionStorage)).not.toContain(SECRET);

  const post = api.calls.find(call => call.method === 'POST');
  expect(post?.body).toEqual({ provider: 'deepseek', label: '主账号', secret: SECRET });
  expect(api.calls.filter(call => call.method === 'POST')).toHaveLength(1);
});

it('names the referencing records and keeps the credential on a 409 delete', async () => {
  installApi({
    items: [credential()],
    deleteFailure: {
      status: 409,
      body: {
        code: 'credential_in_use',
        message: 'Credential is still referenced',
        retryability: 'never',
        references: ['route:route-a', 'production:production-1'],
      },
    },
  });
  renderPanel();
  const list = await screen.findByRole('list', { name: '已配置的模型凭证' });
  await userEvent.click(within(list).getByRole('button', { name: /删除/ }));

  expect(await screen.findByText(CREDENTIAL_IN_USE_TEXT)).toBeInTheDocument();
  expect(screen.getByText('route:route-a')).toBeInTheDocument();
  expect(screen.getByText('production:production-1')).toBeInTheDocument();
  expect(screen.getByText('主账号')).toBeInTheDocument();
});

it('removes a credential from the list after a successful delete', async () => {
  installApi({ items: [credential()] });
  renderPanel();
  const list = await screen.findByRole('list', { name: '已配置的模型凭证' });
  await userEvent.click(within(list).getByRole('button', { name: /删除/ }));

  await waitFor(() => expect(screen.queryByText('主账号')).not.toBeInTheDocument());
  expect(await screen.findByText(EMPTY_CREDENTIALS_TEXT)).toBeInTheDocument();
});

it('reports an unavailable vault without pretending the credential was saved', async () => {
  installApi({ items: [], createFailure: { status: 503, body: { code: 'vault_unavailable', message: 'The OS credential vault is unavailable' } } });
  renderPanel();
  await screen.findByText(EMPTY_CREDENTIALS_TEXT);
  await fillForm();
  await userEvent.click(screen.getByRole('button', { name: '保存' }));

  expect(await screen.findByText(VAULT_UNAVAILABLE_TEXT)).toBeInTheDocument();
  expect(screen.queryByText(/已保存/)).not.toBeInTheDocument();
  expect(screen.getByLabelText('密钥')).toHaveValue('');
  expect(document.body.innerHTML).not.toContain(SECRET);
});

it('does not fake a connection test', async () => {
  const api = installApi({ items: [] });
  renderPanel();
  await screen.findByText(EMPTY_CREDENTIALS_TEXT);
  expect(screen.getByText(CREDENTIAL_TEST_NOTE)).toBeInTheDocument();
  await fillForm();

  await userEvent.click(screen.getByRole('button', { name: '保存并测试' }));

  expect(await screen.findByText(/本次没有保存，也没有执行连接测试/)).toBeInTheDocument();
  expect(screen.queryByText(/测试通过|连接成功|已验证|已保存|保存成功/)).not.toBeInTheDocument();
  expect(api.calls.filter(call => call.method === 'POST')).toHaveLength(0);
});
