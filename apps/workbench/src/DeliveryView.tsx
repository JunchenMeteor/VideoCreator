import { useEffect, useRef, useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { Badge, Button, Callout, Checkbox, Dialog, Flex, Select, Tabs, TextField } from '@radix-ui/themes';
import { Download, Film, Link, RefreshCw, ShieldCheck } from 'lucide-react';
import { ARCHIVE_BUFFER_BYTES, engineData, engineRequest, engineContent, errorMessage, inputHash, PREVIEW_BUFFER_BYTES, rememberLocator, RequestFailure, storedLocator, verifiedContentBlob, verifyContentMetadata } from './engine';
import type { Schemas } from './engine';
import { benchmarkBindingLabel, formatBytes, selfIssuedNote, shortSha } from './productFlow';

type BundleRef = Schemas['BundleRef'];
type Artifact = Schemas['BundleArtifact'];
type OutputRole = Schemas['BundleOutput']['role'];
type LoadedArtifact = { artifact: Artifact; url: string; text?: string; expiresAtUs: number | null };
const OUTPUT_LABEL: Record<OutputRole, string> = { video: '视频', narration_audio: '旁白', mixed_audio: '完整混音', approved_script: '批准原稿', actual_transcript: '实际转写', subtitles: '字幕', semantic_manifest: '语义索引', rag_chunks: '检索文本' };
const EXPORT_STATUS: Record<Schemas['BundleExportAccepted']['status'], string> = { queued: '导出已排队', building: '正在打包', ready: '导出包已就绪', failed: '导出遇到问题' };
const sameRef = (a: BundleRef, b: BundleRef) => a.instance_id === b.instance_id && a.bundle_id === b.bundle_id && a.bundle_revision_id === b.bundle_revision_id && a.manifest_sha256 === b.manifest_sha256 && (a.schema_version ?? '0.2.0-candidate') === (b.schema_version ?? '0.2.0-candidate');
const timestamp = (us: number) => `${Math.floor(us / 60_000_000)}:${String(Math.floor(us / 1_000_000) % 60).padStart(2, '0')}`;

function BlobDownload({ blob, filename, children }: { blob: Blob; filename: string; children: React.ReactNode }) {
  const [url, setUrl] = useState('');
  useEffect(() => { const next = URL.createObjectURL(blob); setUrl(next); return () => URL.revokeObjectURL(next); }, [blob]);
  return url ? <a className="bundle-download" href={url} download={filename}><Download size={15} />{children}</a> : null;
}

export function DeliveryView({ bundleRef: publishedRef, importReceipt, connected, status, onAssets }: { bundleRef?: BundleRef | null; importReceipt?: Schemas['BundleImportReceipt']; connected: boolean; status?: Schemas['RunStatus']; onAssets: () => void }) {
  const bundleRef = importReceipt?.origin_bundle_ref ?? publishedRef;
  const revision = bundleRef?.bundle_revision_id;
  const identity = bundleRef ? `${importReceipt?.local_instance_id ?? bundleRef.instance_id}:${importReceipt?.import_id ?? ''}:${revision}:${bundleRef.manifest_sha256}` : 'empty';
  const [tab, setTab] = useState('video');
  const [selectedRole, setSelectedRole] = useState<OutputRole>('video');
  const [loaded, setLoaded] = useState<LoadedArtifact | null>(null);
  const [subtitles, setSubtitles] = useState<LoadedArtifact | null>(null);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [grantOpen, setGrantOpen] = useState(false);
  const [profile, setProfile] = useState<'full' | 'projection'>('full');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [exportId, setExportId] = useState<string | null>(null);
  const [archive, setArchive] = useState<Blob | null>(null);
  const [archiveExpiry, setArchiveExpiry] = useState<number | null>(null);
  const [grant, setGrant] = useState<Schemas['BundleReferenceGrant'] | null>(null);
  const [recipient, setRecipient] = useState('');
  const [semanticAllowed, setSemanticAllowed] = useState(true);
  const [expires, setExpires] = useState('');
  const loading = useRef<AbortController | null>(null);
  const video = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    loading.current?.abort(); setLoaded(null); setSubtitles(null); setError(null); setArchive(null); setGrant(null);
    setSelectedIds([]); setSelectedRole('video'); setTab('video');
    setExportId(bundleRef ? storedLocator(`video-creator:export:${identity}`) : null);
    return () => loading.current?.abort();
  }, [identity]);
  useEffect(() => () => { if (loaded) URL.revokeObjectURL(loaded.url); }, [loaded]);
  useEffect(() => () => { if (subtitles) URL.revokeObjectURL(subtitles.url); }, [subtitles]);
  const clearContent = () => { loading.current?.abort(); setLoaded(null); setSubtitles(null); setArchive(null); setBusy(false); };
  useEffect(() => { if (!connected) clearContent(); }, [connected]);
  useEffect(() => {
    const expiries = [loaded?.expiresAtUs, subtitles?.expiresAtUs, archive ? archiveExpiry : null].filter((value): value is number => typeof value === 'number');
    if (!expiries.length) return;
    const delay = Math.max(0, Math.min(2_147_483_647, Math.min(...expiries) / 1000 - Date.now()));
    const timer = window.setTimeout(() => { clearContent(); setError(new RequestFailure(403, 'authorization_expired')); }, delay);
    return () => window.clearTimeout(timer);
  }, [loaded, subtitles, archive, archiveExpiry]);

  const manifest = useQuery({ queryKey: ['bundle-manifest', identity], enabled: connected && Boolean(revision), queryFn: async () => {
    if (!bundleRef) throw new RequestFailure(409, 'bundle_version_mismatch');
    const metadata = importReceipt
      ? await engineData('GET /api/v1/bundle-imports/{import_id}/manifest/metadata', { path: { import_id: importReceipt.import_id } })
      : await engineData('GET /api/v1/bundles/{revision_id}/manifest/metadata', { path: { revision_id: revision! } });
    verifyContentMetadata(metadata, { instanceId: importReceipt?.local_instance_id ?? bundleRef.instance_id, size: metadata.size, sha256: bundleRef.manifest_sha256, media_type: 'application/json' });
    const locator = metadata.locator;
    if (importReceipt ? locator.kind !== 'import_manifest' || locator.import_id !== importReceipt.import_id || !sameRef(locator.origin_bundle_ref, bundleRef)
      : locator.kind !== 'bundle_manifest' || !sameRef(locator.bundle_ref, bundleRef)) throw new RequestFailure(409, 'content_metadata_mismatch');
    const response = importReceipt ? await engineContent('GET /api/v1/bundle-imports/{import_id}/manifest', { path: { import_id: importReceipt.import_id } }) : await engineContent('GET /api/v1/bundles/{revision_id}/manifest', { path: { revision_id: revision! } });
    const blob = await verifiedContentBlob(response, metadata);
    const value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(await blob.arrayBuffer())) as Schemas['BundleManifest'] | Schemas['BundleManifestV03'];
    if (!value || value.instance_id !== bundleRef.instance_id || value.bundle_id !== bundleRef.bundle_id || value.bundle_revision_id !== revision || value.schema_version !== (bundleRef.schema_version ?? '0.2.0-candidate') || !Array.isArray(value.artifacts) || !Array.isArray(value.outputs) || !Array.isArray(value.requested_outputs)) throw new RequestFailure(409, 'bundle_version_mismatch');
    return value;
  } });
  const semantics = useInfiniteQuery({ queryKey: ['bundle-semantics', identity], enabled: connected && Boolean(manifest.data) && !importReceipt, initialPageParam: undefined as string | undefined, queryFn: async ({ pageParam }) => {
    const response = await engineRequest('GET /api/v1/bundles/{revision_id}/semantic-segments', { path: { revision_id: revision! }, query: { cursor: pageParam, limit: 50 } });
    if (!response.data || !bundleRef || !sameRef(response.data.bundle_ref, bundleRef)) throw new RequestFailure(409, 'bundle_version_mismatch');
    return response.data;
  }, getNextPageParam: page => page.next_cursor ?? undefined });
  const exportJob = useQuery({ queryKey: ['bundle-export', identity, exportId], enabled: connected && Boolean(exportId), queryFn: async () => {
    const response = await engineRequest('GET /api/v1/bundle-exports/{export_id}', { path: { export_id: exportId! } });
    if (!response.data || !bundleRef || !sameRef(response.data.bundle_ref, bundleRef)) throw new RequestFailure(409, 'bundle_version_mismatch');
    return response.data;
  }, refetchInterval: query => ['queued', 'building'].includes(query.state.data?.status ?? '') ? 2500 : false });
  useEffect(() => { if (manifest.error || exportJob.error || semantics.error) clearContent(); }, [manifest.error, exportJob.error, semantics.error]);
  const outputs = manifest.data?.outputs ?? [];
  const artifacts = manifest.data?.artifacts ?? [];
  const outputArtifacts = (role: OutputRole) => artifacts.filter(item => outputs.find(output => output.role === role)?.artifact_ids.includes(item.artifact_id));
  const segments = semantics.data?.pages.flatMap(page => page.segments) ?? [];
  const complete = manifest.data?.requested_outputs.every(role => outputArtifacts(role).length > 0);
  const benchmarkBinding = manifest.data && 'benchmark_binding' in manifest.data ? manifest.data.benchmark_binding : undefined;
  const evidenceNote = benchmarkBinding ? selfIssuedNote(benchmarkBinding) : undefined;
  const deliveryFiles = (['video', 'subtitles'] as const).flatMap(role => outputArtifacts(role).map(artifact => ({ role, artifact })));

  const readArtifact = async (artifact: Artifact, signal: AbortSignal) => {
    if (!bundleRef) throw new RequestFailure(409, 'bundle_version_mismatch');
    const metadata = importReceipt
      ? await engineData('GET /api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content/metadata', { path: { import_id: importReceipt.import_id, artifact_id: artifact.artifact_id }, signal })
      : await engineData('GET /api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content/metadata', { path: { revision_id: revision!, artifact_id: artifact.artifact_id }, signal });
    verifyContentMetadata(metadata, { ...artifact, instanceId: importReceipt?.local_instance_id ?? bundleRef.instance_id });
    const locator = metadata.locator;
    if (importReceipt ? locator.kind !== 'import_artifact' || locator.import_id !== importReceipt.import_id || locator.artifact_id !== artifact.artifact_id || !sameRef(locator.origin_bundle_ref, bundleRef)
      : locator.kind !== 'bundle_artifact' || locator.artifact_id !== artifact.artifact_id || !sameRef(locator.bundle_ref, bundleRef)) throw new RequestFailure(409, 'content_metadata_mismatch');
    if (artifact.size > PREVIEW_BUFFER_BYTES) throw new RequestFailure(413, 'preview_size_limit');
    const response = importReceipt ? await engineContent('GET /api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content', { path: { import_id: importReceipt.import_id, artifact_id: artifact.artifact_id }, signal }) : await engineContent('GET /api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content', { path: { revision_id: revision!, artifact_id: artifact.artifact_id }, signal });
    const blob = await verifiedContentBlob(response, artifact);
    const textual = artifact.media_type.startsWith('text/') || artifact.media_type.includes('json') || artifact.roles.some(role => ['approved_script', 'actual_transcript', 'subtitles', 'semantic_manifest', 'rag_chunks'].includes(role));
    return { blob, text: textual ? new TextDecoder('utf-8', { fatal: true }).decode(await blob.arrayBuffer()) : undefined, expiresAtUs: metadata.authorization_expires_at_us };
  };
  const openArtifact = async (artifact: Artifact, role: OutputRole) => {
    loading.current?.abort(); const controller = new AbortController(); loading.current = controller;
    setBusy(true); setError(null); setLoaded(null); setSubtitles(null);
    try {
      const result = await readArtifact(artifact, controller.signal);
      if (controller.signal.aborted) return;
      setLoaded({ artifact, url: URL.createObjectURL(result.blob), text: result.text, expiresAtUs: result.expiresAtUs }); setSelectedRole(role);
      setTab(role === 'video' ? 'video' : role === 'narration_audio' || role === 'mixed_audio' ? 'audio' : 'text');
      setSubtitles(null);
      const caption = role === 'video' ? outputArtifacts('subtitles').find(item => item.media_type === 'text/vtt') : undefined;
      if (caption) {
        const track = await readArtifact(caption, controller.signal);
        if (!controller.signal.aborted) setSubtitles({ artifact: caption, url: URL.createObjectURL(track.blob), expiresAtUs: track.expiresAtUs });
      }
    } catch (failure) { if (!controller.signal.aborted) { setLoaded(null); setSubtitles(null); setError(failure); } }
    finally { if (loading.current === controller) setBusy(false); }
  };
  const downloadArtifact = async (artifact: Artifact) => {
    if (!bundleRef || downloading) return;
    setDownloading(artifact.artifact_id); setError(null);
    try {
      const result = await readArtifact(artifact, new AbortController().signal);
      const url = URL.createObjectURL(result.blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = artifact.relative_path.split('/').pop() || artifact.artifact_id;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (failure) { setError(failure); }
    finally { setDownloading(null); }
  };
  const seekSegment = async (segment: Schemas['SemanticSegmentV1']) => {
    const artifact = outputArtifacts('video').find(item => item.asset_id === segment.video_asset_id);
    if (!artifact) { setError(new RequestFailure(409, 'bundle_version_mismatch')); return; }
    // Seeking is applied after React mounts the actual media, without manufacturing playback progress.
    pendingSeek.current = segment.video_range.start_us / 1_000_000;
    if (loaded?.artifact.artifact_id !== artifact.artifact_id) await openArtifact(artifact, 'video');
    setTab('video');
    if (video.current?.readyState && loaded?.artifact.artifact_id === artifact.artifact_id) { video.current.currentTime = pendingSeek.current; pendingSeek.current = null; }
  };
  const pendingSeek = useRef<number | null>(null);
  const startExport = async () => {
    if (!bundleRef || (profile === 'projection' && !selectedIds.length)) return;
    setBusy(true); setError(null); setArchive(null);
    const body: Schemas['BundleExportRequest'] = { delivery_profile: profile, format: 'zip', artifact_ids: profile === 'projection' ? selectedIds : [], purpose: 'export' };
    try {
      const headers = { 'Idempotency-Key': `workbench-export-${await inputHash([identity, body])}` };
      const response = importReceipt ? await engineRequest('POST /api/v1/bundle-imports/{import_id}/exports', { path: { import_id: importReceipt.import_id }, body, headers }) : await engineRequest('POST /api/v1/bundles/{revision_id}/exports', { path: { revision_id: revision! }, body, headers });
      if (!response.data || !sameRef(response.data.bundle_ref, bundleRef)) throw new RequestFailure(409, 'bundle_version_mismatch');
      setExportId(response.data.export_id); rememberLocator(`video-creator:export:${identity}`, response.data.export_id); setExportOpen(false);
    } catch (failure) { setError(failure); } finally { setBusy(false); }
  };
  const downloadExport = async () => {
    const job = exportJob.data;
    if (!job || job.status !== 'ready' || !job.archive_sha256 || !job.size) return;
    loading.current?.abort(); const controller = new AbortController(); loading.current = controller;
    setBusy(true); setError(null); setArchive(null);
    try {
      const metadata = await engineData('GET /api/v1/bundle-exports/{export_id}/content/metadata', { path: { export_id: job.export_id }, signal: controller.signal });
      verifyContentMetadata(metadata, { instanceId: importReceipt?.local_instance_id ?? bundleRef!.instance_id, size: job.size, sha256: job.archive_sha256, media_type: 'application/zip' });
      const locator = metadata.locator;
      if (locator.kind !== 'export_archive' || locator.export_id !== job.export_id || locator.input_sha256 !== job.input_sha256 || locator.delivery_profile !== job.delivery_profile
        || (importReceipt ? locator.source.kind !== 'local_import' || locator.source.import_id !== importReceipt.import_id || !sameRef(locator.source.origin_bundle_ref, bundleRef!)
          : locator.source.kind !== 'local_bundle' || !sameRef(locator.source.bundle_ref, bundleRef!))) throw new RequestFailure(409, 'content_metadata_mismatch');
      // Large ZIPs require a trusted streaming-to-disk host, which has not yet
      // been provided. This is a browser memory capability, not an export cap.
      if (job.size > ARCHIVE_BUFFER_BYTES) throw new RequestFailure(503, 'streaming_save_unavailable');
      const response = await engineContent('GET /api/v1/bundle-exports/{export_id}/content', { path: { export_id: job.export_id }, signal: controller.signal });
      const blob = await verifiedContentBlob(response, metadata, ARCHIVE_BUFFER_BYTES, 'streaming_save_unavailable');
      if (!controller.signal.aborted) { setArchive(blob); setArchiveExpiry(metadata.authorization_expires_at_us); }
    } catch (failure) { if (!controller.signal.aborted) { setArchive(null); setError(failure); } } finally { if (loading.current === controller) setBusy(false); }
  };
  const createGrant = async () => {
    if (!bundleRef || !recipient.trim() || !expires) return;
    setBusy(true); setError(null);
    const body: Schemas['BundleGrantRequest'] = { recipient_id: recipient.trim(), artifact_ids: artifacts.map(item => item.artifact_id), allow_semantic_text: semanticAllowed, purposes: semanticAllowed ? ['playback', 'rag_index'] : ['playback'], expires_at_us: new Date(expires).getTime() * 1000 };
    try {
      const response = await engineRequest('POST /api/v1/bundles/{revision_id}/grants', { path: { revision_id: revision! }, body, headers: { 'Idempotency-Key': `workbench-grant-${await inputHash([bundleRef, body])}` } });
      if (!response.data || !sameRef(response.data.bundle_ref, bundleRef)) throw new RequestFailure(409, 'bundle_version_mismatch');
      setGrant(response.data); setGrantOpen(false);
    } catch (failure) { setError(failure); } finally { setBusy(false); }
  };
  const revokeGrant = async () => {
    if (!grant) return; setBusy(true); setError(null);
    try {
      const response = await engineRequest('POST /api/v1/bundle-grants/{grant_id}/revoke', { path: { grant_id: grant.grant_id } });
      if (response.data) setGrant(response.data);
    } catch (failure) { setError(failure); } finally { setBusy(false); }
  };

  return <section className="delivery-panel">
    <div className="stage-heading"><h2>{bundleRef ? importReceipt && !complete ? '查看已导入内容' : '查看作品与交付内容' : '等待完整作品'}</h2><p>{bundleRef ? '视频、音轨与文本来自同一个固定版本。' : status === 'waiting_user' ? '先审核方案或检查结果，作品包通过后会出现在这里。' : '制作完成并通过检查后，成片、音轨和文本一起交付。'}</p></div>
    {!bundleRef ? <div className="media-empty"><Film size={34} strokeWidth={1.4} /><h3>还没有完整作品包</h3><Button size="2" variant="soft" onClick={onAssets}>查看已有素材</Button></div> : null}
    {manifest.isPending && connected && bundleRef ? <p role="status">正在读取作品版本…</p> : null}
    {manifest.error ? <Callout.Root color="red" role="alert"><Callout.Text>{errorMessage(manifest.error)}</Callout.Text><Button size="1" variant="soft" onClick={() => void manifest.refetch()}>重读作品</Button></Callout.Root> : null}
    {connected && !manifest.isError && manifest.data ? <>
      <div className="bundle-summary"><Badge color="gray">{importReceipt ? '已导入的固定版本' : '固定版本'}</Badge><span>{timestamp(manifest.data.timeline_duration_us)}</span><details><summary>版本与来源</summary><p>{manifest.data.bundle_revision_id}</p>{importReceipt ? <p>来源实例：{bundleRef?.instance_id}；本地实例：{importReceipt.local_instance_id}；本地导入编号：{importReceipt.import_id}。</p> : null}<p>{manifest.data.source_refs.map(source => `${source.system} · ${source.article_id ?? source.topic_id ?? source.namespace}${source.article_revision ? ` / ${source.article_revision}` : ''}`).join('；') || '来源见作品记录'}</p></details></div>
      <Tabs.Root value={tab} onValueChange={setTab}><Tabs.List aria-label="作品交付"><Tabs.Trigger value="video">视频</Tabs.Trigger><Tabs.Trigger value="audio">音频</Tabs.Trigger><Tabs.Trigger value="text">文本与对应</Tabs.Trigger></Tabs.List>
        <Tabs.Content value="video"><div className="output-options">{outputArtifacts('video').map(item => <Button key={item.artifact_id} size="2" variant="soft" disabled={busy || !connected} onClick={() => void openArtifact(item, 'video')}>播放成片</Button>)}</div>{connected && loaded?.artifact.media_type.startsWith('video/') ? <div className="media-preview"><video ref={video} key={loaded.url} src={loaded.url} controls playsInline preload="metadata" aria-label="固定版本成片预览" onLoadedMetadata={() => { if (video.current && pendingSeek.current !== null) { video.current.currentTime = pendingSeek.current; pendingSeek.current = null; } }} onError={() => { clearContent(); setError(new RequestFailure(422, 'media_invalid')); }}>{subtitles ? <track key={subtitles.url} kind="subtitles" src={subtitles.url} srcLang="zh" label="作品字幕" default /> : null}</video></div> : <div className="media-empty"><Film size={30} /><p>选择成片后读取并校验视频。</p></div>}</Tabs.Content>
        <Tabs.Content value="audio"><div className="output-options">{(['narration_audio', 'mixed_audio'] as const).flatMap(role => outputArtifacts(role).map(item => <Button key={item.artifact_id} size="2" variant="soft" disabled={busy || !connected} onClick={() => void openArtifact(item, role)}>{OUTPUT_LABEL[role]}</Button>))}</div>{connected && loaded?.artifact.media_type.startsWith('audio/') ? <div className="audio-preview"><h3>{OUTPUT_LABEL[selectedRole]}</h3><audio key={loaded.url} src={loaded.url} controls preload="metadata" aria-label="固定版本音轨预览" onError={() => { clearContent(); setError(new RequestFailure(422, 'media_invalid')); }} /></div> : <p className="value-empty">选择旁白或完整混音，独立试听。</p>}</Tabs.Content>
        <Tabs.Content value="text"><div className="output-options">{(['approved_script', 'actual_transcript', 'subtitles', 'rag_chunks'] as const).flatMap(role => outputArtifacts(role).map(item => <Button key={item.artifact_id} size="1" variant="soft" disabled={busy || !connected} onClick={() => void openArtifact(item, role)}>{OUTPUT_LABEL[role]}</Button>))}</div>{connected && loaded?.text !== undefined ? <div><h3>{OUTPUT_LABEL[selectedRole]}</h3><pre className="asset-text-preview">{loaded.text}</pre></div> : <p className="value-empty">批准原稿与实际音频转写分别读取。</p>}<h3>选题与画面的对应</h3>{!importReceipt && semantics.isPending ? <p role="status">正在读取语义段落…</p> : null}{semantics.error ? <Callout.Root color="red"><Callout.Text>{errorMessage(semantics.error)}</Callout.Text><Button size="1" variant="soft" onClick={() => void semantics.refetch()}>重读对应关系</Button></Callout.Root> : null}<div className="semantic-segments">{segments.map(segment => <article key={segment.segment_id}><button type="button" disabled={busy || !connected} onClick={() => void seekSegment(segment)}><span>{timestamp(segment.video_range.start_us)}—{timestamp(segment.video_range.end_us)}</span><strong>{segment.topic || segment.summary}</strong></button><p>{segment.main_thesis}</p><p className="semantic-speech">{segment.speech_text}</p><details><summary>来源与识别依据</summary><p>{segment.visual_description}</p><p>{segment.source_refs.map(source => `${source.system} · ${source.article_id ?? source.topic_id ?? source.namespace} · ${source.article_revision ?? source.topic_revision ?? ''}`).join('；')}</p><p>原始转写单元：{segment.transcript_unit_refs.join('、')}</p></details></article>)}</div>{semantics.hasNextPage ? <Button variant="soft" disabled={semantics.isFetchingNextPage} onClick={() => void semantics.fetchNextPage()}>读取更多对应段落</Button> : null}</Tabs.Content>
      </Tabs.Root>
      {benchmarkBinding ? <Callout.Root color="gray" role="note" className="delivery-evidence">
        <Callout.Icon><ShieldCheck size={16} /></Callout.Icon>
        <Callout.Text>
          <strong>{benchmarkBindingLabel(benchmarkBinding)}</strong>
          {evidenceNote ? <p>{evidenceNote}</p> : null}
          <p>{benchmarkBinding === 'embedded_self_issued' ? '这是本机自签证据，不是第三方认证，也不代表精度已测量。' : '这只说明证据绑定方式，不代表精度已测量。'}</p>
        </Callout.Text>
      </Callout.Root> : null}
      <section className="delivery-files" aria-label="成片与字幕文件">
        <h3>成片与字幕</h3>
        <p>文件来自这个固定版本；大小与 SHA-256 前 12 位取自作品清单原件。</p>
        {deliveryFiles.length ? <div className="delivery-file-list">{deliveryFiles.map(({ role, artifact }) => <div className="delivery-file" key={artifact.artifact_id}>
          <div><strong>{OUTPUT_LABEL[role]}</strong><span>{artifact.relative_path}</span></div>
          <span>{formatBytes(artifact.size)} · SHA {shortSha(artifact.sha256)}</span>
          <Button size="1" variant="soft" disabled={!connected || Boolean(downloading)} onClick={() => void downloadArtifact(artifact)}><Download size={13} />{downloading === artifact.artifact_id ? '读取中' : '下载'}</Button>
        </div>)}</div> : <p className="value-empty">作品清单还没有成片或字幕文件。</p>}
      </section>
      {loaded ? <Button variant="ghost" size="1" color="gray" onClick={() => { loading.current?.abort(); setLoaded(null); setSubtitles(null); setBusy(false); }}>关闭预览</Button> : null}
      {importReceipt ? <p className="small-note">本地索引状态：{importReceipt.index_state === 'ready' ? '已建立' : importReceipt.index_state === 'failed' ? '建立失败' : '尚未建立'}。来源版本与本地定位分别保存；引用授权由来源实例管理。</p> : null}
      <div className="delivery-actions"><Button disabled={!connected || busy} onClick={() => setExportOpen(true)}><Download size={16} />导出作品包</Button><Button variant="soft" disabled={!connected || busy || Boolean(importReceipt)} onClick={() => setGrantOpen(true)}><Link size={16} />授权引用</Button></div>
    </> : null}
    {busy ? <p role="status" className="small-note">正在处理，请稍候。已有作品保留。</p> : null}
    {error ? <Callout.Root color="red" role="alert"><Callout.Text>{errorMessage(error)}</Callout.Text></Callout.Root> : null}
    {connected && !exportJob.isError && exportJob.data ? <div className="delivery-job" role="status"><strong>{EXPORT_STATUS[exportJob.data.status]}</strong><p>此导出固定为 {exportJob.data.bundle_ref.bundle_revision_id}。离开页面不会取消打包。</p>{exportJob.data.status === 'ready' ? <>{archive ? <BlobDownload blob={archive} filename={`VideoCreator-${exportJob.data.export_id}.zip`}>保存已校验的ZIP</BlobDownload> : <Button size="2" variant="soft" disabled={busy || !connected} onClick={() => void downloadExport()}>读取并校验导出包</Button>}<BlobDownload blob={new Blob([JSON.stringify(exportJob.data.bundle_ref, null, 2)], { type: 'application/json' })} filename={`VideoCreator-${exportJob.data.export_id}-Origin.json`}>保存来源版本描述</BlobDownload></> : null}{exportJob.data.status === 'failed' ? <p>作品仍保留，请核对权限或实例资源后重新导出。</p> : null}<Button variant="ghost" size="1" onClick={() => void exportJob.refetch()}><RefreshCw size={14} />刷新导出状态</Button></div> : null}
    {exportJob.error ? <Callout.Root color="red"><Callout.Text>{errorMessage(exportJob.error)}</Callout.Text><Button size="1" variant="soft" onClick={() => void exportJob.refetch()}>重读导出状态</Button></Callout.Root> : null}
    {grant ? <div className="delivery-job"><strong>{grant.revoked_at_us ? '引用授权已撤销' : '引用授权已创建'}</strong><p>接收方 {grant.recipient_id}；固定版本 {grant.bundle_ref.bundle_revision_id}；有效至 {new Date(grant.expires_at_us / 1000).toLocaleString()}。</p>{!grant.revoked_at_us ? <><BlobDownload blob={new Blob([JSON.stringify(grant, null, 2)], { type: 'application/json' })} filename={`VideoCreator-${grant.grant_id}.json`}>保存引用描述</BlobDownload><Button variant="ghost" size="1" color="red" disabled={busy || !connected} onClick={() => void revokeGrant()}>撤销引用授权</Button></> : null}</div> : null}
    <Dialog.Root open={exportOpen} onOpenChange={value => { if (!busy) setExportOpen(value); }}><Dialog.Content maxWidth="480px"><Dialog.Title>导出固定版本</Dialog.Title><Dialog.Description>导出不会改变原作品。选择性导出保留所需依赖，由实例检查权限。</Dialog.Description><label className="field-label" htmlFor="export-profile">导出范围</label><Select.Root value={profile} onValueChange={value => setProfile(value as 'full' | 'projection')}><Select.Trigger id="export-profile" /><Select.Content><Select.Item value="full">完整作品包</Select.Item><Select.Item value="projection">选择交付内容</Select.Item></Select.Content></Select.Root>{profile === 'projection' ? <div className="export-selection">{artifacts.map(item => <label key={item.artifact_id}><Checkbox checked={selectedIds.includes(item.artifact_id)} onCheckedChange={checked => setSelectedIds(current => checked ? [...current, item.artifact_id] : current.filter(id => id !== item.artifact_id))} />{item.roles.map(role => OUTPUT_LABEL[role as OutputRole] ?? role).join('、')}<small>{item.relative_path}</small></label>)}</div> : null}{error ? <p className="field-error" role="alert">{errorMessage(error)}</p> : null}<Flex gap="3" justify="end" mt="5"><Dialog.Close><Button variant="soft" color="gray" disabled={busy}>返回</Button></Dialog.Close><Button disabled={busy || !connected || (profile === 'projection' && !selectedIds.length)} onClick={() => void startExport()}>开始导出</Button></Flex></Dialog.Content></Dialog.Root>
    <Dialog.Root open={grantOpen} onOpenChange={value => { if (!busy) setGrantOpen(value); }}><Dialog.Content maxWidth="480px"><Dialog.Title>授权引用</Dialog.Title><Dialog.Description>只授权此固定版本。接收方仍需自己的实例身份；描述文件不含会话凭证。</Dialog.Description><div className="import-fields"><label className="field-label" htmlFor="reference-recipient">接收方编号</label><TextField.Root id="reference-recipient" value={recipient} onChange={event => setRecipient(event.target.value)} /><label className="field-label" htmlFor="reference-expires">有效至</label><input id="reference-expires" type="datetime-local" value={expires} onChange={event => setExpires(event.target.value)} /><label className="reference-option"><Checkbox checked={semanticAllowed} onCheckedChange={value => setSemanticAllowed(value === true)} />允许读取语义文本用于检索</label></div>{error ? <p className="field-error" role="alert">{errorMessage(error)}</p> : null}<Flex gap="3" justify="end" mt="5"><Dialog.Close><Button variant="soft" color="gray" disabled={busy}>返回</Button></Dialog.Close><Button disabled={busy || !connected || !/^[A-Za-z0-9_.:-]{1,128}$/.test(recipient) || !expires || new Date(expires).getTime() <= Date.now()} onClick={() => void createGrant()}>确认引用范围</Button></Flex></Dialog.Content></Dialog.Root>
  </section>;
}
