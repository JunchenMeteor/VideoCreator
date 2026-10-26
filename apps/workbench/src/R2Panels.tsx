import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge, Button, Callout } from '@radix-ui/themes';
import { Info, Send, Wallet } from 'lucide-react';
import type { ProductionInput } from './engine';
import {
  budgetStatusText, costAmountText, costBasisText, exclusionText,
  previewProduction, publishProduction, publishReasonText, readBudget, type ProductionPreview,
} from './r2Api';

function PanelHeading({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="stage-heading"><span className="section-kicker">预算与费用</span><h2>{title}</h2><p>{children}</p></div>;
}

export function BudgetPanel({ connected, instanceId }: { connected: boolean; instanceId?: string }) {
  const budget = useQuery({
    queryKey: ['budget', instanceId],
    enabled: connected,
    queryFn: () => readBudget(),
    retry: false,
  });
  return <section className="product-section" aria-label="预算与费用">
    <div className="r2-heading"><Wallet size={21} strokeWidth={1.7} aria-hidden="true" /><PanelHeading title="预算与费用">{'预算状态来自本机实例；未授权时不会给出任何假设额度。'}</PanelHeading></div>
    {budget.isPending && connected ? <p role="status">正在读取预算状态…</p> : null}
    {budget.error ? <Callout.Root color="amber" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>预算状态暂不可用。不会显示一个假设的额度。</Callout.Text></Callout.Root> : null}
    {budget.data ? <>
      <div className="r2-status-row">
        <Badge color={budget.data.present ? (budget.data.authorization === 'local_zero_cost' ? 'teal' : 'amber') : 'gray'} variant="soft">{budgetStatusText(budget.data)}</Badge>
        {budget.data.present ? <span className="small-note">费用组：{budget.data.group_id ?? '当前实例'}</span> : null}
      </div>
      {!budget.data.present ? <p className="r2-statement" role="note">未授权付费预算。实例没有付费预算授权；这里不会给出可花费额度。</p> : <dl className="review-facts r2-facts">
        <div><dt>预算上限</dt><dd>{costAmountText(budget.data.cap)}</dd></div>
        <div><dt>已花费</dt><dd>{costAmountText(budget.data.spent)}</dd></div>
        <div><dt>已预留</dt><dd>{costAmountText(budget.data.reserved)}</dd></div>
      </dl>}
    </> : null}
    <details className="advanced-settings" open><summary>费用口径（三种说法）<Info size={13} /></summary><div>
      {(['confirmed_no_charge', 'usage_price_calculation', 'unknown'] as const).map(basis => <p key={basis}><strong>{costBasisText(basis)}</strong></p>)}
      <p className="small-note">这三种口径不会互相替代：估算不是账单，待核实不会显示成数字。</p>
    </div></details>
  </section>;
}

function useHeldPreview(body: ProductionInput | null): ProductionInput | null {
  const signature = body ? JSON.stringify(body) : '';
  const [held, setHeld] = useState<ProductionInput | null>(body);
  useEffect(() => {
    if (!body) { setHeld(null); return; }
    const timer = window.setTimeout(() => setHeld(body), 400);
    return () => window.clearTimeout(timer);
  }, [signature]);
  return held;
}

export function ProductionPreviewPanel({ connected, body }: { connected: boolean; body: ProductionInput | null }) {
  const held = useHeldPreview(body);
  const preview = useQuery({
    queryKey: ['production-preview', held ? JSON.stringify(held) : 'empty'],
    enabled: connected && Boolean(held),
    queryFn: () => previewProduction(held!),
    retry: false,
    staleTime: 5000,
  });
  if (!body) return <section className="r2-preview" aria-label="费用预览"><p className="small-note">填写目标并选择项目后，提交前会显示费用预览。</p></section>;
  const data: ProductionPreview | undefined = preview.data;
  return <section className="r2-preview" aria-label="费用预览" aria-busy={preview.isPending}>
    <div className="r2-preview-heading"><strong>费用预览</strong>{data ? <Badge color="gray" variant="soft">{costBasisText(data.cost_basis)}</Badge> : null}</div>
    {preview.isPending ? <p className="small-note" role="status">正在估算这次制作的费用口径…</p> : null}
    {preview.error ? <p className="small-note" role="status">费用预览暂不可用；这不等于免费，也不会显示一个假设金额。</p> : null}
    {data ? <dl className="review-facts r2-facts">
      <div><dt>费用上限</dt><dd>{costAmountText(data.max_cost)}</dd></div>
      <div><dt>费用口径</dt><dd>{costBasisText(data.cost_basis)}{data.cost_basis === 'unknown' ? '（不显示金额）' : ''}</dd></div>
      <div><dt>排除原因</dt><dd>{data.excluded_reasons.length ? <ul className="authorization-reasons">{data.excluded_reasons.map(reason => <li key={reason}>{exclusionText(reason)}</li>)}</ul> : '无排除项'}</dd></div>
    </dl> : null}
    {data?.cost_basis === 'confirmed_no_charge' ? <p className="small-note">这是“已确认不收费”的本地口径，不是从价目表推算。</p> : null}
    {data?.cost_basis === 'usage_price_calculation' ? <p className="small-note">这是按价目估算，不是账单；实际费用仍以实例记录为准。</p> : null}
    {data?.cost_basis === 'unknown' ? <p className="small-note">费用待核实；没有金额可显示。</p> : null}
  </section>;
}

export function PublishPanel({ connected, productionId }: { connected: boolean; productionId?: string }) {
  const publish = useQuery({
    queryKey: ['publish-availability', productionId],
    enabled: connected && Boolean(productionId),
    queryFn: () => publishProduction(productionId!),
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  const unavailable = publish.data;
  const reason = !connected ? '未连接实例，无法检查发布能力'
    : !productionId ? '完成作品后可检查发布能力'
      : unavailable ? publishReasonText(unavailable.reason)
        : publish.error ? '发布能力待核实' : '正在检查发布能力…';
  return <section className="product-section publish-panel" aria-labelledby="publish-title">
    <div className="r2-heading"><Send size={20} strokeWidth={1.7} aria-hidden="true" /><div className="stage-heading"><span className="section-kicker">发布</span><h2 id="publish-title">发布到平台</h2><p>平台发布需要本机适配器和平台账号授权；当前切片没有可用的发布路径。</p></div></div>
    <div className="publish-row">
      <Button size="2" disabled title={reason} aria-describedby="publish-reason">发布</Button>
      <Badge color="gray" variant="soft">不可用</Badge>
      <span id="publish-reason" className="publish-reason">{reason}</span>
    </div>
    <p className="small-note">需要先在设置里配置平台账号（当前不支持）。没有平台发布适配器时，发布始终是“不可用”。</p>
  </section>;
}
