import { useEffect, useRef, useState } from 'react';
import { Button, Callout, Flex } from '@radix-ui/themes';
import { Sparkles } from 'lucide-react';
import { useNativeSetup } from './nativeSetup';
import { engineData, errorMessage, getSubmissionIdentity, RequestFailure } from './engine';
import type { ProjectGoalAccepted, ProjectGoalInput, ProjectInput, Schemas } from './engine';
import { isGoalReceipt, makeGoalIntent, readGoalIntent, saveGoalIntent, verifyGoalIntent, sameGoalProposal } from './goalIntents';
import type { GoalContext, GoalIntent } from './goalIntents';

type Props = { form: ProjectInput; brief: Schemas['CreativeBriefInput']; assetIds?: readonly string[]; connected: boolean; instanceId?: string; contextGeneration: number; onAccepted: (receipt: ProjectGoalAccepted) => boolean };
export function NativeSetupView({ form, brief, assetIds = [], connected, instanceId, contextGeneration, onAccepted }: Props) {
  const setup = useNativeSetup();
  const view = setup.view;
  const identity = getSubmissionIdentity();
  const apiContext: GoalContext | null = connected && identity && identity.instanceId === instanceId
    ? { kind: 'api', instanceId: identity.instanceId, principalId: identity.principalId } : null;
  const context: GoalContext | null = setup.connected ? view ? { kind: 'native', generation: view.generation } : null : apiContext;
  const contextText = JSON.stringify(context);
  const scope = contextText + ':' + contextGeneration;
  const latest = useRef({ scope, identity, mounted: false });
  latest.current.scope = scope; latest.current.identity = identity;
  const [intent, setIntent] = useState<GoalIntent | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [heldScope, setHeldScope] = useState('');
  const locked = useRef(false);
  const shown = useRef('');
  useEffect(() => { latest.current.mounted = true; return () => { latest.current.mounted = false; }; }, []);
  useEffect(() => {
    setIntent(null); setFailure(null);
    if (!context) return;
    try { setIntent(readGoalIntent(context)); } catch (error) { setFailure(error); }
  }, [contextText]);
  const current = (captured: string, owner: typeof identity) => latest.current.mounted && latest.current.scope === captured
    && (setup.connected || (latest.current.identity === owner && getSubmissionIdentity() === owner));

  useEffect(() => {
    if (!context || context.kind !== 'native' || !view || !intent || intent.context.kind !== 'native') return;
    try {
      const original = view.request_identity;
      if (!original || original.original_generation !== intent.context.generation
        || original.idempotency_key !== intent.key || !sameGoalProposal(original.goal, intent.body)) return;
      // A lost prepare ACK may only attach the attempt retained by this exact
      // native proposal. No prepare is replayed and no approval is inferred.
      if (intent.attempt === null && view.attempt !== null) {
        const associated: GoalIntent = { ...intent, attempt: view.attempt };
        saveGoalIntent(associated); setIntent(associated); return;
      }
      if (view.phase === 'completed' && intent.attempt !== null && intent.attempt === view.attempt && isGoalReceipt(view.goal_receipt)) {
        if (intent.disposition !== 'accepted') {
          const accepted: GoalIntent = { ...intent, receipt: view.goal_receipt, disposition: 'accepted' };
          saveGoalIntent(accepted); setIntent(accepted);
        }
      } else if (view.phase === 'aborted' && intent.attempt !== null && intent.attempt === view.attempt && intent.disposition === 'pending') {
        const aborted: GoalIntent = { ...intent, disposition: 'rejected' }; saveGoalIntent(aborted); setIntent(aborted);
      }
    } catch (error) { setFailure(error); }
  }, [view, intent, contextText]);
  useEffect(() => {
    if (!intent?.receipt || !heldScope || heldScope !== scope || shown.current === intent.key) return;
    if (onAccepted(intent.receipt)) shown.current = intent.key;
  }, [intent, scope, instanceId, onAccepted, heldScope]);

  const sendApi = async (original: GoalIntent, captured: string, owner: typeof identity) => {
    if (!apiContext || original.context.kind !== 'api') throw new RequestFailure(503, 'submission_identity_missing', undefined, undefined, 'not_sent');
    await verifyGoalIntent(original, apiContext);
    if (!current(captured, owner)) return;
    const accepted = await engineData('POST /api/v1/project-goals', { body: original.body, headers: { 'Idempotency-Key': original.key } });
    if (!isGoalReceipt(accepted) || accepted.instance_id !== original.context.instanceId) throw new RequestFailure(502, 'response_unavailable');
    const retained: GoalIntent = { ...original, receipt: accepted, disposition: 'accepted' };
    saveGoalIntent(retained);
    if (current(captured, owner)) setIntent(retained);
  };
  const submit = async (recover = false) => {
    if (!context || locked.current || setup.busy || (!recover && !form.goal.trim())) return;
    const captured = scope; const owner = identity;
    locked.current = true; setBusy(true); setFailure(null); setHeldScope(captured);
    let original: GoalIntent | null = null;
    try {
      const existing = readGoalIntent(context);
      if (recover) {
        if (!existing || existing.context.kind !== 'api' || existing.disposition !== 'pending') return;
        original = existing;
      } else {
        if (existing?.disposition === 'pending') { setIntent(existing); return; }
        const body: ProjectGoalInput = {
          format: 'project-goal-input-v1', name: form.name.trim() || '未命名作品', goal: form.goal,
          inputs: { source_text: form.source_text, asset_ids: [...assetIds] }, source_bindings: [],
          brief: { ...brief }, delivery: 'reference', creation_authorization_ref: null,
        };
        original = await makeGoalIntent(context, body);
        if (!current(captured, owner)) return;
        saveGoalIntent(original); setIntent(original);
      }
      if (original.context.kind === 'native') {
        await verifyGoalIntent(original, context);
        if (!current(captured, owner)) return;
        const prepared = await setup.prepare(JSON.parse(JSON.stringify(original.body)), original.key);
        if (prepared?.attempt && prepared.generation === original.context.generation) {
          const bound = { ...original, attempt: prepared.attempt }; saveGoalIntent(bound);
          if (current(captured, owner)) setIntent(bound);
        }
      } else await sendApi(original, captured, owner);
    } catch (error) {
      // A rejected reconciliation request says nothing about the first request's
      // acceptance. Keep its exact body/key pending until the original ACK is read.
      if (!recover && original && original.context.kind === 'api' && error instanceof RequestFailure && error.submissionDisposition !== 'unknown') {
        try {
          const rejected: GoalIntent = { ...original, disposition: 'rejected' }; saveGoalIntent(rejected);
          if (current(captured, owner)) setIntent(rejected);
        } catch (storageError) { if (current(captured, owner)) setFailure(storageError); }
      }
      if (current(captured, owner)) setFailure(error);
    } finally { locked.current = false; if (latest.current.mounted) setBusy(false); }
  };
  const pending = intent?.disposition === 'pending';
  const nativeReady = view?.phase === 'idle' && !view.attempt;
  const nativeAssociated = intent?.context.kind === 'native' && view?.request_identity
    && intent.context.generation === view.request_identity.original_generation
    && intent.key === view.request_identity.idempotency_key
    && sameGoalProposal(intent.body, view.request_identity.goal) && intent.attempt === view.attempt;
  return <section className="native-setup-panel" aria-label="提交创作目标" aria-busy={busy || setup.busy}>
    {setup.connected ? <p role="status" aria-live="polite">{setup.failed ? '暂时无法读取确认进度，原请求仍保留。' : view?.message ?? '正在读取本机准备状态。'}</p> : null}
    {failure ? <Callout.Root color="red" role="alert"><Callout.Text>{errorMessage(failure)}</Callout.Text></Callout.Root> : null}
    {pending || setup.uncertain ? <p className="small-note">原目标已经固定，结果尚待核实。修改表单不会改变原请求，也不会自动创建第二份任务。</p> : null}
    {intent?.receipt ? <p role="status">创作目标已受理，实际视频尚待制作与校验。</p> : null}
    <Flex gap="3" wrap="wrap">
      <Button size="3" disabled={!context || busy || setup.busy || setup.uncertain || pending || !form.goal.trim() || (setup.connected && !nativeReady)} onClick={() => void submit()}><Sparkles size={17} />开始创作</Button>
      {pending && context?.kind === 'api' ? <Button variant="soft" disabled={busy} onClick={() => void submit(true)}>核实原任务</Button> : null}
      {view?.phase === 'review' && view.can_present && view.current_document && nativeAssociated ? <Button disabled={setup.busy || setup.uncertain || setup.failed} onClick={() => void setup.present()}>确认并继续</Button> : null}
      {view?.attempt && ['preparing', 'review'].includes(view.phase) ? <Button variant="ghost" color="gray" disabled={setup.busy || setup.uncertain || setup.failed} onClick={() => void setup.abort()}>暂不开始</Button> : null}
      {intent?.receipt && (!heldScope || heldScope !== scope) ? <Button variant="soft" onClick={() => { if (intent.receipt) onAccepted(intent.receipt); }}>查看原任务</Button> : null}
    </Flex>
    {!context && !setup.connected ? <p className="small-note">应用连接尚未提供当前实例的提交身份。输入仍保留，尚未提交。</p> : null}
    <p className="small-note">本地工具免注册。资料、目标和作品由当前安装实例持有。</p>
  </section>;
}
