import http from 'node:http';
// This fixture owns only an isolated loopback port and natural IPC cleanup.
const requestedPort = Number(process.argv[2] ?? '0');
if (!Number.isInteger(requestedPort) || requestedPort < 0 || requestedPort > 65535) throw new Error('Fixture port invalid');
const server = http.createServer((request, response) => {
  response.writeHead(200, { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store' });
  response.end('T10 self-owned sibling holder\n');
});
server.listen(requestedPort, '127.0.0.1', () => {
  process.send?.({ event: 'holder_ready', port: server.address().port, actual_pid: process.pid });
});
process.on('message', (message) => {
  if (message === 'close') server.close(() => process.disconnect?.());
});
