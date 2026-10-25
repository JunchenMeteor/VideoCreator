import { useEffect, useMemo, useRef, useState } from 'react';
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge, Button, Callout, Checkbox, Flex, Select, TextArea, TextField } from '@radix-ui/themes';
import { Check, ChevronRight, Clapperboard, FileText, RefreshCw, ShieldCheck, Upload, X } from 'lucide-react';
import { engineData, errorMessage, RequestFailure } from './engine';
import type { AssetRecord, ProductionAccepted, ProductionInput, Schemas } from './engine';
import { RevisionView } from './RevisionView';
import { DeliveryView } from './DeliveryView';
import {
  formatBytes, latestReviewRevisions, OUTPUT_LABEL, PRODUCTION_STATUS, productionFailure,
  productionStatusInfo, reviewFailureText, reviewKindOf, REVIEW_INFO, REVIEW_KINDS, REVIEW_VALIDITY,
  shortSha, VOICE_OUTPUTS, waitingProductions,
} from './productFlow';
import type { OutputRole, ReviewKind } from './productFlow';

type Props = {
  connected: boolean;
  instanceId?: string;
  knownAssets: readonly AssetRecord[];
  onRequestImport: () => void;
  onOpenAssets: () => void;
};

const LANGUAGE_OPTIONS = [
  { value: 'zh-CN', label: '中文（普通话）' },
  { value: 'en-US', label: 'English (US)' },
  { value: 'ja-JP', label: '日本語' },
] as const;
const DURATION_OPTIONS = [
  { value: '30', label: '约 30 秒' },
  { value: '60', label: '约 1 分钟' },
  { value: '120', label: '约 2 分钟' },
] as const;
const ASPECT_OPTIONS = [
  { value: '9:16', label: '竖屏 9:16' },
  { value: '16:9', label: '横屏 16:9' },
] as const;
const DEFAULT_PROJECT = 'project-local-install-0001';

function newKey() {
  return crypto.randomUUID();
}

function failureText(error: unknown): string {
  if (error instanceof RequestFailure) return `${error.code}：${errorMessage(error)}`;
  return errorMessage(error);
}

function StatusBadge({ status }: { status: Schemas['RunStatus'] }) {
  const info = productionStatusInfo(status);
  const color = info.tone === 'failed' ? 'red' : info.tone === 'done' ? 'teal' : info.tone === 'waiting' ? 'amber' : 'gray';
  return <Badge color={color} variant="soft">{info.label}</Badge>;
}

