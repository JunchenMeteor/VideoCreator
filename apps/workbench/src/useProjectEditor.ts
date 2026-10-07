import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { engineJson, jsonWrite, rememberLocator, storedLocator, RequestFailure } from './engine';
import type { ProjectDraft, ProjectInput } from './engine';

export const EMPTY_PROJECT: ProjectInput = { name: '未命名作品', goal: '', source_text: '' };
const projectInput = (project: ProjectDraft): ProjectInput => ({ name: project.name, goal: project.goal, source_text: project.source_text });
const sameInput = (a: ProjectInput, b: ProjectInput) => a.name === b.name && a.goal === b.goal && a.source_text === b.source_text;

export function useProjectEditor(instanceId: string | undefined) {
  const queryClient = useQueryClient();
  const [project, setProject] = useState<ProjectDraft | null>(null);
  const [form, setForm] = useState<ProjectInput>({ ...EMPTY_PROJECT });
  const [phase, setPhase] = useState<'idle' | 'loading' | 'saving' | 'saved' | 'failed' | 'conflict'>('idle');
  const [error, setError] = useState<unknown>(null);
  const [serial, setSerial] = useState(0);
  const [edited, setEdited] = useState(false);
  const projectRef = useRef(project);
  const formRef = useRef(form);
  const saveRef = useRef<Promise<ProjectDraft> | null>(null);
  const createIntent = useRef<{ key: string; input: ProjectInput } | null>(null);
  const initialized = useRef<string | null>(null);
  const blockedAutoSave = useRef(false);
  projectRef.current = project;
  formRef.current = form;

  const list = useQuery({
    queryKey: ['projects', instanceId], enabled: Boolean(instanceId),
    queryFn: () => engineJson<ProjectDraft[]>('/api/v1/projects'),
  });
  const dirty = edited && (!project || !sameInput(form, projectInput(project)));

  const load = useCallback(async (id: string) => {
    setPhase('loading');
    setError(null);
    try {
      const saved = await engineJson<ProjectDraft>(`/api/v1/projects/${encodeURIComponent(id)}`);
      projectRef.current = saved;
      formRef.current = projectInput(saved);
      setProject(saved); setForm(projectInput(saved)); setEdited(false);
      setPhase('saved'); blockedAutoSave.current = false; createIntent.current = null;
      if (instanceId) rememberLocator(`video-creator:project:${instanceId}`, saved.project_id);
    } catch (failure) { setPhase('failed'); setError(failure); }
  }, [instanceId]);

  useEffect(() => {
    if (!instanceId || !list.data || initialized.current === instanceId) return;
    initialized.current = instanceId;
    const remembered = storedLocator(`video-creator:project:${instanceId}`);
    const selected = list.data.find(item => item.project_id === remembered) ?? list.data[0];
    if (selected && !edited) void load(selected.project_id);
  }, [instanceId, list.data, edited, load]);

  const save = useCallback(async (): Promise<ProjectDraft> => {
    if (saveRef.current) return saveRef.current;
    if (!instanceId) throw new RequestFailure(503, 'instance_unavailable');
    blockedAutoSave.current = false;
    setPhase('saving'); setError(null);
    const run = async () => {
      const current = projectRef.current;
      const snapshot = { ...formRef.current };
      let saved: ProjectDraft;
      if (current) {
        saved = await engineJson<ProjectDraft>(`/api/v1/projects/${encodeURIComponent(current.project_id)}`,
          jsonWrite('PUT', snapshot, { 'If-Match': String(current.revision) }));
      } else {
        // Keep the same intent on an ambiguous transport failure. New edits are
        // applied only after the original creation is recovered with its key.
        createIntent.current ??= { key: crypto.randomUUID(), input: snapshot };
        const intent = createIntent.current;
        saved = await engineJson<ProjectDraft>('/api/v1/projects', jsonWrite('POST', intent.input, { 'Idempotency-Key': intent.key }));
        createIntent.current = null;
      }
      projectRef.current = saved; setProject(saved); setPhase('saved');
      rememberLocator(`video-creator:project:${instanceId}`, saved.project_id);
      await queryClient.invalidateQueries({ queryKey: ['projects', instanceId] });
      return saved;
    };
    const promise = run().catch(failure => {
      blockedAutoSave.current = true;
      setError(failure); setPhase(failure instanceof RequestFailure && failure.status === 409 ? 'conflict' : 'failed');
      throw failure;
    }).finally(() => { saveRef.current = null; setSerial(current => current + 1); });
    saveRef.current = promise;
    return promise;
  }, [instanceId, queryClient]);

  useEffect(() => {
    if (!dirty || !instanceId || blockedAutoSave.current || phase === 'loading') return;
    const timer = window.setTimeout(() => { void save().catch(() => {}); }, 500);
    return () => window.clearTimeout(timer);
  }, [dirty, form, instanceId, phase, serial, save]);

  const flush = async () => {
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const current = projectRef.current;
      if (current && sameInput(formRef.current, projectInput(current)) && !saveRef.current) return current;
      const saved = await save();
      if (sameInput(formRef.current, projectInput(saved))) return saved;
    }
    throw new RequestFailure(409, 'draft_changed_during_save');
  };

  const update = <K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) => {
    setEdited(true);
    setForm(current => ({ ...current, [key]: value }));
  };
  const newDraft = (keepInput = false) => {
    if (saveRef.current) return;
    setProject(null); projectRef.current = null;
    if (!keepInput) { setForm({ ...EMPTY_PROJECT }); formRef.current = { ...EMPTY_PROJECT }; }
    setEdited(keepInput); setPhase('idle'); setError(null);
    blockedAutoSave.current = false; createIntent.current = null;
  };
  return { project, form, phase, error, dirty, list, update, save, flush, load, newDraft };
}
