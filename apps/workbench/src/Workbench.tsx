import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge, Button, Callout, Dialog, Flex, IconButton, Select, Tabs, TextArea, TextField, Theme } from '@radix-ui/themes';
import { ArrowRight, Check, ChevronDown, ChevronRight, Clapperboard, FileText, Film, FolderOpen, Headphones, Image, Info, Layers, Moon, PanelRightClose, PanelRightOpen, Plus, RefreshCw, Settings2, ShieldCheck, Sparkles, Sun, Upload, X } from 'lucide-react';
import { engineFetch, engineJson, errorMessage, inputHash, jsonWrite, rememberLocator, RequestFailure, storedLocator } from './engine';
import type { AssetRecord, CreativeRevision, ProductionAccepted, ProductionDetail, ProductionInput, Schemas } from './engine';
import { useProjectEditor } from './useProjectEditor';
import { useRunEvents } from './useRunEvents';
import { RevisionView } from './RevisionView';

type Preferences = { mode: 'interactive' | 'unattended'; aspectRatio: '9:16' | '16:9'; durationSeconds: string };
type Preview = { asset: AssetRecord; url: string; text?: string };
const STEPS = ['建项目', '定方向', '看方案', '制作', '成片'] as const;
const STATUS: Record<Schemas['RunStatus'], string> = { queued: '排队中', running: '正在创作', waiting_user: '等待审核', waiting_provider: '等待模型结果', succeeded: '制作已结束', failed: '制作遇到问题', cancel_requested: '正在处理取消', cancelled: '已取消', needs_reconciliation: '结果待核实' };
const KIND: Record<CreativeRevision['kind'], string> = { insight: '洞察', brief: '方向', plan: '制作计划', script: '剧本', storyboard: '分镜', quality: '检查结果' };
const EVENT: Record<string, string> = { 'production.accepted': '任务已受理', 'run.queued': '已进入队列', 'run.started': '开始执行', 'run.paused': '暂停新步骤', 'run.resumed': '恢复新步骤', 'review.required': '产物等待审核', 'review.decided': '审核决定已保存', 'feedback.accepted': '指导意见已保存', 'step.completed': '步骤完成', 'bundle.ready': '作品包已保存' };

