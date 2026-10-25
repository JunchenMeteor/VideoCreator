import http from 'node:http';
const server = http.createServer((request, response) => { response.writeHead(200, { 'Content-Type': 'text/plain' }); response.end('T9 owned loopback child\n'); });
server.listen(0, '127.0.0.1', () => process.send({ event: 'ready', port: server.address().port, actual_pid: process.pid }));
process.on('message', (message) => { if (message === 'close') server.close(() => { process.disconnect(); }); });
