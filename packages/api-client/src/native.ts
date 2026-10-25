import {
  NATIVE_CONSTRAINTS, NATIVE_CONTRACT_VERSION, NATIVE_ROUTES,
  NATIVE_ROUTE_MANIFEST_SHA256, NATIVE_TRANSPORT_FORMAT,
} from './native.routes.generated.ts';
import { decimal, decodeNativeFrame, encodeNativeFrame, NATIVE_MAX_CHUNK_BYTES } from './native.frame.ts';

export interface NativeBridge {
  // Supply the real Tauri invoke function. This interface does not create a session.
  invoke<T>(command: string, args?: Record<string, unknown> | Uint8Array,
    options?: { headers: Record<string, string> }): Promise<T>;
}
export interface NativeSessionDescriptor {
  mode: 'native';
  instance_id: string;
  generation: string;
  contract_version: string;
  route_manifest_sha256: string;
  transport_format: string;
  limits: {
    max_http_handles: number;
    max_chunk_bytes: number;
    max_buffered_frames: number;
    open_timeout_ms: number;
    head_timeout_ms: number;
    upload_idle_timeout_ms: number;
    read_idle_timeout_ms: number;
  };
}
export type NativeTransportPhase = 'session' | 'validation' | 'open' | 'upload' | 'head' | 'read' | 'cleanup' | 'save' | 'media';
export class NativeTransportError extends Error {
  readonly code: string;
  readonly phase: NativeTransportPhase;
  readonly may_have_been_accepted: boolean;
  constructor(code: string, phase: NativeTransportPhase, accepted = false) {
    super(code); this.name = 'NativeTransportError';
    this.code = code; this.phase = phase; this.may_have_been_accepted = accepted;
  }
}
type Json = Record<string, unknown>;
type Rule = { name: string; in: string; required?: boolean; schema?: Json;
  'x-native-value-pattern'?: string; media_types?: string[] };
type Route = { operation_id: string; method: string; parameters: Rule[];
  header_rules: Record<string, Rule>; request_body: { required?: boolean } | null;
  transport: { body: { kind: 'none' | 'json_bytes' | 'raw_bytes'; minimum_bytes?: number; maximum_bytes: number | null };
    request_headers: string[]; response_headers: string[]; response: { kind: string } } };
