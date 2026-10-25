import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import { ProductWorkspaceView } from '../ProductWorkspaceView';
import { bootstrapManagedWorkbench } from '../engine';
import { PRODUCTION_STATUS } from '../productFlow';
import type { ProductionAccepted, ProductionDetail, Schemas } from '../engine';

let dispose: (() => void) | undefined;

const PROJECT: Schemas['ProjectDraft'] = { project_id: 'project-verify', name: '本地测试项目', goal: '', source_text: '', revision: 1, saved_at_us: 1 };
const INSTANCE = 'instance-verify';

function accepted(overrides: Partial<ProductionAccepted> = {}): ProductionAccepted {
  return {
    schema_version: '0.3.0-candidate', instance_id: INSTANCE, production_id: 'production-verify-1',
    run_id: 'run-verify-1', project_id: PROJECT.project_id, request_revision_id: 'request-verify-1',
    status: 'queued', status_path: '/api/v1/productions/production-verify-1', events_path: '/api/v1/runs/run-verify-1/events',
    ...overrides,
  };
}

function detail(status: Schemas['RunStatus'], operations: unknown[] = []): ProductionDetail {
  return {
    ...accepted({ status }), request: {} as never,
    cost: { spent: { currency: 'CNY', amount: '0' }, reserved: { currency: 'CNY', amount: '0' } },
    operations: operations as ProductionDetail['operations'], revision_cycles: 0, bundle_ref: null,
  };
}

type State = {
  projects: Schemas['ProjectDraft'][];
  productions: ProductionAccepted[];
  details: Record<string, ProductionDetail>;
  revisions: Record<string, Schemas['ProductionRevisionSummary'][]>;
  decisions: { runId: string; body: unknown; key: string }[];
  productionBodies: { body: Record<string, unknown>; key: string }[];
};

function installApi(initial: Partial<State> = {}) {
  const state: State = {
    projects: [PROJECT], productions: [], details: {}, revisions: {}, decisions: [], productionBodies: [], ...initial,
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    const method = init?.method ?? 'GET';
    const path = url.pathname;
    const requestHeaders = new Headers(init?.headers);
    const bodyText = String(init?.body ?? '');
    const respond = (status: number, payload: unknown) => ({
      ok: status >= 200 && status < 300, status,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => payload,
    } as unknown as Response);
    if (path === '/api/v1/projects' && method === 'GET') return respond(200, state.projects);
    if (path === '/api/v1/projects' && method === 'POST') {
      const value = JSON.parse(bodyText) as Schemas['ProjectInput'];
      const project = { ...PROJECT, project_id: 'project-created', name: value.name, revision: 1 };
      state.projects = [project];
      return respond(201, project);
    }
    if (path === '/api/v1/productions' && method === 'GET') return respond(200, state.productions);
    if (path === '/api/v1/productions' && method === 'POST') {
      const body = JSON.parse(bodyText) as Record<string, unknown>;
      state.productionBodies.push({ body, key: requestHeaders.get('Idempotency-Key') ?? '' });
      const receipt = accepted({ status: 'queued', production_id: 'production-created' });
      state.productions = [receipt, ...state.productions];
      state.details[receipt.production_id] = detail('queued');
      return respond(202, receipt);
    }
    const productionMatch = /^\/api\/v1\/productions\/([^/]+)$/.exec(path);
    if (productionMatch && method === 'GET') return respond(200, state.details[productionMatch[1]] ?? detail('queued'));
    const revisionsMatch = /^\/api\/v1\/productions\/([^/]+)\/revisions$/.exec(path);
    if (revisionsMatch && method === 'GET') return respond(200, state.revisions[revisionsMatch[1]] ?? []);
    const decisionMatch = /^\/api\/v1\/runs\/([^/]+)\/decisions$/.exec(path);
    if (decisionMatch && method === 'POST') {
      state.decisions.push({ runId: decisionMatch[1], body: JSON.parse(bodyText), key: requestHeaders.get('Idempotency-Key') ?? '' });
      return respond(200, { feedback_id: 'feedback-1', new_run_id: 'run-new' });
    }
    return respond(404, { code: 'not_found', message: 'probe', retryability: 'never', request_id: 'probe' });
  });
  vi.stubGlobal('fetch', fetchMock);
  dispose = bootstrapManagedWorkbench(window.location.origin);
  return { state, fetchMock };
}

