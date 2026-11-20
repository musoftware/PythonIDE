'use strict';
// stdio <-> socket relay for debug adapters served on a TCP port or a named pipe (radide/dap.py runs
// adapters on stdio):  node relay.js <host> <port>   |   node relay.js --pipe <path>
const net = require('net');
const args = process.argv.slice(2);
const sock = args[0] === '--pipe' ? net.connect(args[1]) : net.connect(parseInt(args[1], 10), args[0] || '127.0.0.1');
sock.on('connect', () => { process.stdin.pipe(sock); sock.pipe(process.stdout); });
sock.on('error', (e) => { process.stderr.write('relay: ' + e.message + '\n'); process.exit(1); });
sock.on('close', () => process.exit(0));
process.stdin.on('end', () => sock.end());
