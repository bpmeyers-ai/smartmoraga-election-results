#!/usr/bin/env python3
"""One-time, bounded public election source diagnostics for GitHub Actions."""
import urllib.request, urllib.error, io
URLS=[
 "https://www.contracostavote.gov/election/november-3-2026-general-election/",
 "https://www.contracostavote.gov/wp-json/wp/v2/media?search=ElectionSummaryReportRPT&per_page=20",
 "https://www.contracostavote.gov/wp-content/uploads/ElectionSummaryReportRPT-53.pdf",
 "https://www.contracosta.ca.gov/DocumentCenter/View/93220/ElectionSummaryReportRPT",
 "https://results.enr.clarityelections.com/CA/Contra_Costa/127405/current_ver.txt",
 "https://results.enr.clarityelections.com/CA/Contra_Costa/127405/385037/json/sum.json",
]
HEAD={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15','Accept':'application/pdf,application/json,text/plain,*/*'}
for url in URLS:
 print('URL:',url,flush=True)
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=15) as resp:
   body=resp.read(4_000_000)
   print('Status:',resp.status,'Content-Type:',resp.headers.get('Content-Type'),'bytes:',len(body),'magic:',repr(body[:170]),flush=True)
  if b'ElectionSummaryReport' in body and b'%PDF-' not in body[:5]:
   import re
   for match in list(re.finditer(b'ElectionSummaryReport.{0,130}',body,re.I))[:18]:
    print('PDF-LINK-FRAGMENT:',repr(body[max(0,match.start()-100):match.end()]),flush=True)
  if body.startswith(b'%PDF-'):
   from pypdf import PdfReader
   pdf=PdfReader(io.BytesIO(body))
   print('PDF pages:',len(pdf.pages),'metadata:',str(pdf.metadata)[:500],flush=True)
   texts=[page.extract_text() or '' for page in pdf.pages]
   for needle in ['MORAGA', 'ACALANES', 'FIRE']:
    matches=[]
    for i,t in enumerate(texts):
     import re
     for m in list(re.finditer(needle,t,re.I))[:6]:
      matches.append((i+1, t[max(0,m.start()-90):min(len(t),m.start()+470)].replace('\n',' | ')))
    print('MATCH:',needle, repr(matches[:8]),flush=True)
 except Exception as exc: print('ERROR:',repr(exc),flush=True)
