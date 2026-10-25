import { useCallback, useEffect, useRef, useState } from 'react';
import { Badge, Button, Callout, Flex } from '@radix-ui/themes';
import { ArrowRight, Check, Clock, Info, RefreshCw, ShieldCheck, X } from 'lucide-react';
import {
  asAuthorizationFailure, AuthorizationFailure, authorizationFailureMessage, authorizationSessionSecretAvailable,
  clearAuthorizationSessionSecret, decideAuthorization, describeAuthorizationKind,
  describeAuthorizationScope, formatAuthorizationRemaining, formatMicroseconds,
  isAuthorizationAbort, isAuthorizationExpired, readPendingAuthorization, serializeAuthorizationScope,
} from './productAuthorization';
import type { AuthorizationChannel, ProductAuthorizationView } from './productAuthorization';

/**
 * ADR0081 phase machine, mirroring `native-setup-ui-v1`:
 * unavailable | idle | review | confirming | applying | completed | aborted | blocked.
 * No phase grants authority by itself; only the engine's decision response does.
 */
type Phase = 'unavailable' | 'idle' | 'review' | 'confirming' | 'applying' | 'completed' | 'aborted' | 'blocked';

type Props = {
  readonly channel: AuthorizationChannel | undefined;
  readonly reachable: boolean;
  readonly instanceId?: string;
  readonly onRecheck: () => void;
};

const TERMINAL_FAILURES = new Set([
  'authorization_not_found', 'authorization_expired', 'authorization_already_decided',
  'authorization_conflict', 'authorization_instance_conflict', 'authorization_nonce_denied',
  'authorization_session_denied', 'authorization_session_unavailable', 'origin_denied', 'unauthorized',
  'authorization_nonce_missing', 'authorization_response_invalid',
]);

const delay = (milliseconds: number) => new Promise<void>(resolve => { window.setTimeout(resolve, milliseconds); });

function GateHeading({ icon, kicker, title, headingRef, tone = '' }: {
  icon: React.ReactNode;
  kicker: string;
  title: string;
  headingRef: React.RefObject<HTMLHeadingElement | null>;
  tone?: string;
}) {
  return <div className="authorization-heading">
    <span className={`authorization-mark ${tone}`} aria-hidden="true">{icon}</span>
    <div>
      <span className="section-kicker">{kicker}</span>
      <h1 id="authorization-title" ref={headingRef} tabIndex={-1}>{title}</h1>
    </div>
  </div>;
}

