/* INTERNAL/AI_AUTHORED V3.8.24: warm paired runtime benchmark of the
frozen V3.8.23 cubic/grouped implementations. No new filtering rule.
Every one of the ten existing profiles at n=10 is included, without
selecting favorable results. Input construction and source loading are
excluded; grouping/sorting, allocations and full search are included.
Three warmups and seven alternating-order timed pairs per profile.
Exact results and work counts checked outside timing; no timing gate.
The source loader removes only the frozen final CLI print invocation.
No cold-start, peak-memory, end-to-end or cross-platform speed claim.
*/
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const crypto=require('node:crypto');
const os=require('node:os');
const assert=require('node:assert/strict');
const sourceBlob='fea49f50bd55e72cc37c4535a9da66b52a3e232b';
const raw=fs.readFileSync(path.join(__dirname,'quotient_grouped_order_v3823.js'));
// Git uses LF blobs; Windows checkout may translate CRLF.
const source=raw.toString('utf8').replace(/\r\n/g,'\n');
const bytes=Buffer.from(source,'utf8');
const hash=crypto.createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex');
assert.equal(hash,sourceBlob);
const suffix="console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',audit:audit()}));\n";
assert.ok(source.endsWith(suffix));
const {edges,profiles,cubic,grouped}=vm.compileFunction(source.slice(0,-suffix.length)+'\nreturn {edges,profiles,cubic,grouped};',[])();
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
const n=10,e=edges(n),rows=[];
const expected=[[21400,1980],[21400,1980],[0,1980],[21501,84420],[21498,11880],[50,3954],[637,1980],[1278,38858],[67,40526],[58,38752]];
for(const p of profiles(n,e)){
  const [value,checks]=expected[rows.length];
  function verify(name,r){assert.equal(r.value,value);assert.equal(r.checks,name==='cubic'?84420:checks);}
  const f={cubic,grouped};
  for(let i=0;i<3;i++)for(const name of ['cubic','grouped'])verify(name,f[name](n,e,p));
  const trials=[];
  for(let i=0;i<7;i++){
    const order=(i+rows.length)%2===0?['cubic','grouped']:['grouped','cubic'];
    const t={order};
    for(const name of order){const begin=process.hrtime.bigint();const r=f[name](n,e,p);t[name+'_ns']=Number(process.hrtime.bigint()-begin);verify(name,r);}
    trials.push(t);
  }
  rows.push({profile:p.name,optimum:value,cubic_checks:84420,grouped_checks:checks,trials,median_cubic_ns:median(trials.map(t=>t.cubic_ns)),median_grouped_ns:median(trials.map(t=>t.grouped_ns)),median_paired_speedup:median(trials.map(t=>t.cubic_ns/t.grouped_ns))});
}
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob:sourceBlob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,n,rows},null,2));
