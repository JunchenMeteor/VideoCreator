import type { Schemas } from './engine';
import { reviewExpiry, reviewFailureMessage } from './productFlow';

const SUMMARY_KIND: Readonly<Record<string, string>> = {
  insight: '洞察', brief: '方向', plan: '制作计划', script: '剧本', storyboard: '分镜', quality: '检查结果',
};

/**
 * The revisions route returns `ProductionRevisionSummary` (no body). Show the
 * facts it actually carries: version, confirmation validity and a translated
 * failure reason. Never invent a revision body and never print the raw code.
 */
export function RevisionSummaryView({ revision }: { revision: Schemas['ProductionRevisionSummary'] }) {
  const expiry = reviewExpiry(revision.expires_at_us);
  const failure = reviewFailureMessage(revision.failure_code);
  return <div className="revision-summary">
    <p><strong>{SUMMARY_KIND[revision.kind] ?? '创作产物'}</strong> · 版本标识 <code>{revision.revision_id}</code></p>
    <p>本次确认有效期：{expiry.label}</p>
    {failure ? <p>未通过原因：{failure}</p> : null}
    {!failure && !expiry.provided ? <p className="small-note">实例只提供版本摘要；没有可展开正文，也不会据此伪造内容。</p> : null}
  </div>;
}
