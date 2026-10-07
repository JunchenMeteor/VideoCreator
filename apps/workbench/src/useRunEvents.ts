import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { engineFetch } from './engine';
import type { EngineEvent } from './engine';

export function useRunEvents(runId: string | undefined, productionId: string | undefined) {
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<EngineEvent[]>([]);
  const [phase, setPhase] = useState<'idle' | 'connecting' | 'connected' | 'disconnected'>('idle');
  const [retry, setRetry] = useState(0);
  const cursor = useRef({ runId: '', sequence: 0 });

  useEffect(() => {
    if (!runId || !productionId) { setEvents([]); setPhase('idle'); return; }
    if (cursor.current.runId !== runId) { cursor.current = { runId, sequence: 0 }; setEvents([]); }
    const controller = new AbortController();
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    setPhase('connecting');
    const receive = async () => {
      const response = await engineFetch(`/api/v1/runs/${encodeURIComponent(runId)}/events?after_sequence=${cursor.current.sequence}`,
        { headers: { Accept: 'text/event-stream' }, signal: controller.signal });
      if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) throw new Error('event_stream_unavailable');
      setPhase('connected');
      reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (!controller.signal.aborted) {
        const part = await reader.read();
        if (part.done) throw new Error('event_stream_closed');
        buffer += decoder.decode(part.value, { stream: true }).replaceAll('\r\n', '\n');
        if (buffer.length > 1_048_576) throw new Error('event_stream_limit');
        let boundary: number;
        while ((boundary = buffer.indexOf('\n\n')) >= 0) {
          const record = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
          const data = record.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
          if (!data) continue;
          const event = JSON.parse(data) as EngineEvent;
          if (event.run_id !== runId || event.production_id !== productionId || !Number.isSafeInteger(event.sequence) || event.sequence <= cursor.current.sequence || typeof event.event_id !== 'string') continue;
          cursor.current.sequence = event.sequence;
          setEvents(current => current.some(existing => existing.event_id === event.event_id) ? current : [...current, event]);
          void queryClient.invalidateQueries({ queryKey: ['production', productionId] });
          void queryClient.invalidateQueries({ queryKey: ['revisions', productionId] });
        }
      }
    };
    void receive().catch(() => { if (!controller.signal.aborted) setPhase('disconnected'); }).finally(() => reader?.releaseLock());
    return () => { controller.abort(); void reader?.cancel().catch(() => {}); };
  }, [runId, productionId, retry, queryClient]);

  return { events, phase, reconnect: () => setRetry(current => current + 1) };
}
