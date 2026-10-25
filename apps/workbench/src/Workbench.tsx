import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge, Button, Callout, Dialog, Flex, IconButton, Select, Tabs, TextArea, TextField, Theme } from '@radix-ui/themes';
import { ArrowRight, Check, ChevronDown, ChevronRight, Clapperboard, FileText, FolderOpen, Image, Info, Layers, Moon, PanelRightClose, PanelRightOpen, Plus, RefreshCw, Settings2, ShieldCheck, Sparkles, Sun, Upload, X } from 'lucide-react';
import { engineContent, engineData, engineRequest, errorMessage, PREVIEW_BUFFER_BYTES, rememberLocator, RequestFailure, storedLocator, verifiedContentBlob, verifyContentMetadata, getEngineConnectionContext, subscribeEngineConnection, isEngineConnectionCurrent } from './engine';
import type { AssetRecord, CreativeRevision, ProductionAccepted, ProjectGoalAccepted, Schemas, EngineConnectionContext } from './engine';
import { useProjectEditor } from './useProjectEditor';
import { useRunEvents } from './useRunEvents';
import { RevisionView } from './RevisionView';
import { DeliveryView } from './DeliveryView';
import { BundleImportView } from './BundleImportView';
import { NativeSetupView } from './NativeSetupView';
import { ProductAuthorizationGate, AuthorizationBooting } from './ProductAuthorizationGate';
import { readAuthorizationChannel } from './productAuthorization';
import { clearSubmissionIntent, readSubmissionIntent, saveSubmissionIntent, validReceiptId, verifySubmissionIntent } from './submissionIntents';
import type { SubmissionIntent } from './submissionIntents';

type Preferences = { mode: 'interactive' | 'unattended'; aspectRatio: '9:16' | '16:9'; durationSeconds: string };
type Preview = { connection: EngineConnectionContext; asset: AssetRecord; url: string; text?: string; expiresAtUs: number | null };
type ProductionLocator = Pick<ProductionAccepted, 'instance_id' | 'project_id' | 'production_id'>;
type CancelContext = { instanceId: string | undefined; connected: boolean; projectId: string | null; productionId: string | null; generation: number; mounted: boolean };
type CancelIntent = { context: CancelContext; target: ProductionLocator; projectName: string };
const STEPS = ['建项目', '定方向', '看方案', '制作', '成片'] as const;
const STATUS: Record<Schemas['RunStatus'], string> = { queued: '排队中', running: '正在创作', waiting_user: '等待审核', waiting_authorization: '等待授权', waiting_provider: '等待模型结果', succeeded: '制作已结束', failed: '制作遇到问题', cancel_requested: '正在处理取消', cancelled: '已取消', needs_reconciliation: '结果待核实' };
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
function retainProductionReceipt(intent: SubmissionIntent<'production'>, accepted: ProductionAccepted): void {
  if (!accepted || accepted.instance_id !== intent.instanceId || accepted.project_id !== intent.body.project_id
    || !validReceiptId(accepted.production_id) || !validReceiptId(accepted.run_id) || !validReceiptId(accepted.request_revision_id)
    || !['0.2.0-candidate', '0.3.0-candidate'].includes(accepted.schema_version) || !Object.hasOwn(STATUS, accepted.status)
    || typeof accepted.status_path !== 'string' || !accepted.status_path || typeof accepted.events_path !== 'string' || !accepted.events_path) {
    throw new RequestFailure(502, 'response_unavailable');
  }
  saveSubmissionIntent('production', { ...intent, receiptId: accepted.production_id });
}

