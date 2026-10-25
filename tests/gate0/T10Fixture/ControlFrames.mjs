// Exact test bytes; assertions will exercise the fixed real entry after I7 FINAL.
export const SHUTDOWN = Buffer.from('shutdown\n', 'ascii');
export const invalidFrames = Object.freeze([
  { name: 'Crlf', bytes: Buffer.from('shutdown\r\n', 'ascii') },
  { name: 'LeadingSpace', bytes: Buffer.from(' shutdown\n', 'ascii') },
  { name: 'TrailingSpace', bytes: Buffer.from('shutdown \n', 'ascii') },
  { name: 'Json', bytes: Buffer.from('{"command":"shutdown"}\n', 'ascii') },
  { name: 'CaseChanged', bytes: Buffer.from('SHUTDOWN\n', 'ascii') },
  { name: 'Empty', bytes: Buffer.from('\n', 'ascii') },
  { name: 'NonAscii', bytes: Buffer.from([0x73, 0x68, 0x75, 0x74, 0x64, 0x6f, 0x77, 0x6e, 0xc2, 0xa0, 0x0a]) },
  { name: 'OverlongWithLegalSuffix', bytes: Buffer.concat([Buffer.alloc(64, 0x78), SHUTDOWN]) },
  { name: 'Exactly64Unknown', bytes: Buffer.concat([Buffer.alloc(63, 0x78), Buffer.from('\n')]) },
]);
export const PARTIAL = Buffer.from('shutdown', 'ascii');
