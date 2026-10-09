"""Generate the OpenAPI contract and MCP input schemas from one definition."""
import argparse,json,copy
from pathlib import Path
argparse.ArgumentParser(description=__doc__).parse_args()
ROOT=Path(__file__).resolve().parents[1]
def obj(properties,required=()):return {'type':'object','properties':properties,'required':list(required),'additionalProperties':False}
def integer(lo=0,hi=100):return {'type':'integer','minimum':lo,'maximum':hi}
def string(n=200,description=None):return {'type':'string','maxLength':n,**({'description':description}if description else{})}
def ref(name):return {'$ref':'#/components/schemas/'+name}
date={'type':'string','format':'date','pattern':r'^\d{4}-\d{2}-\d{2}$'}
key={'type':'string','pattern':'^[A-Za-z0-9._:-]{16,120}$','description':'Unique key for one intended write; reuse exactly after an uncertain result. Use a new key for changed input.'}
true={'type':'boolean','const':True,'description':'Set only after the person explicitly requests this action.'}
id={'type':'string','pattern':'^[A-Za-z0-9_-]{32}$'}
common={'arrival':date,'departure':date,'adults':integer(0,100),'youngChildrenAges':{'type':'array','maxItems':30,'items':integer(0,5),'description':'Information only; does not change any guest count, accommodation, food or price.'}}
housing=obj({'resource':string(100),'occupancy':integer(1,3),'quantity':integer(1,100)},['resource','occupancy','quantity'])
activity=obj({'resource':string(100),'day':integer(0,364),'slot':string(100),'options':{'type':'array','items':string(100),'maxItems':20}},['resource','day','slot','options'])
group=obj({**common,'policyVersion':{'type':'integer','const':4},'teens':{**integer(),'description':'Children eligible for the child discount (currently 6–12). Despite the field name, full-rate children (currently 13+) belong in adults. Check the live catalogue.'},'team':{**integer(),'description':'Adult organizers and team, separate from participants. Ordinary tariff charges the team fully; all-inclusive benefits are calculated by the server.'},'youngChildren':{'type':'integer','const':0,'description':'Legacy counter kept at zero; use youngChildrenAges for information.'},'organizer':string(100,'Display name; required and nonempty when saving.'),'title':string(150,'Retreat name; required and nonempty when saving.'),'housing':{'type':'array','items':housing,'maxItems':100},'activities':{'type':'array','items':activity,'maxItems':2000},'food':{'type':'boolean'}},['policyVersion','arrival','departure','adults','teens','team','housing','activities','food'])
resident=obj({**common,'adults':integer(1,20),'name':string(100,'Required and nonempty when saving.'),'children':{'type':'array','maxItems':20,'items':integer(6,17),'description':'Children counted in accommodation; current rules permit ages 6–17. Put younger ages in youngChildrenAges.'},'housing':{'type':'array','minItems':1,'maxItems':30,'items':obj({'resource':string(100),'occupancy':integer(1,3)},['resource','occupancy'])},'bathVisits':integer(0,100)},['arrival','departure','adults','children','housing','bathVisits'])
contact=obj({'name':string(100),'phone':string(80),'email':{**string(254),'format':'email'},'notes':string(4000),'messengers':{'type':'array','minItems':1,'maxItems':8,'items':obj({'type':{'enum':['telegram','whatsapp','max']},'username':string(100),'userId':{'type':'string','const':'','description':'Typed contact is not authenticated identity; must be empty.'}},['type','username','userId'])}},['name','phone','email','notes','messengers'])
kind={'type':'string','enum':['group','biggroup','resident']}
quote_request=obj({'kind':kind,'plan':{'oneOf':[ref('GroupPlan'),ref('ResidentPlan')]},'catalogVersion':integer(1,1000000000)},['kind','plan'])
save_request=obj({**quote_request['properties'],'plan':{'oneOf':[ref('SavedGroupPlan'),ref('SavedResidentPlan')]},'requestKey':key,'userConfirmed':true},['kind','plan','catalogVersion','requestKey','userConfirmed'])
edit_request=obj({'plan':{'oneOf':[ref('SavedGroupPlan'),ref('SavedResidentPlan')]},'catalogVersion':integer(1,1000000000),'documentVersion':string(100),'requestKey':key,'userConfirmed':true},['plan','catalogVersion','documentVersion','requestKey','userConfirmed'])
apply_request=obj({'catalogVersion':integer(1,1000000000),'documentVersion':string(100),'contactProfile':ref('ContactProfile'),'requestKey':key,'userConfirmed':true,'consent':{**true,'description':'Consent to submit contact information for handling this request.'}},['catalogVersion','documentVersion','contactProfile','requestKey','userConfirmed','consent'])
quote_detail={'type':'object','required':['version','total','lines'],'properties':{'version':integer(1,1000000000),'total':{'type':['number','null'],'description':'RUB. Null means incomplete, never zero.'},'lines':{'type':'array','items':{'type':'object','properties':{'label':string(1000),'amount':{'type':'number'},'rate':{'type':'number'}},'additionalProperties':True}},'warnings':{'type':'array','items':string(2000)},'compositionComplete':{'type':'boolean'}},'additionalProperties':True}
estimate={'type':'object','required':['id','kind','url','documentVersion','catalogVersion','state','editable','plan','quote'],'properties':{'id':id,'kind':kind,'url':{'type':'string','format':'uri','description':'Confidential bearer link: document, typed contact alias/comments and normal website actions. Do not publish.'},'documentVersion':string(100),'catalogVersion':integer(1,1000000000),'state':{'enum':['draft','in_application','snapshot']},'editable':{'type':'boolean'},'plan':{'oneOf':[ref('GroupPlan'),ref('ResidentPlan')]},'quote':ref('QuoteDetail'),'updatedAt':string(100)},'additionalProperties':False}
application=obj({'id':{'type':'string','format':'uuid'},'estimateId':id,'status':string(100),'reservationState':{'enum':['none','negotiating','confirmed','cancelled']},'bookingConfirmed':{'type':'boolean'},'createdAt':string(100)},['id','estimateId','status','reservationState','bookingConfirmed','createdAt'])
schemas={'GroupPlan':group,'ResidentPlan':resident,'ContactProfile':contact,'QuoteRequest':quote_request,'SaveEstimateRequest':save_request,'EditEstimateRequest':edit_request,'SubmitApplicationRequest':apply_request,'QuoteDetail':quote_detail,'Estimate':estimate,'Application':application,'Error':obj({'error':obj({'code':string(100),'message':string(2000),'retryAfter':integer(1,86400)},['code','message'])},['error'])}
saved_group=copy.deepcopy(group);saved_resident=copy.deepcopy(resident)
for target,names in [(saved_group,['organizer','title']),(saved_resident,['name'])]:
 for name in names:target['required'].append(name);target['properties'][name]['minLength']=1
