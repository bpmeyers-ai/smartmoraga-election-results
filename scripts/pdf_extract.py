"""Parse three exact 2026 Contra Costa contests from the official results PDF.
The PDF's Reporting Services text extraction places the heading *after* its
candidate table. Using the next table would silently mislabel a contest.
"""
import datetime as dt
import io
import re
from zoneinfo import ZoneInfo

TARGETS = {
 'council': ('TOWN OF MORAGA, MEMBER, TOWN COUNCIL',('STEVEN WOEHLEKE','KERRY HILLIS','ALEXIS I. MAPEL','BILL CARMAN')),
 'measure-w': ('MEASURE W - ACALANES UNION HIGH SCHOOL DISTRICT - 2/3',('YES','NO')),
 'mofd': ('MORAGA-ORINDA FIRE PROTECTION DISTRICT, DIRECTOR, DIVISION 3',('JOHN DONNELLY','STEVE COHN')),
}
TABLE_HEADER='Candidate\nParty\nVote By Mail\nIn-Person\nTotal'

def _read_table(text,title,candidate_names):
    positions=[m.start() for m in re.finditer(re.escape(title),text,re.I)]
    if len(positions)!=1:raise ValueError(f'Expected one heading {title!r}; got {len(positions)}')
    index=positions[0]
    head=text.rfind(TABLE_HEADER,0,index)
    if head<0:raise ValueError('Candidate table header absent for '+title)
    block=text[head+len(TABLE_HEADER):index]
    if 'Total Votes' not in block:raise ValueError('Total Votes marker absent for '+title)
    lines=[line.strip() for line in block.split('Total Votes',1)[0].splitlines() if line.strip()]
    expected={name.upper() for name in candidate_names}
    found={}
    for i,line in enumerate(lines):
        if line.upper() not in expected:continue
        name=line.upper()
        if name in found:raise ValueError('Repeated candidate '+name)
        nums=[]
        pct=None
        for nxt in lines[i+1:i+9]:
            if nxt.upper() in expected:break
            if re.fullmatch(r'\d[\d,]*',nxt):nums.append(int(nxt.replace(',','')))
            if re.fullmatch(r'\d{1,3}\.\d{1,3}%',nxt):
                pct=float(nxt.rstrip('%'));break
        if len(nums)<3 or pct is None or nums[0]+nums[1]!=nums[2]:
            raise ValueError('Invalid vote-by-mail/in-person/total row for '+name)
        found[name]=(nums[2],pct)
    if set(found)!=expected:raise ValueError('Wrong candidate roster for '+title+': '+str(sorted(found)))
    total=sum(v for v,_ in found.values())
    if total<=0:raise ValueError('Zero results for '+title)
    for name,(votes,pct) in found.items():
        if abs(100*votes/total-pct)>0.035:raise ValueError('Percentage mismatch for '+name)
    return {name:count for name,(count,_) in found.items()}

def parse_report_text(text):
    date=re.match(r'\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',text)
    if not date:raise ValueError('Official report timestamp missing')
    timestamp=dt.datetime.strptime(date.group(1),'%m/%d/%Y %I:%M:%S %p')
    if not dt.date(2026,11,3)<=timestamp.date()<=dt.date(2027,1,31):
        raise ValueError('Official report date outside 2026 election-counting period: '+str(timestamp))
    stamp=timestamp.replace(tzinfo=ZoneInfo('America/Los_Angeles')).isoformat()
    return {rid:_read_table(text,title,names) for rid,(title,names) in TARGETS.items()},stamp

def parse_report(blob):
    if not blob.startswith(b'%PDF-'):raise ValueError('Not a PDF response')
    from pypdf import PdfReader
    pdf=PdfReader(io.BytesIO(blob))
    if not 3<=len(pdf.pages)<=150:raise ValueError('Unexpected page count '+str(len(pdf.pages)))
    return parse_report_text('\n'.join(page.extract_text() or '' for page in pdf.pages))