function readPreferences(): Preferences {
  try {
    const value: unknown = JSON.parse(localStorage.getItem('video-creator:preferences:1') ?? 'null');
    if (value && typeof value === 'object' && 'mode' in value && 'aspectRatio' in value && 'durationSeconds' in value && ['interactive', 'unattended'].includes(String(value.mode)) && ['9:16', '16:9'].includes(String(value.aspectRatio)) && ['30', '60', '120'].includes(String(value.durationSeconds))) return value as Preferences;
  } catch { /* Optional preferences never hold project data or credentials. */ }
  return { mode: 'interactive', aspectRatio: '9:16', durationSeconds: '60' };
}
function EmptyResult({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="empty-result"><div className="empty-symbol"><Layers size={25} strokeWidth={1.6} aria-hidden="true" /></div><h2>{title}</h2><p>{children}</p></div>;
}

export function Workbench() {
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ['instance-health'], queryFn: () => engineJson<Schemas['InstanceHealth']>('/api/v1/health'), refetchInterval: 5000 });
  const connected = Boolean(health.data) && !health.isError;
  const instanceId = health.data?.instance_id;
  const editor = useProjectEditor(connected ? instanceId : undefined);
  const [preferences, setPreferences] = useState(readPreferences);
  const [activeStep, setActiveStep] = useState(0);
  const [activePage, setActivePage] = useState('projects');
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [appearance, setAppearance] = useState<'light' | 'dark'>('light');
  const [sourceExpanded, setSourceExpanded] = useState(false);
  const [productionId, setProductionId] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<unknown>(null);
  const [notice, setNotice] = useState('');
  const [feedback, setFeedback] = useState('');
  const [reloadOpen, setReloadOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [assetError, setAssetError] = useState<unknown>(null);
  const [assetLookup, setAssetLookup] = useState('');
  const [knownAssets, setKnownAssets] = useState<AssetRecord[]>([]);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importSource, setImportSource] = useState('');
  const [importRights, setImportRights] = useState('');
  const [importBusy, setImportBusy] = useState(false);
  const [deliveryTab, setDeliveryTab] = useState('video');
  const [goalError, setGoalError] = useState(false);
  const pendingStage = useRef<Schemas['StagedAsset'] | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const decisionKeys = useRef(new Map<string, string>());
  const editDisabled = actionBusy || editor.phase === 'loading';

  const productions = useQuery({ queryKey: ['productions', instanceId], enabled: connected, queryFn: () => engineJson<ProductionAccepted[]>('/api/v1/productions'), refetchInterval: connected ? 5000 : false });
  const production = useQuery({ queryKey: ['production', productionId], enabled: connected && Boolean(productionId), queryFn: () => engineJson<ProductionDetail>(`/api/v1/productions/${encodeURIComponent(productionId!)}`), refetchInterval: connected && productionId ? 5000 : false });
  const revisions = useQuery({ queryKey: ['revisions', productionId], enabled: connected && Boolean(productionId), queryFn: () => engineJson<CreativeRevision[]>(`/api/v1/productions/${encodeURIComponent(productionId!)}/revisions`) });
  const runEvents = useRunEvents(production.data?.run_id, productionId ?? undefined);
  const lastReview = [...runEvents.events].reverse().find(event => event.event_type === 'review.required');
  const reviewRevision = production.data?.status === 'waiting_user' ? revisions.data?.find(item => item.revision_id === lastReview?.entity_revision_id) : undefined;
  const latest = (kind: CreativeRevision['kind']) => revisions.data?.filter(item => item.kind === kind).at(-1);
  const direction = revisions.data?.filter(item => item.kind === 'insight' || item.kind === 'brief') ?? [];

  useEffect(() => { try { localStorage.setItem('video-creator:preferences:1', JSON.stringify(preferences)); } catch { /* Cosmetic preference persistence is optional. */ } }, [preferences]);
  useEffect(() => { if (editor.form.source_text) setSourceExpanded(true); }, [editor.form.source_text]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview.url); }, [preview]);
  useEffect(() => {
    if (!editor.project || !productions.data || !instanceId) { if (!editor.project) setProductionId(null); return; }
    const candidates = productions.data.filter(item => item.project_id === editor.project!.project_id);
    const remembered = storedLocator(`video-creator:production:${instanceId}:${editor.project.project_id}`);
    setProductionId((candidates.find(item => item.production_id === remembered) ?? candidates[0])?.production_id ?? null);
  }, [editor.project?.project_id, productions.data, instanceId]);
  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void editor.flush().catch(() => {}); }
      if (event.key === 'Escape') setAssistantOpen(false);
    };
    window.addEventListener('keydown', keydown); return () => window.removeEventListener('keydown', keydown);
  }, [editor.flush]);

  const chooseProduction = (id: string, projectId: string) => {
    setProductionId(id);
    if (instanceId) rememberLocator(`video-creator:production:${instanceId}:${projectId}`, id);
  };
  const createProduction = async () => {
    if (!editor.form.goal.trim()) { setGoalError(true); document.getElementById('creative-goal')?.focus(); return; }
    setGoalError(false); setActionBusy(true); setActionError(null); setNotice('');
    try {
      const saved = await editor.flush();
      const request: ProductionInput = {
        project_id: saved.project_id, goal: saved.goal, inputs: { source_text: saved.source_text, asset_ids: [] }, source_bindings: [],
        brief: { language: 'zh-CN', aspect_ratio: preferences.aspectRatio, target_duration_us: Number(preferences.durationSeconds) * 1_000_000 },
        automation: { mode: preferences.mode, max_revision_cycles: 2 },
        policy: { version: 'local-default-v1', allowed_provider_routes: [], external_transfer_allowed: false, max_cost: { currency: 'CNY', amount: '0' } },
        outputs: ['video', 'narration_audio', 'mixed_audio', 'approved_script', 'actual_transcript', 'subtitles', 'semantic_manifest', 'rag_chunks'], delivery: 'reference',
      };
      const accepted = await engineJson<ProductionAccepted>('/api/v1/productions', jsonWrite('POST', request, { 'Idempotency-Key': `workbench-${await inputHash(request)}` }));
      chooseProduction(accepted.production_id, accepted.project_id);
      await queryClient.invalidateQueries({ queryKey: ['productions', instanceId] });
      setActivePage('projects'); setActiveStep(3); setNotice('任务已受理。目标、资料与本次配置已固定保存。');
    } catch (failure) { setActionError(failure); } finally { setActionBusy(false); }
  };
  const submitReview = async (action: Schemas['ReviewDecision']['action']) => {
    if (!reviewRevision || !production.data || (action === 'revise' && !feedback.trim())) return;
    setActionBusy(true); setActionError(null); setNotice('');
    const decision: Schemas['ReviewDecision'] = { target_revision_id: reviewRevision.revision_id, action, instruction_text: action === 'revise' ? feedback : '', preserved_constraints: [] };
    const identity = JSON.stringify([production.data.run_id, decision]);
    const key = decisionKeys.current.get(identity) ?? crypto.randomUUID(); decisionKeys.current.set(identity, key);
    try {
      await engineJson<Schemas['ReviewDecision'] | Schemas['FeedbackRevision']>(`/api/v1/runs/${encodeURIComponent(production.data.run_id)}/decisions`, jsonWrite('POST', decision, { 'Idempotency-Key': key }));
      setNotice(action === 'approve' ? '审核确认已保存。' : action === 'revise' ? '指导意见已保存，等待Agent重新规划。' : '否决意见已保存。');
      await Promise.all([production.refetch(), revisions.refetch()]);
    } catch (failure) { setActionError(failure); } finally { setActionBusy(false); }
  };
  const addKnownAsset = (asset: AssetRecord) => setKnownAssets(current => [...current.filter(item => item.asset_id !== asset.asset_id), asset]);
  const openAsset = async (id: string) => {
    setPreviewBusy(true); setAssetError(null);
    try {
      const asset = await engineJson<AssetRecord>(`/api/v1/assets/${encodeURIComponent(id)}`);
      if (asset.size > 128 * 1024 * 1024) throw new RequestFailure(413, 'preview_size_limit');
      const response = await engineFetch(`/api/v1/assets/${encodeURIComponent(asset.asset_id)}/content`);
      const blob = await response.blob();
      if (blob.size !== asset.size) throw new RequestFailure(422, 'asset_integrity_failed');
      const data = await blob.arrayBuffer();
      const digest = await crypto.subtle.digest('SHA-256', data);
      if (Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('') !== asset.sha256) throw new RequestFailure(422, 'object_integrity_failed');
      const isText = asset.media_type.startsWith('text/') || asset.media_type.includes('json');
      setPreview({ asset, url: URL.createObjectURL(blob), ...(isText ? { text: new TextDecoder().decode(data) } : {}) });
      addKnownAsset(asset); setActivePage('projects'); setActiveStep(4); setDeliveryTab(asset.media_type.startsWith('audio/') ? 'audio' : isText ? 'text' : 'video');
    } catch (failure) { setAssetError(failure); } finally { setPreviewBusy(false); }
  };
  const chooseImport = (file: File | undefined) => {
    if (!file) return;
    pendingStage.current = null; setAssetError(null); setImportFile(file); setImportSource(`手动导入：${file.name}`); setImportRights(''); setImportOpen(true);
  };
  const importAsset = async () => {
    if (!importFile || !importRights.trim() || !importSource.trim()) return;
    setImportBusy(true); setAssetError(null);
    try {
      if (!pendingStage.current) pendingStage.current = await engineJson<Schemas['StagedAsset']>('/api/v1/assets/staging', { method: 'POST', headers: { 'Content-Type': importFile.type || 'application/octet-stream' }, body: importFile });
      const candidate: Schemas['AssetCandidate'] = { ...pendingStage.current, source: importSource, rights: importRights };
      const asset = await engineJson<AssetRecord>('/api/v1/assets/import', jsonWrite('POST', candidate));
      addKnownAsset(asset); setImportOpen(false); setImportFile(null); pendingStage.current = null; setNotice('素材已校验并保存到实例。');
      await openAsset(asset.asset_id);
    } catch (failure) { setAssetError(failure); } finally { setImportBusy(false); }
  };
  const saveLabel = editor.phase === 'loading' ? '载入中' : editor.phase === 'saving' || (editor.dirty && !editor.error) ? '保存中' : editor.phase === 'saved' && !editor.dirty ? '实例已保存' : editor.phase === 'conflict' ? '版本冲突' : editor.phase === 'failed' ? '保存失败' : '新项目';
  const renderReview = () => reviewRevision ? <div className="review-controls"><div><span className="review-label">待审核：{KIND[reviewRevision.kind]}</span><p>确认当前版本，或用一句话指导修改。</p></div><Button disabled={!connected || actionBusy} onClick={() => void submitReview('approve')}><Check size={15} />确认{KIND[reviewRevision.kind]}</Button><Button variant="soft" disabled={!connected || actionBusy} onClick={() => setAssistantOpen(true)}>给修改意见</Button></div> : null;
  const latestView = (kind: CreativeRevision['kind'], empty: string) => latest(kind) ? <RevisionView revision={latest(kind)!} /> : <EmptyResult title={empty}>Agent产物实际生成并保存后显示。你不必预先编写。</EmptyResult>;

  return <Theme appearance={appearance} accentColor="teal" grayColor="slate" radius="medium" scaling="100%"><div className="workbench" data-appearance={appearance}>
    <a className="skip-link" href="#workspace-main">跳到创作区</a>
    <aside className="app-nav" aria-label="工作台导航"><a className="brand" href="#workspace-main" aria-label="VideoCreator创作工作台"><span className="brand-mark"><Clapperboard size={21} strokeWidth={1.7} /></span><span>VideoCreator</span></a><nav>{[{ id: 'projects', label: '项目', icon: FolderOpen }, { id: 'assets', label: '素材', icon: Image }, { id: 'tasks', label: '任务', icon: Layers }, { id: 'settings', label: '设置', icon: Settings2 }].map(item => <button key={item.id} type="button" className={`nav-button ${activePage === item.id ? 'is-active' : ''}`} aria-current={activePage === item.id ? 'page' : undefined} onClick={() => setActivePage(item.id)}><item.icon size={18} strokeWidth={1.7} aria-hidden="true" /><span>{item.label}</span></button>)}</nav><div className="nav-bottom"><ShieldCheck size={16} /><span>本地工具</span></div></aside>
    <div className="app-body"><header className="project-header"><div className="project-heading"><span className="workspace-name">我的工作空间</span><div className="project-title-row"><h1>{activePage === 'projects' ? editor.form.name : { assets: '素材库', tasks: '任务中心', settings: '设置' }[activePage]}</h1><span className={`save-status ${editor.error ? 'is-error' : ''}`} aria-live="polite">{saveLabel === '实例已保存' ? <Check size={13} /> : null}{saveLabel}</span></div></div><div className="header-actions"><Badge color={health.isError ? 'amber' : 'gray'} variant="soft">{health.isPending ? '连接中' : connected ? '本地实例' : '连接暂不可用'}</Badge><IconButton size="2" variant="ghost" color="gray" aria-label={appearance === 'light' ? '切换深色主题' : '切换浅色主题'} onClick={() => setAppearance(appearance === 'light' ? 'dark' : 'light')}>{appearance === 'light' ? <Moon size={17} /> : <Sun size={17} />}</IconButton><IconButton size="2" variant="soft" color="gray" aria-label={assistantOpen ? '收起创作助手' : '展开创作助手'} aria-expanded={assistantOpen} aria-controls="creative-assistant" onClick={() => setAssistantOpen(!assistantOpen)}>{assistantOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}</IconButton></div></header>
      {activePage === 'projects' ? <nav className="step-nav" aria-label="创作步骤">{STEPS.map((step, index) => <button key={step} className={`step-button ${index === activeStep ? 'is-active' : ''}`} type="button" aria-current={index === activeStep ? 'step' : undefined} onClick={() => setActiveStep(index)}><span className="step-number">{index + 1}</span><span>{step}</span>{index < 4 ? <ChevronRight className="step-divider" size={14} /> : null}</button>)}</nav> : null}
      <div className={`workspace-layout ${assistantOpen ? 'has-assistant' : ''}`}><main id="workspace-main" className="workspace-main" tabIndex={-1}>
        {health.isError ? <Callout.Root color="amber" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>实例连接暂不可用。当前输入仍保留，已有项目不会锁住。</Callout.Text><Button size="1" variant="soft" onClick={() => void health.refetch()}>重新连接</Button></Callout.Root> : null}
        {editor.error ? <Callout.Root color="red" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{errorMessage(editor.error)}</Callout.Text><div className="error-actions">{editor.phase === 'conflict' && editor.project ? <><Button size="1" variant="soft" color="red" onClick={() => setReloadOpen(true)}>载入已保存版本</Button><Button size="1" variant="soft" color="gray" onClick={() => editor.newDraft(true)}>另存为新项目</Button></> : <Button size="1" variant="soft" color="red" disabled={!connected} onClick={() => void editor.flush().catch(() => {})}>重试保存</Button>}</div></Callout.Root> : null}
        {actionError ? <Callout.Root color="red" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{errorMessage(actionError)}</Callout.Text><Button size="1" variant="soft" color="red" onClick={() => { void production.refetch(); void revisions.refetch(); }}>刷新任务</Button></Callout.Root> : null}
        {notice ? <p className="action-notice" role="status">{notice}</p> : null}
        {activePage === 'projects' ? <><div className="project-switcher"><Select.Root value={editor.project?.project_id ?? ''} onValueChange={id => { void editor.load(id); setActiveStep(0); }} disabled={editor.dirty || editor.phase === 'saving' || editDisabled}><Select.Trigger placeholder="新项目" aria-label="选择已保存项目" /><Select.Content>{editor.list.data?.map(item => <Select.Item key={item.project_id} value={item.project_id}>{item.name}</Select.Item>)}</Select.Content></Select.Root><Button size="2" variant="ghost" color="gray" disabled={editor.dirty || editor.phase === 'saving' || editDisabled} onClick={() => { editor.newDraft(); setProductionId(null); setActiveStep(0); setNotice(''); }}><Plus size={15} />新建</Button>{editor.project ? <span className="project-revision">保存版本 {editor.project.revision}</span> : null}</div>
          {activeStep === 0 ? <section className="creation-panel" aria-labelledby="create-title"><div className="section-intro"><span className="section-kicker">从一个想法开始</span><h2 id="create-title">你想做什么视频？</h2><p>给出目标和资料，Agent负责洞察、剧本、分镜与制作。你来审核和指导。</p></div><label className="field-label" htmlFor="creative-goal">视频目标</label><TextArea id="creative-goal" className="goal-input" size="3" value={editor.form.goal} disabled={editDisabled} aria-invalid={goalError} aria-describedby={goalError ? 'goal-error' : undefined} placeholder="例如：用轻松的游戏解说，介绍这次更新里最值得体验的内容。" onChange={event => { editor.update('goal', event.target.value); setGoalError(false); }} />{goalError ? <p className="field-error" id="goal-error">请先给出一个视频目标。</p> : null}<div className="input-bottom"><Button size="2" variant="ghost" color="gray" onClick={() => setSourceExpanded(!sourceExpanded)} aria-expanded={sourceExpanded} aria-controls="source-input"><FileText size={16} />{sourceExpanded ? '收起文字资料' : '添加文字资料'}</Button><span>不需要先写剧本和分镜</span></div>{sourceExpanded ? <div className="source-input" id="source-input"><label className="field-label" htmlFor="creative-source">可用资料</label><TextArea id="creative-source" size="2" value={editor.form.source_text} disabled={editDisabled} placeholder="粘贴文章、产品介绍、故事设定或已有资料。" onChange={event => editor.update('source_text', event.target.value)} /></div> : null}
            <div className="creation-options"><div><label className="field-label" htmlFor="creation-mode">创作方式</label><Select.Root value={preferences.mode} disabled={actionBusy} onValueChange={value => setPreferences(current => ({ ...current, mode: value as Preferences['mode'] }))}><Select.Trigger id="creation-mode" /><Select.Content><Select.Item value="interactive">审核与指导</Select.Item><Select.Item value="unattended">预授权自动制作</Select.Item></Select.Content></Select.Root></div><div><label className="field-label" htmlFor="aspect-ratio">画幅</label><Select.Root value={preferences.aspectRatio} disabled={actionBusy} onValueChange={value => setPreferences(current => ({ ...current, aspectRatio: value as Preferences['aspectRatio'] }))}><Select.Trigger id="aspect-ratio" /><Select.Content><Select.Item value="9:16">竖屏 9:16</Select.Item><Select.Item value="16:9">横屏 16:9</Select.Item></Select.Content></Select.Root></div><div><label className="field-label" htmlFor="duration">参考时长</label><Select.Root value={preferences.durationSeconds} disabled={actionBusy} onValueChange={value => setPreferences(current => ({ ...current, durationSeconds: value }))}><Select.Trigger id="duration" /><Select.Content><Select.Item value="30">约30秒</Select.Item><Select.Item value="60">约1分钟</Select.Item><Select.Item value="120">约2分钟</Select.Item></Select.Content></Select.Root></div></div><div className="start-row"><Button size="3" disabled={!connected || actionBusy || editor.phase === 'loading' || editor.phase === 'conflict'} onClick={() => void createProduction()}><Sparkles size={17} />{actionBusy ? '正在受理' : '让Agent开始创作'}<ArrowRight size={17} /></Button><p>{health.data?.worker_connected ? '将在已授权能力和预算内制作。' : '创作服务尚未连接。新任务会真实保存到队列。'}</p></div><div className="local-alternative"><span>手里已有素材？</span><Button size="2" variant="ghost" color="gray" disabled={!connected} onClick={() => fileInputRef.current?.click()}><Upload size={15} />导入素材</Button></div><details className="advanced-settings"><summary>项目选项<ChevronDown size={14} /></summary><div><label className="field-label" htmlFor="project-title">作品名称</label><TextField.Root id="project-title" value={editor.form.name} disabled={editDisabled} onChange={event => editor.update('name', event.target.value)} /><p>画幅、时长和创作方式是本机偏好，提交时固定到任务。本开发实例不启用收费模型或外发资料。</p></div></details></section> : null}
          {activeStep === 1 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">定方向</span><h2>把想法变成创作方向</h2><p>Agent研究资料、受众和制作可行性，推荐角度与表现形式。</p></div>{direction.length ? direction.map(item => <section className="creative-proposal" key={item.revision_id}><h3>{KIND[item.kind]}</h3><RevisionView revision={item} /></section>) : <EmptyResult title="还没有方向提案">{production.data ? '任务已保存，方向产物在Agent实际完成后出现。' : '先给出目标和资料，Agent会提出可审核的方向。'}</EmptyResult>}{renderReview()}</section> : null}
          {activeStep === 2 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">看方案</span><h2>先看完整方案，再开始制作</h2><p>剧本、分镜、角色与声音共享同一个方案版本。</p></div><Tabs.Root defaultValue="script" className="plan-tabs"><Tabs.List aria-label="制作方案视图"><Tabs.Trigger value="script">剧本</Tabs.Trigger><Tabs.Trigger value="storyboard">分镜</Tabs.Trigger><Tabs.Trigger value="voices">角色与声音</Tabs.Trigger></Tabs.List><Tabs.Content value="script">{latestView('script', '剧本尚未生成')}</Tabs.Content><Tabs.Content value="storyboard">{latestView('storyboard', '分镜尚未生成')}</Tabs.Content><Tabs.Content value="voices">{latestView('plan', '还没有制作计划')}</Tabs.Content></Tabs.Root>{renderReview()}</section> : null}
          {activeStep === 3 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">制作</span><h2>让AI剧组完成视听制作</h2><p>镜头和音轨完成并校验后逐项出现；已有结果会保留。</p></div>{production.data ? <div className="production-state"><Clapperboard size={27} strokeWidth={1.5} /><h3>{STATUS[production.data.status]}</h3><p>{production.data.status === 'queued' && !health.data?.worker_connected ? '任务已受理，创作服务尚未连接。目标和资料已保留。' : production.data.status === 'needs_reconciliation' ? '上游结果或费用需要核实，系统不会盲目重复提交。' : production.data.status === 'waiting_user' ? '请审核真实产物或给出指导意见。' : '当前状态来自实例执行记录。'}</p><span className="cost-note">{production.data.operations.some(item => item.cost_status === 'unknown') ? '费用待核实' : production.data.operations.length ? `已记录费用 CNY ${production.data.cost.spent.amount}` : '尚无模型调用记录'}</span><div className="production-actions"><Button variant="soft" size="2" onClick={() => { void production.refetch(); runEvents.reconnect(); }}><RefreshCw size={14} />刷新记录</Button>{!['succeeded', 'failed', 'cancelled', 'cancel_requested'].includes(production.data.status) ? <Button size="2" variant="ghost" color="gray" disabled={!connected || actionBusy} onClick={() => setCancelOpen(true)}>取消任务</Button> : null}</div></div> : <EmptyResult title="还没有制作任务">给出目标后一次提交，无需逐个启动内部制作步骤。</EmptyResult>}{renderReview()}<details className="advanced-settings"><summary>任务记录<ChevronDown size={14} /></summary><div><p>{runEvents.phase === 'connected' ? '已连接实例事件' : runEvents.phase === 'disconnected' ? '事件连接已断开，已有记录仍保留。' : runEvents.phase === 'connecting' ? '正在连接事件' : '尚未选择任务'}</p>{runEvents.phase === 'disconnected' ? <Button size="1" variant="soft" onClick={runEvents.reconnect}>重连事件</Button> : null}<ol className="event-records">{runEvents.events.map(event => <li key={event.event_id}><span>{EVENT[event.event_type] ?? event.event_type}</span><time>{new Date(event.occurred_at_us / 1000).toLocaleTimeString()}</time></li>)}</ol></div></details><details className="advanced-settings"><summary>AI剧组职责<ChevronDown size={14} /></summary><div><p>导演把握创作，执行统筹安排任务，画面与声音落实素材，后期组织剪辑，审片检查结果。只在真实执行后显示启用角色与分工。</p></div></details></section> : null}
          {activeStep === 4 ? <section className="delivery-panel"><div className="stage-heading"><span className="section-kicker">成片</span><h2>查看作品与交付内容</h2><p>成片、独立音频和文本属于同一固定版本作品包。</p></div><Tabs.Root value={deliveryTab} onValueChange={setDeliveryTab}><Tabs.List aria-label="作品内容"><Tabs.Trigger value="video">视频</Tabs.Trigger><Tabs.Trigger value="audio">音频</Tabs.Trigger><Tabs.Trigger value="text">文本</Tabs.Trigger></Tabs.List><Tabs.Content value="video">{preview?.asset.media_type.startsWith('video/') ? <div className="media-preview"><video key={preview.url} src={preview.url} controls preload="metadata" playsInline aria-label="受保护实例视频素材预览" onError={() => setAssetError(new RequestFailure(422, 'media_invalid'))} /></div> : preview?.asset.media_type.startsWith('image/') ? <img className="protected-image" src={preview.url} alt="已校验的实例图片素材" /> : <div className="media-empty"><Film size={34} strokeWidth={1.4} /><h3>还没有成片</h3><p>可以打开已入库的实例素材验证播放。</p><Button size="2" variant="soft" onClick={() => setActivePage('assets')}><FolderOpen size={16} />查看素材</Button></div>}</Tabs.Content><Tabs.Content value="audio">{preview?.asset.media_type.startsWith('audio/') ? <div className="audio-preview"><Headphones size={32} strokeWidth={1.4} /><h3>{preview.asset.source}</h3><audio key={preview.url} src={preview.url} controls preload="metadata" aria-label="受保护实例音频素材预览" onError={() => setAssetError(new RequestFailure(422, 'media_invalid'))} /></div> : <EmptyResult title="还没有独立音轨">旁白和完整混音将分别显示，素材预览不会被标成生成作品包。</EmptyResult>}</Tabs.Content><Tabs.Content value="text">{preview?.text !== undefined ? <pre className="asset-text-preview">{preview.text}</pre> : <EmptyResult title="还没有文本交付">批准剧本、实际音频转写、字幕及来源会分别显示。</EmptyResult>}</Tabs.Content></Tabs.Root>{preview ? <div className="asset-preview-meta"><Badge color="gray">实例素材预览</Badge><span>{preview.asset.source}</span><p>使用范围：{preview.asset.rights}</p><Button size="1" variant="ghost" color="gray" onClick={() => setPreview(null)}>关闭预览</Button></div> : null}<p className="preview-notice">作品包交付接口尚未接入。已入库素材与生成作品包分别显示。</p><div className="delivery-actions"><Button disabled>导出作品包</Button><Button disabled variant="soft">授权引用</Button></div></section> : null}
        </> : null}
        {activePage === 'assets' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">素材库</span><h2>让已有资料进入创作</h2><p>素材校验后由安装实例保存，记录来源与使用范围。</p></div><Button variant="soft" disabled={!connected || importBusy} onClick={() => fileInputRef.current?.click()}><Upload size={16} />导入素材</Button><div className="known-assets">{knownAssets.map(asset => <button className="asset-row" key={asset.asset_id} type="button" disabled={previewBusy || !connected} onClick={() => void openAsset(asset.asset_id)}><FileText size={18} /><span>{asset.source}<small>{asset.media_type} · {Math.ceil(asset.size / 1024)} KB</small></span><ChevronRight size={15} /></button>)}</div>{knownAssets.length ? <p className="small-note">这里列出本次打开过的实例素材，完整素材列表接口尚未提供。</p> : <EmptyResult title="还没有打开素材">可以导入，或通过已有素材编号从实例读取。媒体解码能力不足时保留暂存并提示。</EmptyResult>}<details className="advanced-settings"><summary>打开已有实例素材<ChevronDown size={14} /></summary><div><label className="field-label" htmlFor="asset-id">素材编号</label><div className="asset-lookup"><TextField.Root id="asset-id" value={assetLookup} placeholder="asset..." onChange={event => setAssetLookup(event.target.value)} /><Button size="2" disabled={!connected || previewBusy || !/^[A-Za-z0-9_.:-]{1,128}$/.test(assetLookup)} onClick={() => void openAsset(assetLookup)}>{previewBusy ? '读取中' : '打开'}</Button></div><p>只读取已获授权编号，不接受本机路径。</p></div></details></section> : null}
        {activePage === 'tasks' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">任务中心</span><h2>创作任务都在这里</h2><p>桌面、API与MCP任务使用同一份执行记录。</p></div>{productions.data?.length ? <div className="task-list">{productions.data.map(item => <button type="button" className="task-row" key={item.production_id} disabled={editor.dirty || actionBusy || editor.phase === 'saving'} onClick={() => { const open = async () => { if (editor.project?.project_id !== item.project_id) await editor.load(item.project_id); chooseProduction(item.production_id, item.project_id); setActivePage('projects'); setActiveStep(3); }; void open(); }}><Clapperboard size={20} /><span>{editor.list.data?.find(project => project.project_id === item.project_id)?.name ?? '实例创作任务'}<small>{item.production_id}</small></span><Badge color={item.status === 'needs_reconciliation' ? 'amber' : 'gray'}>{STATUS[item.status]}</Badge></button>)}</div> : <EmptyResult title="还没有制作任务">受理后显示真实状态，刷新或断开页面不会取消实例任务。</EmptyResult>}{productions.error ? <Callout.Root color="red"><Callout.Text>{errorMessage(productions.error)}</Callout.Text></Callout.Root> : null}</section> : null}
        {activePage === 'settings' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">设置</span><h2>使用你自己的能力</h2><p>本地工具免产品注册。自有模型和官方服务是可选能力来源。</p></div><div className="settings-row"><ShieldCheck size={21} /><div><h3>本地工具模式</h3><p>项目保存到当前安装实例，免官方账号登录。</p></div><Badge color="teal">免注册</Badge></div><div className="settings-row"><Sparkles size={21} /><div><h3>创作服务</h3><p>{health.data?.worker_connected ? '实例已连接创作服务，能力与预算以实例授权为准。' : '此开发实例尚未启动创作服务。任务可保存，不会伪装成生成完成。'}</p></div><Badge color="gray">{health.data?.worker_connected ? '已连接' : '未连接'}</Badge></div><div className="settings-row"><FolderOpen size={21} /><div><h3>数据与凭证</h3><p>工作台通过受控连接访问项目，不读取模型密钥。浏览器只保存界面偏好与项目定位编号。</p></div></div><details className="advanced-settings"><summary>连接诊断<ChevronDown size={14} /></summary><div><p>实例：{instanceId ?? '尚未连接'}</p><p>接口版本：{health.data?.schema_version ?? '未知'}</p><p>桌面IPC尚未验证，当前连接为本机开发入口。</p><Button size="1" variant="soft" onClick={() => void health.refetch()}><RefreshCw size={13} />重新检查连接</Button></div></details></section> : null}
        {assetError && !importOpen ? <Callout.Root color="red" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{errorMessage(assetError)}</Callout.Text></Callout.Root> : null}
      </main>{assistantOpen ? <aside id="creative-assistant" className="creative-assistant" aria-label="创作助手"><div className="assistant-heading"><h2>创作助手</h2><IconButton size="1" variant="ghost" color="gray" aria-label="关闭创作助手" onClick={() => setAssistantOpen(false)}><X size={17} /></IconButton></div><div className="assistant-empty"><Sparkles size={20} strokeWidth={1.6} /><p>{reviewRevision ? `当前${KIND[reviewRevision.kind]}等待审核，意见绑定这份产物版本。` : '真实产物等待审核后，可在这里给出指导意见。'}</p></div><label className="field-label" htmlFor="creative-feedback">指导意见</label><TextArea id="creative-feedback" size="2" value={feedback} placeholder="例如：表达更年轻，只修改第三镜头。" onChange={event => setFeedback(event.target.value)} /><Button size="2" disabled={!connected || actionBusy || !reviewRevision || !feedback.trim()} className="feedback-submit" onClick={() => void submitReview('revise')}>提交指导</Button><p className="small-note">原目标和事实继续保留。意见不扩大预算或发布权限。</p>{reviewRevision ? <Button size="1" variant="ghost" color="gray" disabled={actionBusy || !connected} onClick={() => void submitReview('reject')}>否决当前提案</Button> : null}</aside> : null}</div>
      <footer className="probe-footer"><span>Gate0连接验证</span><span>{connected ? '项目与任务来自本地实例' : '等待本机实例连接'}</span><Dialog.Root><Dialog.Trigger><Button size="1" variant="ghost" color="gray"><Info size={13} />运行范围</Button></Dialog.Trigger><Dialog.Content maxWidth="460px"><Dialog.Title>当前运行范围</Dialog.Title><Dialog.Description>工作台连接实例项目、任务、事件和受控素材接口。真实媒体生成与桌面安装仍需后续验证。</Dialog.Description><div className="dialog-copy"><p>项目输入真实保存，审核只针对实例已存产物，状态不会由计时器生成。</p><p>此开发实例没有收费模型路线、预算或创作Worker。导出、引用与完整素材列表接口尚未接入。</p></div><Flex justify="end" mt="4"><Dialog.Close><Button>知道了</Button></Dialog.Close></Flex></Dialog.Content></Dialog.Root></footer>
    </div>
    <input ref={fileInputRef} className="visually-hidden" type="file" accept="video/*,audio/*,image/*,text/plain,application/json,application/x-ndjson" aria-label="选择要导入实例的素材" onChange={event => { chooseImport(event.target.files?.[0]); event.currentTarget.value = ''; }} />
    <Dialog.Root open={reloadOpen} onOpenChange={setReloadOpen}><Dialog.Content maxWidth="460px"><Dialog.Title>载入已保存版本</Dialog.Title><Dialog.Description>当前未保存输入会被替换。需要保留时，先选择“另存为新项目”。</Dialog.Description><Flex justify="end" gap="3" mt="5"><Dialog.Close><Button variant="soft" color="gray">保留当前输入</Button></Dialog.Close><Button onClick={() => { if (editor.project) void editor.load(editor.project.project_id); setReloadOpen(false); }}>载入已保存版本</Button></Flex></Dialog.Content></Dialog.Root>
    <Dialog.Root open={cancelOpen} onOpenChange={setCancelOpen}><Dialog.Content maxWidth="460px"><Dialog.Title>取消当前制作任务？</Dialog.Title><Dialog.Description>停止安排后续步骤。已提交的上游请求可能继续，结果与费用仍按实际状态核实。</Dialog.Description><Flex justify="end" gap="3" mt="5"><Dialog.Close><Button variant="soft" color="gray">继续制作</Button></Dialog.Close><Button color="red" disabled={actionBusy} onClick={() => { const cancel = async () => { if (!productionId) return; setActionBusy(true); setActionError(null); try { const current = await engineJson<ProductionDetail>(`/api/v1/productions/${encodeURIComponent(productionId)}/cancel`, { method: 'POST' }); queryClient.setQueryData(['production', productionId], current); await productions.refetch(); setCancelOpen(false); } catch (failure) { setActionError(failure); } finally { setActionBusy(false); } }; void cancel(); }}>确认取消</Button></Flex></Dialog.Content></Dialog.Root>
    <Dialog.Root open={importOpen} onOpenChange={value => { if (!importBusy) setImportOpen(value); }}><Dialog.Content maxWidth="480px"><Dialog.Title>导入素材</Dialog.Title><Dialog.Description>{importFile?.name ?? '选择素材'}。校验后存入安装实例，暂存不代表导入成功。</Dialog.Description><div className="import-fields"><label className="field-label" htmlFor="import-source">来源</label><TextField.Root id="import-source" value={importSource} disabled={importBusy} onChange={event => setImportSource(event.target.value)} /><label className="field-label" htmlFor="import-rights">使用范围与授权</label><TextArea id="import-rights" size="2" value={importRights} disabled={importBusy} placeholder="说明素材来源、你拥有的使用权限及适用范围。" onChange={event => setImportRights(event.target.value)} /></div>{assetError ? <Callout.Root color="red" role="alert"><Callout.Text>{errorMessage(assetError)}</Callout.Text></Callout.Root> : null}<Flex justify="end" gap="3" mt="5"><Dialog.Close><Button variant="soft" color="gray" disabled={importBusy}>稍后导入</Button></Dialog.Close><Button disabled={importBusy || !connected || !importSource.trim() || !importRights.trim()} onClick={() => void importAsset()}>{importBusy ? '正在校验' : pendingStage.current ? '重试校验与导入' : '校验并导入'}</Button></Flex></Dialog.Content></Dialog.Root>
  </div></Theme>;
}
