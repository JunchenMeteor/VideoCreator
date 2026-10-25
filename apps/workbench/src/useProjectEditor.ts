import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { engineData, rememberLocator, storedLocator, RequestFailure } from './engine';
import type { ProjectDraft, ProjectInput } from './engine';

export const EMPTY_PROJECT: ProjectInput = { name: '未命名作品', goal: '', source_text: '' };
const projectInput = (project: ProjectDraft): ProjectInput => ({ name: project.name, goal: project.goal, source_text: project.source_text });
const sameInput = (a: ProjectInput, b: ProjectInput) => a.name === b.name && a.goal === b.goal && a.source_text === b.source_text;
type EditorContext = { instanceId: string | undefined; connected: boolean; generation: number; mounted: boolean };
type EditorState = {
  instanceId: string | undefined; project: ProjectDraft | null; form: ProjectInput;
  phase: 'idle' | 'loading' | 'saving' | 'saved' | 'failed' | 'conflict'; error: unknown; edited: boolean; blockedAutoSave: boolean;
  createIntent: { key: string; input: ProjectInput } | null;
};
const emptyState = (instanceId: string | undefined): EditorState => ({ instanceId, project: null, form: { ...EMPTY_PROJECT }, phase: 'idle', error: null, edited: false, blockedAutoSave: false, createIntent: null });
const contextChanged = () => new RequestFailure(409, 'submission_identity_mismatch');

