import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const root = path.resolve(import.meta.dirname,'..');
const c=await import(pathToFileURL(path.join(root,'src/lib/candidates.ts')));
const m=await import(pathToFileURL(path.join(root,'src/domain/math.ts')));
const official=await import(pathToFileURL(path.join(root,'server/provider.ts')));
assert.deepEqual(c.parseCandidates('00127, 99999\n00127'),['00127','99999']);
assert.deepEqual(c.setOperation(['00000','00127'],['00127','99999'],'intersection'),['00127']);
assert.equal(m.mathFeatures('00127').sum,10);
assert.equal(m.mathFeatures('00127').pattern,'NNNPP');
assert.deepEqual(official.parseOfficial({success:true,value:{list:[{
  lotteryGameNum:'350133',lotteryDrawNum:'26277',lotteryDrawTime:'2026-10-18',lotteryDrawResult:'0 0 1 2 7'
}]}}),[{issue:'26277',date:'2026-10-18',number:'00127'}]);
assert.throws(()=>official.mergeDraws([
  {issue:'26277',date:'2026-10-18',number:'00127'},
  {issue:'26277',date:'2026-10-18',number:'99999'}
]));
console.log('Copied GitHub modules: 7 offline assertions passed');
