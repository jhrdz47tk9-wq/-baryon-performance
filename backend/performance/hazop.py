"""Candidate HAZOP record evaluation. Not an automated HAZOP study or plant approval."""
from engine import number

def text(v): return isinstance(v,str) and bool(v.strip())

def evaluate(nodes):
    if not isinstance(nodes,list): raise ValueError('hazop nodes must be a list')
    seen=set(); results=[]; blocks=[]; pending=[]
    for n in nodes:
        if not isinstance(n,dict): raise ValueError('node must be object')
        key=n.get('id')
        if not text(key) or key in seen: raise ValueError('unique node id required')
        seen.add(key)
        critical=n.get('critical')
        if critical is not None and type(critical) is not bool: raise ValueError('critical must be boolean or null')
        issues=[]
        for field in ('design_intent','parameter','guideword','deviation','cause','consequence','owner','activity_id'):
            if not text(n.get(field)): issues.append('MISSING_'+field.upper())
        if critical is None: issues.append('CRITICALITY_UNVERIFIED')
        barriers=n.get('required_barriers')
        if not isinstance(barriers,list): raise ValueError('required_barriers must be list')
        if not barriers: issues.append('NO_VERIFIED_PROTECTION_PLAN')
        bseen=set(); details=[]
        for b in barriers:
            if not isinstance(b,dict): raise ValueError('barrier must be object')
            bid=b.get('id')
            if not text(bid) or bid in bseen: raise ValueError('unique barrier id per node required')
            bseen.add(bid); reasons=[]
            for field in ('verified','current','response_required'):
                if b.get(field) is not None and type(b[field]) is not bool: raise ValueError(field+': invalid flag')
            if b.get('verified') is not True: reasons.append('BARRIER_FAILED' if b.get('verified') is False else 'BARRIER_UNVERIFIED')
            if b.get('current') is not True: reasons.append('EVIDENCE_NOT_CURRENT')
            if not text(b.get('evidence_id')): reasons.append('EVIDENCE_MISSING')
            if not text(b.get('owner')): reasons.append('OWNER_MISSING')
            response=b.get('response_required'); margin=None
            if response is None: reasons.append('RESPONSE_REQUIREMENT_UNVERIFIED')
            if response is True:
                fields=('detection_h','decision_h','mobilization_h','execution_h','effect_h','reserve_h','available_h')
                for f in fields:
                    if b.get(f) is not None: number(b[f],f)
                if any(b.get(f) is None for f in fields): reasons.append('RESPONSE_TIME_MISSING')
                else:
                    margin=b['available_h']-sum(b[f] for f in fields[:-1])
                    if margin<=0: reasons.append('INSUFFICIENT_RESPONSE_MARGIN')
            details.append({'id':bid,'issues':reasons,'margin_h':margin})
            issues.extend(bid+':'+r for r in reasons)
        state='NO_GO' if critical is True and issues else 'PENDIENTE' if issues else 'LISTO_PARA_REVISION'
        if state=='NO_GO': blocks.append(key)
        elif state=='PENDIENTE': pending.append(key)
        results.append({'id':key,'activity_id':n.get('activity_id'),'status':state,'issues':issues,'barriers':details})
    return {'status':'NO_GO' if blocks else 'PENDIENTE' if pending or not nodes else 'LISTO_PARA_REVISION',
            'nodes':results,'blocking_nodes':blocks,'authorized':False,
            'scope':'REQUIRED_BARRIERS_ONLY_NO_PROBABILITY_CREDIT'}
