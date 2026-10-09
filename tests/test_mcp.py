import json,subprocess,sys,unittest
from pathlib import Path

class MCPWire(unittest.TestCase):
 def exchange(self,requests):
  script=Path(__file__).resolve().parents[1]/'tools/ostrov_mcp.py'
  self.assertTrue(script.exists(),'MCP entry point must exist')
  p=subprocess.run([sys.executable,str(script)],input=''.join(json.dumps(x)+'\n'for x in requests),text=True,capture_output=True,timeout=5)
  self.assertEqual(p.returncode,0,p.stderr);return [json.loads(line)for line in p.stdout.splitlines()]
 def test_initialize_discovery_and_no_notification_execution(self):
  responses=self.exchange([{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'fixture','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'},{'jsonrpc':'2.0','method':'tools/call','params':{'name':'submit_application','arguments':{}}}])
  self.assertEqual(len(responses),2);self.assertEqual(responses[0]['result']['protocolVersion'],'2025-11-25')
  tools={t['name']:t for t in responses[1]['result']['tools']};self.assertIn('calculate_quote',tools);self.assertTrue(tools['calculate_quote']['annotations']['readOnlyHint']);self.assertFalse(tools['submit_application']['annotations']['readOnlyHint']);self.assertIn('estimateId',tools['submit_application']['inputSchema']['required']);self.assertNotIn('_http',tools['get_center'])
 def test_unknown_tool_and_unconfirmed_write_are_errors_before_network(self):
  prefix=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'fixture','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized'}]
  r=self.exchange(prefix+[{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'staff_confirm','arguments':{}}},{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'save_estimate','arguments':{'userConfirmed':False}}}])
  self.assertEqual(r[1]['error']['code'],-32602);self.assertEqual(r[2]['error']['code'],-32602)
 def test_tools_require_initialization(self):
  r=self.exchange([{'jsonrpc':'2.0','id':1,'method':'tools/list'}]);self.assertIn('error',r[0])

if __name__=='__main__':unittest.main()

class MalformedTools(MCPWire):
 def test_invalid_tool_name_does_not_crash_adapter(self):
  result=self.exchange([{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':[],'arguments':{}}},{'jsonrpc':'2.0','id':3,'method':'ping'}])
  self.assertEqual(result[-2]['error']['code'],-32602);self.assertEqual(result[-1]['result'],{})
