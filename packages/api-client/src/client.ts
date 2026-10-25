import type { components, operations } from './schema.d.ts';
import { ROUTES, type RouteKey } from './routes.generated.ts';
import { NativeTransportV1, type NativeBody } from './native.ts';

type Operation<K extends RouteKey> = operations[(typeof ROUTES)[K]['operationId']];
type Parameter<K extends RouteKey, Kind extends string> = Operation<K> extends { parameters: infer P }
  ? Kind extends keyof P ? NonNullable<P[Kind]> : never : never;
type PathArgument<K extends RouteKey> = [Parameter<K, 'path'>] extends [never]
  ? { path?: never } : { path: Parameter<K, 'path'> };
type Body<K extends RouteKey> = Operation<K> extends { requestBody?: { content: infer C } }
  ? C extends { 'application/json': infer J } ? J
    : C extends Record<string, unknown> ? ArrayBuffer | Uint8Array | Blob : never : never;
type BodyArgument<K extends RouteKey> = [Body<K>] extends [never] ? { body?: never }
  : Operation<K> extends { requestBody: unknown } ? { body: Body<K> } : { body?: Body<K> };
type SuccessContent<K extends RouteKey> = Operation<K> extends { responses: infer R }
  ? { [S in keyof R]: `${S & (string | number)}` extends `2${string}`
      ? R[S] extends { content: infer C } ? C : never : never }[keyof R] : never;
type JsonSuccess<K extends RouteKey> = SuccessContent<K> extends infer C
  ? C extends { 'application/json': infer J } ? J : never : never;