export function Workbench() {
  const queryClient = useQueryClient();
  const connection = useSyncExternalStore(subscribeEngineConnection, getEngineConnectionContext, () => null);
  const healthQuery = useQuery({ queryKey: ['instance-health', connection?.epoch], enabled: Boolean(connection), queryFn: async () => {
    if (!connection) throw new RequestFailure(503, 'trusted_connection_missing');
    // The authorization channel is a runtime response header (ADR0081 §9); it
    // stays out of the generated OpenAPI contract, so read it from the response.
    const response = await engineRequest('GET /api/v1/health', {}, connection);
    if (!isEngineConnectionCurrent(connection)) throw new RequestFailure(409, 'material_connection_changed');
    if (!response.data) throw new RequestFailure(502, 'response_unavailable');
    return { value: response.data, authorization: readAuthorizationChannel(response.headers), connection };
  }, refetchInterval: query => {
    const data = query.state.data;
    return data?.authorization === 'pending' || data?.authorization === 'complete' ? 2000 : 5000;
  } });
  const health = { ...healthQuery, data: healthQuery.data?.connection === connection ? healthQuery.data.value : undefined };
  const authorizationChannel = healthQuery.data?.connection === connection ? healthQuery.data.authorization : undefined;
  const authorizationRestricted = authorizationChannel === 'pending' || authorizationChannel === 'complete';
  const reachable = Boolean(health.data) && !health.isError;
  // Restricted processes expose only health and the authorization routes. Keep
  // ordinary project/task queries off until a restart returns `none`.
  const connected = reachable && !authorizationRestricted;
  const instanceId = health.data?.instance_id;
  const editor = useProjectEditor(instanceId, connected, false);
  const [preferences, setPreferences] = useState(readPreferences);
  const [activeStep, setActiveStep] = useState(0);
  const [goalSelectionGeneration, setGoalSelectionGeneration] = useState(0);
  const [activePage, setActivePage] = useState('projects');
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [appearance, setAppearance] = useState<'light' | 'dark'>('light');
  const [sourceExpanded, setSourceExpanded] = useState(false);
  const [productionLocator, setProductionLocator] = useState<ProductionLocator | null>(null);
  const productionId = productionLocator && productionLocator.instance_id === instanceId ? productionLocator.production_id : null;
  const viewingOtherProject = Boolean(productionId && productionLocator?.project_id !== editor.project?.project_id);
  const selectedProjectName = editor.list.data?.find(item => item.project_id === productionLocator?.project_id)?.name ?? '已选创作任务';
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<unknown>(null);
  const [notice, setNotice] = useState('');
  const [feedback, setFeedback] = useState('');
  const [acceptedFeedback, setAcceptedFeedback] = useState<Schemas['FeedbackRevision'] | null>(null);
  const [reloadOpen, setReloadOpen] = useState(false);
  const [cancelIntent, setCancelIntent] = useState<CancelIntent | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [assetError, setAssetError] = useState<unknown>(null);
  const [assetLookup, setAssetLookup] = useState('');
  const [knownMaterials, setKnownMaterials] = useState<{ connection: EngineConnectionContext; asset: AssetRecord }[]>([]);
  const knownAssets = knownMaterials.filter(item => item.connection === connection).map(item => item.asset);
  const [materialSelection, setMaterialSelection] = useState<{ connection: EngineConnectionContext; id: string }[]>([]);
  const selectedAssetIds = materialSelection.filter(item => item.connection === connection).map(item => item.id);
  const setSelectedAssetIds = (update: string[] | ((current: string[]) => string[])) => {
    if (!isEngineConnectionCurrent(connection)) return;
    setMaterialSelection(current => {
      const ownIds = current.filter(item => item.connection === connection).map(item => item.id);
      const next = typeof update === 'function' ? update(ownIds) : update;
      return [...current.filter(item => item.connection !== connection), ...next.map(id => ({ connection, id }))];
    });
  };
  const selectedAssets = knownAssets.filter(asset => selectedAssetIds.includes(asset.asset_id));
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importSource, setImportSource] = useState('');
  const [importRights, setImportRights] = useState('');
  const [importBusy, setImportBusy] = useState(false);
  const [goalError, setGoalError] = useState(false);
  const [creationUncertain, setCreationUncertain] = useState(false);
  const [recoveringCreation, setRecoveringCreation] = useState(false);
  const creationSubmitting = useRef(false);
  const currentInstance = useRef(instanceId); currentInstance.current = instanceId;
  const cancelContext = useRef<CancelContext>({ instanceId, connected, projectId: productionLocator?.project_id ?? null, productionId, generation: 0, mounted: true });
  if (cancelContext.current.instanceId !== instanceId || cancelContext.current.connected !== connected
    || cancelContext.current.projectId !== (productionLocator?.project_id ?? null) || cancelContext.current.productionId !== productionId) {
    cancelContext.current = { instanceId, connected, projectId: productionLocator?.project_id ?? null, productionId, generation: cancelContext.current.generation + 1, mounted: cancelContext.current.mounted };
  }
  const cancelOperation = useRef<CancelIntent | null>(null);
  const pendingStage = useRef<Schemas['StagedAsset'] | null>(null);
  const importConnection = useRef<EngineConnectionContext | null>(null);
  const materialMounted = useRef(true);
  const assetLoading = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const decisionKeys = useRef(new Map<string, string>());
  const shownReview = useRef('');
  const editDisabled = actionBusy || editor.phase === 'loading';

  const productions = useQuery({ queryKey: ['productions', instanceId], enabled: connected, queryFn: () => engineData('GET /api/v1/productions', {}), refetchInterval: connected ? 5000 : false });
  const production = useQuery({ queryKey: ['production', productionId], enabled: connected && Boolean(productionId), queryFn: async () => {
    const detail = await engineData('GET /api/v1/productions/{production_id}', { path: { production_id: productionId! } });
    if (detail.instance_id !== instanceId || detail.project_id !== productionLocator?.project_id || detail.production_id !== productionId) throw new RequestFailure(409, 'submission_identity_mismatch');
    return detail;
  }, refetchInterval: connected && productionId ? 5000 : false });
  const selectedProduction = production.data && production.data.instance_id === instanceId && production.data.project_id === productionLocator?.project_id && production.data.production_id === productionId ? production.data : undefined;
  const revisions = useQuery({ queryKey: ['revisions', productionId], enabled: connected && Boolean(productionId), queryFn: () => engineData('GET /api/v1/productions/{production_id}/revisions', { path: { production_id: productionId! } }) });
  const runEvents = useRunEvents(selectedProduction?.run_id, productionId ?? undefined);
  const selectedEvents = runEvents.events.filter(event => event.run_id === selectedProduction?.run_id && event.production_id === productionId);
  const lastReview = [...selectedEvents].reverse().find(event => event.event_type === 'review.required');
  const reviewRevision = selectedProduction?.status === 'waiting_user' ? revisions.data?.find(item => item.revision_id === lastReview?.entity_revision_id) : undefined;
  const latest = (kind: CreativeRevision['kind']) => revisions.data?.filter(item => item.kind === kind).at(-1);
  const direction = revisions.data?.filter(item => item.kind === 'insight' || item.kind === 'brief') ?? [];
  const isCurrentCancellation = (intent: CancelIntent) => cancelContext.current === intent.context && intent.context.mounted && intent.context.connected
    && intent.context.instanceId === intent.target.instance_id && intent.context.projectId === intent.target.project_id && intent.context.productionId === intent.target.production_id;
  const cancelValid = Boolean(cancelIntent && isCurrentCancellation(cancelIntent) && selectedProduction);

  useLayoutEffect(() => {
    cancelContext.current = { ...cancelContext.current, generation: cancelContext.current.generation + 1, mounted: true };
    return () => { cancelContext.current = { ...cancelContext.current, generation: cancelContext.current.generation + 1, mounted: false }; cancelOperation.current = null; };
  }, []);
  useLayoutEffect(() => {
    if (cancelIntent && !isCurrentCancellation(cancelIntent)) setCancelIntent(null);
    if (cancelOperation.current && !isCurrentCancellation(cancelOperation.current)) {
      cancelOperation.current = null; setActionBusy(false);
    }
  }, [instanceId, connected, productionId, productionLocator?.project_id, cancelIntent]);

  useEffect(() => {
    if (!reviewRevision || shownReview.current === reviewRevision.revision_id) return;
    shownReview.current = reviewRevision.revision_id;
    setActiveStep(reviewRevision.kind === 'insight' || reviewRevision.kind === 'brief' ? 1 : reviewRevision.kind === 'quality' ? 3 : 2);
  }, [reviewRevision?.revision_id]);

  useEffect(() => { try { localStorage.setItem('video-creator:preferences:1', JSON.stringify(preferences)); } catch { /* Cosmetic preference persistence is optional. */ } }, [preferences]);
  useEffect(() => { if (editor.form.source_text) setSourceExpanded(true); }, [editor.form.source_text]);
  useEffect(() => { setAcceptedFeedback(null); setFeedback(''); }, [productionId, instanceId]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview.url); }, [preview]);
  useEffect(() => {
    assetLoading.current?.abort(); setPreview(null); setPreviewBusy(false);
    return () => assetLoading.current?.abort();
  }, [connected, instanceId, connection]);
  useEffect(() => {
    materialMounted.current = true;
    return () => { materialMounted.current = false; assetLoading.current?.abort(); };
  }, []);
  useEffect(() => {
    // Keep the original file/stage/source context; none may migrate to a newly
    // configured connection, even if cached health or the instance ID agrees.
    if (importConnection.current && importConnection.current !== connection) {
      setImportBusy(false); setAssetError(new RequestFailure(409, 'material_connection_changed'));
    }
  }, [connection]);
  useEffect(() => {
    if (!instanceId) return;
    try {
      const intent = readSubmissionIntent('production', instanceId);
      setCreationUncertain(Boolean(intent && !intent.receiptId));
      if (intent?.receiptId) rememberLocator(`video-creator:production:${instanceId}:${intent.body.project_id}`, intent.receiptId);
    } catch (failure) { setCreationUncertain(true); setActionError(failure); }
  }, [instanceId]);
  useEffect(() => {
    if (!preview?.expiresAtUs) return;
    const delay = Math.max(0, Math.min(2_147_483_647, preview.expiresAtUs / 1000 - Date.now()));
    const timer = window.setTimeout(() => {
      if (isEngineConnectionCurrent(preview.connection)) { setPreview(null); setAssetError(new RequestFailure(403, 'authorization_expired')); }
    }, delay);
    return () => window.clearTimeout(timer);
  }, [preview]);
  useEffect(() => {
    // A chosen/recovered task is independent of the editor. List refreshes only
    // fill an empty selection; explicit project navigation releases it.
    if (productionLocator?.instance_id === instanceId && instanceId) return;
    if (!editor.project || !productions.data || !instanceId) {
      setProductionLocator(selected => selected && selected.instance_id === instanceId ? selected : null);
      return;
    }
    const candidates = productions.data.filter(item => item.project_id === editor.project!.project_id);
    const remembered = storedLocator(`video-creator:production:${instanceId}:${editor.project.project_id}`);
    const chosen = candidates.find(item => item.production_id === remembered) ?? candidates[0];
    setProductionLocator(selected => selected?.instance_id === instanceId ? selected : chosen ? { instance_id: instanceId, project_id: chosen.project_id, production_id: chosen.production_id } : null);
  }, [editor.project?.project_id, productions.data, instanceId, productionLocator]);
  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void editor.flush().catch(() => {}); }
      if (event.key === 'Escape') setAssistantOpen(false);
    };
    window.addEventListener('keydown', keydown); return () => window.removeEventListener('keydown', keydown);
  }, [editor.flush]);

  const chooseProduction = (id: string, projectId: string) => {
    if (!instanceId) return;
    setGoalSelectionGeneration(value => value + 1);
    editor.cancelLoad();
    setProductionLocator({ instance_id: instanceId, project_id: projectId, production_id: id });
    rememberLocator(`video-creator:production:${instanceId}:${projectId}`, id);
  };
  const returnToEditor = () => { if (actionBusy) return; setGoalSelectionGeneration(value => value + 1); editor.cancelLoad(); setProductionLocator(null); setActivePage('projects'); setActiveStep(0); };
  const selectProject = async (id: string) => {
    if (actionBusy) return;
    setGoalSelectionGeneration(value => value + 1);
    const navigationInstance = instanceId;
    setSelectedAssetIds([]);
    await editor.load(id, () => { if (currentInstance.current === navigationInstance) returnToEditor(); });
  };
  const beginDraft = (keepInput = false) => {
    if (actionBusy || editor.phase === 'saving') return;
    if (!keepInput) setSelectedAssetIds([]);
    editor.newDraft(keepInput); returnToEditor(); setNotice('');
  };
  const acceptGoalReceipt = (receipt: ProjectGoalAccepted): boolean => {
    if (!connected || currentInstance.current !== receipt.instance_id) return false;
    chooseProduction(receipt.production_id, receipt.project_id);
    rememberLocator(`video-creator:production:${receipt.instance_id}:${receipt.project_id}`, receipt.production_id);
    void queryClient.invalidateQueries({ queryKey: ['projects', receipt.instance_id] });
    void queryClient.invalidateQueries({ queryKey: ['productions', receipt.instance_id] });
    setActivePage('projects'); setActiveStep(1);
    setNotice('目标已受理。方向、方案和作品将在真实完成后出现。');
    return true;
  };
  const recoverProduction = async () => {
    if (creationSubmitting.current || actionBusy || !connected || !instanceId) return;
    creationSubmitting.current = true;
    const submissionInstance = instanceId;
    let receiptRetained = false;
    let progressRead = false;
    setRecoveringCreation(true); setActionBusy(true); setActionError(null); setNotice('');
    try {
      const intent = readSubmissionIntent('production', submissionInstance);
      if (!intent) throw new RequestFailure(409, 'submission_identity_mismatch');
      await verifySubmissionIntent('production', intent, submissionInstance);
      if (!validReceiptId(intent.body.project_id)) throw new RequestFailure(409, 'submission_identity_mismatch');
      const originalProjectId = intent.body.project_id;
      if (currentInstance.current !== submissionInstance) throw new RequestFailure(409, 'submission_identity_mismatch');
      let recoveredId = intent.receiptId;
      if (!recoveredId) {
        // B28 replay reads the original acceptance. Never flush the current form,
        // rebuild its request, change its key, or grant new execution authority.
        const accepted = await engineData('POST /api/v1/productions', { body: intent.body, headers: { 'Idempotency-Key': intent.idempotencyKey } });
        retainProductionReceipt(intent, accepted); recoveredId = accepted.production_id;
      }
      receiptRetained = true;
      if (currentInstance.current !== submissionInstance) return;
      setCreationUncertain(false);
      chooseProduction(recoveredId, originalProjectId);
      if (editor.project?.project_id !== originalProjectId) setActivePage('tasks');
      // The replay's Run/status are a first-acceptance snapshot. Only this GET
      // supplies current progress, including a later feedback Run.
      const current = await engineData('GET /api/v1/productions/{production_id}', { path: { production_id: recoveredId } });
      if (!current || current.instance_id !== submissionInstance || current.project_id !== intent.body.project_id
        || current.production_id !== recoveredId || !validReceiptId(current.run_id) || !validReceiptId(current.request_revision_id)
        || !Object.hasOwn(STATUS, current.status)) throw new RequestFailure(502, 'response_unavailable');
      if (currentInstance.current !== submissionInstance) return;
      queryClient.setQueryData(['production', recoveredId], current);
      progressRead = true;
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['productions', submissionInstance] }),
        queryClient.invalidateQueries({ queryKey: ['revisions', recoveredId] }),
      ]);
      if (currentInstance.current !== submissionInstance) return;
      if (editor.project?.project_id === current.project_id) {
        setActivePage('projects'); setActiveStep(3);
      } else setActivePage('tasks');
      setNotice('原任务回执已恢复，当前进度来自实例最新记录。当前输入仍保留。');
    } catch (failure) {
      if (currentInstance.current === submissionInstance) {
        setActionError(failure);
        // A later permission/rejection/not-sent response cannot prove the first
        // request was unaccepted. Recovery never clears that original intent.
        if (!receiptRetained) setCreationUncertain(true);
        else setNotice(progressRead ? '原任务回执和进度已读取，部分记录暂未刷新。当前输入仍保留。' : '原任务回执已保留。最新进度暂未读到，可刷新任务记录；当前输入仍保留。');
      }
    } finally { creationSubmitting.current = false; setRecoveringCreation(false); setActionBusy(false); }
  };
  const controlRun = async (action: 'pause' | 'resume') => {
    if (!selectedProduction || !connected || editDisabled) return;
    const operationInstance = instanceId;
    setActionBusy(true); setActionError(null); setNotice('');
    try {
      const receipt = action === 'pause'
        ? await engineRequest('POST /api/v1/runs/{run_id}/pause', { path: { run_id: selectedProduction.run_id } })
        : await engineRequest('POST /api/v1/runs/{run_id}/resume', { path: { run_id: selectedProduction.run_id } });
      if (receipt.status !== 200) throw new RequestFailure(receipt.status, 'response_unavailable');
      if (currentInstance.current !== operationInstance) return;
      setNotice(action === 'pause' ? '暂停请求已受理。是否停下新步骤以实例记录为准。' : '恢复请求已受理。后续步骤以实例记录为准。');
      await production.refetch(); if (currentInstance.current === operationInstance) runEvents.reconnect();
    } catch (failure) { if (currentInstance.current === operationInstance) setActionError(failure); } finally { setActionBusy(false); }
  };
  const submitReview = async (action: Schemas['ReviewDecision']['action']) => {
    if (!reviewRevision || !selectedProduction || !connected || editDisabled || (action === 'revise' && !feedback.trim())) return;
    const operationInstance = instanceId;
    setActionBusy(true); setActionError(null); setNotice('');
    const decision: Schemas['ReviewDecision'] = { target_revision_id: reviewRevision.revision_id, action, instruction_text: action === 'revise' ? feedback : '', preserved_constraints: [] };
    const identity = JSON.stringify([selectedProduction.run_id, decision]);
    const key = decisionKeys.current.get(identity) ?? crypto.randomUUID(); decisionKeys.current.set(identity, key);
    try {
      const accepted = await engineData('POST /api/v1/runs/{run_id}/decisions', { path: { run_id: selectedProduction.run_id }, body: decision, headers: { 'Idempotency-Key': key } });
      if (currentInstance.current !== operationInstance) return;
      if ('feedback_id' in accepted) setAcceptedFeedback(accepted);
      setNotice(action === 'approve' ? '审核确认已保存。' : action === 'revise' ? '指导意见已保存，等待Agent重新规划。' : '否决意见已保存。');
      await Promise.all([production.refetch(), revisions.refetch()]);
    } catch (failure) { if (currentInstance.current === operationInstance) setActionError(failure); } finally { setActionBusy(false); }
  };
  const openCancellation = () => {
    if (!selectedProduction || !connected || editDisabled) return;
    const intent: CancelIntent = { context: cancelContext.current, target: { instance_id: selectedProduction.instance_id, project_id: selectedProduction.project_id, production_id: selectedProduction.production_id }, projectName: selectedProjectName };
    if (isCurrentCancellation(intent)) setCancelIntent(intent);
  };
  const cancelProduction = async () => {
    const intent = cancelIntent;
    if (!intent || !isCurrentCancellation(intent) || !selectedProduction || editDisabled || cancelOperation.current) return;
    const target = intent.target;
    cancelOperation.current = intent; setActionBusy(true); setActionError(null);
    try {
      const current = await engineData('POST /api/v1/productions/{production_id}/cancel', { path: { production_id: target.production_id } });
      if (current.instance_id !== target.instance_id || current.project_id !== target.project_id || current.production_id !== target.production_id) throw new RequestFailure(409, 'submission_identity_mismatch');
      if (!isCurrentCancellation(intent)) return;
      queryClient.setQueryData(['production', target.production_id], current);
      if (!isCurrentCancellation(intent)) return;
      await productions.refetch();
      if (isCurrentCancellation(intent)) setCancelIntent(value => value === intent && isCurrentCancellation(intent) ? null : value);
    } catch (failure) { if (isCurrentCancellation(intent)) setActionError(failure); } finally {
      if (isCurrentCancellation(intent) && cancelOperation.current === intent) { cancelOperation.current = null; setActionBusy(false); }
    }
  };
  const addKnownAsset = (asset: AssetRecord, owner: EngineConnectionContext) => {
    if (!isEngineConnectionCurrent(owner) || !materialMounted.current) return;
    setKnownMaterials(current => [...current.filter(item => item.connection !== owner || item.asset.asset_id !== asset.asset_id), { connection: owner, asset }]);
  };
  const openAsset = async (id: string) => {
    const owner = connection;
    if (!connected || !instanceId || !isEngineConnectionCurrent(owner)) return;
    const operationInstance = instanceId;
    assetLoading.current?.abort(); const controller = new AbortController(); assetLoading.current = controller;
    const current = () => materialMounted.current && isEngineConnectionCurrent(owner)
      && currentInstance.current === operationInstance && assetLoading.current === controller && !controller.signal.aborted;
    setPreviewBusy(true); setAssetError(null); setPreview(null);
    try {
      const asset = await engineData('GET /api/v1/assets/{asset_id}', { path: { asset_id: id }, signal: controller.signal }, owner);
      if (!current()) return;
      const metadata = await engineData('GET /api/v1/assets/{asset_id}/content/metadata', { path: { asset_id: id }, signal: controller.signal }, owner);
      if (!current()) return;
      verifyContentMetadata(metadata, { ...asset, instanceId: operationInstance });
      if (metadata.locator.kind !== 'asset' || metadata.locator.asset_id !== id) throw new RequestFailure(409, 'content_metadata_mismatch');
      if (asset.size > PREVIEW_BUFFER_BYTES) throw new RequestFailure(413, 'preview_size_limit');
      const response = await engineContent('GET /api/v1/assets/{asset_id}/content', { path: { asset_id: asset.asset_id }, signal: controller.signal }, owner);
      if (!current()) { await response.body?.cancel().catch(() => {}); return; }
      const blob = await verifiedContentBlob(response, asset);
      if (!current()) return;
      const isText = asset.media_type.startsWith('text/') || asset.media_type.includes('json');
      const text = isText ? new TextDecoder('utf-8', { fatal: true }).decode(await blob.arrayBuffer()) : undefined;
      if (!current()) return;
      setPreview({ connection: owner, asset, url: URL.createObjectURL(blob), expiresAtUs: metadata.authorization_expires_at_us, text });
      addKnownAsset(asset, owner); setActivePage('projects'); setActiveStep(4);
    } catch (failure) { if (current()) setAssetError(failure); } finally { if (current()) setPreviewBusy(false); }
  };
  const chooseImport = (file: File | undefined) => {
    if (!file || importBusy || !connected || !isEngineConnectionCurrent(connection)) return;
    importConnection.current = connection;
    pendingStage.current = null; setAssetError(null); setImportFile(file); setImportSource(`手动导入：${file.name}`); setImportRights(''); setImportOpen(true);
  };
  const importAsset = async () => {
    const owner = importConnection.current;
    if (!connected || !instanceId || !importFile || !importRights.trim() || !importSource.trim()
      || owner !== connection || !isEngineConnectionCurrent(owner) || importBusy) return;
    const operationInstance = instanceId;
    const current = () => materialMounted.current && isEngineConnectionCurrent(owner)
      && importConnection.current === owner && currentInstance.current === operationInstance;
    setImportBusy(true); setAssetError(null);
    try {
      const staged = pendingStage.current ?? await engineData('POST /api/v1/assets/staging', { headers: { 'Content-Type': importFile.type || 'application/octet-stream' }, body: importFile }, owner);
      if (!current()) return;
      pendingStage.current = staged;
      const candidate: Schemas['AssetCandidate'] = { ...pendingStage.current, source: importSource, rights: importRights };
      const asset = await engineData('POST /api/v1/assets/import', { body: candidate }, owner);
      if (!current()) return;
      addKnownAsset(asset, owner); setImportOpen(false); setImportFile(null); pendingStage.current = null; setNotice('素材已校验并保存到实例。');
      setSelectedAssetIds(current => current.includes(asset.asset_id) ? current : [...current, asset.asset_id]);
      // Stay in the target editor: imported assets are inputs, not a finished work.
      setActivePage('projects'); setActiveStep(0);
    } catch (failure) { if (current()) setAssetError(failure); } finally { if (current()) setImportBusy(false); }
  };
  const saveLabel = editor.phase === 'loading' ? '载入中' : !connected && editor.dirty ? '尚未保存' : editor.phase === 'saving' || (editor.dirty && !editor.error) ? '保存中' : editor.phase === 'saved' && !editor.dirty ? '实例已保存' : editor.phase === 'conflict' ? '版本冲突' : editor.phase === 'failed' ? '保存失败' : '新项目';
  const renderReview = () => reviewRevision ? <section className="review-section">{reviewRevision.kind === 'quality' ? <RevisionView revision={reviewRevision} /> : null}<div className="review-controls"><div><span className="review-label">待审核：{KIND[reviewRevision.kind]}</span><p>确认当前版本，或用一句话指导修改。</p></div><Button disabled={!connected || actionBusy} onClick={() => void submitReview('approve')}><Check size={15} />确认{KIND[reviewRevision.kind]}</Button><Button variant="soft" disabled={!connected || actionBusy} onClick={() => setAssistantOpen(true)}>给修改意见</Button></div></section> : null;
  const latestView = (kind: CreativeRevision['kind'], empty: string) => latest(kind) ? <RevisionView revision={latest(kind)!} /> : <EmptyResult title={empty}>Agent产物实际生成并保存后显示。你不必预先编写。</EmptyResult>;
  const checkingAuthorization = Boolean(connection) && !healthQuery.isError && healthQuery.isPending;

  // ADR0081 startup gate: a restricted instance must never fall through to the
  // project/task surface or the old "connection unavailable" dead state.
  if (authorizationRestricted || checkingAuthorization) {
    return <Theme appearance={appearance} accentColor="teal" grayColor="slate" radius="medium" scaling="100%"><div className="workbench is-authorization" data-appearance={appearance}>
      <a className="skip-link" href="#authorization-main">跳到授权区</a>
      <main id="authorization-main" className="authorization-main" tabIndex={-1}>
        {authorizationRestricted
          ? <ProductAuthorizationGate key={authorizationChannel} channel={authorizationChannel} reachable={reachable} instanceId={instanceId} onRecheck={() => { void healthQuery.refetch(); }} />
          : <AuthorizationBooting />}
      </main>
    </div></Theme>;
  }

  return <Theme appearance={appearance} accentColor="teal" grayColor="slate" radius="medium" scaling="100%"><div className="workbench" data-appearance={appearance}>
    <a className="skip-link" href="#workspace-main">跳到创作区</a>
    <aside className="app-nav" aria-label="工作台导航"><a className="brand" href="#workspace-main" aria-label="VideoCreator创作工作台"><span className="brand-mark"><Clapperboard size={21} strokeWidth={1.7} /></span><span>VideoCreator</span></a><nav>{[{ id: 'projects', label: '项目', icon: FolderOpen }, { id: 'assets', label: '素材', icon: Image }, { id: 'tasks', label: '任务', icon: Layers }, { id: 'settings', label: '设置', icon: Settings2 }].map(item => <button key={item.id} type="button" className={`nav-button ${activePage === item.id ? 'is-active' : ''}`} aria-current={activePage === item.id ? 'page' : undefined} onClick={() => setActivePage(item.id)}><item.icon size={18} strokeWidth={1.7} aria-hidden="true" /><span>{item.label}</span></button>)}</nav><div className="nav-bottom"><ShieldCheck size={16} /><span>本地工具</span></div></aside>
    <div className="app-body"><header className="project-header"><div className="project-heading"><span className="workspace-name">我的工作空间</span><div className="project-title-row"><h1>{activePage === 'projects' ? (viewingOtherProject && activeStep > 0 ? selectedProjectName : editor.form.name) : { assets: '素材库', tasks: '任务中心', settings: '设置' }[activePage]}</h1><span className={`save-status ${editor.error ? 'is-error' : ''}`} aria-live="polite">{saveLabel === '实例已保存' ? <Check size={13} /> : null}{viewingOtherProject && activePage === 'projects' && activeStep > 0 ? '当前创作：' : ''}{saveLabel}</span></div></div><div className="header-actions"><Badge color={health.isError ? 'amber' : 'gray'} variant="soft">{health.isPending ? '连接中' : connected ? '本地实例' : '连接暂不可用'}</Badge><IconButton size="2" variant="ghost" color="gray" aria-label={appearance === 'light' ? '切换深色主题' : '切换浅色主题'} onClick={() => setAppearance(appearance === 'light' ? 'dark' : 'light')}>{appearance === 'light' ? <Moon size={17} /> : <Sun size={17} />}</IconButton><IconButton size="2" variant="soft" color="gray" aria-label={assistantOpen ? '收起创作助手' : '展开创作助手'} aria-expanded={assistantOpen} aria-controls="creative-assistant" onClick={() => setAssistantOpen(!assistantOpen)}>{assistantOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}</IconButton></div></header>
      {activePage === 'projects' ? <nav className="step-nav" aria-label="创作步骤">{STEPS.map((step, index) => <button key={step} className={`step-button ${index === activeStep ? 'is-active' : ''}`} type="button" aria-current={index === activeStep ? 'step' : undefined} disabled={actionBusy} onClick={() => { if (index === 0) returnToEditor(); else setActiveStep(index); }}><span className="step-number">{index + 1}</span><span>{step}</span>{index < 4 ? <ChevronRight className="step-divider" size={14} /> : null}</button>)}</nav> : null}
      <div className={`workspace-layout ${assistantOpen ? 'has-assistant' : ''}`}><main id="workspace-main" className="workspace-main" tabIndex={-1}>
        {health.isError ? <Callout.Root color="amber" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>实例连接暂不可用。当前输入仍保留，已有项目不会锁住。</Callout.Text><Button size="1" variant="soft" onClick={() => void health.refetch()}>重新连接</Button></Callout.Root> : null}
        {editor.error ? <Callout.Root color="red" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{errorMessage(editor.error)}</Callout.Text><div className="error-actions">{editor.phase === 'conflict' && editor.project ? <><Button size="1" variant="soft" color="red" onClick={() => setReloadOpen(true)}>载入已保存版本</Button><Button size="1" variant="soft" color="gray" onClick={() => beginDraft(true)}>另存为新项目</Button></> : <Button size="1" variant="soft" color="red" disabled={!connected} onClick={() => void editor.flush().catch(() => {})}>重试保存</Button>}</div></Callout.Root> : null}
        {actionError ? <Callout.Root color="red" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{errorMessage(actionError)}</Callout.Text><Button size="1" variant="soft" color="red" onClick={() => { void production.refetch(); void revisions.refetch(); }}>刷新任务</Button></Callout.Root> : null}
        {notice ? <p className="action-notice" role="status">{notice}</p> : null}{creationUncertain ? <Callout.Root color="amber" role="alert"><Callout.Text>原请求的受理结果待核实。恢复只使用发起项目和原输入，当前修改仍保留，核实前不会新建制作。</Callout.Text><Flex gap="2" wrap="wrap"><Button size="1" variant="soft" disabled={!connected || actionBusy} onClick={() => void recoverProduction()}>{recoveringCreation ? '正在读取回执' : '恢复原请求'}</Button><Button size="1" variant="ghost" color="gray" disabled={!connected || actionBusy} onClick={() => { setActivePage('tasks'); void productions.refetch(); }}>查看任务记录</Button></Flex></Callout.Root> : null}
        {activePage === 'projects' ? <>{viewingOtherProject ? <Callout.Root color="gray"><Callout.Text>正在查看：{selectedProjectName}。{editor.form.name}的输入和保存状态仍保留。</Callout.Text><Button size="1" variant="soft" disabled={actionBusy} onClick={returnToEditor}>返回当前创作</Button></Callout.Root> : null}<div className="project-switcher"><Select.Root value={editor.project?.project_id ?? ''} onValueChange={id => { void selectProject(id); }} disabled={editor.dirty || editor.phase === 'saving' || editDisabled}><Select.Trigger placeholder="新项目" aria-label="选择已保存项目" /><Select.Content>{editor.list.data?.map(item => <Select.Item key={item.project_id} value={item.project_id}>{item.name}</Select.Item>)}</Select.Content></Select.Root><Button size="2" variant="ghost" color="gray" disabled={editor.dirty || editor.phase === 'saving' || editDisabled} onClick={() => beginDraft()}><Plus size={15} />新建</Button>{editor.project ? <span className="project-revision">保存版本 {editor.project.revision}</span> : null}</div>
          
          {activeStep === 0 ? <section className="creation-panel" aria-labelledby="create-title"><div className="section-intro"><span className="section-kicker">从一个想法开始</span><h2 id="create-title">你想做什么视频？</h2><p>给出目标和资料，Agent负责洞察、剧本、分镜与制作。你来审核和指导。</p></div><label className="field-label" htmlFor="creative-goal">视频目标</label><TextArea id="creative-goal" className="goal-input" size="3" value={editor.form.goal} disabled={editDisabled} aria-invalid={goalError} aria-describedby={goalError ? 'goal-error' : undefined} placeholder="例如：用轻松的游戏解说，介绍这次更新里最值得体验的内容。" onChange={event => { editor.update('goal', event.target.value); setGoalError(false); }} />{goalError ? <p className="field-error" id="goal-error">请先给出一个视频目标。</p> : null}<div className="input-bottom"><Button size="2" variant="ghost" color="gray" onClick={() => setSourceExpanded(!sourceExpanded)} aria-expanded={sourceExpanded} aria-controls="source-input"><FileText size={16} />{sourceExpanded ? '收起文字资料' : '添加文字资料'}</Button><span>不需要先写剧本和分镜</span></div>{sourceExpanded ? <div className="source-input" id="source-input"><label className="field-label" htmlFor="creative-source">可用资料</label><TextArea id="creative-source" size="2" value={editor.form.source_text} disabled={editDisabled} placeholder="粘贴文章、产品介绍、故事设定或已有资料。" onChange={event => editor.update('source_text', event.target.value)} /></div> : null}
            <div className="creation-options"><div><label className="field-label" htmlFor="creation-mode">创作方式</label><Select.Root value={preferences.mode} disabled={actionBusy} onValueChange={value => setPreferences(current => ({ ...current, mode: value as Preferences['mode'] }))}><Select.Trigger id="creation-mode" /><Select.Content><Select.Item value="interactive">审核与指导</Select.Item><Select.Item value="unattended">预授权自动制作</Select.Item></Select.Content></Select.Root></div><div><label className="field-label" htmlFor="aspect-ratio">画幅</label><Select.Root value={preferences.aspectRatio} disabled={actionBusy} onValueChange={value => setPreferences(current => ({ ...current, aspectRatio: value as Preferences['aspectRatio'] }))}><Select.Trigger id="aspect-ratio" /><Select.Content><Select.Item value="9:16">竖屏 9:16</Select.Item><Select.Item value="16:9">横屏 16:9</Select.Item></Select.Content></Select.Root></div><div><label className="field-label" htmlFor="duration">参考时长</label><Select.Root value={preferences.durationSeconds} disabled={actionBusy} onValueChange={value => setPreferences(current => ({ ...current, durationSeconds: value }))}><Select.Trigger id="duration" /><Select.Content><Select.Item value="30">约30秒</Select.Item><Select.Item value="60">约1分钟</Select.Item><Select.Item value="120">约2分钟</Select.Item></Select.Content></Select.Root></div></div><NativeSetupView form={editor.form} assetIds={selectedAssets.map(asset => asset.asset_id)} brief={{ language: "zh-CN", aspect_ratio: preferences.aspectRatio, target_duration_us: Number(preferences.durationSeconds) * 1_000_000, guidance: preferences.mode === "interactive" ? "请优先提供可审核的方向和方案，等待用户确认后继续。" : "在本机已有授权允许的范围内自动制作；遇到必须审核的步骤，等待用户确认。" }} connected={connected} instanceId={instanceId} contextGeneration={goalSelectionGeneration} onAccepted={acceptGoalReceipt} /><div className="local-alternative"><span>手里已有素材？</span><Button size="2" variant="ghost" color="gray" disabled={!connected} onClick={() => fileInputRef.current?.click()}><Upload size={15} />导入素材</Button></div><section className="goal-materials" aria-label="本次创作资料"><div className="goal-materials-heading"><h3>本次创作资料</h3><span>{selectedAssets.length} 份已选择</span></div>{knownAssets.length ? <div className="goal-materials-list">{knownAssets.map(asset => <label className="goal-material-option" key={asset.asset_id}><input type="checkbox" checked={selectedAssetIds.includes(asset.asset_id)} disabled={!connected || editDisabled || importBusy} onChange={event => { const selected = event.target.checked; setSelectedAssetIds(current => selected ? current.includes(asset.asset_id) ? current : [...current, asset.asset_id] : current.filter(id => id !== asset.asset_id)); }} /><span><strong>{asset.source}</strong><small>{asset.media_type} · {Math.ceil(asset.size / 1024)} KB</small><small>使用范围：{asset.rights}</small></span></label>)}</div> : <p className="small-note">导入文字、图片、音频或视频，或在素材库打开已有资料后选择。</p>}<p className="small-note">导入或读取素材不等于获得制作权限，仍按实例授权范围检查。开始创作后资料随原目标固定，待核实请求不会随这里的选择改变。</p></section><details className="advanced-settings"><summary>项目选项<ChevronDown size={14} /></summary><div><label className="field-label" htmlFor="project-title">作品名称</label><TextField.Root id="project-title" value={editor.form.name} disabled={editDisabled} onChange={event => editor.update('name', event.target.value)} /><p>画幅、时长和创作方式是本机偏好，提交时固定到任务。可用模型、预算与资料外发范围由实例授权控制。</p></div></details></section> : null}
          {activeStep === 1 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">定方向</span><h2>把想法变成创作方向</h2><p>Agent研究资料、受众和制作可行性，推荐角度与表现形式。</p></div>{direction.length ? direction.map(item => <section className="creative-proposal" key={item.revision_id}><h3>{KIND[item.kind]}</h3><RevisionView revision={item} /></section>) : <EmptyResult title="还没有方向提案">{selectedProduction ? '任务已保存，方向产物在Agent实际完成后出现。' : '先给出目标和资料，Agent会提出可审核的方向。'}</EmptyResult>}{renderReview()}</section> : null}
          {activeStep === 2 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">看方案</span><h2>先看完整方案，再开始制作</h2><p>剧本、分镜、角色与声音共享同一个方案版本。</p></div><Tabs.Root defaultValue="script" className="plan-tabs"><Tabs.List aria-label="制作方案视图"><Tabs.Trigger value="script">剧本</Tabs.Trigger><Tabs.Trigger value="storyboard">分镜</Tabs.Trigger><Tabs.Trigger value="voices">角色与声音</Tabs.Trigger></Tabs.List><Tabs.Content value="script">{latestView('script', '剧本尚未生成')}</Tabs.Content><Tabs.Content value="storyboard">{latestView('storyboard', '分镜尚未生成')}</Tabs.Content><Tabs.Content value="voices">{latestView('plan', '还没有制作计划')}</Tabs.Content></Tabs.Root>{renderReview()}</section> : null}
          {activeStep === 3 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">制作</span><h2>让AI剧组完成视听制作</h2><p>镜头和音轨完成并校验后逐项出现；已有结果会保留。</p></div>{selectedProduction ? <div className="production-state"><Clapperboard size={27} strokeWidth={1.5} /><h3>{STATUS[selectedProduction.status]}</h3><p>{selectedProduction.status === 'queued' && !health.data?.worker_connected ? '任务已受理，创作服务尚未连接。目标和资料已保留。' : selectedProduction.status === 'waiting_authorization' ? '任务已保存，等待实例完成所需授权。已有资料保留，授权齐备前不会开始后续制作。' : selectedProduction.status === 'needs_reconciliation' ? '上游结果或费用需要核实，系统不会盲目重复提交。' : selectedProduction.status === 'waiting_user' ? '请审核真实产物或给出指导意见。' : '当前状态来自实例执行记录。'}</p><span className="cost-note">{selectedProduction.operations.some(item => item.cost_status === 'unknown') ? '费用待核实' : selectedProduction.operations.length ? `已记录费用 CNY ${selectedProduction.cost.spent.amount}` : '尚无模型调用记录'}</span><div className="production-actions"><Button variant="soft" size="2" onClick={() => { void production.refetch(); runEvents.reconnect(); }}><RefreshCw size={14} />刷新记录</Button>{!['succeeded', 'failed', 'cancelled', 'cancel_requested', 'needs_reconciliation'].includes(selectedProduction.status) ? <><Button size="2" variant="soft" disabled={!connected || actionBusy} onClick={() => void controlRun('pause')}>暂停新步骤</Button><Button size="2" variant="ghost" color="gray" disabled={!connected || actionBusy} onClick={() => void controlRun('resume')}>恢复新步骤</Button></> : null}{!['succeeded', 'failed', 'cancelled', 'cancel_requested'].includes(selectedProduction.status) ? <Button size="2" variant="ghost" color="gray" disabled={!connected || actionBusy} onClick={openCancellation}>取消任务</Button> : null}</div></div> : <EmptyResult title="还没有制作任务">给出目标后一次提交，无需逐个启动内部制作步骤。</EmptyResult>}{renderReview()}<details className="advanced-settings"><summary>任务记录<ChevronDown size={14} /></summary><div><p>{runEvents.phase === 'connected' ? '已连接实例事件' : runEvents.phase === 'disconnected' ? '事件连接已断开，已有记录仍保留。' : runEvents.phase === 'connecting' ? '正在连接事件' : '尚未选择任务'}</p>{runEvents.phase === 'disconnected' ? <Button size="1" variant="soft" onClick={runEvents.reconnect}>重连事件</Button> : null}<ol className="event-records">{selectedEvents.map(event => <li key={event.event_id}><span>{EVENT[event.event_type] ?? event.event_type}</span><time>{new Date(event.occurred_at_us / 1000).toLocaleTimeString()}</time></li>)}</ol></div></details><details className="advanced-settings"><summary>AI剧组职责<ChevronDown size={14} /></summary><div><p>导演把握创作，执行统筹安排任务，画面与声音落实素材，后期组织剪辑，审片检查结果。只在真实执行后显示启用角色与分工。</p></div></details></section> : null}
          {activeStep === 4 ? <><DeliveryView key={selectedProduction?.bundle_ref?.bundle_revision_id ?? productionId ?? 'empty'} bundleRef={selectedProduction?.bundle_ref} connected={connected} status={selectedProduction?.status} onAssets={() => setActivePage('assets')} />{preview && preview.connection === connection ? <section className="delivery-panel standalone-asset"><div className="stage-heading"><h2>实例素材预览</h2><p>这份素材尚未绑定完整作品包。</p></div>{preview.asset.media_type.startsWith('video/') ? <div className="media-preview"><video key={preview.url} src={preview.url} controls preload="metadata" playsInline aria-label="受保护实例视频素材预览" onError={() => { setPreview(null); setAssetError(new RequestFailure(422, 'media_invalid')); }} /></div> : preview.asset.media_type.startsWith('audio/') ? <div className="audio-preview"><h3>{preview.asset.source}</h3><audio key={preview.url} src={preview.url} controls preload="metadata" aria-label="受保护实例音频素材预览" onError={() => { setPreview(null); setAssetError(new RequestFailure(422, 'media_invalid')); }} /></div> : preview.asset.media_type.startsWith('image/') ? <img className="protected-image" src={preview.url} alt="已校验的实例图片素材" /> : preview.text !== undefined ? <pre className="asset-text-preview">{preview.text}</pre> : null}<div className="asset-preview-meta"><Badge color="gray">实例素材</Badge><span>{preview.asset.source}</span><p>使用范围：{preview.asset.rights}</p><Button size="1" variant="ghost" color="gray" onClick={() => setPreview(null)}>关闭素材预览</Button></div></section> : null}</> : null}
        </> : null}
        {activePage === 'assets' ? <><section className="result-panel"><div className="stage-heading"><span className="section-kicker">素材库</span><h2>让已有资料进入创作</h2><p>素材校验后由安装实例保存，记录来源与使用范围。</p></div><Button variant="soft" disabled={!connected || importBusy} onClick={() => fileInputRef.current?.click()}><Upload size={16} />导入素材</Button><div className="known-assets">{knownAssets.map(asset => <button className="asset-row" key={asset.asset_id} type="button" disabled={previewBusy || !connected} onClick={() => void openAsset(asset.asset_id)}><FileText size={18} /><span>{asset.source}<small>{asset.media_type} · {Math.ceil(asset.size / 1024)} KB</small></span><ChevronRight size={15} /></button>)}</div>{knownAssets.length ? <p className="small-note">这里列出本次打开过的实例素材，完整素材列表接口尚未提供。</p> : <EmptyResult title="还没有打开素材">可以导入，或通过已有素材编号从实例读取。媒体解码能力不足时保留暂存并提示。</EmptyResult>}<details className="advanced-settings"><summary>打开已有实例素材<ChevronDown size={14} /></summary><div><label className="field-label" htmlFor="asset-id">素材编号</label><div className="asset-lookup"><TextField.Root id="asset-id" value={assetLookup} placeholder="asset..." onChange={event => setAssetLookup(event.target.value)} /><Button size="2" disabled={!connected || previewBusy || !/^[A-Za-z0-9_.:-]{1,128}$/.test(assetLookup)} onClick={() => void openAsset(assetLookup)}>{previewBusy ? '读取中' : '打开'}</Button></div><p>只读取已获授权编号，不接受本机路径。</p></div></details></section><BundleImportView key={instanceId} instanceId={instanceId} projectId={editor.project?.project_id} connected={connected} /></> : null}
        {activePage === 'tasks' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">任务中心</span><h2>创作任务都在这里</h2><p>桌面、API与MCP任务使用同一份执行记录。</p></div>{productions.data?.length ? <div className="task-list">{productions.data.map(item => <button type="button" className="task-row" key={item.production_id} disabled={!connected || actionBusy} aria-current={productionId === item.production_id ? 'true' : undefined} onClick={() => { try { chooseProduction(item.production_id, item.project_id); setActivePage('projects'); setActiveStep(3); } catch (failure) { setActionError(failure); } }}><Clapperboard size={20} /><span>{editor.list.data?.find(project => project.project_id === item.project_id)?.name ?? '实例创作任务'}<small>{item.production_id}</small></span><Badge color={item.status === 'needs_reconciliation' ? 'amber' : 'gray'}>{STATUS[item.status]}</Badge></button>)}</div> : <EmptyResult title="还没有制作任务">受理后显示真实状态，刷新或断开页面不会取消实例任务。</EmptyResult>}{productions.error ? <Callout.Root color="red"><Callout.Text>{errorMessage(productions.error)}</Callout.Text></Callout.Root> : null}</section> : null}
        {activePage === 'settings' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">设置</span><h2>使用你自己的能力</h2><p>本地工具免产品注册。自有模型和官方服务是可选能力来源。</p></div><div className="settings-row"><ShieldCheck size={21} /><div><h3>本地工具模式</h3><p>项目保存到当前安装实例，免官方账号登录。</p></div><Badge color="teal">免注册</Badge></div><div className="settings-row"><Sparkles size={21} /><div><h3>创作服务</h3><p>{health.data?.worker_connected ? '实例已连接创作服务，能力与预算以实例授权为准。' : '此开发实例尚未启动创作服务。任务可保存，不会伪装成生成完成。'}</p></div><Badge color="gray">{health.data?.worker_connected ? '已连接' : '未连接'}</Badge></div><div className="settings-row"><FolderOpen size={21} /><div><h3>数据与凭证</h3><p>工作台通过受控连接访问项目，不读取模型密钥。浏览器还会保留待核实请求的完整目标和资料正文，用于恢复原任务。</p></div></div><div className="settings-row"><FolderOpen size={21} /><div><h3>已导入素材的使用授权</h3><p>将已导入作品用于新创作，需要所有者确认素材范围、用途与有效期。当前入口尚未接通所有者管理身份。</p><Button size="1" variant="soft" disabled>等待所有者连接</Button></div><Badge color="gray">未接通</Badge></div><details className="advanced-settings"><summary>连接诊断<ChevronDown size={14} /></summary><div><p>实例：{instanceId ?? '尚未连接'}</p><p>接口版本：{health.data?.schema_version ?? '未知'}</p><p>连接由应用入口提供；桌面IPC与安装仍需独立验证。</p><Button size="1" variant="soft" onClick={() => void health.refetch()}><RefreshCw size={13} />重新检查连接</Button></div></details></section> : null}
        {assetError && !importOpen ? <Callout.Root color="red" className="storage-error" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{errorMessage(assetError)}</Callout.Text></Callout.Root> : null}
      </main>{assistantOpen ? <aside id="creative-assistant" className="creative-assistant" aria-label="创作助手"><div className="assistant-heading"><h2>创作助手</h2><IconButton size="1" variant="ghost" color="gray" aria-label="关闭创作助手" onClick={() => setAssistantOpen(false)}><X size={17} /></IconButton></div><div className="assistant-empty"><Sparkles size={20} strokeWidth={1.6} /><p>{reviewRevision ? `当前${KIND[reviewRevision.kind]}等待审核，意见绑定这份产物版本。` : '真实产物等待审核后，可在这里给出指导意见。'}</p></div><label className="field-label" htmlFor="creative-feedback">指导意见</label><TextArea id="creative-feedback" size="2" value={feedback} placeholder="例如：表达更年轻，只修改第三镜头。" onChange={event => setFeedback(event.target.value)} /><Button size="2" disabled={!connected || actionBusy || !reviewRevision || !feedback.trim()} className="feedback-submit" onClick={() => void submitReview('revise')}>提交指导</Button><p className="small-note">意见绑定当前版本，不扩大预算或发布权限。</p>{acceptedFeedback ? <div className="feedback-receipt"><strong>指导意见已保存</strong><p>{acceptedFeedback.instruction_text}</p><details><summary>意见版本与保留约束</summary><p>{acceptedFeedback.feedback_id}</p><p>后续任务：{acceptedFeedback.new_run_id}</p><p>{acceptedFeedback.preserved_constraints.join('；') || '保留约束按原任务和后端规划执行。'}</p></details></div> : null}{reviewRevision ? <Button size="1" variant="ghost" color="gray" disabled={actionBusy || !connected} onClick={() => void submitReview('reject')}>否决当前提案</Button> : null}</aside> : null}</div>
      <footer className="probe-footer"><span>Gate0连接验证</span><span>{connected ? '项目与任务来自本地实例' : '等待本机实例连接'}</span><Dialog.Root><Dialog.Trigger><Button size="1" variant="ghost" color="gray"><Info size={13} />运行范围</Button></Dialog.Trigger><Dialog.Content maxWidth="460px"><Dialog.Title>当前运行范围</Dialog.Title><Dialog.Description>工作台连接实例项目、任务、事件和受控素材接口。真实媒体生成与桌面安装仍需后续验证。</Dialog.Description><div className="dialog-copy"><p>项目输入真实保存，审核只针对实例已存产物，状态不会由计时器生成。</p><p>创作能力与预算以实例授权为准。只有实际作品包存在才提供固定版本导出和引用；桌面会话和完整素材列表仍待接入验证。</p></div><Flex justify="end" mt="4"><Dialog.Close><Button>知道了</Button></Dialog.Close></Flex></Dialog.Content></Dialog.Root></footer>
    </div>
    <input ref={fileInputRef} className="visually-hidden" type="file" accept="video/*,audio/*,image/*,text/plain,application/json,application/x-ndjson" aria-label="选择要导入实例的素材" onChange={event => { chooseImport(event.target.files?.[0]); event.currentTarget.value = ''; }} />
    <Dialog.Root open={reloadOpen} onOpenChange={setReloadOpen}><Dialog.Content maxWidth="460px"><Dialog.Title>载入已保存版本</Dialog.Title><Dialog.Description>当前未保存输入会被替换。需要保留时，先选择“另存为新项目”。</Dialog.Description><Flex justify="end" gap="3" mt="5"><Dialog.Close><Button variant="soft" color="gray">保留当前输入</Button></Dialog.Close><Button onClick={() => { if (editor.project) void selectProject(editor.project.project_id); setReloadOpen(false); }}>载入已保存版本</Button></Flex></Dialog.Content></Dialog.Root>
    <Dialog.Root open={Boolean(cancelIntent)} onOpenChange={value => { if (!value) setCancelIntent(null); }}><Dialog.Content maxWidth="460px"><Dialog.Title>取消这份制作任务？</Dialog.Title><Dialog.Description>停止安排后续步骤。已提交的上游请求可能继续，结果与费用仍按实际状态核实。</Dialog.Description><div className="dialog-copy"><p>{cancelIntent?.projectName}</p><p>{cancelIntent?.target.production_id}</p>{!cancelValid ? <p>连接或任务已变化，请重新打开取消确认。</p> : null}</div><Flex justify="end" gap="3" mt="5"><Dialog.Close><Button variant="soft" color="gray">继续制作</Button></Dialog.Close><Button color="red" disabled={actionBusy || !cancelValid} onClick={() => void cancelProduction()}>确认取消</Button></Flex></Dialog.Content></Dialog.Root>
    <Dialog.Root open={importOpen} onOpenChange={value => { if (!importBusy) setImportOpen(value); }}><Dialog.Content maxWidth="480px"><Dialog.Title>导入素材</Dialog.Title><Dialog.Description>{importFile?.name ?? '选择素材'}。校验后存入安装实例，暂存不代表导入成功。</Dialog.Description><div className="import-fields"><label className="field-label" htmlFor="import-source">来源</label><TextField.Root id="import-source" value={importSource} disabled={importBusy} onChange={event => setImportSource(event.target.value)} /><label className="field-label" htmlFor="import-rights">使用范围与授权</label><TextArea id="import-rights" size="2" value={importRights} disabled={importBusy} placeholder="说明素材来源、你拥有的使用权限及适用范围。" onChange={event => setImportRights(event.target.value)} /></div>{assetError ? <Callout.Root color="red" role="alert"><Callout.Text>{errorMessage(assetError)}</Callout.Text></Callout.Root> : null}<Flex justify="end" gap="3" mt="5"><Dialog.Close><Button variant="soft" color="gray" disabled={importBusy}>稍后导入</Button></Dialog.Close><Button disabled={importBusy || !connected || importConnection.current !== connection || !isEngineConnectionCurrent(importConnection.current) || !importSource.trim() || !importRights.trim()} onClick={() => void importAsset()}>{importBusy ? '正在校验' : pendingStage.current ? '重试校验与导入' : '校验并导入'}</Button></Flex></Dialog.Content></Dialog.Root>
  </div></Theme>;
}