schemas.update(SavedGroupPlan=saved_group,SavedResidentPlan=saved_resident)
season_prices=obj({k:{'type':'number','minimum':0}for k in ['low','medium','high']},['low','medium','high'])
resource=obj({'id':string(100),'name':string(300),'kind':{'enum':['room','venue','food']},'unit':string(100),'quantity':integer(0,10000),'capacity':integer(0,10000),'rates':{'type':'object','additionalProperties':season_prices},'prices':season_prices,'slots':{'type':'array','items':obj({'id':string(100),'start':string(5),'end':string(5)},['id','start','end'])},'gapMinutes':integer(0,1440),'options':{'type':'array','items':obj({'id':string(100),'name':string(300),'prices':season_prices},['id','name','prices'])},'enabled':{'type':'boolean'},'availabilityRule':{'oneOf':[obj({'annualPeriod':obj({'start':string(5),'end':string(5)},['start','end'])},['annualPeriod']),obj({'months':{'type':'array','items':integer(1,12)}},['months'])]}},['id','name','kind','unit','enabled','availabilityRule'])
schemas['Resource']=resource
resources={'type':'array','items':ref('Resource')}
calendar_event={'type':'object','required':['start','end','title','kind'],'properties':{'start':date,'end':date,'title':string(1000),'kind':{'enum':['program','occupancy','demo']},'organizer':string(1000),'eventUrl':string(2000)},'additionalProperties':True}
schemas['CalendarEvent']=calendar_event
catalog_detail={'type':'object','required':['version','bookingStart','calendarYears','seasonIntervals','groupMinimumNights','biggroupMinimumNights','arrivalPricing','resources','bigGroups','residents'],'properties':{'version':integer(1,1000000000),'bookingStart':date,'calendarYears':{'type':'array','items':integer(2020,2200)},'seasonIntervals':{'type':'array','items':obj({'start':date,'end':date,'season':{'enum':['low','medium','high']}},['start','end','season'])},'groupMinimumNights':integer(1,366),'biggroupMinimumNights':integer(1,366),'arrivalPricing':{'type':'boolean'},'resources':resources,'bigGroups':{'type':'object','description':'Current all-inclusive thresholds, rates and team benefits. The server applies them.'},'residents':{'type':'object','description':'Current child-age and stay-discount policies. The server applies them.'}},'additionalProperties':False}
catalog_response=obj({'apiVersion':{'const':'1'},'catalog':catalog_detail,'currency':{'const':'RUB'},'generatedAt':string(100),'availabilityStatus':{'const':'requires_confirmation'},'ordinaryTeamBenefits':{'const':False}},['apiVersion','catalog','currency','generatedAt','availabilityStatus','ordinaryTeamBenefits'])

