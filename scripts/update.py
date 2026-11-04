#!/usr/bin/env python3
"""SMARTMoraga election updater. Fail closed: never publish partially parsed votes.

Uses only Python standard library. Designed for GitHub Actions or local use.
"""
from __future__ import annotations
import argparse
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
import urllib.parse
import html
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'data.json'
BASE='https://results.enr.clarityelections.com/CA/Contra_Costa/127405'
FIRST_VERSION='385037'  # only fallback when version-file inaccessible, never interpreted as latest
HEADER={'User-Agent':'Mozilla/5.0 (compatible; SMARTMoragaElectionWidget/1.0; +https://smartmoraga.com)', 'Accept':'application/json,application/xml,text/plain,*/*'}

RACES=[
 {'id':'council','title':'Moraga Town Council','subtitle':'Town of Moraga · Vote for up to 2','seats':2,'type':'candidate', 'expected':{'woehleke','hillis','mapel','carman'}},
 {'id':'measure-w','title':'Measure W','subtitle':'Acalanes Union High School District · Parcel tax','seats':1,'type':'measure', 'expected':{'yes','no'}},
 {'id':'mofd','title':'MOFD Division 3','subtitle':'Moraga-Orinda Fire District · Division 3','seats':1,'type':'candidate','expected':{'donnelly','cohn'}}]

def get(url,timeout=18,max_bytes=8_000_000,allow_html=False):
    req=urllib.request.Request(url,headers=HEADER)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        content=response.read(max_bytes+1)
        if len(content)>max_bytes: raise ValueError('Source too large')
        if response.status==202 and not content: raise ValueError('HTTP 202 empty body (Clarity bot protection)')
        if not allow_html and content.lstrip()[:20].lower().startswith((b'<!doctype html',b'<html')):
            raise ValueError('HTML received instead of election data')
        sample=content[:1024].lower()
        if b'javascript is disabled' in sample or (b'robot' in sample and b'javascript' in sample):
            raise ValueError('HTML bot-verification page returned instead of election data')
        return content

def compact(s):return re.sub(r'[^a-z0-9]+',' ',str(s or '').lower()).strip()

def identify_contest(title):
    t=compact(title)
    if 'moraga' in t and ('council' in t or 'town' in t) and not ('orinda' in t or 'fire' in t):return 'council'
    if ('measure w' in t or re.search(r'\bmeasure\s+w\b',t)) and ('acalanes' in t or 'union high' in t or len(t)<35):return 'measure-w'
    if ('fire' in t or 'mofd' in t) and ('division 3' in t or 'div 3' in t):return 'mofd'
    return None

def canonical_name(name,rid):
    n=compact(name)
    if rid=='measure-w':
        if re.fullmatch(r'yes( votes)?',n):return 'YES'
        if re.fullmatch(r'no( votes)?',n):return 'NO'
        return None
    lookup={'woehleke':'Steven Woehleke','hillis':'Kerry Hillis','mapel':'Alexis I. Mapel','carman':'Bill Carman',
            'donnelly':'John Donnelly','cohn':'Steve Cohn'}
    for key,label in lookup.items():
        if re.search(r'\b'+key+r'\b',n) and ((rid=='council' and key in RACES[0]['expected']) or (rid=='mofd' and key in RACES[2]['expected'])):
            return label
    return None

def safe_int(v):
    if isinstance(v,bool) or v is None:raise ValueError('Missing votes')
    if isinstance(v,(float,int)) and v>=0 and int(v)==v:return int(v)
    s=str(v).replace(',','').strip()
    if not re.fullmatch(r'\d+',s):raise ValueError(f'Not a vote count: {v!r}')
    return int(s)

def assemble(extracted,source,reported_at=None,version=None):
    races=[]
    for r in RACES:
        choices=extracted.get(r['id'])
        if not choices:raise ValueError(f"Missing contest {r['id']}")
        names={canonical_name(k,r['id']):safe_int(v) for k,v in choices.items()}
        if None in names or len(names)!=len(r['expected']):raise ValueError(f"Unexpected choices in {r['id']}: {names}")
        observed={compact(k).split()[-1] for k in names}
        if observed!=r['expected']:raise ValueError(f"Missing candidate in {r['id']}: {observed}")
        total=sum(names.values())
        if total<=0:raise ValueError(f"Zero votes in {r['id']} - no updated election report")
        race={k:v for k,v in r.items() if k not in ('expected',)}
        race['choices']=[{'name':name,'votes':count,'percent':round(count*100/total,2)} for name,count in sorted(names.items(),key=lambda x:-x[1])]
        races.append(race)
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    return {'election':'2026-11-03','certified':False,'sample':False,'reported_at':reported_at,'reported_at_text':'Source did not expose an independently verified timestamp' if not reported_at else None,'fetched_at':now,'source_url':source,'version':version,'races':races}

