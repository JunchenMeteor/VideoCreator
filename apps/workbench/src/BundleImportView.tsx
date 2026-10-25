import { useEffect, useRef, useState } from 'react';
import { Button, Callout, TextField } from '@radix-ui/themes';
import { engineData, errorMessage, RequestFailure } from './engine';
import type { Schemas } from './engine';
import { DeliveryView } from './DeliveryView';
import { clearSubmissionIntent, makeSubmissionIntent, readSubmissionIntent, saveSubmissionIntent, validReceiptId, verifySubmissionIntent } from './submissionIntents';
import type { SubmissionIntent } from './submissionIntents';

function readOrigin(value: unknown): Schemas['BundleRef'] {
  const candidate = value && typeof value === 'object' && 'bundle_ref' in value ? value.bundle_ref : value;
  if (!candidate || typeof candidate !== 'object') throw new RequestFailure(422, 'invalid_request');
  const id = (key: string) => { const field = Reflect.get(candidate, key); if (typeof field !== 'string' || !/^[A-Za-z0-9_.:-]{1,128}$/.test(field)) throw new RequestFailure(422, 'invalid_request'); return field; };
  const hash = Reflect.get(candidate, 'manifest_sha256');
  if (typeof hash !== 'string' || !/^[a-f0-9]{64}$/.test(hash)) throw new RequestFailure(422, 'invalid_request');
  const schemaVersion = id('schema_version');
  if (schemaVersion !== '0.2.0-candidate' && schemaVersion !== '0.3.0-candidate') throw new RequestFailure(415, 'unsupported_bundle_version');
  return { instance_id: id('instance_id'), bundle_id: id('bundle_id'), bundle_revision_id: id('bundle_revision_id'), manifest_sha256: hash, schema_version: schemaVersion };
}