paths={};tools=[]
def operation(path,method,name,summary,request=None,response=None,private=False,write=False,params=None,status='200'):
 schema=response or {'type':'object','additionalProperties':True}
 op={'operationId':name,'summary':summary,'responses':{status:{'description':'Successful operation. A quote/application does not itself confirm a booking.','content':{'application/json':{'schema':schema}}},**{str(code):{'description':desc,'content':{'application/json':{'schema':ref('Error')}}}for code,desc in [(400,'Invalid input'),(401,'Missing or expired session'),(403,'Writes disabled'),(404,'Not found or not owned'),(409,'Version, idempotency or document conflict'),(429,'Rate limit; Retry-After header applies'),(503,'Unavailable or capacity reached; do not infer a zero price/free dates')]}}}
 if private:op['security']=[{'GuestSession':[]}]
 if request:op['requestBody']={'required':True,'content':{'application/json':{'schema':request}}}
 if params:op['parameters']=params
 paths.setdefault(path,{})[method]=op
 if name not in ['open_session','revoke_session','openapi','examples','skill_document']:
  tool_request=request or obj({})
  if '$ref'in tool_request:tool_request=schemas[tool_request['$ref'].rsplit('/',1)[1]]
  if params:
   tool_request=json.loads(json.dumps(tool_request));tool_request.setdefault('properties',{});tool_request.setdefault('required',[])
   for param in params:
    tool_request['properties'][param['name']]=param['schema']
    if param.get('required'):tool_request['required'].append(param['name'])
  tools.append({'name':name,'description':summary,'inputSchema':tool_request,'annotations':{'readOnlyHint':not write,'destructiveHint':name=='edit_estimate','idempotentHint':True,'openWorldHint':True},'_http':{'path':path,'method':method.upper(),'private':private,'write':write}})
def parameter(name,where,schema):return {'name':name,'in':where,'required':True,'schema':schema}
operation('/center','get','get_center','Public location and contact information.')
operation('/catalog','get','get_catalog','Current tariff version, resources and rules. Do not cache prices as permanent knowledge.',response=catalog_response)
operation('/objects','get','get_objects','Current public resource descriptions and availability rules; no guarantee of open places.',response=obj({'objects':resources,'availabilityStatus':{'const':'requires_confirmation'}},['objects','availabilityStatus']))
operation('/calendar','get','get_calendar','Confirmed public activity; empty dates do not mean availability.',params=[parameter('start','query',date),parameter('end','query',date)])
operation('/events','get','get_events','Public programs and labeled demo data; contact the organizer to ask about joining.')
operation('/examples','get','examples','Example dated plans; not reservations.')
operation('/openapi.json','get','openapi','This contract.')
for doc in ['skill','quickstart','access','readme']:
 operation('/'+doc+'.md','get','skill_document','Public '+doc+' documentation.')
 paths['/'+doc+'.md']['get']['operationId']='get_'+doc+'_document'
 paths['/'+doc+'.md']['get']['responses']['200']['content']={'text/markdown':{'schema':{'type':'string'}}}
