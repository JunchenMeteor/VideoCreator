export const NATIVE_FRAME_HEADER_BYTES = 24;
export const NATIVE_MAX_CHUNK_BYTES = 65536;
const MAX_UINT64 = (1n << 64n) - 1n;

export function decimal(value: unknown): bigint {
  if (typeof value !== 'string' || !/^(0|[1-9][0-9]*)$/.test(value)) throw new Error('native_offset_invalid');
  const number = BigInt(value);
  if (number > MAX_UINT64) throw new Error('native_offset_invalid');
  return number;
}

export function encodeNativeFrame(offset: bigint, payload: Uint8Array, eof = false): Uint8Array {
  if (offset < 0n || offset > MAX_UINT64 || payload.length > NATIVE_MAX_CHUNK_BYTES || (eof && payload.length) || (!eof && !payload.length) || offset + BigInt(payload.length) > MAX_UINT64) throw new Error('native_frame_invalid');
  const frame = new Uint8Array(NATIVE_FRAME_HEADER_BYTES + payload.length);
  const view = new DataView(frame.buffer);
  view.setUint8(0, 1); view.setUint8(1, eof ? 1 : 0); view.setUint16(2, 0, true);
  view.setBigUint64(4, offset, true); view.setUint32(12, payload.length, true);
  view.setBigUint64(16, offset + BigInt(payload.length), true); frame.set(payload, 24);
  return frame;
}

export function decodeNativeFrame(raw: ArrayBuffer | Uint8Array, expectedOffset: bigint): { payload: Uint8Array; eof: boolean; nextOffset: bigint } {
  const frame = raw instanceof Uint8Array ? raw : new Uint8Array(raw);
  if (frame.byteLength < 24) throw new Error('native_frame_invalid');
  const view = new DataView(frame.buffer, frame.byteOffset, frame.byteLength);
  const kind = view.getUint8(1), length = view.getUint32(12, true), next = view.getBigUint64(16, true);
  if (view.getUint8(0) !== 1 || kind > 1 || view.getUint16(2, true) !== 0 || view.getBigUint64(4, true) !== expectedOffset || length > NATIVE_MAX_CHUNK_BYTES || length + 24 !== frame.byteLength || next !== expectedOffset + BigInt(length) || (kind === 1 && length !== 0) || (kind === 0 && length === 0)) throw new Error('native_frame_invalid');
  return { payload: frame.slice(24), eof: kind === 1, nextOffset: next };
}
