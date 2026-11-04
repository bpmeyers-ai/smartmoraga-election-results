import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update
class TestUpdate(unittest.TestCase):
 def test_xml_three_races(self):
  raw=(Path(__file__).parent/'fixture.xml').read_bytes()
  data=update.assemble(update.parse_xml(raw),'fixture')
  self.assertEqual(len(data['races']),3)
  self.assertEqual(data['races'][0]['choices'][1]['votes'],2417)
  self.assertEqual(data['races'][1]['choices'][0]['percent'],70.09)
 def test_missing_candidate_fails(self):
  raw=(Path(__file__).parent/'fixture.xml').read_bytes().replace(b'<Choice text="Bill Carman" totalVotes="586"/>',b'')
  with self.assertRaises(ValueError):update.assemble(update.parse_xml(raw),'fixture')
 def test_wrong_contest_fails(self):
  raw=(Path(__file__).parent/'fixture.xml').read_bytes().replace(b'Division 3',b'Division 4')
  with self.assertRaises(ValueError):update.assemble(update.parse_xml(raw),'fixture')
 def test_json_sample(self):
  doc={'contests':[{'name':'Town of Moraga Member Town Council','choices':[{'name':'Kerry Hillis','votes':2417},{'name':'Steven Woehleke','votes':2753},{'name':'Alexis Mapel','votes':2093},{'name':'Bill Carman','votes':586}]},{'name':'Acalanes Union High School District Measure W','choices':[{'name':'YES','votes':24652},{'name':'NO','votes':10518}]},{'name':'Moraga-Orinda Fire District Division 3','choices':[{'name':'John Donnelly','votes':1237},{'name':'Steve Cohn','votes':728}]}]}
  import json
  self.assertEqual(len(update.parse_json(json.dumps(doc).encode())),3)
 def test_actual_clarity_sum_schema(self):
  import json
  payload={'VPCFE':False,'Contests':[
   {'C':'TOWN OF MORAGA, MEMBER, TOWN COUNCIL',
    'CH':['STEVEN WOEHLEKE','KERRY HILLIS','ALEXIS I. MAPEL','BILL CARMAN'],
    'V':[2824,2473,2169,610],'PCT':[34.97,30.62,26.86,7.55]},
   {'C':'MEASURE W - ACALANES UNION HIGH SCHOOL DISTRICT - 2/3',
    'CH':['YES','NO'],'V':[25444,10911],'PCT':[69.99,30.01]},
   {'C':'MORAGA-ORINDA FIRE PROTECTION DISTRICT, DIRECTOR, DIVISION 3',
    'CH':['JOHN DONNELLY','STEVE COHN'],'V':[1296,768],'PCT':[62.79,37.21]}
  ]}
  results=update.parse_json(json.dumps(payload).encode('utf-8'))
  data=update.assemble(results,'fixture')
  self.assertEqual(data['races'][0]['choices'][0]['votes'],2824)
  self.assertEqual(data['races'][1]['choices'][0]['votes'],25444)
  self.assertEqual(data['races'][2]['choices'][0]['votes'],1296)

if __name__=='__main__':unittest.main()
