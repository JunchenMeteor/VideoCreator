import { inputHash, RequestFailure } from './engine';
import type { ProductionInput, Schemas } from './engine';

type IntentBodies = { production: ProductionInput; 'bundle-import': Schemas['BundleImportRequest'] };
export type SubmissionIntent<K extends keyof IntentBodies> = {
  instanceId: string;
  body: IntentBodies[K];
  idempotencyKey: string;
  receiptId: string | null;
};
const prefixes = { production: 'workbench-', 'bundle-import': 'workbench-import-' } as const;
const identifier = /^[A-Za-z0-9_.:-]{1,128}$/;
function storageKey(kind: keyof IntentBodies, instanceId: string): string {
  if (!identifier.test(instanceId)) throw new RequestFailure(422, 'invalid_request');
  return `video-creator:submission:${kind}:${instanceId}`;
}

// Only generated JSON inputs and non-secret instance/receipt locators are stored.
// ZIP/File/media bytes and connection/model credentials never enter this record.
export function readSubmissionIntent<K extends keyof IntentBodies>(kind: K, instanceId: string): SubmissionIntent<K> | null {
  try {
    const text = localStorage.getItem(storageKey(kind, instanceId));
    if (text === null) return null;
    const value: unknown = JSON.parse(text);
    if (!value || typeof value !== 'object'
      || !('instanceId' in value) || value.instanceId !== instanceId
      || !('body' in value) || !value.body || typeof value.body !== 'object' || Array.isArray(value.body)
      || !('project_id' in value.body) || typeof value.body.project_id !== 'string' || !identifier.test(value.body.project_id)
      || !('idempotencyKey' in value) || typeof value.idempotencyKey !== 'string'
      || !new RegExp(`^${prefixes[kind]}[a-f0-9]{64}$`).test(value.idempotencyKey)
      || !('receiptId' in value) || !(value.receiptId === null || (typeof value.receiptId === 'string' && identifier.test(value.receiptId)))) {
      throw new Error('Invalid local submission record');
    }
    // Runtime public-body validation remains the installation's generated contract.
    // Before any replay, verifySubmissionIntent also checks the exact saved body/key.
    return value as SubmissionIntent<K>;
  } catch { throw new RequestFailure(503, 'intent_storage_unavailable'); }
}

export function saveSubmissionIntent<K extends keyof IntentBodies>(kind: K, intent: SubmissionIntent<K>): void {
  try {
    const key = storageKey(kind, intent.instanceId);
    const existing = readSubmissionIntent(kind, intent.instanceId);
    if (existing && !existing.receiptId && existing.idempotencyKey !== intent.idempotencyKey) throw new Error('Another submission is unresolved');
    const text = JSON.stringify(intent);
    localStorage.setItem(key, text);
    if (localStorage.getItem(key) !== text) throw new Error('Local submission record was not retained');
  } catch { throw new RequestFailure(503, 'intent_storage_unavailable'); }
}

export function clearSubmissionIntent(kind: keyof IntentBodies, instanceId: string, expectedKey: string): void {
  try {
    const key = storageKey(kind, instanceId);
    const existing = readSubmissionIntent(kind, instanceId);
    if (existing && existing.idempotencyKey !== expectedKey) throw new Error('Submission identity changed');
    localStorage.removeItem(key);
    if (localStorage.getItem(key) !== null) throw new Error('Local submission record was not cleared');
  } catch { throw new RequestFailure(503, 'intent_storage_unavailable'); }
}

export async function makeSubmissionIntent<K extends keyof IntentBodies>(kind: K, instanceId: string, body: IntentBodies[K]): Promise<SubmissionIntent<K>> {
  // Clone JSON once before retaining it; later UI edits cannot mutate this body.
  const fixedBody = JSON.parse(JSON.stringify(body)) as IntentBodies[K];
  return { instanceId, body: fixedBody, idempotencyKey: `${prefixes[kind]}${await inputHash(fixedBody)}`, receiptId: null };
}

export async function verifySubmissionIntent<K extends keyof IntentBodies>(kind: K, intent: SubmissionIntent<K>, instanceId: string): Promise<void> {
  if (intent.instanceId !== instanceId || intent.idempotencyKey !== `${prefixes[kind]}${await inputHash(intent.body)}`) {
    throw new RequestFailure(409, 'submission_identity_mismatch');
  }
}

export function validReceiptId(value: unknown): value is string {
  return typeof value === 'string' && identifier.test(value);
}
