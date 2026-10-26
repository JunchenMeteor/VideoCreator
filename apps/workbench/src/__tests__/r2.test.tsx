import { afterEach, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import { BudgetPanel, ProductionPreviewPanel, PublishPanel } from '../R2Panels';
import type { ProductionInput } from '../engine';
import type { CostAmount } from '../r2Api';

function respond(status: number, payload: unknown): Response {
  return { ok: status >= 200 && status < 300, status, headers: new Headers({ 'content-type': 'application/json' }), json: async () => payload } as unknown as Response;
}

function installApi(routes: Record<string, { status: number; body: unknown }>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), window.location.origin);
    const key = `${url.pathname}`;
    const route = routes[key];
    if (!route) return respond(404, { code: 'not_found', message: 'probe', retryability: 'never', request_id: 'probe' });
    return respond(route.status, route.body);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderPanel(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
  return render(<Theme><QueryClientProvider client={client}>{node}</QueryClientProvider></Theme>);
}

const BODY = { request_format_version: '0.3.0-candidate', goal: '预览测试', outputs: ['video'], delivery: 'reference' } as unknown as ProductionInput;
const NONE: CostAmount = { kind: 'not_configured', amount: null, currency: null };
const UNKNOWN: CostAmount = { kind: 'unknown', amount: null, currency: null };

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('shows no budget without inventing a 0-yuan allowance', async () => {
  installApi({ '/api/v1/budget': { status: 200, body: { present: false, authorization: 'none', cap: NONE, spent: NONE, reserved: NONE } } });
  renderPanel(<BudgetPanel connected instanceId="instance-verify" />);
  expect(await screen.findByText('未授权付费预算')).toBeInTheDocument();
  expect(screen.queryByText(/CNY|¥|0\.00|0 元/)).not.toBeInTheDocument();
  expect(screen.queryByText('预算上限')).not.toBeInTheDocument();
  expect(screen.getByText('本地零成本（已确认不收费）')).toBeInTheDocument();
});

it.each([
  ['confirmed_no_charge', '本地零成本（已确认不收费）', { kind: 'confirmed', amount: '0', currency: 'CNY' }],
  ['usage_price_calculation', '按价目估算，非账单', UNKNOWN],
  ['unknown', '待核实', UNKNOWN],
] as const)('renders cost basis %s without pretending unknown is a number', async (basis, text, maxCost) => {
  installApi({ '/api/v1/productions/preview': { status: 200, body: { max_cost: maxCost, excluded_reasons: basis === 'usage_price_calculation' ? ['route_unavailable:local.asr.test'] : [], cost_basis: basis } } });
  renderPanel(<ProductionPreviewPanel connected body={BODY} />);
  expect((await screen.findAllByText(new RegExp(text))).length).toBeGreaterThan(0);
  if (basis === 'unknown') {
    expect(screen.getByText(/费用待核实；没有金额可显示/)).toBeInTheDocument();
    expect(screen.queryByText(/CNY/)).not.toBeInTheDocument();
  }
  if (basis === 'usage_price_calculation') {
    expect(screen.getByText(/模型路线不可用/)).toBeInTheDocument();
    expect(screen.getByText(/按价目估算，不是账单/)).toBeInTheDocument();
  }
});

it('shows the preview cap and exclusion reasons before submit', async () => {
  installApi({ '/api/v1/productions/preview': { status: 200, body: { max_cost: { kind: 'confirmed', amount: '12.50', currency: 'CNY' }, excluded_reasons: ['no_routes_selected'], cost_basis: 'confirmed_no_charge' } } });
  renderPanel(<ProductionPreviewPanel connected body={BODY} />);
  expect(await screen.findByText('费用上限')).toBeInTheDocument();
  expect(screen.getByText('CNY 12.50')).toBeInTheDocument();
  expect(screen.getByText('没有选择可用的模型路线')).toBeInTheDocument();
});

it('shows publish as unavailable with the reason, never as a failure or success', async () => {
  installApi({ '/api/v1/productions/production-verify/publish': { status: 503, body: { status: 'unavailable', code: 'publish_unavailable', reason: 'No platform publishing adapter is installed for this instance' } } });
  renderPanel(<PublishPanel connected productionId="production-verify" />);
  expect(await screen.findByText('本实例未安装平台发布适配器')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '发布' })).toBeDisabled();
  expect(screen.getByText('不可用')).toBeInTheDocument();
  expect(screen.getByText(/需要先在设置里配置平台账号（当前不支持）/)).toBeInTheDocument();
  expect(screen.queryByText(/发布失败|已发布|发布成功/)).not.toBeInTheDocument();
});