export function useProjectEditor(instanceId: string | undefined, connected = Boolean(instanceId), allowLegacyCreate = true) {
  const queryClient = useQueryClient();
  const [state, setState] = useState(() => emptyState(instanceId));
  const [serial, setSerial] = useState(0);
  const stateRef = useRef(state); stateRef.current = state;
  const contextRef = useRef<EditorContext>({ instanceId, connected, generation: 0, mounted: true });
  if (contextRef.current.instanceId !== instanceId || contextRef.current.connected !== connected) {
    contextRef.current = { instanceId, connected, generation: contextRef.current.generation + 1, mounted: contextRef.current.mounted };
  }
  const drafts = useRef(new Map<string | undefined, EditorState>());
  const saveRef = useRef<{ context: EditorContext; promise: Promise<ProjectDraft> } | null>(null);
  const initialized = useRef<string | null>(null);
  const isCurrent = useCallback((context: EditorContext) => contextRef.current === context && context.mounted, []);
  const commit = useCallback((context: EditorContext, change: (current: EditorState) => EditorState) => {
    if (!isCurrent(context) || stateRef.current.instanceId !== context.instanceId) return false;
    const next = change(stateRef.current);
    stateRef.current = next;
    setState(previous => isCurrent(context) ? next : previous);
    return true;
  }, [isCurrent]);

  useLayoutEffect(() => {
    contextRef.current = { ...contextRef.current, generation: contextRef.current.generation + 1, mounted: true };
    return () => {
      contextRef.current = { ...contextRef.current, generation: contextRef.current.generation + 1, mounted: false };
      initialized.current = null;
    };
  }, []);
  useLayoutEffect(() => {
    const context = contextRef.current;
    if (!isCurrent(context)) return;
    const previous = stateRef.current;
    if (previous.instanceId !== instanceId) {
      const interrupted = previous.phase === 'loading' || previous.phase === 'saving';
      drafts.current.set(previous.instanceId, { ...previous, phase: interrupted ? 'idle' : previous.phase, blockedAutoSave: interrupted || previous.blockedAutoSave });
      const restored = drafts.current.get(instanceId) ?? (previous.instanceId === undefined && previous.edited
        ? { ...previous, instanceId, project: null, phase: 'idle' as const, error: null, blockedAutoSave: false }
        : emptyState(instanceId));
      stateRef.current = restored;
      setState(current => isCurrent(context) ? restored : current);
      saveRef.current = null; initialized.current = null;
    } else if (!connected && (previous.phase === 'loading' || previous.phase === 'saving')) {
      if (previous.phase === 'loading') initialized.current = null;
      commit(context, current => ({ ...current, phase: 'idle', blockedAutoSave: true }));
      saveRef.current = null;
    }
  }, [instanceId, connected, commit, isCurrent]);

  const list = useQuery({
    queryKey: ['projects', instanceId], enabled: connected && Boolean(instanceId),
    queryFn: async () => {
      const context = contextRef.current;
      const rows = await engineData('GET /api/v1/projects', {});
      if (!isCurrent(context) || context.instanceId !== instanceId || !context.connected) throw contextChanged();
      return rows;
    },
  });
  const dirty = state.edited && (!state.project || !sameInput(state.form, projectInput(state.project)));

  const load = useCallback(async (id: string, onLoaded?: () => void) => {
    const previous = contextRef.current;
    if (!isCurrent(previous) || !previous.connected || !previous.instanceId || stateRef.current.instanceId !== previous.instanceId) return;
    const owner = previous.instanceId;
    const context = { ...previous, generation: previous.generation + 1 };
    contextRef.current = context; saveRef.current = null; initialized.current = owner;
    commit(context, current => ({ ...current, phase: 'loading', error: null }));
    try {
      const saved = await engineData('GET /api/v1/projects/{project_id}', { path: { project_id: id } });
      if (!isCurrent(context)) return;
      if (saved.project_id !== id) throw contextChanged();
      if (!commit(context, current => ({ ...current, project: saved, form: projectInput(saved), edited: false, phase: 'saved', error: null, blockedAutoSave: false, createIntent: null }))) return;
      if (!isCurrent(context)) return;
      rememberLocator(`video-creator:project:${context.instanceId}`, saved.project_id);
      if (!isCurrent(context)) return;
      onLoaded?.();
      return isCurrent(context) ? saved : undefined;
    } catch (failure) {
      if (isCurrent(context)) commit(context, current => ({ ...current, phase: 'failed', error: failure, blockedAutoSave: true }));
    }
  }, [commit, isCurrent]);

  useEffect(() => {
    const context = contextRef.current;
    if (!connected || !instanceId || state.instanceId !== instanceId || !list.data || initialized.current === instanceId || !isCurrent(context)) return;
    initialized.current = instanceId;
    const remembered = storedLocator(`video-creator:project:${instanceId}`);
    const selected = list.data.find(item => item.project_id === remembered) ?? list.data[0];
    if (selected && !stateRef.current.edited) void load(selected.project_id);
  }, [instanceId, connected, state.instanceId, list.data, load, isCurrent]);

  const save = useCallback(async (): Promise<ProjectDraft> => {
    const context = contextRef.current;
    const owner = context.instanceId;
    if (!isCurrent(context) || !context.connected || !owner || stateRef.current.instanceId !== owner) throw new RequestFailure(503, 'instance_unavailable');
    if (saveRef.current?.context === context) return saveRef.current.promise;
    commit(context, current => ({ ...current, phase: 'saving', error: null, blockedAutoSave: false }));
    const run = async () => {
      const current = stateRef.current;
      const snapshot = { ...current.form };
      let saved: ProjectDraft;
      if (current.project) {
        saved = await engineData('PUT /api/v1/projects/{project_id}', { path: { project_id: current.project.project_id }, body: snapshot, headers: { 'If-Match': String(current.project.revision) } });
      } else {
        if (!allowLegacyCreate) throw new RequestFailure(409, 'goal_submission_required', undefined, undefined, 'not_sent');
        // Ambiguous creation retries retain the same body/key in its own instance.
        const intent = current.createIntent ?? { key: crypto.randomUUID(), input: snapshot };
        if (!commit(context, value => ({ ...value, createIntent: intent }))) throw contextChanged();
        saved = await engineData('POST /api/v1/projects', { body: intent.input, headers: { 'Idempotency-Key': intent.key } });
      }
      if (!isCurrent(context)) throw contextChanged();
      if (current.project && saved.project_id !== current.project.project_id) throw contextChanged();
      if (!commit(context, value => ({ ...value, project: saved, phase: 'saved', createIntent: null }))) throw contextChanged();
      if (!isCurrent(context)) throw contextChanged();
      rememberLocator(`video-creator:project:${owner}`, saved.project_id);
      if (!isCurrent(context)) throw contextChanged();
      await queryClient.invalidateQueries({ queryKey: ['projects', owner] });
      if (!isCurrent(context)) throw contextChanged();
      return saved;
    };
    const promise = run().catch(failure => {
      if (isCurrent(context)) commit(context, current => ({ ...current, blockedAutoSave: true, error: failure, phase: failure instanceof RequestFailure && failure.status === 409 ? 'conflict' : 'failed' }));
      throw failure;
    }).finally(() => {
      if (!isCurrent(context) || saveRef.current?.promise !== promise) return;
      saveRef.current = null;
      setSerial(current => isCurrent(context) ? current + 1 : current);
    });
    if (isCurrent(context)) saveRef.current = { context, promise };
    return promise;
  }, [queryClient, commit, isCurrent, allowLegacyCreate]);

  useEffect(() => {
    const context = contextRef.current;
    if (!dirty || !connected || !instanceId || (!state.project && !allowLegacyCreate) || state.instanceId !== instanceId || state.blockedAutoSave || state.phase === 'loading') return;
    const timer = window.setTimeout(() => { if (isCurrent(context)) void save().catch(() => {}); }, 500);
    return () => window.clearTimeout(timer);
  }, [dirty, state, instanceId, connected, serial, save, isCurrent, allowLegacyCreate]);

  const flush = async () => {
    const context = contextRef.current;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      if (!isCurrent(context) || !context.connected || stateRef.current.instanceId !== context.instanceId) throw contextChanged();
      const current = stateRef.current;
      if (current.project && sameInput(current.form, projectInput(current.project)) && saveRef.current?.context !== context) return current.project;
      const saved = await save();
      if (!isCurrent(context)) throw contextChanged();
      if (sameInput(stateRef.current.form, projectInput(saved))) return saved;
    }
    throw new RequestFailure(409, 'draft_changed_during_save');
  };
  const update = <K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) => {
    const context = contextRef.current;
    commit(context, current => ({ ...current, edited: true, form: { ...current.form, [key]: value } }));
  };
  const cancelLoad = () => {
    const previous = contextRef.current;
    if (!isCurrent(previous) || stateRef.current.instanceId !== previous.instanceId || stateRef.current.phase !== 'loading') return;
    const context = { ...previous, generation: previous.generation + 1 };
    contextRef.current = context; saveRef.current = null;
    if (context.instanceId) initialized.current = context.instanceId;
    commit(context, current => ({ ...current, phase: 'idle', error: null, blockedAutoSave: true }));
  };
  const newDraft = (keepInput = false) => {
    const previous = contextRef.current;
    if (!isCurrent(previous) || stateRef.current.instanceId !== previous.instanceId) return;
    const context = { ...previous, generation: previous.generation + 1 };
    contextRef.current = context; saveRef.current = null;
    if (context.instanceId) initialized.current = context.instanceId;
    commit(context, current => ({ ...emptyState(context.instanceId), form: keepInput ? current.form : { ...EMPTY_PROJECT }, edited: keepInput }));
  };
  return { project: state.project, form: state.form, phase: state.phase, error: state.error, dirty, list, update, save, flush, load, cancelLoad, newDraft };
}
