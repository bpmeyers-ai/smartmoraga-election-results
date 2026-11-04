import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pdf_extract
class PDFReportTest(unittest.TestCase):
 def sample(self):
  def table(rows,title):
   lines=['Candidate','Party','Vote By Mail','In-Person','Total']
   for name,votes,pct in rows:lines += [name,str(votes-10),'10',str(votes),str(pct)+'%']
   lines+=['Total Votes','12,345','Vote By Mail','In-Person','Total','Times Cast','14,000','Precincts Reported:','0',' of ','10',title,'(Vote for 1)']
   return '\n'.join(lines)
  return '\n'.join(['11/3/2026 9:20:31 PM','Page: 1 of 30',
   table([('JOHN DONNELLY',1296,62.79),('STEVE COHN',768,37.21)],pdf_extract.TARGETS['mofd'][0]),
   table([('STEVEN WOEHLEKE',2824,34.97),('KERRY HILLIS',2473,30.62),('ALEXIS I. MAPEL',2169,26.86),('BILL CARMAN',610,7.55)],pdf_extract.TARGETS['council'][0]),
   table([('YES',25444,69.99),('NO',10911,30.01)],pdf_extract.TARGETS['measure-w'][0])])
 def test_three_contests_and_report_time(self):
  r,t=pdf_extract.parse_report_text(self.sample())
  self.assertEqual(r['council']['KERRY HILLIS'],2473)
  self.assertEqual(r['measure-w']['YES'],25444)
  self.assertEqual(r['mofd']['JOHN DONNELLY'],1296)
  self.assertEqual(t,'2026-11-03T21:20:31-08:00')
 def test_wrong_contest_rejected(self):
  with self.assertRaises(ValueError):pdf_extract.parse_report_text(self.sample().replace('DIVISION 3','DIVISION 4'))
 def test_vote_sum_rejected(self):
  with self.assertRaises(ValueError):pdf_extract.parse_report_text(self.sample().replace('2824','9999'))
if __name__=='__main__':unittest.main()
