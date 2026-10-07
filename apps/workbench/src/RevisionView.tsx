import type { CreativeRevision } from './engine';

const LABELS: Record<string, string> = {
  title: '标题', topic: '选题', main_thesis: '主旨', thesis: '主旨', audience: '受众', angle: '表达角度',
  summary: '摘要', rationale: '推荐理由', source_gaps: '来源缺口', facts: '事实', hypotheses: '假设',
  candidates: '备选方案', script: '剧本', text: '内容', narration: '旁白', visual: '画面',
  shots: '分镜', scenes: '场景', characters: '角色', voices: '声音', evidence: '依据',
  action: '动作', camera: '运镜', constraints: '约束', findings: '检查发现', recommended: '推荐',
};

function ValueView({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined) return <span className="value-empty">未提供</span>;
  if (typeof value !== 'object') return <p className="revision-text">{String(value)}</p>;
  if (depth > 5) return <details><summary>展开内容</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>;
  if (Array.isArray(value)) return <div className="revision-items">{value.map((item, index) => <div className="revision-item" key={index}><ValueView value={item} depth={depth + 1} /></div>)}</div>;
  return <dl className="revision-fields">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{LABELS[key] ?? key.replaceAll('_', ' ')}</dt><dd><ValueView value={item} depth={depth + 1} /></dd></div>)}</dl>;
}

export function RevisionView({ revision }: { revision: CreativeRevision }) {
  return <div className="revision-view"><ValueView value={revision.body} /><details className="revision-provenance"><summary>版本与依据</summary><p>当前版本：{revision.revision_id}</p>{revision.input_revision_refs.length ? <p>采用的产物：{revision.input_revision_refs.join('、')}</p> : <p>没有附带产物引用。</p>}</details></div>;
}
