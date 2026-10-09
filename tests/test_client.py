import json,threading,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
try:
 from ostrov_api.client import Client,APIError
except ImportError:
 Client=None;APIError=Exception

class WireClient(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(Client,'HTTP client must be implemented')
  self.requests=[];self.response={'status':200,'data':{'ok':True}}
  outer=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):self.answer()
   def do_POST(self):self.answer()
   def answer(self):
    raw=self.rfile.read(int(self.headers.get('Content-Length',0)));outer.requests.append({'method':self.command,'path':self.path,'authorization':self.headers.get('Authorization'),'body':json.loads(raw)if raw else None})
    body=json.dumps(outer.response['data']).encode();self.send_response(outer.response['status']);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
    if outer.response['status']==302:self.send_header('Location','/redirect-target')
    if outer.response['status']==429:self.send_header('Retry-After','60')
    self.end_headers();self.wfile.write(body)
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=self.server.serve_forever,daemon=True).start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  self.client=Client('http://127.0.0.1:'+str(self.server.server_port)+'/api/public/v1',token='fixture-token')
 def test_public_quote_does_not_send_a_session_secret(self):
  self.client.calculate_quote(kind='resident',plan={'name':'Гость'},catalogVersion=7)
  self.assertEqual(self.requests,[{'method':'POST','path':'/api/public/v1/quotes','authorization':None,'body':{'kind':'resident','plan':{'name':'Гость'},'catalogVersion':7}}])
 def test_write_requires_confirmation_before_any_request(self):
  with self.assertRaises(ValueError):self.client.save_estimate(kind='group',plan={},catalogVersion=7,requestKey='fixture-request-key',userConfirmed=False)
  self.assertEqual(self.requests,[])
 def test_owned_request_uses_header_and_never_follows_redirect(self):
  self.response={'status':302,'data':{}}
  with self.assertRaises(APIError):self.client.get_estimate(estimateId='a'*32)
  self.assertEqual(len(self.requests),1);self.assertEqual(self.requests[0]['authorization'],'Bearer fixture-token');self.assertNotIn('fixture-token',self.requests[0]['path'])
 def test_rate_limit_is_reported_without_automatic_retry(self):
  self.response={'status':429,'data':{'error':{'code':'RATE_LIMIT','message':'Wait'}}}
  with self.assertRaises(APIError)as ctx:self.client.get_catalog()
  self.assertEqual(ctx.exception.retry_after,60);self.assertEqual(len(self.requests),1)
 def test_resource_id_cannot_change_request_path(self):
  with self.assertRaises(ValueError):self.client.get_estimate(estimateId='../../staff')
  self.assertEqual(self.requests,[])

if __name__=='__main__':unittest.main()
