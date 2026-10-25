import { expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import { DeliveryView } from '../DeliveryView';
import { bootstrapManagedWorkbench } from '../engine';
import type { Schemas } from '../engine';

const INSTANCE = 'instance-verify';
const REVISION = 'bundle-revision-verify';

async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

function jsonResponse(status: number, payload: unknown): Response {
  return { ok: status >= 200 && status < 300, status, headers: new Headers({ 'content-type': 'application/json' }), json: async () => payload } as unknown as Response;
}

it('shows size, SHA prefix, local self-issued and unmeasured precision for a finished bundle', async () => {
  const manifest = {
    schema_version: '0.3.0-candidate', bundle_format_version: 1, instance_id: INSTANCE,
    bundle_id: 'bundle-verify', bundle_revision_id: REVISION, project_id: 'project-verify',
    production_id: 'production-verify', run_id: 'run-verify', request_revision_id: 'request-verify',
    request_sha256: 'a'.repeat(64), workflow_version: 'registered-media-bundle-v1',
    created_at_us: 1, timeline_duration_us: 60_000_000,
    creative_revision_refs: [], approval_refs: [], feedback_revision_refs: [], source_refs: [],
    requested_outputs: ['video', 'subtitles'],
    outputs: [
      { role: 'video', artifact_ids: ['artifact-video'], status: 'present', provenance_revision_refs: [] },
      { role: 'subtitles', artifact_ids: ['artifact-subtitles'], status: 'present', provenance_revision_refs: [] },
    ],
    artifacts: [
      { artifact_id: 'artifact-video', sha256: 'c'.repeat(64), size: 1_234_567, media_type: 'video/mp4', relative_path: 'video/final.mp4', roles: ['video'], dependency_artifact_ids: [], method_ref: 'method', rights_ref: 'rights' },
      { artifact_id: 'artifact-subtitles', sha256: 'd'.repeat(64), size: 2_048, media_type: 'text/vtt', relative_path: 'text/subtitles.vtt', roles: ['subtitles'], dependency_artifact_ids: [], method_ref: 'method', rights_ref: 'rights' },
    ],
    audio_mappings: [], methods: [], rights: [],
    quality_ref: { revision_id: 'quality-1', kind: 'quality', content_sha256: 'e'.repeat(64) },
    evidence_policy_revision_ref: {}, qualification_ref: {},
    benchmark_binding: 'embedded_self_issued', benchmark_document_artifact_id: 'artifact-benchmark',
    policy_document_artifact_id: 'artifact-policy', qualification_document_artifact_id: 'artifact-qualification',
    work_validation_document_artifact_id: 'artifact-work',
  } as unknown as Schemas['BundleManifestV03'];
  const bytes = new TextEncoder().encode(JSON.stringify(manifest));
  const manifestSha = await sha256(JSON.stringify(manifest));
  const bundleRef: Schemas['BundleRef'] = {
    instance_id: INSTANCE, bundle_id: 'bundle-verify', bundle_revision_id: REVISION,
    schema_version: '0.3.0-candidate', manifest_sha256: manifestSha,
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    if (url.pathname.endsWith('/manifest/metadata')) {
      return jsonResponse(200, {
        state: 'ready', local_instance_id: INSTANCE, size: bytes.length, sha256: manifestSha,
        media_type: 'application/json', locator: { kind: 'bundle_manifest', bundle_ref: bundleRef },
        authorization_expires_at_us: null,
      });
    }
    if (url.pathname.endsWith('/manifest')) {
      return new Response(bytes, { status: 200, headers: { 'content-type': 'application/json', 'content-length': String(bytes.length) } });
    }
    if (url.pathname.endsWith('/semantic-segments')) return jsonResponse(200, { bundle_ref: bundleRef, segments: [], next_cursor: null });
    return jsonResponse(404, { code: 'not_found', message: 'probe', retryability: 'never', request_id: 'probe' });
  });
  vi.stubGlobal('fetch', fetchMock);
  const dispose = bootstrapManagedWorkbench(window.location.origin);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
  try {
    render(<Theme><QueryClientProvider client={client}>
      <DeliveryView bundleRef={bundleRef} connected status="succeeded" onAssets={() => {}} />
    </QueryClientProvider></Theme>);

    expect(await screen.findByText('本地自签（非第三方认证）')).toBeInTheDocument();
    expect(screen.getByText(/1\.2 MB · SHA c{12}/)).toBeInTheDocument();
    expect(screen.getByText(/2\.0 KB · SHA d{12}/)).toBeInTheDocument();
    expect(screen.getByText(/能力基准：未执行；精度声明：未测量/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /下载/ })).toHaveLength(2);
    expect(screen.queryByText(/已认证/)).not.toBeInTheDocument();
    expect(screen.queryByText(/已测精度/)).not.toBeInTheDocument();
  } finally {
    dispose?.();
  }
});