function renderWorkspace() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
  return render(<Theme><QueryClientProvider client={client}>
    <ProductWorkspaceView connected instanceId={INSTANCE} knownAssets={[]} onRequestImport={() => {}} onOpenAssets={() => {}} />
  </QueryClientProvider></Theme>);
}

afterEach(() => { dispose?.(); dispose = undefined; cleanup(); vi.restoreAllMocks(); });

it('creates a production with the selected outputs and shows the real accepted state', async () => {
  const { state } = installApi();
  renderWorkspace();
  await screen.findByText('本地测试项目');
  expect(screen.getByText(/暂无可审核项/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('作品目标'), { target: { value: '做一条一分钟的本地介绍' } });
  fireEvent.click(screen.getByRole('button', { name: /提交制作/ }));
  expect(await screen.findByText(/实例已受理/)).toBeInTheDocument();
  expect(state.productionBodies).toHaveLength(1);
  const { body, key } = state.productionBodies[0];
  expect(key).toBeTruthy();
  expect(body).toMatchObject({
    request_format_version: '0.3.0-candidate',
    goal: '做一条一分钟的本地介绍',
    project_id: 'project-verify',
    outputs: ['video', 'subtitles'],
    delivery: 'reference',
  });
  expect(body.inputs).toEqual({ source_text: '', asset_ids: [] });
  expect(body.brief).toMatchObject({ language: 'zh-CN', aspect_ratio: '9:16', target_duration_us: 60_000_000 });
  expect((await screen.findAllByRole('heading', { name: '已受理，排队中' })).length).toBeGreaterThan(0);
});

it('lists real waiting revisions and rejects with a required reason', async () => {
  const production = accepted({ status: 'waiting_user', production_id: 'production-review' });
  const revision: Schemas['ProductionRevisionSummary'] = {
    revision_id: 'revision-plan-1', kind: 'plan',
    expires_at_us: Date.now() * 1000 + 5 * 60 * 1_000_000,
  };
  const { state } = installApi({ productions: [production], details: { [production.production_id]: detail('waiting_user') }, revisions: { [production.production_id]: [revision] } });
  renderWorkspace();
  expect(await screen.findByRole('heading', { name: '制作计划' })).toBeInTheDocument();
  expect(screen.getByText('它是什么')).toBeInTheDocument();
  expect(screen.getByText('会影响什么')).toBeInTheDocument();
  expect(screen.getByText('本次确认有效期')).toBeInTheDocument();
  expect(screen.queryByText(/已过期/)).not.toBeInTheDocument();
  const reject = screen.getByRole('button', { name: /拒绝并保存原因/ });
  expect(reject).toBeDisabled();
  fireEvent.change(screen.getByLabelText(/拒绝原因/), { target: { value: '第三个镜头与主题不符，请保留前两个镜头重做。' } });
  expect(reject).toBeEnabled();
  fireEvent.click(reject);
  expect(await screen.findByText(/已拒绝并保存原因/)).toBeInTheDocument();
  expect(state.decisions).toHaveLength(1);
  expect(state.decisions[0].body).toEqual({
    target_revision_id: 'revision-plan-1',
    action: 'reject',
    instruction_text: '第三个镜头与主题不符，请保留前两个镜头重做。',
    preserved_constraints: [],
  });
});

it('shows a named failure code and human explanation for a failed production', async () => {
  const production = accepted({ status: 'failed', production_id: 'production-failed' });
  const operation = { operation_id: 'op-1', status: 'provider_unavailable', cost_status: 'unknown', actual_cost: null, cost_evidence: '', external_id: null };
  installApi({ productions: [production], details: { [production.production_id]: detail('failed', [operation]) } });
  renderWorkspace();
  fireEvent.click(await screen.findByText(new RegExp(production.production_id)));
  expect(await screen.findByRole('heading', { name: '制作失败' })).toBeInTheDocument();
  expect(await screen.findByText(/错误码：operation_provider_unavailable/)).toBeInTheDocument();
  expect(screen.getByText(/一个执行步骤明确失败/)).toBeInTheDocument();
});

it('maps queued, running, review, success and failure to honest product copy', () => {
  expect(PRODUCTION_STATUS.queued.label).toBe('已受理，排队中');
  expect(PRODUCTION_STATUS.running.label).toBe('制作中');
  expect(PRODUCTION_STATUS.waiting_user.label).toBe('待你审核');
  expect(PRODUCTION_STATUS.succeeded.label).toBe('已完成');
  expect(PRODUCTION_STATUS.failed.label).toBe('制作失败');
  for (const info of Object.values(PRODUCTION_STATUS)) {
    expect(info.label).not.toMatch(/capability_benchmark|embedded_self_issued|not_measured/);
    expect(info.detail.length).toBeGreaterThan(4);
  }
});

it('approves a real waiting revision with the approve action and no instruction', async () => {
  const production = accepted({ status: 'waiting_user', production_id: 'production-approve' });
  const revision: Schemas['ProductionRevisionSummary'] = {
    revision_id: 'revision-quality-1', kind: 'quality',
    expires_at_us: Date.now() * 1000 + 5 * 60 * 1_000_000,
    failure_code: 'alignment_required',
  };
  const { state } = installApi({ productions: [production], details: { [production.production_id]: detail('waiting_user') }, revisions: { [production.production_id]: [revision] } });
  renderWorkspace();
  expect(await screen.findByRole('heading', { name: '质量检查' })).toBeInTheDocument();
  expect(screen.getByText(/制作能力尚未对齐/)).toBeInTheDocument();
  expect(screen.queryByText('alignment_required')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '同意' }));
  expect(await screen.findByText(/已同意/)).toBeInTheDocument();
  expect(state.decisions[0].body).toEqual({
    target_revision_id: 'revision-quality-1', action: 'approve', instruction_text: '', preserved_constraints: [],
  });
});

