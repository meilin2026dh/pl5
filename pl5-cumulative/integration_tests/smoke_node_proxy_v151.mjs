import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {handleEsseProxy} from '../github_overlay/server/esseProxy.mjs';
const server=createServer((req,res)=>handleEsseProxy(req,res));
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
try {
 const {port}=server.address();
 const res=await fetch(`http://127.0.0.1:${port}/api/esse/status`);
 assert.equal(res.status,200);
 const data=await res.json();
 assert.equal(data.schema,'pl5-live-status-v151');
 assert.equal(data.bridge.read_only,true);
 const wrong=await fetch(`http://127.0.0.1:${port}/api/esse/status`,{method:'POST'});
 assert.equal(wrong.status,405);
 process.stdout.write('V1.5.1 Node -> Python bridge smoke passed\n');
} finally {
 await new Promise(resolve=>server.close(resolve));
}
