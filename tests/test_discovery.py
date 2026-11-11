import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update
import pdf_extract
import test_pdf_extract

class DiscoveryTest(unittest.TestCase):
 def test_links_ignore_comments_and_unofficial_hosts(self):
  parser=update.ReportLinks(update.COUNTY_RESULTS)
  parser.feed('''<!-- <a href="/wp-content/uploads/ElectionSummaryReportRPT-99.pdf"> -->
  <a href = '/wp-content/uploads/ElectionSummaryReportRPT-65.pdf?x=1&amp;y=2'>Current</a>
  <a href="https://fake.example/wp-content/uploads/ElectionSummaryReportRPT-999.pdf">Fake</a>''')
  self.assertEqual(parser.urls,['https://www.contracostavote.gov/wp-content/uploads/ElectionSummaryReportRPT-65.pdf?x=1&y=2'])
 def test_discovery_keeps_previous_and_bounds_probes(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'data.json';out.write_text(json.dumps({'source_url':'https://www.contracostavote.gov/wp-content/uploads/ElectionSummaryReportRPT-64.pdf'}))
   with patch.object(update,'OUT',out),patch.object(update,'get',return_value=b'<a href="/wp-content/uploads/ElectionSummaryReportRPT-65.pdf">Current</a>'):
    urls=update.discover_pdf_urls()
   self.assertEqual(len(urls),7)
   self.assertTrue(any('RPT-64.pdf' in u for u in urls))
   self.assertTrue(any('RPT-69.pdf' in u for u in urls))
 def test_newest_timestamp_wins_not_filename(self):
  results,stamp=pdf_extract.parse_report_text(test_pdf_extract.PDFReportTest().sample())
  def parse(blob):
   if blob==b'bad':raise ValueError('Invalid PDF')
   return results, '2026-11-10T15:12:20-08:00' if blob==b'65' else stamp
  with patch.object(update,'discover_pdf_urls',return_value=['65','99','bad']),patch.object(update,'get',side_effect=lambda url,**kw:url.encode()),patch.object(pdf_extract,'parse_report',side_effect=parse):
   self.assertEqual(update.load_county_pdf()['source_url'],'65')
 def test_failed_or_old_source_preserves_bytes(self):
  results,stamp=pdf_extract.parse_report_text(test_pdf_extract.PDFReportTest().sample())
  older=update.assemble(results,'fixture',stamp)
  previous=copy.deepcopy(older);previous['reported_at']='2026-11-10T15:12:20-08:00'
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'data.json';out.write_text(json.dumps(previous));original=out.read_bytes()
   with patch.object(update,'OUT',out),patch.object(sys,'argv',['update.py']):
    with patch.object(update,'load_preferred',return_value=older):self.assertEqual(update.main(),1)
    self.assertEqual(out.read_bytes(),original)
    with patch.object(update,'load_preferred',side_effect=ValueError('Source failure')):self.assertEqual(update.main(),1)
    self.assertEqual(out.read_bytes(),original)
 def test_identical_results_do_not_churn(self):
  results,stamp=pdf_extract.parse_report_text(test_pdf_extract.PDFReportTest().sample())
  data=update.assemble(results,'fixture',stamp)
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'data.json';out.write_text(json.dumps(data));original=out.read_bytes()
   with patch.object(update,'OUT',out),patch.object(sys,'argv',['update.py']),patch.object(update,'load_preferred',return_value=data):self.assertEqual(update.main(),0)
   self.assertEqual(out.read_bytes(),original)
