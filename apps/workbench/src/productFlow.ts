import type { ProductionAccepted, ProductionDetail, Schemas } from './engine';

export type OutputRole = Schemas['BundleOutput']['role'];

export const OUTPUT_LABEL: Readonly<Record<OutputRole, string>> = {
  video: '成片视频',
  narration_audio: '旁白音轨',
  mixed_audio: '完整混音',
  approved_script: '批准原稿',
  actual_transcript: '实际转写',
  subtitles: '字幕',
  semantic_manifest: '语义索引',
  rag_chunks: '检索文本',
};

/** Video is mandatory; these are the opt-in outputs for a spoken work. */
export const VOICE_OUTPUTS: readonly OutputRole[] = [
  'mixed_audio', 'actual_transcript', 'subtitles', 'semantic_manifest', 'rag_chunks',
];

type StatusTone = 'queued' | 'running' | 'waiting' | 'done' | 'failed' | 'neutral';
export type ProductionStatusInfo = { label: string; detail: string; tone: StatusTone };

/**
 * Product-facing status copy. No internal evidence vocabulary is shown here;
 * failure detail is supplied separately from named operation/API codes.
 */
export const PRODUCTION_STATUS: Readonly<Record<Schemas['RunStatus'], ProductionStatusInfo>> = {
  queued: { label: '已受理，排队中', detail: '任务已保存，等待本机制作进程接单。可以关闭页面，任务仍会保留。', tone: 'queued' },
  running: { label: '制作中', detail: '本机正在执行这条作品；已有结果会逐步出现，离开页面不会取消。', tone: 'running' },
  waiting_user: { label: '待你审核', detail: '有制作计划或质量检查需要你确认；未确认前不会进入下一步。', tone: 'waiting' },
  waiting_authorization: { label: '等待授权', detail: '任务已保存，但实例还缺少所需授权。已有资料保留，授权齐备前不会继续。', tone: 'waiting' },
  waiting_provider: { label: '等待模型结果', detail: '上游模型或服务还没有返回。费用或受理结果不明时不会自动重交。', tone: 'waiting' },
  succeeded: { label: '已完成', detail: '成片与请求的输出已经保存，可以在下方取片。', tone: 'done' },
  failed: { label: '制作失败', detail: '制作没有完成。已有资料和部分产物会保留，请按错误码核对后重试。', tone: 'failed' },
  cancel_requested: { label: '正在取消', detail: '已请求停止安排后续步骤；上游已提交的操作仍按实际结果核实。', tone: 'waiting' },
  cancelled: { label: '已取消', detail: '任务已停止，已产生的素材和记录仍保留。', tone: 'neutral' },
  needs_reconciliation: { label: '结果待核实', detail: '上游结果或费用需要核实；核实前不会盲目重复提交。', tone: 'waiting' },
};

export function productionStatusInfo(status: Schemas['RunStatus']): ProductionStatusInfo {
  return PRODUCTION_STATUS[status];
}

const FAILED_OPERATION = /fail|error|invalid|denied|timeout|unavailable|mismatch|reject/i;

/**
 * Named failure fact for the UI. The public production detail has no dedicated
 * failure-code field, so a failed operation's fixed status string is used when
 * present; otherwise `run_failed` is shown rather than pretending a 500.
 */
export function productionFailure(
  production: Pick<ProductionDetail, 'status' | 'operations'>,
): { code: string; detail: string } | null {
  if (production.status !== 'failed') return null;
  const operation = production.operations.find(item => FAILED_OPERATION.test(item.status));
  const code = operation ? `operation_${operation.status}` : 'run_failed';
  return {
    code,
    detail: operation
      ? '一个执行步骤明确失败；已有资料和部分产物保留。请按错误码核对素材、能力或实例状态后重试。'
      : '实例没有返回更具体的公开错误码。已有资料和部分产物保留；可刷新状态或查看任务记录。',
  };
}

export type ReviewKind = 'plan' | 'quality';
export const REVIEW_KINDS: readonly ReviewKind[] = ['plan', 'quality'];
export const REVIEW_INFO: Readonly<Record<ReviewKind, { title: string; what: string; impact: string }>> = {
  plan: {
    title: '制作计划',
    what: '这份计划决定镜头、素材、声音和制作顺序。',
    impact: '同意后才会进入实际制作；拒绝会停在这份计划，需要重新发起或补充意见。',
  },
  quality: {
    title: '质量检查',
    what: '这份检查决定当前产物能否交付。',
    impact: '同意后才会进入交付或下一步；拒绝会保留问题并停止，避免把不合格内容当成完成。',
  },
};

/** Review validity is task-state bound; there is no independent public expiry. */
export const REVIEW_VALIDITY = '本次审核只在任务处于“待审核”期间有效；任务状态改变后失效。';

const REVIEW_CODE_TEXT: Readonly<Record<string, string>> = {
  alignment_required: '制作能力尚未对齐：实例缺少完成这条作品所需的执行或证据能力。同意不能补齐缺失能力，需要先补装配。',
  media_invalid: '素材无法解码或格式不受支持，需要更换素材后重试。',
  provider_unavailable: '所需的本地模型或服务当前不可用，需先恢复能力。',
  budget_unauthorized: '这次制作没有相应预算授权，不能进入执行。',
  production_authorization_unconfigured: '实例还没有可用的执行身份，当前只能保存任务，不能开始制作。',
};

export function reviewFailureText(code: unknown): string | undefined {
  return typeof code === 'string' ? REVIEW_CODE_TEXT[code] : undefined;
}

export function reviewKindOf(kind: string): kind is ReviewKind {
  return kind === 'plan' || kind === 'quality';
}

export function latestReviewRevisions(revisions: readonly Schemas['CreativeRevision'][]) {
  return REVIEW_KINDS.flatMap(kind => {
    const revision = revisions.filter(item => item.kind === kind).at(-1);
    return revision ? [{ kind, revision }] : [];
  });
}

export function waitingProductions(productions: readonly ProductionAccepted[]): ProductionAccepted[] {
  return productions.filter(item => item.status === 'waiting_user');
}

export function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size < 0) return '未知大小';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function shortSha(sha: string): string {
  return sha.length > 12 ? sha.slice(0, 12) : sha;
}

export function benchmarkBindingLabel(binding: string): string {
  if (binding === 'embedded_self_issued') return '本地自签（非第三方认证）';
  if (binding === 'embedded_full_report') return '内嵌完整报告（以文档为准）';
  if (binding === 'provenance_reference') return '来源引用（以原始报告为准）';
  return binding;
}

export function selfIssuedNote(binding: string): string | undefined {
  return binding === 'embedded_self_issued'
    ? '能力基准：未执行；精度声明：未测量（precision_claim=not_measured）。'
    : undefined;
}

export function isPreviewableRevisionCode(body: unknown): string | undefined {
  return body && typeof body === 'object' && 'code' in body && typeof body.code === 'string' ? body.code : undefined;
}

export type { ProductionAccepted };