const routes: Readonly<Record<string, Route>> = NATIVE_ROUTES as unknown as Record<string, Route>;
const construction = Symbol('actual-native-descriptor');
export type NativeBody = Uint8Array | ArrayBuffer | Blob;
export interface NativeRequest {
  path?: Readonly<Record<string, unknown>>;
  query?: Readonly<Record<string, unknown>>;
  headers?: Readonly<Record<string, string>>;
  body?: NativeBody;
  signal?: AbortSignal;
}
interface ResponseHead { status: number; headers: Record<string, string>; body_kind: 'none' | 'bytes'; content_length?: string }
interface Handle {
  id: string; route: Route; seq: bigint; offset: bigint; accepted: boolean;
  consumer: 'none' | 'stream' | 'save'; close?: Promise<void>;
  signal?: AbortSignal; onAbort?: () => void; streamController?: ReadableStreamDefaultController<Uint8Array>;
}
const token = (value: unknown): value is string => typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const control = /[\u0000-\u001f\u007f]/;
function fail(code: string, phase: NativeTransportPhase = 'validation', accepted = false): never {
  throw new NativeTransportError(code, phase, accepted);
}
function object(value: unknown): value is Json { return !!value && typeof value === 'object' && !Array.isArray(value); }
function safePositive(value: unknown, maximum = Number.MAX_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 && value <= maximum;
}
function matches(value: unknown, schema?: Json): boolean {
  if (!schema) return true;
  if (Array.isArray(schema.anyOf)) return schema.anyOf.some(s => object(s) && matches(value, s));
  if (Array.isArray(schema.enum) && !schema.enum.includes(value)) return false;
  if (schema.type === 'string' && typeof value !== 'string') return false;
  if (schema.type === 'integer' && (typeof value !== 'number' || !Number.isSafeInteger(value))) return false;
  if (schema.type === 'number' && (typeof value !== 'number' || !Number.isFinite(value))) return false;
  if (schema.type === 'boolean' && typeof value !== 'boolean') return false;
  if (schema.type === 'null' && value !== null) return false;
  if (typeof value === 'string' &&
      ((typeof schema.minLength === 'number' && [...value].length < schema.minLength) ||
       (typeof schema.maxLength === 'number' && [...value].length > schema.maxLength) ||
       (typeof schema.pattern === 'string' && !new RegExp(schema.pattern).test(value)))) return false;
  if (typeof value === 'number' &&
      ((typeof schema.minimum === 'number' && value < schema.minimum) ||
       (typeof schema.maximum === 'number' && value > schema.maximum))) return false;
  return true;
}
function parameters(values: Readonly<Record<string, unknown>>, rules: Rule[]): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [name, value] of Object.entries(values)) {
    const rule = rules.find(p => p.name === name);
    if (!rule) fail('native_parameter_unknown');
    if (value === undefined || value === null) continue;
    if (!matches(value, rule.schema) || (typeof value === 'string' && control.test(value))) fail('native_parameter_invalid');
    result[name] = value;
  }
  if (rules.some(p => p.required && !(p.name in result))) fail('native_parameter_missing');
  return result;
}
function declaredHeaders(input: Readonly<Record<string, string>>, route: Route): Record<string, string> {
  const output: Record<string, string> = {};
  const forbidden = NATIVE_CONSTRAINTS.forbidden_renderer_headers.map(name => name.toLowerCase());
  for (const [original, value] of Object.entries(input)) {
    const name = original.toLowerCase(), rule = route.header_rules[name];
    if (!/^[a-z0-9!#$%&'*+.^_`|~-]+$/.test(name) || forbidden.includes(name) ||
        !route.transport.request_headers.some(h => h.toLowerCase() === name) || !rule || name in output) fail('native_header_unknown');
    if (typeof value !== 'string' || control.test(value) || !matches(value, rule.schema) ||
        (rule['x-native-value-pattern'] && !new RegExp(rule['x-native-value-pattern']).test(value))) fail('native_header_invalid');
    if (rule.media_types) {
      const mime = value.split(';', 1)[0].trim().toLowerCase();
      if (!/^[a-z0-9!#$&^_.+-]+\/[a-z0-9!#$&^_.+-]+$/.test(mime) ||
          !rule.media_types.some(m => m === '*/*' || m.toLowerCase() === mime)) fail('native_content_type_invalid');
    }
    output[name] = value;
  }
  if (Object.values(route.header_rules).some(p => p.required && !(p.name.toLowerCase() in output))) fail('native_header_missing');
  return output;
}
function bodySize(body?: NativeBody): number { return body instanceof Blob ? body.size : body?.byteLength ?? 0; }
async function bodyChunk(body: NativeBody, offset: number, count: number): Promise<Uint8Array> {
  if (body instanceof Blob) return new Uint8Array(await body.slice(offset, offset + count).arrayBuffer());
  const bytes = body instanceof Uint8Array ? body : new Uint8Array(body);
  return bytes.subarray(offset, offset + count);
}
function deadline<T>(promise: Promise<T>, milliseconds: number, phase: NativeTransportPhase, accepted = true): Promise<T> {
  let timeout: ReturnType<typeof setTimeout>;
  const timer = new Promise<never>((_, reject) => { timeout = setTimeout(() => reject(new NativeTransportError('native_timeout', phase, accepted)), milliseconds); });
  return Promise.race([promise, timer]).finally(() => clearTimeout(timeout));
}
class SingleConsumerResponse extends Response {
  override clone(): Response { fail('native_response_single_consumer'); }
}

/** An actual bridge must return a ready descriptor matching this generated manifest. */
async function getDescriptor(bridge: NativeBridge): Promise<NativeSessionDescriptor> {
  let value: unknown;
  try { value = await bridge.invoke<unknown>('get_engine_session'); }
  catch { fail('native_session_unavailable', 'session'); }
  if (!object(value) || value.mode !== 'native' || !token(value.instance_id) || !token(value.generation) ||
      value.contract_version !== NATIVE_CONTRACT_VERSION || value.route_manifest_sha256 !== NATIVE_ROUTE_MANIFEST_SHA256 ||
      value.transport_format !== NATIVE_TRANSPORT_FORMAT || !object(value.limits)) fail('native_session_incompatible', 'session');
  if (Object.keys(value).some(k => !['mode', 'instance_id', 'generation', 'contract_version', 'route_manifest_sha256', 'transport_format', 'limits'].includes(k))) fail('native_session_incompatible', 'session');
  const l = value.limits;
  if (!safePositive(l.max_http_handles, 8) || !safePositive(l.max_chunk_bytes, NATIVE_MAX_CHUNK_BYTES) ||
      !safePositive(l.max_buffered_frames, 2) ||
      !['open_timeout_ms', 'head_timeout_ms', 'upload_idle_timeout_ms', 'read_idle_timeout_ms'].every(k => safePositive(l[k], 2147483647))) fail('native_session_incompatible', 'session');
  if (Object.keys(l).some(k => !['max_http_handles', 'max_chunk_bytes', 'max_buffered_frames', 'open_timeout_ms', 'head_timeout_ms', 'upload_idle_timeout_ms', 'read_idle_timeout_ms'].includes(k))) fail('native_session_incompatible', 'session');
  return value as unknown as NativeSessionDescriptor;
}

export function createNativeTransportV1(bridge: NativeBridge): Promise<NativeTransportV1> {
  return NativeTransportV1.connect(bridge);
}

export class NativeTransportV1 {
  readonly session: Readonly<NativeSessionDescriptor>;
  private readonly bridge: NativeBridge;
  private invalid = false;
  private reserved = 0;
  private readonly handles = new Set<Handle>();
  private readonly responses = new WeakMap<Response, Handle>();
  private readonly media = new Set<string>();
  private constructor(bridge: NativeBridge, descriptor: NativeSessionDescriptor, authority: symbol) {
    if (authority !== construction) fail('native_session_unavailable', 'session');
    this.bridge = bridge;
    this.session = Object.freeze({ ...descriptor, limits: Object.freeze({ ...descriptor.limits }) });
  }
  static async connect(bridge: NativeBridge): Promise<NativeTransportV1> {
    return new NativeTransportV1(bridge, await getDescriptor(bridge), construction);
  }
  private async call<T>(command: string, args: Record<string, unknown> | Uint8Array,
    phase: NativeTransportPhase, timeout: number, accepted = true, headers?: Record<string, string>): Promise<T> {
    try { return await deadline(this.bridge.invoke<T>(command, args, headers ? { headers } : undefined), timeout, phase, accepted); }
    catch (error) {
      if (error instanceof NativeTransportError) throw error;
      fail('native_ipc_failed', phase, accepted); // Never echo native exceptions, tokens or internal paths.
    }
  }
  private args(handle: Handle): Record<string, unknown> { return { generation: this.session.generation, request_handle: handle.id }; }
  private close(handle: Handle, abort: boolean): Promise<void> {
    if (handle.close) return handle.close;
    handle.close = (async () => {
      try {
        if (abort) await this.call('engine_request_abort', this.args(handle), 'cleanup', this.session.limits.open_timeout_ms);
      } finally {
        try { await this.call('engine_request_release', this.args(handle), 'cleanup', this.session.limits.open_timeout_ms); }
        finally {
          this.handles.delete(handle); this.reserved--;
          if (handle.onAbort) handle.signal?.removeEventListener('abort', handle.onAbort);
        }
      }
    })().catch(error => { this.invalid = true; throw error; });
    return handle.close;
  }
  async request(operationId: string, input: NativeRequest): Promise<Response> {
    if (this.invalid) fail('native_session_invalid', 'session');
    if (!Object.hasOwn(routes, operationId)) fail('native_operation_unknown');
    const route = routes[operationId];
    if (Object.keys(input).some(k => !['path', 'query', 'headers', 'body', 'signal'].includes(k))) fail('native_argument_unknown');
    const path = parameters(input.path ?? {}, route.parameters.filter(p => p.in === 'path'));
    const query = parameters(input.query ?? {}, route.parameters.filter(p => p.in === 'query'));
    const headers = declaredHeaders(input.headers ?? {}, route);
    const body = input.body, mode = route.transport.body;
    if (body !== undefined && !(body instanceof ArrayBuffer || body instanceof Uint8Array || body instanceof Blob)) fail('native_body_invalid');
    const length = bodySize(body);
    if (mode.kind === 'none' && body !== undefined || route.request_body?.required && body === undefined ||
        mode.maximum_bytes !== null && length > mode.maximum_bytes ||
        mode.minimum_bytes !== undefined && length < mode.minimum_bytes) fail('native_body_invalid');
    if (input.signal?.aborted) fail('native_aborted', 'open');
    if (this.reserved >= this.session.limits.max_http_handles) fail('native_handle_limit', 'open');
    this.reserved++;
    let handle: Handle | undefined;
    try {
      // No automatic retry: an open failure may already have sent the HTTP operation.
      const opened = await this.call<unknown>('engine_request_open', {
        generation: this.session.generation, client_request_id: crypto.randomUUID(), operation_id: operationId,
        path_params: path, query, headers, body: body === undefined ? { kind: 'none' } : { kind: 'bytes', length: String(length) },
      }, 'open', this.session.limits.open_timeout_ms);
      if (!object(opened) || !token(opened.request_handle)) fail('native_handle_invalid', 'open', true);
      handle = { id: opened.request_handle, route, seq: 0n, offset: 0n, accepted: true, consumer: 'none', signal: input.signal };
      this.handles.add(handle);
      const h = handle;
      if (this.invalid) { await this.close(h, true); fail('native_session_invalid', 'open', true); }
      h.onAbort = () => {
        h.streamController?.error(new NativeTransportError('native_aborted', 'read', true));
        void this.close(h, true).catch(() => { /* No fabrication of an HTTP response on cleanup failure. */ });
      };
      input.signal?.addEventListener('abort', h.onAbort, { once: true });
      if (input.signal?.aborted) { h.onAbort(); fail('native_aborted', 'open', true); }
      let early = false;
      // Start listening before uploading. A server rejection can stop a large upload early.
      const headPromise = this.bridge.invoke<unknown>('engine_response_head', this.args(h)).then(value => {
        early = true; return value;
      }, () => { early = true; fail('native_ipc_failed', 'head', true); });
      // Attach a rejection observer while upload is in progress, without masking it.
      void headPromise.catch(() => {});
      if (body !== undefined) {
        for (let offset = 0; offset < length && !early; ) {
          if (h.close || input.signal?.aborted) fail('native_aborted', 'upload', true);
          const bytes = await bodyChunk(body, offset, this.session.limits.max_chunk_bytes);
          if (early) break;
          const frame = encodeNativeFrame(BigInt(offset), bytes);
          const uploaded = this.call<unknown>('engine_upload_chunk', frame, 'upload', this.session.limits.upload_idle_timeout_ms, true, {
            'x-video-creator-request-handle': h.id, 'x-video-creator-generation': this.session.generation,
            'x-video-creator-sequence': String(h.seq),
          });
          const outcome = await Promise.race([uploaded.then(ack => ({ ack })), headPromise.then(() => ({ early: true as const }))]);
          if ('early' in outcome) { void uploaded.catch(() => {}); break; }
          const ack = outcome.ack;
          if (!object(ack) || ack.seq !== String(h.seq) || ack.next_offset !== String(offset + bytes.length)) fail('native_upload_ack_invalid', 'upload', true);
          h.seq++; offset += bytes.length;
        }
        if (!early) await this.call('engine_upload_finish', {
          ...this.args(h), seq: String(h.seq), total_bytes: String(length),
        }, 'upload', this.session.limits.upload_idle_timeout_ms);
      }
      // Head timeout starts after upload completion, not at the start of a legitimate large upload.
      const rawHead = await deadline(headPromise, this.session.limits.head_timeout_ms, 'head');
      if (!object(rawHead) || !Number.isInteger(rawHead.status) || Number(rawHead.status) < 200 || Number(rawHead.status) > 599 ||
          !object(rawHead.headers) || !['none', 'bytes'].includes(String(rawHead.body_kind))) fail('native_head_invalid', 'head', true);
      const head = rawHead as unknown as ResponseHead;
      const responseHeaders = new Headers();
      for (const [name, value] of Object.entries(head.headers)) {
        if (!route.transport.response_headers.some(n => n.toLowerCase() === name.toLowerCase()) || typeof value !== 'string' || control.test(value)) fail('native_response_header_invalid', 'head', true);
        responseHeaders.set(name, value);
      }
      let expected: bigint | undefined;
      try { if (head.content_length !== undefined) expected = decimal(head.content_length); }
      catch { fail('native_head_invalid', 'head', true); }
      const contentLength = responseHeaders.get('content-length');
      if (contentLength !== null && expected !== undefined && contentLength !== String(expected)) fail('native_head_invalid', 'head', true);
      if ([204, 304].includes(head.status) && head.body_kind !== 'none') fail('native_head_invalid', 'head', true);
      if (head.status === 401) {
        this.invalid = true;
        for (const other of this.handles) if (other !== h) void this.close(other, true).catch(() => {});
      }
      h.seq = 0n;
      const stream = head.body_kind === 'none' ? null : new ReadableStream<Uint8Array>({
        start: controller => { h.streamController = controller; },
        pull: async controller => {
          if (h.consumer === 'save') { controller.error(new NativeTransportError('native_response_single_consumer', 'read', true)); return; }
          h.consumer = 'stream';
          try {
            if (h.close) fail('native_response_closed', 'read', true);
            const raw = await this.call<unknown>('engine_response_read', {
              ...this.args(h), seq: String(h.seq), offset: String(h.offset), max_bytes: this.session.limits.max_chunk_bytes,
            }, 'read', this.session.limits.read_idle_timeout_ms);
            if (!(raw instanceof ArrayBuffer || raw instanceof Uint8Array)) fail('native_frame_invalid', 'read', true);
            let frame: ReturnType<typeof decodeNativeFrame>;
            try { frame = decodeNativeFrame(raw, h.offset); } catch { fail('native_frame_invalid', 'read', true); }
            if (frame.payload.length > this.session.limits.max_chunk_bytes || expected !== undefined && frame.nextOffset > expected) fail('native_frame_invalid', 'read', true);
            h.seq++; h.offset = frame.nextOffset;
            if (frame.eof) {
              if (expected !== undefined && h.offset !== expected) fail('native_body_truncated', 'read', true);
              await this.close(h, false); controller.close();
            } else controller.enqueue(frame.payload);
          } catch (error) {
            void this.close(h, true).catch(() => {});
            controller.error(error instanceof NativeTransportError ? error : new NativeTransportError('native_read_failed', 'read', true));
          }
        },
        cancel: () => this.close(h, true),
      }, { highWaterMark: 0 });
      if (!stream) await this.close(h, false);
      const response = new SingleConsumerResponse(stream, { status: head.status, headers: responseHeaders });
      this.responses.set(response, h);
      return response;
    } catch (error) {
      if (handle) await this.close(handle, true).catch(() => {});
      else this.reserved--;
      throw error instanceof NativeTransportError ? error : new NativeTransportError('native_request_failed', 'open', true);
    }
  }
  async saveResponse(response: Response, deliveryRef: unknown, suggestedName?: string): Promise<unknown> {
    const h = this.responses.get(response);
    if (!h || h.consumer !== 'none' || h.close || response.bodyUsed || response.body?.locked ||
        h.route.transport.response.kind !== 'original_file_bytes' || response.status !== 200) fail('native_response_not_saveable', 'save');
    if (suggestedName !== undefined && (!suggestedName || control.test(suggestedName) || /[\\/]/.test(suggestedName))) fail('native_filename_invalid', 'save');
    h.consumer = 'save';
    try {
      // Host owns the dialog, delivery authorization, streaming hash and atomic final rename.
      return await this.call('engine_response_save', { ...this.args(h), delivery_ref: deliveryRef, suggested_name: suggestedName },
        'save', 2147483647);
    } finally { await this.close(h, false); }
  }
  async mediaOpen(deliveryRef: unknown, purpose: string): Promise<{ media_handle: string; uri: string }> {
    if (this.invalid) fail('native_session_invalid', 'media');
    const value = await this.call<unknown>('engine_media_open', {
      generation: this.session.generation, delivery_ref: deliveryRef, purpose,
    }, 'media', this.session.limits.open_timeout_ms, false);
    if (!object(value) || !token(value.media_handle) || typeof value.uri !== 'string') fail('native_media_invalid', 'media');
    const uri = new URL(value.uri);
    if (!((uri.protocol === 'native-media:' && uri.hostname === 'localhost') ||
          (['http:', 'https:'].includes(uri.protocol) && uri.hostname === 'native-media.localhost')) ||
        uri.username || uri.password || uri.port || uri.search || uri.hash) fail('native_media_invalid', 'media');
    this.media.add(value.media_handle);
    return { media_handle: value.media_handle, uri: value.uri };
  }
  async mediaClose(handle: string): Promise<void> {
    if (!this.media.has(handle)) return;
    await this.call('engine_media_close', { generation: this.session.generation, media_handle: handle }, 'media', this.session.limits.open_timeout_ms, false);
    this.media.delete(handle);
  }
  async dispose(): Promise<void> {
    this.invalid = true;
    const results = await Promise.allSettled([
      ...[...this.handles].map(h => this.close(h, true)), ...[...this.media].map(h => this.mediaClose(h)),
    ]);
    if (results.some(r => r.status === 'rejected')) fail('native_cleanup_failed', 'cleanup', true);
  }
}
