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
    # Both Reporting Services layouts use the same tokens: older PDFs put
    # fields on separate lines; optimized PDFs put an entire row on one line.
    text=' '.join(text.split())
    title=' '.join(title.split())
    header=' '.join(TABLE_HEADER.split())
    positions=[m.start() for m in re.finditer(re.escape(title),text,re.I)]
    if len(positions)!=1:raise ValueError(f'Expected one heading {title!r}; got {len(positions)}')
    index=positions[0]
    head=text.rfind(header,0,index)
    if head<0:raise ValueError('Candidate table header absent for '+title)
    block=text[head+len(header):index].strip()
    rows,marker,summary=block.partition('Total Votes')
    if not marker:raise ValueError('Total Votes marker absent for '+title)
    number=r'(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)'
    names='|'.join(re.escape(name) for name in candidate_names)
    row=re.compile(r'('+names+r')\s+('+number+r')\s+('+number+r')\s+('+number+r')\s+(\d{1,3}\.\d{1,3})%',re.I)
    found={}
    subtotals=[0,0,0]
    remaining=rows.strip()
    while remaining:
        match=row.match(remaining)
        if not match:raise ValueError('Unexpected candidate row for '+title+': '+remaining[:100])
        name=match[1].upper()
        if name in found:raise ValueError('Repeated candidate '+name)
        nums=[int(match[i].replace(',','')) for i in (2,3,4)]
        pct=float(match[5])
        if nums[0]+nums[1]!=nums[2]:raise ValueError('Invalid vote-by-mail/in-person/total row for '+name)
        found[name]=(nums[2],pct)
        subtotals=[a+b for a,b in zip(subtotals,nums)]
        remaining=remaining[match.end():].strip()
    if set(found)!={n.upper() for n in candidate_names}:raise ValueError('Wrong candidate roster for '+title)
    totals=re.match(r'\s*('+number+r')\s+('+number+r')\s+('+number+r')\s+Vote By Mail In-Person Total\b',summary)
    if not totals or [int(v.replace(',','')) for v in totals.groups()]!=subtotals:
        raise ValueError('Contest Total Votes mismatch for '+title)
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
