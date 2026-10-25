import { NativeTransportError } from './native.ts';

export interface EngineServerEvent {
  id: string | undefined;
  event: string;
  data_raw: string;
}
/** Optional SSE parser; requestRaw itself always exposes unchanged wire bytes. */
export async function* readEngineEvents(response: Response, options: { maximumEventBytes: number }): AsyncGenerator<EngineServerEvent> {
  if (!response.ok || !response.body || !(response.headers.get('content-type') ?? '').toLowerCase().startsWith('text/event-stream') ||
      !Number.isSafeInteger(options.maximumEventBytes) || options.maximumEventBytes < 1) throw new NativeTransportError('native_sse_invalid', 'read');
  const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', { fatal: true });
  const encoder = new TextEncoder();
  let pending = '', data: string[] = [], event = 'message', id: string | undefined, size = 0, last: bigint | undefined;
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      pending += decoder.decode(chunk.value, { stream: true });
      let newline: number;
      while ((newline = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0, newline).replace(/\r$/, ''); pending = pending.slice(newline + 1);
        size += encoder.encode(line).length + 1;
        if (size > options.maximumEventBytes) throw new NativeTransportError('native_sse_event_limit', 'read', true);
        if (line === '') {
          if (data.length) {
            if (id !== undefined) {
              if (!/^(0|[1-9][0-9]*)$/.test(id) || last !== undefined && BigInt(id) <= last) throw new NativeTransportError('native_sse_cursor_invalid', 'read', true);
              last = BigInt(id);
            }
            yield { id, event, data_raw: data.join('\n') };
          }
          data = []; event = 'message'; id = undefined; size = 0;
        } else if (!line.startsWith(':')) {
          const colon = line.indexOf(':'), field = colon < 0 ? line : line.slice(0, colon);
          const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
          if (field === 'data') data.push(value);
          else if (field === 'event') event = value;
          else if (field === 'id') id = value;
        }
      }
      if (size + encoder.encode(pending).length > options.maximumEventBytes) throw new NativeTransportError('native_sse_event_limit', 'read', true);
    }
    pending += decoder.decode();
    // Do not emit an unterminated event as a fully received record.
    if (pending || data.length) throw new NativeTransportError('native_sse_truncated', 'read', true);
  } finally {
    await reader.cancel().catch(() => {}); reader.releaseLock();
  }
}
