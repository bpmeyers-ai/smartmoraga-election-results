const test = require('node:test');
const assert = require('node:assert/strict');
const deploy = require('../scripts/deploy_pages.cjs');
function setup(responses) {
  const calls = [], outputs = {}, sleeps = [];
  return {calls, outputs, sleeps, args: {
    artifactId: '123', context: {repo: {owner:'owner',repo:'repo'},sha:'sha'},
    core: {getIDToken: async ()=>'test-token',setSecret(){},info(){},warning(){},setOutput(k,v){outputs[k]=v;}},
    sleep: async ms=>sleeps.push(ms),createAttempts:2,pollAttempts:2,
    github: {request:async (route, body)=> {calls.push({route,body}); const response=responses.shift(); if(response instanceof Error)throw response; return {data:response};}}
  }};
}
function error(status,message) {return Object.assign(new Error(message),{status});}
test('waits on collision, then verifies success',async()=>{
  const s=setup([error(400,'Deployment request failed due to in progress deployment'),{id:'ours',page_url:'https://results.smartmoraga.com'}, {status:'deployment_in_progress'},{status:'succeed'}]);
  await deploy(s.args); assert.deepEqual(s.sleeps,[15000,5000,5000]); assert.equal(s.outputs.page_url,'https://results.smartmoraga.com');
});
test('does not retry other errors',async()=>{
  for(const e of [error(403,'denied'),error(400,'invalid artifact')]) {
    const s=setup([e]); await assert.rejects(deploy(s.args)); assert.equal(s.calls.length,1);
  }
});
test('collision retry is bounded and never cancels other deployment',async()=>{
  const e=error(400,'due to in progress deployment'); const s=setup([e,e]);
  await assert.rejects(deploy(s.args)); assert.equal(s.calls.length,2); assert.equal(s.sleeps.length,1);
});
test('timeout fails and cancels only own deployment',async()=>{
  const s=setup([{id:'ours'},{status:'deployment_in_progress'},{status:'deployment_in_progress'},{}]);
  await assert.rejects(deploy(s.args),/Timed out/); assert.equal(s.calls.at(-1).body.deployment_id,'ours'); assert.match(s.calls.at(-1).route,/cancel$/); assert.deepEqual(s.outputs,{});
});
test('terminal failure is not reported as success',async()=>{
  const s=setup([{id:'ours'},{status:'deployment_content_failed'},{}]);
  await assert.rejects(deploy(s.args),/deployment_content_failed/); assert.deepEqual(s.outputs,{});
});
