//! Private framing only; these bytes never change the HTTP payload.
pub const CHUNK: usize = 65_536;
pub const HEADER: usize = 24;

pub fn decimal(input: &str) -> Result<u64, &'static str> {
    if input.is_empty() || (input.len() > 1 && input.starts_with('0')) || !input.bytes().all(|c| c.is_ascii_digit()) {
        return Err("native_offset_invalid");
    }
    input.parse().map_err(|_| "native_offset_invalid")
}
pub struct Frame<'a> { pub offset: u64, pub next: u64, pub eof: bool, pub payload: &'a [u8] }
pub fn decode(raw: &[u8]) -> Result<Frame<'_>, &'static str> {
    if raw.len() < HEADER || raw[0] != 1 || raw[1] > 1 || raw[2..4] != [0, 0] { return Err("native_frame_invalid"); }
    let offset = u64::from_le_bytes(raw[4..12].try_into().map_err(|_| "native_frame_invalid")?);
    let length = u32::from_le_bytes(raw[12..16].try_into().map_err(|_| "native_frame_invalid")?) as usize;
    let next = u64::from_le_bytes(raw[16..24].try_into().map_err(|_| "native_frame_invalid")?);
    let eof = raw[1] == 1;
    if length > CHUNK || raw.len() != HEADER + length || offset.checked_add(length as u64) != Some(next) ||
        (eof && length != 0) || (!eof && length == 0) { return Err("native_frame_invalid"); }
    Ok(Frame { offset, next, eof, payload: &raw[HEADER..] })
}
pub fn encode(offset: u64, data: &[u8], eof: bool) -> Result<Vec<u8>, &'static str> {
    if data.len() > CHUNK || (eof && !data.is_empty()) || (!eof && data.is_empty()) { return Err("native_frame_invalid"); }
    let next = offset.checked_add(data.len() as u64).ok_or("native_frame_invalid")?;
    let mut frame = Vec::with_capacity(HEADER + data.len());
    frame.extend([1, u8::from(eof), 0, 0]); frame.extend(offset.to_le_bytes());
    frame.extend((data.len() as u32).to_le_bytes()); frame.extend(next.to_le_bytes()); frame.extend(data);
    Ok(frame)
}
