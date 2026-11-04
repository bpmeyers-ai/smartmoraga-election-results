'use strict';
const $ = id => document.getElementById(id);
const nf = new Intl.NumberFormat('en-US');
const percent = n => `${Number(n).toFixed(2)}%`;
const sourceFallback = 'https://www.contracostavote.gov/election/november-3-2026-general-election/';
function el(tag,cls,text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=String(text);return node;}
function resultRow(c, rank, maxVotes, mode){
  const node=el('div','candidate'); const hd=el('div','candidate-head');
  hd.append(el('span','candidate-name',c.name)); const votes=el('span','candidate-votes',percent(c.percent));
  votes.append(el('small','',`(${nf.format(c.votes)})`));hd.append(votes);node.append(hd);
  const bg=el('div','bar');const fill=el('div','bar-fill'+(mode==='measure'?(c.name.toLowerCase()==='yes'?' yes':' no'):(rank===0?' leading':'')));
  // Scale all bar widths consistently to 100% of contest votes.
  fill.style.width=`${Math.min(100,Math.max(0,c.percent))}%`;bg.append(fill);node.append(bg);return node;
}
function raceBlock(r){
 const root=el('article','race');const heading=el('div','race-title');const wrap=el('div');wrap.append(el('h2','',r.title),el('div','race-desc',r.subtitle));heading.append(wrap,el('span','tag',r.seats===2?'2 seats':r.type==='measure'?'2/3 required':'1 seat'));root.append(heading);
 const arr=[...r.choices].sort((a,b)=>b.votes-a.votes);const maxVotes=Math.max(...arr.map(c=>c.votes),1);
 arr.forEach((c,i)=>root.append(resultRow(c,i,maxVotes,r.type)));
 const note=el('div','summary-line');
 if(r.type==='measure'){
   const yes=arr.find(c=>/^yes$/i.test(c.name));
   if(yes){const diff=yes.percent-100*2/3; note.textContent=`YES is ${Math.abs(diff).toFixed(2)} percentage points ${diff>=0?'above':'below'} the 66.67% passage threshold. This is not a final determination.`;}
 }else if(r.seats===2&&arr.length>=3){note.textContent=`Second-seat margin: ${arr[1].name} leads ${arr[2].name} by ${nf.format(arr[1].votes-arr[2].votes)} votes.`;}
 else if(arr.length>=2){note.textContent=`Leading margin: ${arr[0].name} leads by ${nf.format(arr[0].votes-arr[1].votes)} votes.`;}
 if(note.textContent)root.append(note);
 if(r.precincts_text)root.append(el('div','footnote',r.precincts_text));
 return root;
}
function show(data){
 const demo=Boolean(data.sample);
 $('status-label').textContent=data.certified?'Certified':demo?'First report / sample':'Unofficial results';
 document.querySelector('.status-dot').style.background=data.certified?'#2b8a6e':demo?'#c19135':'#db9d2a';
 const timestamp=data.reported_at?new Date(data.reported_at):null;
 $('stamp').textContent=`County report: ${timestamp&&!isNaN(timestamp)?new Intl.DateTimeFormat('en-US',{timeZone:'America/Los_Angeles',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(timestamp):data.reported_at_text||'Report time not independently verified'}`;
 $('source-detail').textContent=demo?'First-report baseline for testing · Not a live result':`Last successful data check: ${data.fetched_at?new Intl.DateTimeFormat('en-US',{timeZone:'America/Los_Angeles',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(new Date(data.fetched_at))+' PT':'Unavailable'}`;
 $('source-link').href=(/^https:\/\//.test(data.source_url||'')?data.source_url:sourceFallback);
 const section=$('races');section.replaceChildren();for(const r of data.races||[])section.append(raceBlock(r));
 if(!data.races?.length){$('error').hidden=false;$('error').textContent='No verified results are currently available.';}
 // Tell Wix/other embedding parent the content height when possible.
 const resize=()=>{try{parent.postMessage({type:'smartmoraga-election-height',height:document.documentElement.scrollHeight},'*')}catch(_){}};
 if('ResizeObserver' in window)new ResizeObserver(resize).observe(document.body);resize();
}
async function load(){try{const res=await fetch(`data.json?t=${Date.now()}`,{cache:'no-store'});if(!res.ok)throw Error(`HTTP ${res.status}`);const data=await res.json();show(data);}catch(e){$('status-label').textContent='Unavailable';$('error').hidden=false;$('error').textContent='Could not load the results data. Please use the official source link.';}}
load();
// Reload data while an election-night page remains open; the backend checks separately.
setInterval(load, 5 * 60 * 1000);
