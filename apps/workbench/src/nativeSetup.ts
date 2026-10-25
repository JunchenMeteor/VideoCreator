import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { createOwnerSetupPort } from '../../desktop/OwnerSetupPort';
import type { Json, NativeSetupInvoke, SetupView } from '../../desktop/OwnerSetupPort';
import { sameGoalProposal } from './goalIntents';

type SetupPort = ReturnType<typeof createOwnerSetupPort>;
type Connection = { readonly port: SetupPort };
let connection: Connection | null = null;
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
const snapshot = () => connection;
export const useNativeSetupAvailable = () => Boolean(useSyncExternalStore(subscribe, snapshot, () => null));

// The actual desktop bootstrap supplies its invoke transport. No window/global,
// URL, caller-supplied authority, or successful health response substitutes it.
export function configureNativeSetup(invoke: NativeSetupInvoke): () => void {
  const installed = { port: createOwnerSetupPort(invoke) };
  connection = installed; listeners.forEach(listener => listener());
  return () => {
    if (connection !== installed) return;
    connection = null; listeners.forEach(listener => listener());
  };
}

export function useNativeSetup() {
  const installed = useSyncExternalStore(subscribe, snapshot, () => null);
  const [view, setView] = useState<SetupView | null>(null);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [failed, setFailed] = useState(false);
  const current = useRef<{ installed: Connection | null; epoch: number; mounted: boolean }>({ installed, epoch: 0, mounted: false });
  if (current.current.installed !== installed) current.current = { installed, epoch: current.current.epoch + 1, mounted: current.current.mounted };
  const original = useRef<{ owner: Connection; generation: string; key: string; goal: Json } | null>(null);
  const command = useRef(false);
  const status = useRef<SetupView | null>(null);
  const viewConnection = useRef<Connection | null>(null);
  const revision = useRef(0);
  const valid = (owner: typeof current.current) => current.current === owner && owner.mounted && snapshot() === owner.installed;

  useEffect(() => {
    const owner = { installed, epoch: current.current.epoch + 1, mounted: true };
    current.current = owner; status.current = null; viewConnection.current = null; setView(null); setFailed(false); setBusy(false); setUncertain(false);
    let timer: ReturnType<typeof setTimeout> | undefined;
    const read = async () => {
      if (!installed || !valid(owner)) return;
      try {
        // A fresh document may inspect the original native attempt, never replay it.
        const observedRevision = revision.current;
        const next = await installed.port.status(status.current?.generation ?? null);
        if (!valid(owner)) return;
        if (observedRevision !== revision.current) return;
        if (status.current && next.generation !== status.current.generation) { setFailed(true); return; }
        const proposal = original.current;
        if (proposal && proposal.owner === installed) {
          const identity = next.request_identity;
          if (!identity || identity.original_generation !== proposal.generation
            || identity.idempotency_key !== proposal.key || !sameGoalProposal(identity.goal, proposal.goal)) {
            setFailed(true); setUncertain(true); return;
          }
          // The same original native status can resolve a lost ACK without a
          // second prepare. Failed/mismatched reads leave the request uncertain.
          if (next.attempt !== null) setUncertain(false);
        }
        viewConnection.current = installed; status.current = next; setView(next); setFailed(false);
      } catch { if (valid(owner)) setFailed(true); }
      finally { if (valid(owner)) timer = setTimeout(() => { void read(); }, 1500); }
    };
    void read();
    return () => {
      if (timer) clearTimeout(timer);
      if (current.current === owner) current.current = { ...owner, mounted: false };
    };
  }, [installed]);

  const run = async (operation: 'present' | 'abort') => {
    const owner = current.current; const before = status.current;
    if (!owner.installed || !valid(owner) || !before?.attempt || command.current || uncertain) return;
    if (operation === 'present' && (before.phase !== 'review' || !before.can_present || !before.current_document)) return;
    if (operation === 'abort' && !['preparing', 'review'].includes(before.phase)) return;
    command.current = true; revision.current++; setBusy(true); setFailed(false);
    try {
      const next = await owner.installed.port[operation](before.generation, before.attempt);
      if (!valid(owner)) return;
      if (next.generation !== before.generation || next.attempt !== before.attempt) { setUncertain(true); return; }
      revision.current++; viewConnection.current = owner.installed; status.current = next; setView(next);
      return next;
    } catch { if (valid(owner)) { setFailed(true); setUncertain(true); } }
    finally { command.current = false; if (valid(owner)) setBusy(false); }
  };

  // The caller must build the unique generated ProjectGoalInput, then pass its
  // JSON proposal here. This module deliberately has no duplicate Goal schema.
  const prepare = async (goal: Json, idempotencyKey: string) => {
    const owner = current.current; const before = status.current;
    if (!owner.installed || !valid(owner) || !before || before.phase !== 'idle'
      || before.attempt || command.current || original.current || uncertain) return;
    // Hold a detached original proposal, so later form changes cannot mutate it.
    const heldGoal: Json = JSON.parse(JSON.stringify(goal));
    const intent = { owner: owner.installed, generation: before.generation, key: idempotencyKey, goal: heldGoal };
    original.current = intent; command.current = true; revision.current++; setBusy(true); setFailed(false);
    try {
      const next = await intent.owner.port.prepare(intent.generation, intent.key, intent.goal);
      if (!valid(owner)) return;
      if (next.generation !== intent.generation) { setUncertain(true); return; }
      revision.current++; viewConnection.current = owner.installed; status.current = next; setView(next);
      return next;
    } catch { if (valid(owner)) { setFailed(true); setUncertain(true); } }
    finally { command.current = false; if (valid(owner)) setBusy(false); }
  };
  return { connected: Boolean(installed), view: viewConnection.current === installed ? view : null, busy, uncertain, failed, prepare,
    present: () => run('present'), abort: () => run('abort') };
}
