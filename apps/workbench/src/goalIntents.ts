import { inputHash, RequestFailure } from './engine';
import type { ProjectGoalAccepted, ProjectGoalInput } from './engine';
import { validReceiptId } from './submissionIntents';

export type GoalContext = { kind: 'native'; generation: string } | { kind: 'api'; instanceId: string; principalId: string };
export type GoalIntent = { version: 1; context: GoalContext; body: ProjectGoalInput; bodyHash: string; key: string; receipt: ProjectGoalAccepted | null; attempt: string | null; disposition: 'pending' | 'accepted' | 'rejected' };
function slot(context: GoalContext): string {
  if (context.kind === 'native') return 'video-creator:first-goal:1';
  if (!validReceiptId(context.instanceId) || !validReceiptId(context.principalId)) throw new RequestFailure(409, 'submission_identity_mismatch');
  return `video-creator:goal:1:${context.instanceId}:${context.principalId}`;
}
export const sameGoalContext = (a: GoalContext, b: GoalContext) => JSON.stringify(a) === JSON.stringify(b);
// Object property order is irrelevant to the native JSON proposal; array order
// and every value must remain exact. This is equality, not a server hash codec.
export function sameGoalProposal(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return false;
  if (Array.isArray(a) || Array.isArray(b)) return Array.isArray(a) && Array.isArray(b)
    && a.length === b.length && a.every((value, index) => sameGoalProposal(value, b[index]));
  const left = Object.keys(a); const right = Object.keys(b);
  return left.length === right.length && left.every(key => Object.hasOwn(b, key)
    && sameGoalProposal((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key]));
}
export function readGoalIntent(context: GoalContext): GoalIntent | null {
  try {
    const text = localStorage.getItem(slot(context));
    if (text === null) return null;
    const value = JSON.parse(text) as GoalIntent;
    if (value?.version !== 1 || !value.context || !['native', 'api'].includes(value.context.kind)
      || !value.body || value.body.format !== 'project-goal-input-v1'
      || !/^[a-f0-9]{64}$/.test(value.bodyHash) || !/^goal-[a-f0-9-]{36}$/.test(value.key)
      || !['pending', 'accepted', 'rejected'].includes(value.disposition)
      || !(value.attempt === null || validReceiptId(value.attempt))
      || !(value.receipt === null || isGoalReceipt(value.receipt))) throw new Error('Invalid Goal record');
    if (context.kind === 'api' && !sameGoalContext(context, value.context)) throw new Error('Goal identity changed');
    if (value.context.kind === 'native' && (typeof value.context.generation !== 'string' || !value.context.generation)) throw new Error('Missing document generation');
    if (value.disposition === 'accepted' && !value.receipt) throw new Error('Missing original receipt');
    if (value.context.kind === 'api' && value.receipt && value.receipt.instance_id !== value.context.instanceId) throw new Error('Foreign receipt');
    return value;
  } catch { throw new RequestFailure(503, 'intent_storage_unavailable'); }
}
export function saveGoalIntent(intent: GoalIntent): void {
  try {
    const existing = readGoalIntent(intent.context);
    if (existing && existing.disposition === 'pending' && existing.key !== intent.key) throw new Error('Original Goal unresolved');
    const text = JSON.stringify(intent); localStorage.setItem(slot(intent.context), text);
    if (localStorage.getItem(slot(intent.context)) !== text) throw new Error('Goal not retained');
  } catch { throw new RequestFailure(503, 'intent_storage_unavailable'); }
}
export async function makeGoalIntent(context: GoalContext, body: ProjectGoalInput): Promise<GoalIntent> {
  const fixed: ProjectGoalInput = JSON.parse(JSON.stringify(body));
  return { version: 1, context, body: fixed, bodyHash: await inputHash(fixed), key: `goal-${crypto.randomUUID()}`, receipt: null, attempt: null, disposition: 'pending' };
}
export async function verifyGoalIntent(intent: GoalIntent, context: GoalContext): Promise<void> {
  if (!sameGoalContext(intent.context, context) || intent.bodyHash !== await inputHash(intent.body)) throw new RequestFailure(409, 'submission_identity_mismatch');
}
export function isGoalReceipt(value: unknown): value is ProjectGoalAccepted {
  if (!value || typeof value !== 'object') return false;
  const receipt = value as ProjectGoalAccepted;
  return receipt.format === 'project-goal-accepted-v1'
    && [receipt.instance_id, receipt.project_id, receipt.production_id, receipt.run_id].every(validReceiptId)
    && /^[a-f0-9]{64}$/.test(receipt.goal_sha256)
    && validReceiptId(receipt.derivation_ref?.derivation_id) && /^[a-f0-9]{64}$/.test(receipt.derivation_ref?.content_sha256)
    && receipt.production?.instance_id === receipt.instance_id && receipt.production.project_id === receipt.project_id
    && receipt.production.production_id === receipt.production_id && receipt.production.run_id === receipt.run_id
    && validReceiptId(receipt.production.request_revision_id);
}
