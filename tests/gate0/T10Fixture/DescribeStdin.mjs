import fs from 'node:fs';
import net from 'node:net';
// Observer only: never admits production input or launches product resources.
let metadata;
try {
  const stat = fs.fstatSync(0);
  metadata = { regular_file: stat.isFile(), character_device: stat.isCharacterDevice(), fifo: stat.isFIFO(), socket: stat.isSocket() };
} catch { metadata = { observed_error: 'fd0_inspection_failed' }; }
console.log(JSON.stringify({ event: 'fixture_stdin_observation', stdin_socket_instance: process.stdin instanceof net.Socket, stdin_is_tty: process.stdin.isTTY === true, stdin_readable: process.stdin.readable, fd0: metadata }));
process.stdin.destroy();