def parse_xml(blob):
    xml=ET.fromstring(blob)
    result={}
    for contest in xml.iter():
        if contest.tag.rsplit('}',1)[-1].lower()!='contest':continue
        attrs={k.lower():v for k,v in contest.attrib.items()}
        rid=identify_contest(attrs.get('text') or attrs.get('name') or attrs.get('title'))
        if not rid:continue
        found={}
        for choice in contest:
            if choice.tag.rsplit('}',1)[-1].lower()!='choice':continue
            d={k.lower():v for k,v in choice.attrib.items()}
            n=d.get('text') or d.get('name')
            v=d.get('totalvotes') or d.get('votes')
            if n is not None and v is not None:found[n]=v
        if found:
            if rid in result:raise ValueError('Duplicate matched contest '+rid)
            result[rid]=found
    return result

def extract_zip(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        files=[f for f in archive.namelist() if f.lower().endswith('.xml') and not f.startswith('__MACOSX/')]
        if not files:raise ValueError('No XML in Clarity detail ZIP')
        # A single detail report should contain all contests.
        for name in files:
            if archive.getinfo(name).file_size>20_000_000:continue
            parsed=parse_xml(archive.read(name))
            if len(parsed)==3:return parsed
        raise ValueError('XML does not contain all three complete contests')

def parse_json(blob):
    doc=json.loads(blob)
    result={}
    # Clarity's real sum.json schema, confirmed in browser by the website owner.
    # Contests holds one entry per race; C=name, CH=candidate labels, V=votes.
    if isinstance(doc,dict) and isinstance(doc.get('Contests'),list):
        for contest in doc['Contests']:
            if not isinstance(contest,dict):continue
            rid=identify_contest(contest.get('C'))
            if not rid:continue
            labels,votes=contest.get('CH'),contest.get('V')
            if not isinstance(labels,list) or not isinstance(votes,list) or len(labels)!=len(votes):
                raise ValueError('Clarity CH/V mismatch for '+str(contest.get('C')))
            rows={}
            for name,count in zip(labels,votes):
                if not isinstance(name,str) or name in rows:
                    raise ValueError('Clarity candidate name invalid or duplicated')
                rows[name]=safe_int(count)
            if rid in result:raise ValueError('Duplicate Clarity contest '+rid)
            result[rid]=rows
        if result:return result
    def traverse(node,depth=0):
        if depth>9:return
        if isinstance(node,dict):
            name=next((node[k] for k in ('name','title','text','contestName','contest_name') if isinstance(node.get(k),str)),None)
            rid=identify_contest(name) if name else None
            if rid:
                choices=next((node[k] for k in ('choices','candidates','options','results') if isinstance(node.get(k),list)),None)
                if choices:
                    rows={}
                    for ch in choices:
                        if not isinstance(ch,dict):continue
                        ch_name=next((ch[k] for k in ('name','title','text','candidate','choiceName') if isinstance(ch.get(k),str)),None)
                        count=next((ch[k] for k in ('votes','totalVotes','total_votes','voteCount','count') if k in ch),None)
                        if ch_name is not None and count is not None:rows[ch_name]=count
                    if rows:
                        if rid in result and result[rid]!=rows:raise ValueError('Multiple different matches: '+rid)
                        result[rid]=rows
            for v in node.values():traverse(v,depth+1)
        elif isinstance(node,list):
            for v in node:traverse(v,depth+1)
    traverse(doc)
    return result

def discover_version():
    try:
        v=get(BASE+'/current_ver.txt',timeout=15).decode('utf-8').strip()
        if re.fullmatch(r'\d{4,12}',v):return v
        raise ValueError('Unexpected current_ver.txt content')
    except Exception as e:
        print('Current version lookup failed:',e,file=sys.stderr)
        return FIRST_VERSION

def load_clarity():
    version=discover_version()
    urls=[(f'{BASE}/{version}/json/sum.json',parse_json),(f'{BASE}/{version}/json/en/summary.json',parse_json),(f'{BASE}/{version}/json/details.json',parse_json),
          (f'{BASE}/{version}/reports/detailxml.zip',extract_zip)]
    failures=[]
    for url,fn in urls:
        try:
            results=fn(get(url))
            data=assemble(results,url,version=version)
            print(f'OK: {url}',file=sys.stderr)
            return data
        except Exception as e:failures.append(f'{url}: {e}')
    raise RuntimeError('No complete verified data from Clarity:\n'+'\n'.join(failures))

PDF_FALLBACK="https://www.contracostavote.gov/wp-content/uploads/ElectionSummaryReportRPT-53.pdf"
COUNTY_ELECTION="https://www.contracostavote.gov/election/november-3-2026-general-election/"

def discover_pdf_urls():
    urls=[]
    try:
        page=get(COUNTY_ELECTION,timeout=15,max_bytes=2_000_000,allow_html=True).decode("utf-8",errors="ignore")
        page=re.sub(r"<!--.*?-->","",page,flags=re.S)
        for link in re.findall(r'href="([^"]+)',page,re.I):
            href=html.unescape(link)
            if "ElectionSummaryReportRPT" in href and ".pdf" in href:
                urls.append(urllib.parse.urljoin(COUNTY_ELECTION,href))
    except Exception as e:
        print("County results landing page unavailable:",e,file=sys.stderr)
    urls.append(PDF_FALLBACK)
    def file_number(url):
        match=re.search(r"-(\d+)\.pdf",url,re.I)
        return int(match.group(1)) if match else -1
    return sorted({url for url in urls if url.startswith("https://")},key=file_number,reverse=True)[:12]

def load_county_pdf():
    import pdf_extract
    failures=[]
    for url in discover_pdf_urls():
        try:
            content=get(url,timeout=25,max_bytes=15_000_000)
            results,reported_at=pdf_extract.parse_report(content)
            data=assemble(results,url,reported_at=reported_at)
            print("Verified official PDF:",url,reported_at,file=sys.stderr)
            return data
        except Exception as e:
            failures.append(url+": "+str(e))
    raise RuntimeError("No valid official county PDF: "+"; ".join(failures))

def load_preferred():
    try:return load_county_pdf()
    except Exception as e:print("County PDF unavailable; trying Clarity:",e,file=sys.stderr)
    return load_clarity()

def validate_seed(path):
    doc=json.loads(Path(path).read_text())
    if doc.get("election")!="2026-11-03":raise ValueError("Wrong election")
    mapping={r["id"]:{c["name"]:c["votes"] for c in r["choices"]} for r in doc["races"]}
    return assemble(mapping,doc["source_url"],doc.get("reported_at"),doc.get("version"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input-json',type=Path,help='Import already verified normalized data (optional manual fallback)')
    ap.add_argument('--test-xml',type=Path,help='Use a local Clarity XML fixture for offline testing')
    ap.add_argument('--dry-run',action='store_true',help='Validate and print without overwriting docs/data.json')
    args=ap.parse_args()
    try:
        if args.input_json:data=validate_seed(args.input_json)
        elif args.test_xml:data=assemble(parse_xml(args.test_xml.read_bytes()),'local-fixture')
        else:data=load_preferred()
        if args.dry_run:print(json.dumps(data,indent=2));return 0
        previous=json.loads(OUT.read_text()) if OUT.exists() else {}
        if previous.get('reported_at') and data.get('reported_at') and not previous.get('sample'):
            if dt.datetime.fromisoformat(data['reported_at']) < dt.datetime.fromisoformat(previous['reported_at']):
                raise ValueError('Older election report rejected; keeping newer published snapshot')
        # A same-version recheck should not churn GitHub commits with fetched_at changes.
        old_tallies={r['id']:[(c['name'],c['votes']) for c in r['choices']] for r in previous.get('races',[])}
        new_tallies={r['id']:[(c['name'],c['votes']) for c in r['choices']] for r in data['races']}
        if old_tallies==new_tallies and previous.get('reported_at')==data.get('reported_at') and not previous.get('sample') and previous.get('certified')==data['certified']:
            print('No changed results; keeping existing file');return 0
        if previous.get('reported_at') and not data.get('reported_at'):
            # The new API response lacked an as-of timestamp. Do NOT reuse stale report time.
            data['reported_at_text']='Clarity feed did not provide a verified as-of timestamp'
        OUT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
        print('Published updated verified totals to',OUT)
        return 0
    except Exception as e:
        print('No publication; last verified results preserved. Reason:',e,file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
