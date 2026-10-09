"""Small standard-library HTTP client. No pricing logic or automatic retries."""
import http.client,json,re,urllib.request,urllib.error,urllib.parse

DEFAULT_BASE='https://ostrov.center/api/public/v1'
class APIError(Exception):
 def __init__(self,status,code,message,retry_after=None):
  self.status=status;self.code=code;self.message=message;self.retry_after=retry_after
  super().__init__(message)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

class Client:
 def __init__(self,base_url=DEFAULT_BASE,token=None,timeout=20):
  u=urllib.parse.urlsplit(base_url)
  if u.scheme not in ['https','http']or not u.hostname or u.username or u.password or u.query or u.fragment:raise ValueError('Use an API base URL without credentials, query or fragment')
  if u.scheme=='http'and u.hostname not in ['127.0.0.1','localhost','::1']:raise ValueError('HTTPS is required except for local tests')
  self.base=base_url.rstrip('/');self.token=token;self.timeout=timeout;self.opener=urllib.request.build_opener(NoRedirect)
 def _call(self,method,path,body=None,private=False):
  if not path.startswith('/')or path.startswith('//'):raise ValueError('Expected a relative API path')
  if private and not self.token:raise APIError(401,'SESSION_REQUIRED','Open a session or provide your existing token to access this document')
  headers={'Content-Type':'application/json','Accept':'application/json','User-Agent':'ostrov-public-api/0.1.0'}
  if private:headers['Authorization']='Bearer '+self.token
  raw=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()if body is not None else None
  if raw is not None and len(raw)>65536:raise ValueError('API request exceeds 65536 bytes')
  request=urllib.request.Request(self.base+path,data=raw,headers=headers,method=method)
  try:
   with self.opener.open(request,timeout=self.timeout)as response:
    data=response.read(1024*1024+1)
    if len(data)>1024*1024:raise APIError(502,'INVALID_RESPONSE','API response is too large')
    try:
     value=json.loads(data,parse_constant=lambda x:(_ for _ in ()).throw(ValueError()))if data else None
     if value is not None and not isinstance(value,dict):raise ValueError('Expected response object')
     return value
    except (ValueError,UnicodeError):raise APIError(502,'INVALID_RESPONSE','API response was not valid JSON')from None
  except urllib.error.HTTPError as error:
   try:data=json.loads(error.read(1024*1024));detail=data.get('error',{})if isinstance(data,dict)else{}
   except (ValueError,UnicodeError):detail={}
   if not isinstance(detail,dict):detail={}
   retry=error.headers.get('Retry-After','')
   raise APIError(error.code,detail.get('code','HTTP_ERROR'),detail.get('message','API request refused'),int(retry)if retry.isdigit()else None)from None
  except (OSError,http.client.HTTPException):raise APIError(None,'TRANSPORT_ERROR','Network outcome is unknown; do not repeat a write with a new requestKey')from None
 def open_session(self):
  result=self._call('POST','/sessions',{})
  if not isinstance(result,dict)or not re.fullmatch(r'[A-Za-z0-9_-]{43}',result.get('token','')):raise APIError(502,'INVALID_RESPONSE','Invalid session response')
  self.token=result['token'];return {k:v for k,v in result.items()if k!='token'}
 def revoke_session(self):
  result=self._call('POST','/sessions/revoke',{},True);self.token=None;return result
 def _write(self,path,body,application=False):
  if body.get('userConfirmed')is not True:raise ValueError('Explicit user confirmation is required')
  if application and body.get('consent')is not True:raise ValueError('Contact consent is required')
  if not re.fullmatch(r'[A-Za-z0-9._:-]{16,120}',body.get('requestKey','')):raise ValueError('Provide one stable requestKey for this intended write')
  raw=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
  if len(raw)>65536:raise ValueError('API request exceeds 65536 bytes')
  if not self.token:self.open_session()
  return self._call('POST',path,body,True)
 @staticmethod
 def _id(value):
  if not isinstance(value,str)or not re.fullmatch(r'[A-Za-z0-9_-]{32}',value):raise ValueError('Invalid estimate ID')
  return value
 def get_center(self):return self._call('GET','/center')
 def get_catalog(self):return self._call('GET','/catalog')
 def get_objects(self):return self._call('GET','/objects')
 def get_events(self):return self._call('GET','/events')
 def get_examples(self):return self._call('GET','/examples')
 def get_calendar(self,*,start,end):return self._call('GET','/calendar?'+urllib.parse.urlencode({'start':start,'end':end}))
 def calculate_quote(self,*,kind,plan,catalogVersion=None):return self._call('POST','/quotes',{'kind':kind,'plan':plan,**({'catalogVersion':catalogVersion}if catalogVersion is not None else{})})
 def suggest_group(self,*,kind,plan,catalogVersion=None):return self._call('POST','/suggestions',{'kind':kind,'plan':plan,**({'catalogVersion':catalogVersion}if catalogVersion is not None else{})})
 def save_estimate(self,*,kind,plan,catalogVersion,requestKey,userConfirmed):return self._write('/estimates',{'kind':kind,'plan':plan,'catalogVersion':catalogVersion,'requestKey':requestKey,'userConfirmed':userConfirmed})
 def get_estimate(self,*,estimateId):return self._call('GET','/estimates/'+self._id(estimateId),private=True)
 def edit_estimate(self,*,estimateId,plan,catalogVersion,documentVersion,requestKey,userConfirmed):return self._write('/estimates/'+self._id(estimateId)+'/edit',{'plan':plan,'catalogVersion':catalogVersion,'documentVersion':documentVersion,'requestKey':requestKey,'userConfirmed':userConfirmed})
 def submit_application(self,*,estimateId,catalogVersion,documentVersion,contactProfile,requestKey,userConfirmed,consent):return self._write('/estimates/'+self._id(estimateId)+'/applications',{'catalogVersion':catalogVersion,'documentVersion':documentVersion,'contactProfile':contactProfile,'requestKey':requestKey,'userConfirmed':userConfirmed,'consent':consent},True)
 def get_application(self,*,applicationId):
  if not isinstance(applicationId,str)or not re.fullmatch(r'[a-f0-9-]{36}',applicationId):raise ValueError('Invalid application ID')
  return self._call('GET','/applications/'+applicationId,private=True)
