"""Incremental EBITDA bridge at constant prices. No accounting classification inferred."""
from decimal import Decimal, InvalidOperation

def money(value):
    if isinstance(value,bool) or not isinstance(value,(str,int,float)):
        raise ValueError('amount must be a numeric string or number')
    try: d=Decimal(str(value))
    except InvalidOperation: raise ValueError('invalid amount')
    if not d.is_finite() or d<0: raise ValueError('amount must be finite and nonnegative')
    return d

def bridge(entries, *, currency, period, price_basis):
    """Entries use the SAME consequence_id across departments/documents.
    Permitted bases: contribution_margin, incremental_opex.
    Sales losses must be expressed as contribution margin, not gross revenue.
    Each consequence has baseline and scenario amounts in a single common currency.
    Separate consequences must not cover the same economic loss (upstream reconciliation).
    """
    for x in (currency,period,price_basis):
        if not isinstance(x,str) or not x.strip(): raise ValueError('currency, period and price basis required')
    if not isinstance(entries,list): raise ValueError('entries must be a list')
    seen=set(); rows=[]; missing=[]; delta=Decimal(0)
    for row in entries:
        if not isinstance(row,dict): raise ValueError('entry must be an object')
        cid=row.get('consequence_id')
        if not isinstance(cid,str) or not cid.strip() or cid in seen: raise ValueError('unique consequence_id required; reconcile duplicates first')
        seen.add(cid)
        kind=row.get('kind')
        if kind not in ('contribution_margin','incremental_opex'): raise ValueError('unsupported EBITDA component')
        if row.get('currency')!=currency or row.get('period')!=period or row.get('price_basis')!=price_basis:
            raise ValueError('incompatible currency, period or price basis')
        if not isinstance(row.get('source_id'),str) or not row['source_id'].strip(): missing.append(cid+':source_id')
        baseline=row.get('baseline'); scenario=row.get('scenario')
        # Validate available values even when another value is absent.
        b=money(baseline) if baseline is not None else None
        s=money(scenario) if scenario is not None else None
        if b is None or s is None:
            missing.append(cid+':amount'); continue
        change=(s-b) if kind=='contribution_margin' else (b-s)
        delta+=change
        rows.append({'consequence_id':cid,'delta':str(change)})
    if not entries: missing.append('consequences')
    return {'status':'DATOS_PENDIENTES' if missing else 'CALCULADO_CONDICIONAL',
            'delta_ebitda':None if missing else str(delta),'currency':currency,'period':period,
            'price_basis':price_basis,'missing':missing,'components':rows,
            'scope':'INCREMENTAL_BRIDGE_NOT_TOTAL_COMPANY_EBITDA'}
