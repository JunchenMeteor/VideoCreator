import type { ProductionInput } from './engine';

/**
 * R2 slice endpoints are not in the generated client yet; they are same-origin
 * installation-session endpoints, so this module uses the managed proxy with
 * the same marker the generated client uses. It never reads or stores a token.
 */

export type CostBasis = 'confirmed_no_charge' | 'usage_price_calculation' | 'unknown';
export type CostAmount = {
  kind: 'confirmed' | 'unknown' | 'not_configured';
  amount: string | null;
  currency: string | null;
};
export type BudgetSummary = {
  present: boolean;
  group_id?: string | null;
  authorization: 'none' | 'local_zero_cost' | 'authorized_cap';
  cap: CostAmount;
  spent: CostAmount;
  reserved: CostAmount;
};
export type ProductionPreview = {
  max_cost: CostAmount;
  excluded_reasons: string[];
  cost_basis: CostBasis;
};
export type PublishUnavailable = {
  status: 'unavailable';
  code: 'publish_unavailable';
  reason: string;
};

export const COST_BASIS_TEXT: Readonly<Record<CostBasis, string>> = {
  confirmed_no_charge: '本地零成本（已确认不收费）',
  usage_price_calculation: '按价目估算，非账单',
  unknown: '待核实',
};

export const PUBLISH_REASON = '本实例未安装平台发布适配器';

export class R2ApiFailure extends Error {
  constructor(public readonly status: number, public readonly code: string) {
    super(code);
    this.name = 'R2ApiFailure';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function costAmount(value: unknown): CostAmount | null {
  if (!isRecord(value) || !['confirmed', 'unknown', 'not_configured'].includes(String(value.kind))) return null;
  const amount = typeof value.amount === 'string' || value.amount === null ? value.amount : null;
  const currency = typeof value.currency === 'string' || value.currency === null ? value.currency : null;
  if (value.kind === 'confirmed' && (amount === null || currency === null)) return null;
  return { kind: value.kind as CostAmount['kind'], amount, currency };
}

function envelopeCode(value: unknown): string {
  return isRecord(value) && typeof value.code === 'string' && /^[a-z0-9_]{1,80}$/.test(value.code)
    ? value.code : 'r2_request_failed';
}

async function request(path: string, init: { method: 'GET' | 'POST'; body?: unknown; signal?: AbortSignal }): Promise<Response> {
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
    throw new R2ApiFailure(0, 'r2_transport_unavailable');
  }
}

export async function readBudget(signal?: AbortSignal): Promise<BudgetSummary> {
  const response = await request('/api/v1/budget', { method: 'GET', signal });
  if (!response.ok) throw new R2ApiFailure(response.status, envelopeCode(await response.json().catch(() => undefined)));
  const value = await response.json().catch(() => undefined);
  if (!isRecord(value) || typeof value.present !== 'boolean') throw new R2ApiFailure(502, 'r2_response_invalid');
  if (!['none', 'local_zero_cost', 'authorized_cap'].includes(String(value.authorization))) throw new R2ApiFailure(502, 'r2_response_invalid');
  const cap = costAmount(value.cap);
  const spent = costAmount(value.spent);
  const reserved = costAmount(value.reserved);
  if (!cap || !spent || !reserved) throw new R2ApiFailure(502, 'r2_response_invalid');
  return {
    present: value.present,
    group_id: typeof value.group_id === 'string' ? value.group_id : null,
    authorization: value.authorization as BudgetSummary['authorization'],
    cap, spent, reserved,
  };
}

export async function previewProduction(body: ProductionInput, signal?: AbortSignal): Promise<ProductionPreview> {
  const response = await request('/api/v1/productions/preview', { method: 'POST', body, signal });
  if (!response.ok) throw new R2ApiFailure(response.status, envelopeCode(await response.json().catch(() => undefined)));
  const value = await response.json().catch(() => undefined);
  if (!isRecord(value)) throw new R2ApiFailure(502, 'r2_response_invalid');
  const maxCost = costAmount(value.max_cost);
  const basis = value.cost_basis;
  if (!maxCost || !['confirmed_no_charge', 'usage_price_calculation', 'unknown'].includes(String(basis))
    || !Array.isArray(value.excluded_reasons) || !value.excluded_reasons.every(item => typeof item === 'string')) {
    throw new R2ApiFailure(502, 'r2_response_invalid');
  }
  return { max_cost: maxCost, excluded_reasons: value.excluded_reasons, cost_basis: basis as CostBasis };
}

export async function publishProduction(productionId: string, signal?: AbortSignal): Promise<PublishUnavailable> {
  const response = await request(`/api/v1/productions/${encodeURIComponent(productionId)}/publish`, { method: 'POST', signal });
  const value = await response.json().catch(() => undefined);
  if (response.status === 503 && isRecord(value) && value.code === 'publish_unavailable') {
    return {
      status: 'unavailable',
      code: 'publish_unavailable',
      reason: typeof value.reason === 'string' && value.reason ? value.reason : PUBLISH_REASON,
    };
  }
  if (!response.ok) throw new R2ApiFailure(response.status, envelopeCode(value));
  // The frozen slice has no successful publish path. Never claim one.
  throw new R2ApiFailure(502, 'publish_contract_unexpected');
}

export function costBasisText(basis: CostBasis): string {
  return COST_BASIS_TEXT[basis];
}

export function budgetStatusText(budget: BudgetSummary): string {
  if (!budget.present) return '未授权付费预算';
  if (budget.authorization === 'local_zero_cost') return '本地零成本（已确认不收费）';
  return '已授权付费预算';
}

/** A confirmed cost may be shown. Unknown/not-configured never becomes 0. */
export function costAmountText(cost: CostAmount): string {
  if (cost.kind === 'confirmed' && cost.amount !== null) {
    return `${cost.currency ?? ''} ${cost.amount}`.trim();
  }
  return cost.kind === 'not_configured' ? '未配置' : '待核实';
}

export function exclusionText(reason: string): string {
  if (reason === 'no_routes_selected') return '没有选择可用的模型路线';
  if (reason.startsWith('route_unavailable:')) {
    const route = reason.slice('route_unavailable:'.length);
    return `模型路线不可用：${route}`;
  }
  return reason;
}

export function publishReasonText(reason: string): string {
  return reason === 'No platform publishing adapter is installed for this instance'
    ? PUBLISH_REASON
    : reason || PUBLISH_REASON;
}