export function BundleImportView({ instanceId, projectId, connected }: { instanceId?: string; projectId?: string; connected: boolean }) {
  const [archive, setArchive] = useState<File | null>(null);
  const [origin, setOrigin] = useState<Schemas['BundleRef'] | null>(null);
  const [receipt, setReceipt] = useState<Schemas['BundleImportReceipt'] | null>(null);
  const [id, setId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const pending = useRef<SubmissionIntent<'bundle-import'> | null>(null);
  const [unresolved, setUnresolved] = useState(false);
  const [recoveryBlocked, setRecoveryBlocked] = useState(false);
  const submitting = useRef(false);
  const mounted = useRef(true);
  const currentInstance = useRef(instanceId); currentInstance.current = instanceId;
  const stage = useRef<Schemas['StagedAsset'] | null>(null);
  const archiveInput = useRef<HTMLInputElement | null>(null);
  const originInput = useRef<HTMLInputElement | null>(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!instanceId) return;
    try {
      const intent = readSubmissionIntent('bundle-import', instanceId);
      pending.current = intent; setUnresolved(Boolean(intent && !intent.receiptId)); setRecoveryBlocked(false);
      setArchive(null); stage.current = null;
      setOrigin(intent && !intent.receiptId ? intent.body.expected_origin_ref : null);
      if (intent?.receiptId) setId(intent.receiptId);
      setReceipt(null);
    } catch (failure) { setRecoveryBlocked(true); setError(failure); }
  }, [instanceId]);
  const canReplace = () => {
    if (submitting.current || recoveryBlocked) return false;
    try {
      const intent = instanceId ? readSubmissionIntent('bundle-import', instanceId) : pending.current;
      if (intent && !intent.receiptId) { pending.current = intent; setUnresolved(true); return false; }
      return true;
    } catch (failure) { setRecoveryBlocked(true); setError(failure); return false; }
  };
  const openReceipt = async () => {
    setBusy(true); setError(null); setReceipt(null);
    try {
      const saved = await engineData('GET /api/v1/bundle-imports/{import_id}', { path: { import_id: id } });
      if (saved.local_instance_id !== instanceId || saved.import_id !== id) throw new RequestFailure(409, 'bundle_version_mismatch');
      // An arbitrary matching project/origin is not proof about the pending key.
      // Reading another receipt must never release an unknown import intent.
      setReceipt(saved);
    } catch (failure) { setError(failure); } finally { setBusy(false); }
  };
  const chooseOrigin = async (file: File | undefined) => {
    if (!file || !canReplace()) return; setError(null); setOrigin(null);
    try {
      if (file.size > 64 * 1024) throw new RequestFailure(413, 'invalid_request');
      const parsed = readOrigin(JSON.parse(await file.text()));
      if (mounted.current && canReplace()) setOrigin(parsed);
    } catch (failure) { setError(failure instanceof RequestFailure && failure.status === 415 ? failure : new RequestFailure(422, 'invalid_reference_descriptor')); }
  };
  const importArchive = async () => {
    if (submitting.current || !instanceId || !connected || recoveryBlocked) return;
    submitting.current = true;
    const submissionInstance = instanceId;
    let submitted = false;
    let wasUnknown = false;
    let submissionKey = '';
    setBusy(true); setError(null);
    try {
      const retained = readSubmissionIntent('bundle-import', submissionInstance);
      let intent = retained && !retained.receiptId ? retained : null;
      wasUnknown = Boolean(intent);
      if (!intent) {
        if (!archive || !origin || !projectId) return;
        const sourceOrigin = origin; const sourceProject = projectId;
        // The installation's generated raw-upload contract enforces its own cap.
        // Browser preview limits do not decide whether a ZIP can be imported.
        stage.current ??= await engineData('POST /api/v1/assets/staging', { headers: { 'Content-Type': 'application/zip' }, body: archive });
        // Leaving before the import POST does not submit a new import later.
        if (!mounted.current) return;
        if (currentInstance.current !== submissionInstance) throw new RequestFailure(409, 'submission_identity_mismatch');
        const body: Schemas['BundleImportRequest'] = { staging_id: stage.current.staging_id, archive_sha256: stage.current.sha256, expected_origin_ref: sourceOrigin, project_id: sourceProject };
        intent = await makeSubmissionIntent('bundle-import', submissionInstance, body);
        if (!mounted.current) return;
        const other = readSubmissionIntent('bundle-import', submissionInstance);
        if (other && !other.receiptId) { pending.current = other; setUnresolved(true); return; }
        saveSubmissionIntent('bundle-import', intent);
      }
      pending.current = intent; setUnresolved(true);
      if (wasUnknown) await verifySubmissionIntent('bundle-import', intent, submissionInstance);
      if (!mounted.current) return;
      if (currentInstance.current !== submissionInstance) throw new RequestFailure(409, 'submission_identity_mismatch');
      submitted = true;
      submissionKey = intent.idempotencyKey;
      const saved = await engineData('POST /api/v1/bundle-imports', { body: intent.body, headers: { 'Idempotency-Key': intent.idempotencyKey } });
      const expected = intent.body.expected_origin_ref;
      if (!saved || saved.local_instance_id !== submissionInstance || saved.project_id !== intent.body.project_id
        || !validReceiptId(saved.import_id) || saved.status !== 'ready' || !saved.origin_bundle_ref
        || (Object.keys(expected) as Array<keyof typeof expected>).some(key => saved.origin_bundle_ref[key] !== expected[key])
        || typeof saved.status_path !== 'string' || !saved.status_path || typeof saved.manifest_path !== 'string' || !saved.manifest_path
        || !['not_built', 'ready', 'failed'].includes(saved.index_state)) throw new RequestFailure(502, 'response_unavailable');
      const received = { ...intent, receiptId: saved.import_id };
      saveSubmissionIntent('bundle-import', received); pending.current = received;
      submitted = false;
      if (mounted.current && currentInstance.current === submissionInstance) {
        setReceipt(saved); setId(saved.import_id); setUnresolved(false); stage.current = null; setArchive(null); setOrigin(null);
      }
    } catch (failure) {
      // A rejection of a replay does not prove the earlier unknown POST failed.
      if (submitted && !wasUnknown && failure instanceof RequestFailure && failure.submissionDisposition !== 'unknown') {
        try { clearSubmissionIntent('bundle-import', submissionInstance, submissionKey); pending.current = null; if (mounted.current && currentInstance.current === submissionInstance) setUnresolved(false); }
        catch (storageFailure) { setRecoveryBlocked(true); setError(storageFailure); return; }
      }
      if (mounted.current) setError(failure);
    } finally { submitting.current = false; if (mounted.current) setBusy(false); }
  };
  return <div className="bundle-import-view"><details className="advanced-settings"><summary>导入作品包或打开导入记录</summary><div>
    <p>ZIP与来源版本描述一起导入。来源编号不会被改成本地编号，引用描述也不授予实例访问权限。</p>
    <div className="import-fields"><span className="field-label">作品ZIP</span><div className="bundle-file-choice"><Button size="2" variant="soft" disabled={busy || unresolved || recoveryBlocked} onClick={() => archiveInput.current?.click()}>选择ZIP文件</Button><span>{archive?.name ?? (unresolved ? '原暂存与请求已保留' : '尚未选择')}</span></div><input ref={archiveInput} className="visually-hidden" id="bundle-archive" aria-label="选择作品ZIP" type="file" accept=".zip,application/zip" disabled={busy || unresolved || recoveryBlocked} onChange={event => { if (!canReplace()) return; setArchive(event.target.files?.[0] ?? null); stage.current = null; setError(null); }} /><span className="field-label">来源版本描述</span><Button size="2" variant="soft" disabled={busy || unresolved || recoveryBlocked} onClick={() => originInput.current?.click()}>选择来源描述JSON</Button><input ref={originInput} className="visually-hidden" id="bundle-origin" aria-label="选择来源版本描述" type="file" accept=".json,application/json" disabled={busy || unresolved || recoveryBlocked} onChange={event => void chooseOrigin(event.target.files?.[0])} />{origin ? <p className="small-note">来源版本 {origin.bundle_revision_id}</p> : null}</div>
    <Button disabled={!connected || busy || recoveryBlocked || (!unresolved && (!projectId || !archive || !origin))} onClick={() => void importArchive()}>{busy ? '正在校验导入' : unresolved ? '重试原项目的同一导入' : '导入到当前项目'}</Button>{!projectId && !unresolved ? <p className="small-note">先保存一个项目，作为本地导入的位置。</p> : null}
    {unresolved ? <Callout.Root color="amber" role="status"><Callout.Text>原导入结果待核实。请求与发起项目已保留，切换页面或重开不会新建导入；重试只使用原暂存和原输入。</Callout.Text></Callout.Root> : null}
    <label className="field-label" htmlFor="bundle-import-id">已有导入编号</label><div className="asset-lookup"><TextField.Root id="bundle-import-id" value={id} disabled={busy} onChange={event => setId(event.target.value)} /><Button size="2" variant="soft" disabled={!connected || busy || !/^[A-Za-z0-9_.:-]{1,128}$/.test(id)} onClick={() => void openReceipt()}>读取导入记录</Button></div>
    {error ? <Callout.Root color="red" role="alert"><Callout.Text>{errorMessage(error)}</Callout.Text></Callout.Root> : null}
    {error && !busy && !unresolved && !recoveryBlocked ? <Button variant="ghost" size="1" color="gray" onClick={() => { if (!canReplace()) return; stage.current = null; setArchive(null); setOrigin(null); setError(null); if (archiveInput.current) archiveInput.current.value = ''; if (originInput.current) originInput.current.value = ''; }}>重新选择文件</Button> : null}
  </div></details>{receipt ? <DeliveryView key={receipt.import_id} importReceipt={receipt} connected={connected} onAssets={() => setReceipt(null)} /> : null}</div>;
}