function ReviewCard({ production, revision, projectName, connected, onChanged, onDecision }: {
  production: ProductionAccepted;
  revision: Schemas['CreativeRevision'];
  projectName?: string;
  connected: boolean;
  onChanged: () => void;
  onDecision: (message: string) => void;
}) {
  const reviewKind: ReviewKind | null = reviewKindOf(revision.kind) ? revision.kind : null;
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [done, setDone] = useState('');
  const approveIntent = useRef<{ key: string; signature: string } | null>(null);
  const rejectIntent = useRef<{ key: string; signature: string } | null>(null);
  const code = revision.body && typeof revision.body === 'object' && 'code' in revision.body && typeof revision.body.code === 'string'
    ? revision.body.code : undefined;
  const codeText = reviewFailureText(code);
  const info = reviewKind ? REVIEW_INFO[reviewKind] : null;

  const decide = async (action: 'approve' | 'reject') => {
    if (!connected || busy || done) return;
    if (action === 'reject' && !reason.trim()) {
      setFailure(new RequestFailure(400, 'invalid_request'));
      return;
    }
    setBusy(true); setFailure(null);
    try {
      const signature = action === 'approve' ? 'approve' : `reject:${reason.trim()}`;
      const intentRef = action === 'approve' ? approveIntent : rejectIntent;
      if (intentRef.current?.signature !== signature) {
        intentRef.current = { key: newKey(), signature };
      }
      await engineData('POST /api/v1/runs/{run_id}/decisions', {
        path: { run_id: production.run_id },
        body: {
          target_revision_id: revision.revision_id,
          action,
          instruction_text: action === 'reject' ? reason.trim() : '',
          preserved_constraints: [],
        },
        headers: { 'Idempotency-Key': intentRef.current.key },
      });
      const message = action === 'approve' ? '已同意。制作会按这条决定继续。' : '已拒绝并保存原因。这条决定不会把内容当成通过。';
      setDone(message);
      onDecision(message);
      onChanged();
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  };

  return <article className="review-card" aria-label={`${info?.title ?? revision.kind}待审核`}>
    <div className="review-card-heading">
      <div>
        <span className="section-kicker">待你审核 · {production.production_id.slice(-8)}</span>
        <h3>{info?.title ?? revision.kind}</h3>
      </div>
      <Badge color="amber" variant="soft">等待决定</Badge>
    </div>
    <dl className="review-facts">
      <div><dt>它是什么</dt><dd>{info?.what ?? '一项需要确认的创作产物。'}</dd></div>
      <div><dt>会影响什么</dt><dd>{info?.impact ?? '决定会固定到当前任务。'}</dd></div>
      <div><dt>有效期</dt><dd>{REVIEW_VALIDITY}</dd></div>
      <div><dt>所属作品</dt><dd>{projectName ?? '当前实例作品'} · {production.production_id}</dd></div>
      {code ? <div><dt>检查代码</dt><dd><code>{code}</code>{codeText ? `：${codeText}` : '：实例返回的具名检查结果。'}</dd></div> : null}
    </dl>
    <details className="review-detail"><summary>查看这份产物的实际内容<ChevronRight size={13} /></summary><RevisionView revision={revision} /></details>
    {failure ? <Callout.Root color="red" role="alert"><Callout.Text>{failureText(failure)}</Callout.Text></Callout.Root> : null}
    {!done ? <>
      <label className="field-label" htmlFor={`review-reason-${revision.revision_id}`}>拒绝原因（拒绝时必填）</label>
      <TextArea id={`review-reason-${revision.revision_id}`} size="2" value={reason} disabled={busy} placeholder="例如：第三个镜头与主题不符，请保留前两个镜头重做。" onChange={event => setReason(event.target.value)} />
      <Flex gap="3" wrap="wrap" className="review-actions">
        <Button size="2" disabled={!connected || busy} onClick={() => void decide('approve')}><Check size={15} />同意</Button>
        <Button size="2" variant="soft" color="red" disabled={!connected || busy || !reason.trim()} onClick={() => void decide('reject')}><X size={15} />拒绝并保存原因</Button>
      </Flex>
    </> : null}
  </article>;
}

function ReviewQueue({ connected, productions, projects, onSelectProduction, onChanged, onDecision }: {
  connected: boolean;
  productions: readonly ProductionAccepted[];
  projects: readonly Schemas['ProjectDraft'][] | undefined;
  onSelectProduction: (production: ProductionAccepted) => void;
  onChanged: () => void;
  onDecision: (message: string) => void;
}) {
  const waiting = useMemo(() => waitingProductions(productions), [productions]);
  const uniqueWaiting = useMemo(() => {
    const seen = new Set<string>();
    return waiting.filter(item => seen.has(item.production_id) ? false : (seen.add(item.production_id), true));
  }, [waiting]);
  const revisionQueries = useQueries({
    queries: uniqueWaiting.map(production => ({
      queryKey: ['product-review-revisions', production.production_id],
      enabled: connected,
      queryFn: () => engineData('GET /api/v1/productions/{production_id}/revisions', { path: { production_id: production.production_id } }),
      refetchInterval: 4000,
    })),
  });
  const items = uniqueWaiting.flatMap((production, index) => {
    const revisions = revisionQueries[index]?.data;
    if (!revisions) return [];
    return latestReviewRevisions(revisions).map(({ kind, revision }) => ({ production, kind, revision }));
  });
  return <section className="product-section" aria-labelledby="review-title">
    <div className="stage-heading"><span className="section-kicker">待我审核</span><h2 id="review-title">先确认，再继续</h2><p>每条都来自实例中真实的制作计划或质量检查；没有待审项时不会造一条。</p></div>
    {!uniqueWaiting.length ? <p className="product-empty">暂无可审核项。任务进入“待你审核”后，计划或质量检查会出现在这里。</p> : null}
    {uniqueWaiting.length && !items.length ? <p className="product-empty" role="status">任务正在等待审核，但还没有可读取的计划或质量检查。请刷新或稍后再看。</p> : null}
    <div className="review-list">{items.map(({ production, revision }) => <div key={`${production.production_id}:${revision.revision_id}`}>
      <ReviewCard production={production} revision={revision} connected={connected}
        projectName={projects?.find(item => item.project_id === production.project_id)?.name}
        onChanged={onChanged} onDecision={onDecision} />
      <Button size="1" variant="ghost" color="gray" onClick={() => onSelectProduction(production)}>查看这条作品状态</Button>
    </div>)}</div>
  </section>;
}

function SelectedProduction({ connected, production, projectName, onOpenAssets }: {
  connected: boolean;
  production?: ProductionAccepted;
  projectName?: string;
  onOpenAssets: () => void;
}) {
  const detail = useQuery({
    queryKey: ['product-detail', production?.production_id],
    enabled: connected && Boolean(production),
    queryFn: () => engineData('GET /api/v1/productions/{production_id}', { path: { production_id: production!.production_id } }),
    refetchInterval: query => ['queued', 'running', 'waiting_user', 'waiting_provider', 'waiting_authorization'].includes(query.state.data?.status ?? '') ? 3000 : false,
  });
  const revisions = useQuery({
    queryKey: ['product-selected-revisions', production?.production_id],
    enabled: connected && Boolean(production),
    queryFn: () => engineData('GET /api/v1/productions/{production_id}/revisions', { path: { production_id: production!.production_id } }),
    refetchInterval: production ? 4000 : false,
  });
  if (!production) return <section className="product-section"><div className="stage-heading"><span className="section-kicker">作品状态</span><h2>还没有选中作品</h2><p>创建或点击上方作品后，这里会显示真实执行状态。没有任务时不会显示“已完成”。</p></div></section>;
  const status = detail.data?.status ?? production.status;
  const operations = detail.data?.operations ?? [];
  const info = productionStatusInfo(status);
  const failure = status === 'failed' ? productionFailure({ status, operations }) : null;
  const bundleRef = detail.data?.bundle_ref;
  const reviewCount = (revisions.data ?? []).filter(item => reviewKindOf(item.kind)).length;
  return <section className="product-section" aria-labelledby="status-title">
    <div className="product-section-heading">
      <div className="stage-heading"><span className="section-kicker">作品状态</span><h2 id="status-title">{info.label}</h2><p>{info.detail}</p></div>
      <div className="product-status-badges"><StatusBadge status={status} />{reviewCount ? <Badge color="amber" variant="soft">{reviewCount} 项待审</Badge> : null}</div>
    </div>
    <dl className="review-facts">
      <div><dt>作品</dt><dd>{projectName ?? '当前实例作品'} · {production.production_id}</dd></div>
      <div><dt>执行编号</dt><dd><code>{production.run_id}</code></dd></div>
      <div><dt>费用</dt><dd>{operations.some(item => item.cost_status === 'unknown') ? '费用待核实' : operations.length ? `已记录 CNY ${detail.data?.cost.spent.amount ?? '0'}` : '尚无模型调用记录'}</dd></div>
      <div><dt>下一步</dt><dd>{status === 'waiting_user' ? '先在上方“待我审核”中确认计划或质量检查。' : status === 'succeeded' ? '在下方“取片”中下载成片与字幕。' : status === 'failed' ? '按错误码核对后重新创建；已有内容仍保留。' : '可以关闭页面，任务会在本机继续。'}</dd></div>
    </dl>
    {failure ? <Callout.Root color="red" role="alert" className="product-failure">
      <Callout.Icon><ShieldCheck size={16} /></Callout.Icon>
      <Callout.Text><strong>错误码：{failure.code}</strong><p>{failure.detail}</p></Callout.Text>
    </Callout.Root> : null}
    <Flex gap="3" wrap="wrap" className="production-actions">
      <Button variant="soft" size="2" onClick={() => void detail.refetch()}><RefreshCw size={14} />刷新状态</Button>
      {bundleRef ? <Button size="2" variant="soft" onClick={() => { document.getElementById('product-delivery')?.scrollIntoView({ behavior: 'smooth' }); }}><Clapperboard size={14} />去取片</Button> : null}
    </Flex>
    {bundleRef ? <div id="product-delivery"><DeliveryView key={bundleRef.bundle_revision_id} bundleRef={bundleRef} connected={connected} status={status} onAssets={onOpenAssets} /></div> : null}
    {status === 'succeeded' && !bundleRef ? <p className="product-empty">实例报告已完成，但还没有可读取的作品包；不会把“已完成”当作可取片。</p> : null}
    {reviewCount && status === 'waiting_user' ? <p className="small-note">审核队列在页面顶部；同意或拒绝后这里的状态会刷新。</p> : null}
  </section>;
}

export function ProductWorkspaceView({ connected, instanceId, knownAssets, onRequestImport, onOpenAssets }: Props) {
  const queryClient = useQueryClient();
  const projects = useQuery({
    queryKey: ['product-projects', instanceId],
    enabled: connected,
    queryFn: () => engineData('GET /api/v1/projects', {}),
  });
  const productions = useQuery({
    queryKey: ['product-productions', instanceId],
    enabled: connected,
    queryFn: () => engineData('GET /api/v1/productions', {}),
    refetchInterval: 3000,
  });
  const [selected, setSelected] = useState<{ productionId: string; projectId: string } | null>(null);
  const [projectId, setProjectId] = useState('');
  const [newProjectName, setNewProjectName] = useState('');
  const [goal, setGoal] = useState('');
  const [sourceText, setSourceText] = useState('');
  const [assetIds, setAssetIds] = useState<string[]>([]);
  const [manualAsset, setManualAsset] = useState('');
  const [extras, setExtras] = useState<OutputRole[]>(['subtitles']);
  const [language, setLanguage] = useState<string>('zh-CN');
  const [duration, setDuration] = useState<string>('60');
  const [aspect, setAspect] = useState<string>('9:16');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [formError, setFormError] = useState('');
  const [notice, setNotice] = useState('');
  const [reviewNotice, setReviewNotice] = useState('');
  const productionIntent = useRef<{ key: string; signature: string } | null>(null);
  const projectIntent = useRef<{ key: string; signature: string } | null>(null);

  useEffect(() => {
    if (!projectId && projects.data?.length) setProjectId(projects.data[0].project_id);
  }, [projects.data, projectId]);

  const selectedProduction = productions.data?.find(item => item.production_id === selected?.productionId);
  const selectedProjectName = projects.data?.find(item => item.project_id === selectedProduction?.project_id)?.name;
  const selectedAssetRecords = knownAssets.filter(asset => assetIds.includes(asset.asset_id));

  const addManualAsset = () => {
    const id = manualAsset.trim();
    if (!/^[A-Za-z0-9_.:-]{1,128}$/.test(id)) { setFormError('素材编号格式不正确。'); return; }
    if (!assetIds.includes(id)) setAssetIds(current => [...current, id]);
    setManualAsset(''); setFormError('');
  };

  const submit = async () => {
    if (!connected || busy) return;
    setFormError(''); setFailure(null); setNotice('');
    if (!goal.trim()) { setFormError('请先填写作品目标。'); return; }
    if ((!projectId || projectId === 'new') && !newProjectName.trim()) { setFormError('请选择已有项目，或填写新项目名称。'); return; }
    setBusy(true);
    try {
      let destination = projectId;
      if (!destination || destination === 'new') {
        const signature = JSON.stringify([newProjectName.trim(), goal, sourceText]);
        if (projectIntent.current?.signature !== signature) projectIntent.current = { key: newKey(), signature };
        const project = await engineData('POST /api/v1/projects', {
          body: { name: newProjectName.trim() || '未命名作品', goal, source_text: sourceText },
          headers: { 'Idempotency-Key': projectIntent.current.key },
        });
        destination = project.project_id;
        setProjectId(project.project_id);
        await queryClient.invalidateQueries({ queryKey: ['product-projects', instanceId] });
      }
      const body: ProductionInput = {
        request_format_version: '0.3.0-candidate',
        goal,
        project_id: destination,
        inputs: { source_text: sourceText, asset_ids: [...new Set(assetIds)] },
        source_bindings: [],
        brief: { language, aspect_ratio: aspect as '9:16' | '16:9', target_duration_us: Number(duration) * 1_000_000, guidance: '请优先给出可审核的制作计划，等待用户确认后再继续。' },
        automation: { mode: 'interactive', max_revision_cycles: 2 },
        outputs: ['video', ...VOICE_OUTPUTS.filter(role => extras.includes(role))],
        delivery: 'reference',
      };
      const signature = JSON.stringify(body);
      if (productionIntent.current?.signature !== signature) productionIntent.current = { key: newKey(), signature };
      const receipt = await engineData('POST /api/v1/productions', {
        body,
        headers: { 'Idempotency-Key': productionIntent.current.key },
      });
      if (receipt.instance_id !== instanceId || receipt.project_id !== destination) throw new RequestFailure(409, 'submission_identity_mismatch');
      productionIntent.current = null;
      setSelected({ productionId: receipt.production_id, projectId: receipt.project_id });
      setNotice(`实例已受理：${PRODUCTION_STATUS[receipt.status].label}。作品编号 ${receipt.production_id}。`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-productions', instanceId] }),
        queryClient.invalidateQueries({ queryKey: ['product-detail', receipt.production_id] }),
        queryClient.invalidateQueries({ queryKey: ['product-selected-revisions', receipt.production_id] }),
      ]);
    } catch (error) {
      setFailure(error);
    } finally {
      setBusy(false);
    }
  };

  const selectProduction = (production: ProductionAccepted) => setSelected({ productionId: production.production_id, projectId: production.project_id });

  return <div className="product-workspace">
    <section className="product-section" aria-labelledby="create-product-title">
      <div className="stage-heading"><span className="section-kicker">创建作品</span><h2 id="create-product-title">做一条能取片的作品</h2><p>选项目、资料和输出，一次提交给本机实例。每个请求都走同源接口，不在页面保存安装凭证。</p></div>
      <div className="product-form">
        <div>
          <label className="field-label" htmlFor="product-project">项目</label>
          <Select.Root value={projectId} onValueChange={value => { setProjectId(value); setFormError(''); }} disabled={busy}>
            <Select.Trigger id="product-project" aria-label="选择项目" />
            <Select.Content>
              {(projects.data ?? []).map(item => <Select.Item key={item.project_id} value={item.project_id}>{item.name}</Select.Item>)}
              <Select.Item value="new">新建项目</Select.Item>
            </Select.Content>
          </Select.Root>
          {projectId === 'new' ? <TextField.Root mt="2" aria-label="新项目名称" placeholder="新项目名称" value={newProjectName} disabled={busy} onChange={event => setNewProjectName(event.target.value)} /> : null}
        </div>
        <div className="product-form-wide">
          <label className="field-label" htmlFor="product-goal">作品目标</label>
          <TextArea id="product-goal" className="goal-input" size="3" value={goal} disabled={busy} placeholder="例如：用一分钟介绍这次更新里最值得体验的内容。" onChange={event => setGoal(event.target.value)} />
        </div>
        <div className="product-form-wide">
          <label className="field-label" htmlFor="product-source">文字资料（可选）</label>
          <TextArea id="product-source" size="2" value={sourceText} disabled={busy} placeholder="粘贴文章、产品介绍或已有资料。" onChange={event => setSourceText(event.target.value)} />
        </div>
        <div><label className="field-label" htmlFor="product-language">语言</label><Select.Root value={language} onValueChange={setLanguage} disabled={busy}><Select.Trigger id="product-language" /><Select.Content>{LANGUAGE_OPTIONS.map(item => <Select.Item key={item.value} value={item.value}>{item.label}</Select.Item>)}</Select.Content></Select.Root></div>
        <div><label className="field-label" htmlFor="product-duration">时长</label><Select.Root value={duration} onValueChange={setDuration} disabled={busy}><Select.Trigger id="product-duration" /><Select.Content>{DURATION_OPTIONS.map(item => <Select.Item key={item.value} value={item.value}>{item.label}</Select.Item>)}</Select.Content></Select.Root></div>
        <div><label className="field-label" htmlFor="product-aspect">画幅</label><Select.Root value={aspect} onValueChange={setAspect} disabled={busy}><Select.Trigger id="product-aspect" /><Select.Content>{ASPECT_OPTIONS.map(item => <Select.Item key={item.value} value={item.value}>{item.label}</Select.Item>)}</Select.Content></Select.Root></div>
      </div>

      <fieldset className="product-fieldset">
        <legend>输出</legend>
        <label className="product-check"><Checkbox checked disabled /> <span>成片视频<small>必选</small></span></label>
        {VOICE_OUTPUTS.map(role => <label className="product-check" key={role}><Checkbox checked={extras.includes(role)} disabled={busy} onCheckedChange={checked => setExtras(current => checked === true ? [...current, role] : current.filter(item => item !== role))} /><span>{OUTPUT_LABEL[role]}{role === 'subtitles' ? <small>建议语音作品勾选</small> : null}</span></label>)}
      </fieldset>

      <section className="goal-materials" aria-label="为作品选素材">
        <div className="goal-materials-heading"><h3>已有素材</h3><span>{assetIds.length} 份已选</span></div>
        {knownAssets.length ? <div className="goal-materials-list">{knownAssets.map(asset => <label className="goal-material-option" key={asset.asset_id}>
          <input type="checkbox" checked={assetIds.includes(asset.asset_id)} disabled={busy} onChange={event => setAssetIds(current => event.target.checked ? [...current, asset.asset_id] : current.filter(id => id !== asset.asset_id))} />
          <span><strong>{asset.source}</strong><small>{asset.media_type} · {formatBytes(asset.size)}</small><small>使用范围：{asset.rights}</small></span>
        </label>)}</div> : <p className="product-empty">还没有已加载素材。可以在“素材库”导入或打开已有素材，再回来选择；也可以直接粘贴素材编号。</p>}
        <Flex gap="2" wrap="wrap" align="end" mt="3">
          <div style={{ flex: 1, minWidth: 220 }}><label className="field-label" htmlFor="product-asset">素材编号</label><TextField.Root id="product-asset" value={manualAsset} disabled={busy} placeholder="asset..." onChange={event => setManualAsset(event.target.value)} /></div>
          <Button type="button" variant="soft" disabled={busy || !manualAsset.trim()} onClick={addManualAsset}>添加编号</Button>
          <Button type="button" variant="ghost" color="gray" disabled={busy} onClick={onRequestImport}><Upload size={15} />导入素材</Button>
          <Button type="button" variant="ghost" color="gray" onClick={onOpenAssets}><FileText size={15} />素材库</Button>
        </Flex>
        {selectedAssetRecords.length ? <p className="small-note">已加载素材：{selectedAssetRecords.map(asset => asset.source).join('、')}</p> : null}
        <p className="small-note">导入或读取素材不等于获得制作权限；是否允许使用仍由实例授权检查。素材编号只接受实例标识，不接受本机路径。</p>
      </section>

      {formError ? <p className="field-error" role="alert">{formError}</p> : null}
      {failure ? <Callout.Root color="red" role="alert"><Callout.Text>{failureText(failure)}</Callout.Text></Callout.Root> : null}
      {notice ? <p className="action-notice" role="status">{notice}</p> : null}
      <Flex gap="3" wrap="wrap" align="center" className="product-submit">
        <Button size="3" disabled={!connected || busy || !goal.trim()} onClick={() => void submit()}><Clapperboard size={16} />{busy ? '正在提交' : '提交制作'}</Button>
        <span className="small-note">提交后显示实例返回的真实状态；没有受理不会显示“排队中”。</span>
      </Flex>
    </section>

    <ReviewQueue connected={connected} productions={productions.data ?? []} projects={projects.data}
      onSelectProduction={selectProduction}
      onDecision={setReviewNotice}
      onChanged={() => {
        void queryClient.invalidateQueries({ queryKey: ['product-productions', instanceId] });
        void queryClient.invalidateQueries({ queryKey: ['product-review-revisions'] });
      }} />
    {reviewNotice ? <p className="action-notice" role="status">{reviewNotice}</p> : null}

    <section className="product-section" aria-labelledby="works-title">
      <div className="stage-heading"><span className="section-kicker">我的作品</span><h2 id="works-title">实例里的真实任务</h2><p>状态来自实例记录；没有任务时不会显示示例作品。</p></div>
      {productions.isPending ? <p role="status">正在读取作品…</p> : null}
      {productions.error ? <Callout.Root color="red" role="alert"><Callout.Text>{errorMessage(productions.error)}</Callout.Text></Callout.Root> : null}
      {!productions.data?.length && !productions.isPending ? <p className="product-empty">还没有作品。先在上方创建一条。</p> : null}
      <div className="product-list">{productions.data?.map(item => <button key={item.production_id} type="button" className={`product-row ${selected?.productionId === item.production_id ? 'is-selected' : ''}`} onClick={() => selectProduction(item)} aria-current={selected?.productionId === item.production_id ? 'true' : undefined}>
        <Clapperboard size={18} aria-hidden="true" />
        <span><strong>{projects.data?.find(project => project.project_id === item.project_id)?.name ?? '实例作品'}</strong><small>{item.production_id} · {item.run_id}</small></span>
        <StatusBadge status={item.status} />
      </button>)}</div>
    </section>

    <SelectedProduction connected={connected} production={selectedProduction} projectName={selectedProjectName}
      onOpenAssets={onOpenAssets} />
  </div>;
}