operation('/quotes','post','calculate_quote','Calculate without saving or contacting anyone. Check complete, warnings and availabilityStatus.',ref('QuoteRequest'),obj({'kind':kind,'quote':ref('QuoteDetail'),'currency':{'const':'RUB'},'complete':{'type':'boolean'},'calculatedAt':string(100),'availabilityStatus':{'const':'requires_confirmation'}},['kind','quote','currency','complete','calculatedAt','availabilityStatus']))
operation('/suggestions','post','suggest_group','Suggest room/program selection for the ordinary group tariff; not an availability check.',obj({'kind':{'type':'string','const':'group'},'plan':ref('GroupPlan'),'catalogVersion':integer(1,1000000000)},['kind','plan']))
operation('/sessions','post','open_session','Create a 30-day capability session without signup.',obj({}),obj({'token':string(43),'tokenType':{'const':'Bearer'},'expiresAt':string(100),'scope':{'const':'own_estimates_and_applications'}},['token','tokenType','expiresAt','scope']),write=True,status='201')
operation('/sessions/revoke','post','revoke_session','Revoke own API access. Saved human documents remain.',obj({}),private=True,write=True,status='204');paths['/sessions/revoke']['post']['responses']['204']={'description':'Session revoked; no response body.'}
estimate_response=obj({'estimate':ref('Estimate'),'applicationId':{'type':['string','null']},'availabilityStatus':{'const':'requires_confirmation'},'linkAccess':string(500)},['estimate','applicationId','availabilityStatus','linkAccess'])
operation('/estimates','post','save_estimate','Save after explicit user request. Requires name/title. Confidential human link returned.',ref('SaveEstimateRequest'),estimate_response,True,True,status='201')
operation('/estimates/{estimateId}','get','get_estimate','Read only a document owned by this session.',response=estimate_response,private=True,params=[parameter('estimateId','path',id)])
operation('/estimates/{estimateId}/edit','post','edit_estimate','Edit an owned draft after explicit user request; stale versions conflict.',ref('EditEstimateRequest'),estimate_response,True,True,[parameter('estimateId','path',id)])
operation('/estimates/{estimateId}/applications','post','submit_application','Submit only after user confirmation and contact consent. This does not confirm a booking.',ref('SubmitApplicationRequest'),obj({'application':ref('Application')},['application']),True,True,[parameter('estimateId','path',id)],'201')
operation('/applications/{applicationId}','get','get_application','Read the actual state of the session-owned application.',response=obj({'application':ref('Application')},['application']),private=True,params=[parameter('applicationId','path',{'type':'string','format':'uuid'})])
def deref(v):
 if isinstance(v,list):return [deref(x)for x in v]
 if isinstance(v,dict):
  if '$ref'in v:return deref(schemas[v['$ref'].rsplit('/',1)[1]])
  return {k:deref(x)for k,x in v.items()}
 return v
spec={'openapi':'3.1.0','info':{'title':'Ostrov public API','version':'0.1.0','description':'Public retreat information and indicative quotes. A saved estimate or accepted application never implies confirmed availability. Guest sessions authorize only their own documents. Human links are confidential bearer capabilities.'},'servers':[{'url':'https://ostrov.center/api/public/v1'}],'paths':paths,'components':{'securitySchemes':{'GuestSession':{'type':'http','scheme':'bearer','description':'Token from POST sessions. Never send in a URL. Expires after 30 days; signup and private center keys are not required.'}},'schemas':schemas}}
(ROOT/'openapi.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
(ROOT/'ostrov_api/tools.json').write_text(json.dumps(deref(tools),ensure_ascii=False,indent=2)+'\n')
print('Generated OpenAPI and MCP schemas')
