"""BP2 motor 0.2 candidate. Pure functions; no plant actuation or authorization."""
from math import isfinite

VERSION = '0.5-candidate'

def number(x, name, maximum=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x) or x < 0 or (maximum is not None and x > maximum):
        raise ValueError(name + ': expected finite nonnegative number within range')
    return x

def evidence(*, applicable=None, identity=False, excluded_reason=None, criteria=(), due=None, received=None):
    """criteria: required criteria, each True/False/None; timestamps aware datetimes."""
    if applicable is not None and type(applicable) is not bool:
        raise ValueError('applicable must be boolean or null')
    if type(identity) is not bool or any(x is not None and type(x) is not bool for x in criteria):
        raise ValueError('invalid evidence flags')
    for t in (due, received):
        if t is not None and (t.tzinfo is None or t.utcoffset() is None):
            raise ValueError('timestamps require timezone')
    rejected = any(x is False for x in criteria) or (due is not None and received is not None and received > due)
    # A documented rejection cannot be hidden by subsequent incomplete/exclusion flags.
    if identity and rejected:
        return 'DESVIACION'
    if applicable is None:
        return 'APLICABILIDAD_PENDIENTE'
    if applicable is False:
        return 'EXCLUIDO_JUSTIFICADO' if identity and excluded_reason and excluded_reason.strip() else 'EXCLUSION_SIN_JUSTIFICAR'
    if not identity:
        return 'SIN_RESPALDO'
    if not criteria or any(x is None for x in criteria) or due is None or received is None:
        return 'EVALUACION_INCOMPLETA'
    return 'CONFORME'

def gate(checks):
    """Each required control: id, critical (bool), verified (True/False/None).
    Passing checks means eligible for site review, never permission to operate.
    """
    if not checks:
        return {'status':'PENDIENTE', 'reasons':['NO_CONTROLS'], 'authorized':False}
    seen=set(); blocked=[]; pending=[]
    for c in checks:
        key=c['id']
        if not isinstance(key,str) or not key.strip() or key in seen:
            raise ValueError('control IDs must be nonempty and unique')
        seen.add(key)
        critical=c['critical']; ok=c['verified']
        if type(critical) is not bool or (ok is not None and type(ok) is not bool):
            raise ValueError('control flags must be booleans or verified=null')
        if critical and ok is not True:
            blocked.append({'id':key,'reason':'FAILED' if ok is False else 'UNVERIFIED'})
        elif ok is not True:
            pending.append({'id':key,'reason':'FAILED' if ok is False else 'UNVERIFIED'})
    return {'status':'NO_GO' if blocked else 'PENDIENTE' if pending else 'LISTO_PARA_REVISION',
            'reasons':blocked+pending,'authorized':False}

def autonomy(initial_h, elapsed_h, unchanged, recovery_h=None, mitigation_h=None, reserve_h=None):
    if unchanged is not True:
        return {'status':'RECALCULAR_BALANCE', 'remaining_h':None,'recovery_margin_h':None,'mitigation_margin_h':None}
    if initial_h is None or elapsed_h is None:
        return {'status':'DATOS_PENDIENTES','remaining_h':None,'recovery_margin_h':None,'mitigation_margin_h':None}
    remaining=number(initial_h,'initial_h')-number(elapsed_h,'elapsed_h')
    def margin(t):
        if t is not None: number(t,'duration')
        if reserve_h is not None: number(reserve_h,'reserve_h')
        return None if t is None or reserve_h is None else remaining-t-reserve_h
    return {'status':'CALCULADO_CONDICIONAL','remaining_h':remaining,
            'recovery_margin_h':margin(recovery_h),'mitigation_margin_h':margin(mitigation_h)}

def balance(volume_m3, limit_m3, intervals):
    """Piecewise constant flows. Interval fields: hours, in_m3_h, out_m3_h.
    Stops at first boundary: does not integrate physically impossible volumes.
    """
    v=number(volume_m3,'volume'); limit=number(limit_m3,'limit'); t=0.
    if v>limit: raise ValueError('initial volume exceeds authorized limit')
    if v==limit: return {'status':'LIMITE_ALCANZADO','hours':0.,'volume_m3':v}
    for row in intervals:
        h=number(row['hours'],'hours'); net=number(row['in_m3_h'],'inflow')-number(row['out_m3_h'],'outflow')
        if net>0 and v+net*h>=limit:
            return {'status':'LIMITE_ALCANZADO','hours':t+(limit-v)/net,'volume_m3':limit}
        if net<0 and v+net*h<0:
            return {'status':'REVISAR_SALIDA_AL_VACIARSE','hours':t+v/(-net),'volume_m3':0.}
        v+=net*h; t+=h
    return {'status':'DENTRO_DEL_LIMITE_EN_HORIZONTE','hours':t,'volume_m3':v}

def error_tree(p_error, p_detect_given_error, p_recover_given_detected):
    if any(v is None for v in (p_error,p_detect_given_error,p_recover_given_detected)):
        return None
    e=number(p_error,'p_error',1); d=number(p_detect_given_error,'p_detect',1); r=number(p_recover_given_detected,'p_recover',1)
    return {'initial_success':1-e,'undetected':e*(1-d),'recovered':e*d*r,'detected_unresolved':e*d*(1-r),'unresolved':e*(1-d*r)}

def coverage(statuses):
    applicable={'SIN_RESPALDO','EVALUACION_INCOMPLETA','CONFORME','DESVIACION'}
    allowed=applicable|{'APLICABILIDAD_PENDIENTE','EXCLUIDO_JUSTIFICADO','EXCLUSION_SIN_JUSTIFICAR'}
    if any(s not in allowed for s in statuses): raise ValueError('unknown evidence status')
    n=sum(s in applicable for s in statuses); ev=sum(s in {'CONFORME','DESVIACION'} for s in statuses)
    return {'applicable':n,'evaluated':ev,'coverage':ev/n if n else None,'conformity':statuses.count('CONFORME')/ev if ev else None,
            'unresolved_applicability':sum(s in {'APLICABILIDAD_PENDIENTE','EXCLUSION_SIN_JUSTIFICAR'} for s in statuses)}

def oee(planned_h, running_h, ideal_t_h, total_t, good_t):
    if any(x is None for x in (planned_h,running_h,ideal_t_h,total_t,good_t)): return None
    for name,x in zip(('planned','running','ideal','total','good'),(planned_h,running_h,ideal_t_h,total_t,good_t)): number(x,name)
    if running_h>planned_h or good_t>total_t: raise ValueError('inconsistent production data')
    if not planned_h or not running_h or not ideal_t_h or not total_t: return None
    a=running_h/planned_h; p=total_t/(ideal_t_h*running_h); q=good_t/total_t
    return {'availability':a,'performance':p,'quality':q,'oee':a*p*q,'review_ideal_rate':p>1}
