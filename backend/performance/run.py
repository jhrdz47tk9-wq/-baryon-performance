"""JSON stdin/stdout adapter. python3 run.py < case.json; no network or database writes."""
import hashlib,json,sys
from engine import gate,autonomy,oee,error_tree
from economics import bridge
from hazop import evaluate
VERSION='0.4-candidate'

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

def execute(payload):
    if not isinstance(payload,dict): raise ValueError('object required')
    allowed={'schema','case_id','evidence_class','controls','autonomy','oee','error_tree','economics','hazop'}
    if set(payload)-allowed: raise ValueError('unknown top-level fields')
    if payload.get('schema') not in ('baryon-performance/0.3','baryon-performance/0.4'): raise ValueError('unsupported schema')
    if payload.get('evidence_class') not in ('SYNTHETIC_TEST_ONLY','UNVALIDATED_CASE'): raise ValueError('unvalidated engine cannot certify plant data')
    if not isinstance(payload.get('case_id'),str) or not payload['case_id'].strip(): raise ValueError('case_id required')
    if not isinstance(payload.get('controls'),list): raise ValueError('controls required')
    digest=hashlib.sha256(canonical(payload).encode()).hexdigest()
    checks=gate(payload['controls'])
    if payload['schema']=='baryon-performance/0.4' and 'hazop' not in payload:
        raise ValueError('hazop required for schema 0.4')
    h=evaluate(payload.get('hazop',[]))
    if h['status']=='NO_GO':
        checks['status']='NO_GO'
        checks['reasons'].append({'id':'hazop','reason':'CRITICAL_PROTECTION_GAP','nodes':h['blocking_nodes']})
    elif h['status']=='PENDIENTE' and checks['status']!='NO_GO':
        checks['status']='PENDIENTE'
        checks['reasons'].append({'id':'hazop','reason':'ASSESSMENT_INCOMPLETE'})
    result={'gate':checks,'hazop':h}
    for key,fn in [('autonomy',autonomy),('oee',oee),('error_tree',error_tree),('economics',bridge)]:
        if key in payload:
            if not isinstance(payload[key],dict): raise ValueError(key+': object required')
            result[key]=fn(**payload[key])
    return {'schema':'baryon-performance-result/0.4','engine_version':VERSION,'case_id':payload['case_id'],
            'evidence_class':payload['evidence_class'],'input_sha256':digest,'outputs':result,
            'operational_authorization':False,'persistence':'NOT_SAVED','plant_validation':'NOT_EXECUTED'}

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(1048577)
        if len(raw)>1048576: raise ValueError('input exceeds 1 MiB')
        def pairs(items):
            d={}
            for k,v in items:
                if k in d: raise ValueError('duplicate JSON key')
                d[k]=v
            return d
        data=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('non-finite JSON')))
        print(canonical(execute(data)))
    except (ValueError,TypeError,KeyError,AttributeError) as e:
        print(json.dumps({'error':'INVALID_INPUT','detail':str(e)},ensure_ascii=False));sys.exit(2)
