import type { CreativeRevision, Schemas } from './engine';

const SCOPE_LABEL: Record<Schemas['EvidenceReportRef']['evaluation_scope'], string> = {
  // Honest states: a skipped benchmark is not a measured capability.
  capability_benchmark: '能力基准',
  capability_benchmark_not_performed: '未执行基准/未测量',
  work_runtime_validation: '本作品运行检查',
  per_work_reference_measurement: '本作品参考测量',
};

// Enum literals that must never read as a pass/certification. `not_measured`
// stays "未测量"; an embedded local benchmark stays self-issued, not certified.
const VALUE_LABELS: Record<string, string> = {
  embedded_full_report: '内嵌完整报告',
  provenance_reference: '来源引用',
  embedded_self_issued: '本地自签（非第三方认证）',
  not_measured: '未测量',
};

const LABELS: Record<string, string> = {
  title: '标题', topic: '选题', main_thesis: '主旨', thesis: '主旨', audience: '受众', angle: '表达角度',
  summary: '摘要', rationale: '推荐理由', source_gaps: '来源缺口', facts: '事实', hypotheses: '假设',
  candidates: '备选方案', script: '剧本', text: '内容', narration: '旁白', visual: '画面',
  shots: '分镜', scenes: '场景', characters: '角色', voices: '声音', evidence: '依据',
  action: '动作', camera: '运镜', constraints: '约束', findings: '检查发现', recommended: '推荐',
  evaluation_scope: '检查范围', report_id: '报告编号', content_sha256: '原件校验值',
  benchmark_binding: '基准绑定方式', precision: '精度', benchmark_precision: '基准精度',
  p95_error_us: 'P95误差（微秒）', reference_sample_count: '参考样本数量',
};

function ValueView({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined) return <span className="value-empty">未提供</span>;
  if (typeof value !== 'object') {
    const text = String(value);
    return <p className="revision-text">{Object.hasOwn(VALUE_LABELS, text) ? VALUE_LABELS[text] : text}</p>;
  }
  if (depth > 5) return <details><summary>展开内容</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>;
  if (Array.isArray(value)) return <div className="revision-items">{value.map((item, index) => <div className="revision-item" key={index}><ValueView value={item} depth={depth + 1} /></div>)}</div>;
  const scope = 'evaluation_scope' in value && typeof value.evaluation_scope === 'string' && Object.hasOwn(SCOPE_LABEL, value.evaluation_scope)
    ? value.evaluation_scope as Schemas['EvidenceReportRef']['evaluation_scope'] : undefined;
  return <><dl className="revision-fields">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{LABELS[key] ?? key.replaceAll('_', ' ')}</dt><dd>{key === 'evaluation_scope' && scope ? SCOPE_LABEL[scope] : item === null && /p95|reference_sample|measurement|precision/.test(key) ? <span className="value-empty">未测量</span> : <ValueView value={item} depth={depth + 1} />}</dd></div>)}</dl>{scope === 'capability_benchmark' ? <p className="small-note">能力基准仅说明方法能力，不能代替本作品的参考测量。</p> : scope === 'capability_benchmark_not_performed' ? <p className="small-note">本次未执行能力基准，也没有测量精度；该值不能作为能力或认证结论。</p> : scope === 'work_runtime_validation' ? <p className="small-note">本作品运行检查与参考测量分别记录。未提供本作品参考时，精度测量值为未测。</p> : null}</>;
}

export function RevisionView({ revision }: { revision: CreativeRevision }) {
  return <div className="revision-view"><ValueView value={revision.body} /><details className="revision-provenance"><summary>版本与依据</summary><p>当前版本：{revision.revision_id}</p>{revision.input_revision_refs.length ? <p>采用的产物：{revision.input_revision_refs.join('、')}</p> : <p>没有附带产物引用。</p>}</details></div>;
}