it('shows an expired review window and disables both decisions', async () => {
  const production = accepted({ status: 'waiting_user', production_id: 'production-expired' });
  const revision: Schemas['ProductionRevisionSummary'] = {
    revision_id: 'revision-quality-expired', kind: 'quality',
    expires_at_us: Date.now() * 1000 - 60 * 1_000_000,
    failure_code: 'media_invalid',
  };
  installApi({ productions: [production], details: { [production.production_id]: detail('waiting_user') }, revisions: { [production.production_id]: [revision] } });
  renderWorkspace();
  expect(await screen.findByRole('heading', { name: '质量检查' })).toBeInTheDocument();
  expect(screen.getByText('本次确认有效期')).toBeInTheDocument();
  expect(screen.getAllByText(/已过期/).length).toBeGreaterThan(0);
  expect(screen.getByText(/素材无法解码或格式不受支持/)).toBeInTheDocument();
  expect(screen.queryByText('media_invalid')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: '同意' })).toBeDisabled();
  expect(screen.getByRole('button', { name: /拒绝并保存原因/ })).toBeDisabled();
});

it('does not invent a review item when nothing is waiting', async () => {
  installApi();
  renderWorkspace();
  await screen.findByText('本地测试项目');
  expect(screen.getByText(/暂无可审核项/)).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole('button', { name: /同意/ })).not.toBeInTheDocument());
});