function ScopeFacts({ view, now }: { view: ProductAuthorizationView; now: number }) {
  const ownerSubject = typeof view.scope.owner_subject === 'string' && view.scope.owner_subject.trim()
    ? view.scope.owner_subject.trim() : undefined;
  const expired = isAuthorizationExpired(view, now);
  const scopeRows = describeAuthorizationScope(view.scope)
    .filter(row => !['授权对象', '创建时间', '范围说明'].includes(row.label));
  return <dl className="authorization-facts">
    <div><dt>给谁</dt><dd>本机 Owner{ownerSubject ? `（${ownerSubject}）` : ''}<span className="authorization-hint">只对这个安装实例生效</span></dd></div>
    <div><dt>能做什么</dt><dd>{describeAuthorizationKind(view.kind)}</dd></div>
    <div>
      <dt>本次确认</dt>
      <dd>
        {formatMicroseconds(view.expires_at_us)}
        <span className={`authorization-countdown ${expired ? 'is-expired' : ''}`}>
          <Clock size={13} aria-hidden="true" />
          {expired ? '已过期' : `剩余 ${formatAuthorizationRemaining(view.expires_at_us, now)}`}
        </span>
        <span className="authorization-hint">这次确认的短窗口，过期后需重新发起</span>
      </dd>
    </div>
    {scopeRows.map((row, index) => <div key={`${row.label}-${index}`}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}
    <div><dt>一次性</dt><dd>只提交一次。确认后用过的凭据立即失效，重放不会被接受。</dd></div>
    <div>
      <dt>范围指纹</dt>
      <dd><code>{view.scope_sha256.slice(0, 16)}…</code><span className="authorization-hint">这份摘要绑定你看到的上方范围</span></dd>
    </div>
  </dl>;
}

function RawScope({ view }: { view: ProductAuthorizationView }) {
  return <details className="authorization-raw">
    <summary>查看原始授权范围<ArrowRight size={13} aria-hidden="true" /></summary>
    <pre>{serializeAuthorizationScope(view.scope)}</pre>
    <p>范围由实例生成，只描述这次授权；不包含凭据或文件路径。</p>
  </details>;
}

function BlockedReasons({ reasons, failure }: { reasons: readonly string[]; failure: AuthorizationFailure | null }) {
  if (!failure && reasons.length === 0) return null;
  return <>
    {failure ? <Callout.Root color="amber" role="alert" className="authorization-callout">
      <Callout.Icon><Info size={16} /></Callout.Icon>
      <Callout.Text>{authorizationFailureMessage(failure)}</Callout.Text>
    </Callout.Root> : null}
    {reasons.length > 0 ? <div className="authorization-note" role="note">
      <Info size={16} aria-hidden="true" />
      <ul className="authorization-reasons">{reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
    </div> : null}
  </>;
}

/** First health probe, before the channel is known. */
export function AuthorizationBooting() {
  return <section className="authorization-card is-booting" role="status" aria-live="polite">
    <span className="authorization-mark" aria-hidden="true"><ShieldCheck size={21} strokeWidth={1.8} /></span>
    <h1>正在检查本机授权…</h1>
    <p className="authorization-lead">工作台先确认这个安装实例是否已完成 Owner 授权，再打开创作界面。</p>
    <div className="authorization-boot-line" />
  </section>;
}

/**
 * The product authorization page. Rendered instead of the five-step workbench
 * while `/health` reports `pending` (a request can be reviewed) or `complete`
 * (authorization written, restart required). It never becomes the normal
 * workbench on its own; only a fresh `/health` with `none` does that.
 */
export function ProductAuthorizationGate({ channel, reachable, instanceId, onRecheck }: Props) {
  const [phase, setPhase] = useState<Phase>(channel === 'complete' ? 'completed' : 'idle');
  const [view, setView] = useState<ProductAuthorizationView | null>(null);
  const [failure, setFailure] = useState<AuthorizationFailure | null>(null);
  const [decision, setDecision] = useState<'approve' | 'deny' | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [secretReady, setSecretReady] = useState(() => authorizationSessionSecretAvailable());
  const [busy, setBusy] = useState(false);
  const mounted = useRef(true);
  const deciding = useRef(false);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const reload = useCallback(() => {
    setReloadToken(value => value + 1);
    onRecheck();
  }, [onRecheck]);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  // Read the single pending request. A restricted engine may still be creating
  // it right after health reports `pending`, so a 404 is retried briefly before
  // it is treated as a dead end.
  useEffect(() => {
    if (channel === 'complete') { setPhase('completed'); return; }
    if (channel !== 'pending' || !reachable) { setPhase('unavailable'); return; }
    let cancelled = false;
    const controller = new AbortController();
    setPhase('idle'); setFailure(null); setDecision(null); setBusy(false); deciding.current = false;
    const adopt = (next: ProductAuthorizationView) => {
      if (cancelled || !mounted.current) return;
      setView(next); setNow(Date.now());
      if (next.state === 'pending') {
        // The review card stays visible even when this session cannot decide:
        // disabled actions plus an explicit reason are the honest state.
        setPhase('review'); return;
      }
      if (next.state === 'denied') { setDecision('deny'); setPhase('aborted'); return; }
      if (next.state === 'expired' || next.state === 'superseded') {
        setFailure(new AuthorizationFailure(409, next.state === 'expired' ? 'authorization_expired' : 'authorization_conflict'));
        setPhase('blocked'); return;
      }
      // approved | applied | complete: the binding/audit step already ran.
      setDecision('approve'); setPhase('completed');
    };
    const load = async () => {
      try {
        for (let attempt = 0; attempt < 3; attempt += 1) {
          const next = await readPendingAuthorization(controller.signal);
          if (cancelled || !mounted.current) return;
          if (next) { adopt(next); return; }
          if (attempt < 2) await delay(700);
          if (cancelled) return;
        }
        setFailure(new AuthorizationFailure(404, 'authorization_not_found'));
        setPhase('blocked');
      } catch (error) {
        if (cancelled || !mounted.current) return;
        if (isAuthorizationAbort(error)) return;
        setFailure(asAuthorizationFailure(error));
        setPhase('blocked');
      }
    };
    void load();
    return () => { cancelled = true; controller.abort(); };
  }, [channel, reachable, reloadToken]);

  // Countdown while a decision is still possible. The server remains the
  // authority; this only stops the buttons from inviting a doomed submit.
  useEffect(() => {
    if (phase !== 'review') return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, [phase]);

  // Move keyboard/screen-reader focus to the new state, not a vanished button.
  useEffect(() => { headingRef.current?.focus(); }, [phase, view?.authorization_id]);

  const expired = view ? isAuthorizationExpired(view, now) : false;
  const noncePresent = view !== null && view.nonce !== null;
  const canDecide = phase === 'review' && view !== null && view.can_decide && !expired && noncePresent && secretReady && !busy;

  const reasons: string[] = [];
  if (view && !view.can_decide) reasons.push('这个请求当前不能由此窗口确认：可能已在另一个窗口确认，或授权会话已更换。');
  if (view && !noncePresent) reasons.push('授权通道没有随视图提供一次性确认凭据，当前页面无法安全提交。请更新启动器或引擎；在此之前可继续使用终端兜底。');
  if (!secretReady) reasons.push('当前页面没有拿到启动器注入的授权会话凭据，无法提交确认。请关闭后从启动器重新打开工作台。');
  if (expired) reasons.push('这次请求的有效期已过，按钮已停用；没有写入任何内容。');

  const runDecision = async (choice: 'approve' | 'deny') => {
    if (!view || deciding.current || phase !== 'review' || !view.can_decide || expired || view.nonce === null) return;
    if (!authorizationSessionSecretAvailable()) {
      setSecretReady(false);
      setFailure(new AuthorizationFailure(403, 'authorization_session_missing'));
      return;
    }
    deciding.current = true; setBusy(true); setFailure(null); setPhase('confirming');
    try {
      await delay(0);
      if (!mounted.current) return;
      setPhase('applying');
      const result = await decideAuthorization(view, choice);
      if (!mounted.current) return;
      setView(result); setNow(Date.now()); setDecision(choice);
      // decideAuthorization drops the closure secret once the engine accepted it.
      setSecretReady(authorizationSessionSecretAvailable());
      setPhase(choice === 'deny' ? 'aborted' : 'completed');
      onRecheck();
    } catch (error) {
      if (!mounted.current) return;
      const next = asAuthorizationFailure(error);
      if (next.code === 'authorization_session_denied') clearAuthorizationSessionSecret();
      setSecretReady(authorizationSessionSecretAvailable());
      setFailure(next);
      // Terminal decisions can never be retried against this request; unknown
      // transport failures stay on the review card so the user can recheck
      // first (the decision itself is idempotent per ADR0081 §3).
      setPhase(TERMINAL_FAILURES.has(next.code) ? 'blocked' : 'review');
    } finally {
      deciding.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  const instanceNote = instanceId ? <p className="authorization-footnote">本机实例：<code>{instanceId}</code>。凭据只在当前页面内存中使用，不会写入浏览器存储。</p> : null;
  const rawScope = view ? <RawScope view={view} /> : null;

  if (phase === 'idle') {
    return <section className="authorization-card is-booting" role="status" aria-live="polite" aria-busy="true">
      <span className="authorization-mark" aria-hidden="true"><ShieldCheck size={21} strokeWidth={1.8} /></span>
      <h1>正在读取待授权请求…</h1>
      <p className="authorization-lead">实例已进入受限模式，完成这次 Owner 授权后才能打开完整工作台。</p>
      <div className="authorization-boot-line" />
    </section>;
  }

  if (phase === 'unavailable') {
    return <section className="authorization-card" aria-labelledby="authorization-title">
      <GateHeading icon={<Info size={21} strokeWidth={1.8} />} kicker="本机授权" title="授权通道暂时不可用" headingRef={headingRef} tone="is-neutral" />
      <p className="authorization-lead">工作台还没有连上本机实例的授权通道。没有写入任何内容，已有项目不会因此改变。</p>
      <Callout.Root color="amber" role="alert" className="authorization-callout">
        <Callout.Icon><Info size={16} /></Callout.Icon>
        <Callout.Text>请关闭当前窗口，从启动器重新打开 VideoCreator；如果实例已经停止，先重新启动实例。</Callout.Text>
      </Callout.Root>
      <Flex gap="3" wrap="wrap" className="authorization-actions">
        <Button size="3" onClick={reload}><RefreshCw size={16} />重新检查</Button>
      </Flex>
      {instanceNote}
    </section>;
  }

  if (phase === 'completed') {
    return <section className="authorization-card" aria-labelledby="authorization-title">
      <GateHeading icon={<Check size={22} strokeWidth={2} />} kicker="授权已写入" title="授权已完成，请重启应用" headingRef={headingRef} tone="is-complete" />
      <p className="authorization-lead">本机 Owner 授权已经写入并由实例记录。当前进程仍处于受限模式，重启后才能进入完整工作台。</p>
      <ol className="authorization-steps">
        <li>关闭当前工作台窗口。</li>
        <li>重新打开 VideoCreator。开发环境下重新运行启动器（<code>pnpm dev:runtime --data-dir &lt;实例目录&gt;</code>）。</li>
        <li>重启后实例自动完成初始化，这次授权不会再次询问。</li>
      </ol>
      <Callout.Root color="teal" role="status" className="authorization-callout">
        <Callout.Icon><Info size={16} /></Callout.Icon>
        <Callout.Text>如果启动器支持自动重启，这一页会自行关闭并回到工作台。</Callout.Text>
      </Callout.Root>
      <Flex gap="3" wrap="wrap" className="authorization-actions">
        <Button size="3" onClick={reload}><RefreshCw size={16} />重新检查状态</Button>
      </Flex>
      <p className="authorization-status" role="status" aria-live="polite">正在等待应用重启…</p>
      {instanceNote}
    </section>;
  }

  if (phase === 'aborted') {
    return <section className="authorization-card" aria-labelledby="authorization-title">
      <GateHeading icon={<X size={22} strokeWidth={2} />} kicker="已拒绝" title="没有写入任何授权" headingRef={headingRef} tone="is-neutral" />
      <p className="authorization-lead">你拒绝了这次授权。实例没有写入 Owner 授权，已有项目、素材和设置都不受影响。</p>
      <ol className="authorization-steps">
        <li>Owner 初始化尚未完成，工作台会保持受限模式。</li>
        <li>可以关闭工作台；下次从启动器打开时可以重新决定。</li>
        <li>如果实例随后生成了新的待授权请求，需要重新从启动器打开工作台才能确认（本页的授权凭据已按一次性原则丢弃）。</li>
      </ol>
      <Flex gap="3" wrap="wrap" className="authorization-actions">
        <Button size="3" onClick={reload}><RefreshCw size={16} />重新检查状态</Button>
      </Flex>
      {instanceNote}
    </section>;
  }

  if (phase === 'blocked') {
    return <section className="authorization-card" aria-labelledby="authorization-title">
      <GateHeading icon={<Info size={21} strokeWidth={1.8} />} kicker="本机授权" title="现在无法确认这次授权" headingRef={headingRef} tone="is-neutral" />
      <p className="authorization-lead">这次授权不能在此页面完成。为避免误批，没有提交任何决定，也没有写入 Owner 授权。</p>
      <BlockedReasons reasons={reasons} failure={failure} />
      {view ? <ScopeFacts view={view} now={now} /> : null}
      <Flex gap="3" wrap="wrap" className="authorization-actions">
        <Button size="3" onClick={reload}><RefreshCw size={16} />重新检查状态</Button>
      </Flex>
      {failure?.code === 'authorization_nonce_missing' ? <p className="small-note">如果你需要立即完成首次初始化，仍可在终端使用启动器提供的兜底确认方式；本页面不会伪造一次性凭据。</p> : null}
      {view ? rawScope : null}
      {instanceNote}
    </section>;
  }

  return <section className="authorization-card" aria-labelledby="authorization-title" aria-busy={busy || phase === 'confirming' || phase === 'applying'}>
    <div className="authorization-topline">
      <GateHeading icon={<ShieldCheck size={22} strokeWidth={1.8} />} kicker="本机授权" title="需要你的授权" headingRef={headingRef} />
      <Badge color="amber" variant="soft">待授权</Badge>
    </div>
    <p className="authorization-lead">这是首次打开工作台的前置授权。它只初始化本机 Owner，不会开始制作、不会产生费用，也不会扩大任何权限。</p>
    {view ? <ScopeFacts view={view} now={now} /> : null}
    <div className="authorization-commitment">
      <ShieldCheck size={18} strokeWidth={1.8} aria-hidden="true" />
      <div>
        <strong>不接受就不会写入</strong>
        <p>选择“拒绝”不会写入 Owner 授权，也不会修改已有项目。授权凭据只在当前页面内存中使用，不会保存到浏览器。</p>
      </div>
    </div>
    <BlockedReasons reasons={reasons} failure={failure} />
    <Flex gap="3" wrap="wrap" className="authorization-actions">
      <Button size="3" onClick={() => void runDecision('approve')} disabled={!canDecide}><Check size={17} />同意并继续</Button>
      <Button size="3" variant="soft" color="gray" onClick={() => void runDecision('deny')} disabled={!canDecide}><X size={17} />拒绝</Button>
      <Button size="2" variant="ghost" color="gray" onClick={reload} disabled={busy}><RefreshCw size={15} />重新检查</Button>
    </Flex>
    <p className="authorization-status" role="status" aria-live="polite">{busy || phase === 'confirming' || phase === 'applying' ? '正在提交你的选择，请稍候…' : ''}</p>
    {view ? rawScope : null}
    {instanceNote}
  </section>;
}
