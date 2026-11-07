"""Precise, read-only summaries from visible rows. No inferred receipts or stock."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from collections import OrderedDict

FIELDS=(
    ('sqm','م²',('sqm','م²','المساحة م²','المساحات المسجلة (م²)')),
    ('linear','م/ط',('linear_m','م/ط','الطول م/ط')),
    ('amount','ر.س',('invoice_amount','مبلغ الفاتورة','مبلغ الفاتورة (ر.س)','قيمة الفواتير (ر.س)')),
    ('glue','كمية غراء',('glue_qty','كمية الغراء','كمية الغراء المسجلة')),
)

def as_decimal(value):
    try:
        if value is None or str(value).strip()=='':return None
        result=Decimal(str(value).replace(',',''))
        return result if result.is_finite() else None
    except (ValueError, InvalidOperation):
        return None

def summarize_orders(rows):
    rows=list(rows)
    result={'count':len(rows),'priced':0,'dated':0}
    for key,_,_ in FIELDS:result[key]=Decimal('0')
    for r in rows:
        for key,_,_ in FIELDS:
            value=as_decimal(r[dict(sqm='sqm',linear='linear_m',amount='invoice_amount',glue='glue_qty')[key]])
            if value is not None:
                result[key]+=value
                if key=='amount':result['priced']+=1
        if r['install_date']:result['dated']+=1
    return result

def summarize_report(headers, rows):
    result=OrderedDict()
    for key,label,aliases in FIELDS:
        indexes=[i for i,h in enumerate(headers) if str(h).strip() in aliases]
        if not indexes:continue
        index=indexes[0]
        vals=[as_decimal(r[index]) for r in rows]
        real=[v for v in vals if v is not None]
        if real:
            result[label]=sum(real,Decimal('0'))
    return result

def pretty(num,places=2):
    return format(num,f',.{places}f')

def orders_line(stat):
    return (f"العقود: {stat['count']:,}   |   "
            f"إجمالي م²: {pretty(stat['sqm'])}   |   "
            f"إجمالي م/ط: {pretty(stat['linear'])}   |   "
            f"إجمالي الفواتير: {pretty(stat['amount'])} ر.س")

def report_line(aggregate):
    return '  |  '.join(f'إجمالي {label}: {pretty(v,3 if label=="كمية غراء" else 2)}'
                         for label,v in aggregate.items())