export type RequestArguments<K extends RouteKey> = PathArgument<K> & BodyArgument<K> & {
  query?: Parameter<K, 'query'>;
  headers?: Readonly<Record<string, string>>;
  signal?: AbortSignal;
};
export type ApiResponse<K extends RouteKey> = {
  status: number;
  headers: Headers;
  data: [JsonSuccess<K>] extends [never] ? ArrayBuffer | string | undefined : JsonSuccess<K> | undefined;
};
export type ErrorEnvelope = components['schemas']['ErrorEnvelope'];
export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;
  readonly headers: Headers;
  constructor(status: number, payload: unknown, headers: Headers) {
    // Keep transport/auth secrets out of error text. The backend public payload is separately available.
    super(`Engine API returned HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
    this.headers = headers;
  }
}
type TransportOptions = {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
};
export type ApiClientOptions = (TransportOptions & ({
  mode?: 'direct';
  getToken: () => string | Promise<string>;
  trustedOrigin?: never;
} | {
  mode: 'managed-proxy';
  // From the local host's ready message or the already trusted workbench page.
  // This is a routing constraint, never an authorization credential.
  trustedOrigin: string;
  getToken?: never;
})) | {
  mode: 'native';
  nativeTransport: NativeTransportV1;
  baseUrl?: never;
  getToken?: never;
  trustedOrigin?: never;
  fetch?: never;
};
export function createApiClient(options: ApiClientOptions) {
  const mode = options.mode ?? 'direct';
  const native = mode === 'native' ? options as Extract<ApiClientOptions, { mode: 'native' }> : undefined;
  if (native && (!(native.nativeTransport instanceof NativeTransportV1) ||
      ['baseUrl', 'getToken', 'trustedOrigin', 'fetch'].some(k => k in native))) {
    throw new Error('Native transport uses only the real private host bridge');
  }
  const base = native ? undefined : new URL(options.baseUrl!);
  if (base && (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash || base.pathname !== '/')) {
    throw new Error('Engine baseUrl must be an HTTP(S) origin without credentials, query or path');
  }
  if (mode !== 'direct' && mode !== 'managed-proxy' && mode !== 'native') throw new Error('Unknown engine connection mode');
  if (mode === 'managed-proxy') {
    const trusted = new URL(options.trustedOrigin!);
    if (base!.protocol !== 'http:' || base!.hostname !== '127.0.0.1' || options.getToken !== undefined ||
        trusted.href !== base!.href || options.trustedOrigin !== base!.origin) {
      throw new Error('Managed proxy requires the exact trusted loopback workbench origin');
    }
    if (typeof globalThis.location !== 'undefined' && globalThis.location.origin !== base!.origin) {
      throw new Error('Managed proxy must belong to the current workbench origin');
    }
  } else if (mode === 'direct' && typeof options.getToken !== 'function') {
    throw new Error('Direct engine connection requires a trusted session token provider');
  }
  const fetcher = options.fetch ?? globalThis.fetch;
  async function requestRaw<K extends RouteKey>(key: K, args: RequestArguments<K>): Promise<Response> {
    if (!Object.hasOwn(ROUTES, key)) throw new Error('Unknown generated engine operation');
    const route = ROUTES[key];
    if (native) {
      const headers = { ...args.headers };
      const payload: unknown = args.body;
      let body: NativeBody | undefined;
      if (payload !== undefined) {
        if (route.requestMedia.some(media => media === 'application/json')) {
          if (!Object.keys(headers).some(h => h.toLowerCase() === 'content-type')) headers['Content-Type'] = 'application/json';
          const serialized = JSON.stringify(payload);
          if (serialized === undefined) throw new Error('Engine JSON operation requires a JSON value');
          body = new TextEncoder().encode(serialized);
        } else if (payload instanceof ArrayBuffer || payload instanceof Uint8Array || payload instanceof Blob) {
          if (!route.requestMedia.length) throw new Error('OpenAPI does not declare a request body for this operation');
          if (!Object.keys(headers).some(h => h.toLowerCase() === 'content-type')) headers['Content-Type'] = route.requestMedia[0] === '*/*' ? 'application/octet-stream' : route.requestMedia[0];
          body = payload;
        } else throw new Error('Engine binary operation requires Blob, Uint8Array or ArrayBuffer');
      }
      return native.nativeTransport.request(route.operationId, {
        path: args.path as Record<string, unknown> | undefined,
        query: args.query as Record<string, unknown> | undefined,
        headers, body, signal: args.signal,
      });
    }
    const pathValues = (args.path ?? {}) as Record<string, unknown>;
    const template = route.template.replace(/\{([^}]+)\}/g, (_, name: string) => {
      const value = pathValues[name];
      if (value === undefined || value === null) throw new Error('Missing engine path parameter');
      return encodeURIComponent(String(value));
    });
    const url = new URL(template, base);
    if (url.origin !== base!.origin || (mode === 'managed-proxy' && !url.pathname.startsWith('/api/'))) {
      throw new Error('Generated operation is outside the trusted engine connection');
    }
    for (const [name, value] of Object.entries(args.query ?? {})) {
      if (value === undefined || value === null) continue;
      for (const item of Array.isArray(value) ? value : [value]) url.searchParams.append(name, String(item));
    }
    const headers = new Headers(args.headers);
    for (const name of ['authorization', 'host', 'cookie', 'origin', 'sec-fetch-site', 'x-video-creator-client']) {
      if (headers.has(name)) throw new Error('Authentication and host headers are controlled by the engine connection');
    }
    if (mode === 'managed-proxy') {
      headers.set('X-Video-Creator-Client', 'workbench');
    } else {
      const token = await options.getToken!();
      if (!token || /[\r\n]/.test(token)) throw new Error('Missing or invalid engine session token');
      headers.set('Authorization', `Bearer ${token}`);
    }
    let body: BodyInit | undefined;
    const payload: unknown = args.body;
    if (payload !== undefined) {
      if (route.requestMedia.some(media => media === 'application/json')) {
        headers.set('Content-Type', 'application/json');
        body = JSON.stringify(payload);
      } else if (payload instanceof ArrayBuffer || payload instanceof Uint8Array || payload instanceof Blob) {
        if (!route.requestMedia.length) throw new Error('OpenAPI does not declare a request body for this operation');
        if (!headers.has('Content-Type')) headers.set('Content-Type', route.requestMedia[0] === '*/*' ? 'application/octet-stream' : route.requestMedia[0]);
        body = payload instanceof Uint8Array ? new Blob([new Uint8Array(payload)]) : payload;
      } else {
        throw new Error('Engine binary operation requires Blob, Uint8Array or ArrayBuffer');
      }
    }
    return fetcher(url, { method: route.method, headers, body, signal: args.signal,
      credentials: 'omit', redirect: 'error' });
  }
  async function request<K extends RouteKey>(key: K, args: RequestArguments<K>): Promise<ApiResponse<K>> {
    const response = await requestRaw(key, args);
    const contentType = (response.headers.get('content-type') ?? '').split(';')[0].trim().toLowerCase();
    let data: unknown;
    if (response.status === 204 || response.status === 304) data = undefined;
    else if (contentType === 'application/json' || contentType.endsWith('+json')) data = await response.json();
    else if (contentType.startsWith('text/')) data = await response.text();
    else data = await response.arrayBuffer();
    if (!response.ok && response.status !== 304) throw new ApiError(response.status, data, response.headers);
    return { status: response.status, headers: response.headers, data: data as ApiResponse<K>['data'] };
  }
  // requestRaw leaves every body (including errors, 206 and 304) untouched.
  // The caller owns stream consumption, status handling and complete-object hashing.
  return { request, requestRaw, routes: ROUTES };
}
