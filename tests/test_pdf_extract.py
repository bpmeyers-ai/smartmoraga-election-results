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
   lines+=['Total Votes',str(sum(v-10 for _,v,_ in rows)),str(10*len(rows)),str(sum(v for _,v,_ in rows)),'Vote By Mail','In-Person','Total','Times Cast','14,000','Precincts Reported:','0',' of ','10',title,'(Vote for 1)']
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

class PDFLayoutsTest(unittest.TestCase):
 sample = PDFReportTest.sample
 def test_horizontal_layout(self):
  r,t=pdf_extract.parse_report_text(' '.join(self.sample().split()))
  self.assertEqual(r['council']['KERRY HILLIS'],2473)
 def test_unknown_candidate_rejected(self):
  with self.assertRaises(ValueError):pdf_extract.parse_report_text(self.sample().replace('Total Votes','UNEXPECTED 0 0 0 0.00%\nTotal Votes',1))
 def test_duplicate_candidate_rejected(self):
  with self.assertRaises(ValueError):pdf_extract.parse_report_text(self.sample().replace('JOHN DONNELLY','JOHN DONNELLY 1286 10 1296 62.79%\nJOHN DONNELLY',1))
 def test_total_rejected(self):
  with self.assertRaises(ValueError):pdf_extract.parse_report_text(self.sample().replace('Total Votes\n2044','Total Votes\n9999',1))
 def test_percentage_rejected(self):
  with self.assertRaises(ValueError):pdf_extract.parse_report_text(self.sample().replace('62.79%','12.79%'))
 def test_duplicate_contest_rejected(self):
  with self.assertRaises(ValueError):pdf_extract.parse_report_text(self.sample()+'\n'+pdf_extract.TARGETS['mofd'][0])

 def test_actual_november_10_report(self):
  text=(Path(__file__).parent/'report-65-excerpt.txt').read_text()
  races,stamp=pdf_extract.parse_report_text(text)
  self.assertEqual(stamp,'2026-11-10T15:12:20-08:00')
  self.assertEqual(races['council'],{'STEVEN WOEHLEKE':4597,'KERRY HILLIS':4152,'ALEXIS I. MAPEL':3746,'BILL CARMAN':1039})
  self.assertEqual(races['measure-w'],{'YES':41486,'NO':16438})
  self.assertEqual(races['mofd'],{'JOHN DONNELLY':2136,'STEVE COHN':1287})
