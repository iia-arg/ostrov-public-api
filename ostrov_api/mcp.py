"""MCP stdio adapter over the public HTTP client; no server-side pricing copy."""
import argparse,json,os,re,sys
from datetime import date
from pathlib import Path
from . import __version__
from .client import Client,APIError,DEFAULT_BASE

def validate(value,schema):
 if 'oneOf'in schema:
  passed=0
  for option in schema['oneOf']:
   try:validate(value,option);passed+=1
   except ValueError:pass
  if passed!=1:raise ValueError('Input must match exactly one plan schema')
  return
 kind=schema.get('type')
 valid={'object':lambda:isinstance(value,dict),'array':lambda:isinstance(value,list),'string':lambda:isinstance(value,str),'integer':lambda:type(value)is int,'boolean':lambda:type(value)is bool,'number':lambda:type(value)in [int,float]}
 if kind in valid and not valid[kind]():raise ValueError('Invalid field type')
 if 'const'in schema and(type(value)is not type(schema['const'])or value!=schema['const']):raise ValueError('Required constant or user confirmation is missing')
 if 'enum'in schema and value not in schema['enum']:raise ValueError('Unknown field value')
 if kind=='object':
  if set(schema.get('required',[]))-set(value):raise ValueError('Required fields are missing')
  props=schema.get('properties',{})
  if schema.get('additionalProperties')is False and set(value)-set(props):raise ValueError('Unknown fields are not allowed')
  for k,v in value.items():
   if k in props:validate(v,props[k])
 if kind=='array':
  if len(value)<schema.get('minItems',0)or len(value)>schema.get('maxItems',10000):raise ValueError('Invalid list size')
  for v in value:validate(v,schema.get('items',{}))
 if kind=='string':
  if len(value)>schema.get('maxLength',1000000)or len(value)<schema.get('minLength',0):raise ValueError('Invalid text length')
  if 'pattern'in schema and not re.fullmatch(schema['pattern'],value):raise ValueError('Invalid text format')
  if schema.get('format')=='date':
   try:date.fromisoformat(value)
   except ValueError:raise ValueError('Use an ISO date YYYY-MM-DD')from None
 if kind in ['integer','number']:
  if value<schema.get('minimum',float('-inf'))or value>schema.get('maximum',float('inf')):raise ValueError('Number outside supported range')

class Server:
 def __init__(self,client):
  self.client=client;self.initialized=False;self.ready=False
  self.tools={t['name']:t for t in json.loads(Path(__file__).with_name('tools.json').read_text())}
 def handle(self,message):
  id=message.get('id')if isinstance(message,dict)else None
  def error(code,text):return {'jsonrpc':'2.0','id':id,'error':{'code':code,'message':text}}
  def result(value):return {'jsonrpc':'2.0','id':id,'result':value}
  if not isinstance(message,dict)or message.get('jsonrpc')!='2.0'or not isinstance(message.get('method'),str):return error(-32600,'Invalid JSON-RPC request')
  method=message['method'];params=message.get('params',{})
  if 'id'not in message:
   if method=='notifications/initialized'and self.initialized:self.ready=True
   return None
  if type(id)not in [str,int]:return error(-32600,'Invalid request id')
  if not isinstance(params,dict):return error(-32602,'Expected object parameters')
  if method=='initialize':
   if self.initialized:return error(-32600,'Already initialized')
   if not isinstance(params.get('protocolVersion'),str):return error(-32602,'Protocol version is required')
   self.initialized=True;version=params['protocolVersion']if params['protocolVersion']in ['2025-06-18','2025-11-25']else'2025-11-25'
   return result({'protocolVersion':version,'capabilities':{'tools':{}},'serverInfo':{'name':'ostrov-public-api','version':__version__},'instructions':'Quotes are preliminary. Availability and booking require confirmation. Obtain explicit user confirmation before saving or submitting.'})
  if method=='ping':return result({})
  if not self.ready:return error(-32002,'Initialize the MCP session first')
  if method=='tools/list':return result({'tools':[{k:v for k,v in t.items()if k!='_http'}for t in self.tools.values()]})
  if method!='tools/call':return error(-32601,'Method not supported')
  if not isinstance(params.get('name'),str)or params['name']not in self.tools:return error(-32602,'Unknown tool')
  tool=self.tools[params['name']];arguments=params.get('arguments',{})
  try:
   validate(arguments,tool['inputSchema'])
   value=getattr(self.client,tool['name'])(**arguments)
   return result({'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False,allow_nan=False)}],'structuredContent':value,'isError':False})
  except (ValueError,TypeError):return error(-32602,'Arguments do not match the tool schema or required confirmation')
  except APIError as e:return result({'content':[{'type':'text','text':json.dumps({'code':e.code,'message':e.message,'httpStatus':e.status,'retryAfter':e.retry_after},ensure_ascii=False)}],'isError':True})
  except Exception:return result({'content':[{'type':'text','text':'Request failed; outcome is unknown. Do not repeat a write with a new requestKey.'}],'isError':True})

def main():
 argparse.ArgumentParser(description=__doc__).parse_args()
 server=Server(Client(os.environ.get('OSTROV_API_BASE_URL',DEFAULT_BASE),token=os.environ.get('OSTROV_API_TOKEN')))
 while True:
  line=sys.stdin.buffer.readline(1024*1024+1)
  if not line:return
  if len(line)>1024*1024:
   sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Message too large'}})+'\n');sys.stdout.flush();raise SystemExit(1)
  try:
   def pairs(items):
    result={}
    for k,v in items:
     if k in result:raise ValueError('Duplicate key')
     result[k]=v
    return result
   message=json.loads(line,object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError()));response=server.handle(message)
  except (ValueError,UnicodeError,RecursionError):response={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Invalid JSON'}}
  if response is not None:sys.stdout.write(json.dumps(response,ensure_ascii=True,allow_nan=False)+'\n');sys.stdout.flush()

if __name__=='__main__':main()
