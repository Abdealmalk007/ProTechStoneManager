"""Source-faithful material detail and subtotal calculations for one customer's contracts.

A descriptor like "قطع" or "1كبير" is not a numeric quantity. Distinguish
recorded contract quantities from verified warehouse consumption.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal, InvalidOperation

def number(value):
    if value is None or str(value).strip()=="":return None
    try:
        n=Decimal(str(value).strip().replace(",",""))
        if n.is_finite() and n>=0:return n
    except (InvalidOperation,ValueError):pass
    return None

def nfmt(val):
    s=f"{val:,.3f}"
    return s.rstrip("0").rstrip(".") if "." in s else s

def summarize(rows):
    rows=list(rows)
    money=Decimal("0");sqm=Decimal("0");linear=Decimal("0");glue=Decimal("0")
    numeric_h=Decimal("0");numeric_b=Decimal("0")
    numeric_h_count=numeric_b_count=0
    glue_types=defaultdict(lambda:Decimal("0"))
    glue_type_counts=defaultdict(int)
    unknown_h=[];unknown_b=[]
    details=[]
    for r in rows:
        amount=number(r["invoice_amount"])
        if amount is not None:money+=amount
        for field,collector in [("sqm", "sqm"),("linear_m","linear")]:
            v=number(r[field])
            if v is not None:
                if collector=="sqm":sqm+=v
                else:linear+=v
        qty=number(r["glue_qty"])
        kind=(r["glue_type"] or "").strip() or "نوع غير محدد"
        if qty is not None:
            glue+=qty;glue_types[kind]+=qty
        glue_type_counts[kind]+=1
        btext=str(r["boards"] or "").strip()
        htext=str(r["honeycomb"] or "").strip()
        if btext:
            bnum=number(btext)
            if bnum is None:unknown_b.append((r["id"],btext))
            else:numeric_b+=bnum;numeric_b_count+=1
        if htext:
            hnum=number(htext)
            if hnum is None:unknown_h.append((r["id"],htext))
            else:numeric_h+=hnum;numeric_h_count+=1
        details.extend([
            ("العقد",str(r["contract_no"] or f'السجل #{r["id"]}'),"الغراء: "+kind+" | الكمية: "+(nfmt(qty) if qty is not None else "غير مسجلة")),
            ("العقد",str(r["contract_no"] or f'السجل #{r["id"]}'),"الألواح: "+(btext or "غير مسجلة")+" | الهانيكام: "+(htext or "غير مسجل"))
        ])
    h_valid="مجموع القيم الرقمية فقط" if unknown_h else "إجمالي رقمي مسجل"
    b_valid="مجموع القيم الرقمية فقط" if unknown_b else "إجمالي رقمي مسجل"
    extras=[
        ("معلومات","عدد العقود",str(len(rows))),
        ("المساحات","إجمالي المساحة المسجلة (م²)",nfmt(sqm)),
        ("المساحات","إجمالي الأطوال المسجلة (م/ط)",nfmt(linear)),
        ("الفواتير","إجمالي مبالغ الفواتير (ر.س)",f"{money:,.2f}"),
        ("الغراء","إجمالي كمية الغراء المسجلة (دون وحدة محددة)",nfmt(glue)),
    ]
    for kind in sorted(glue_type_counts):
        extras.append(("الغراء حسب النوع",kind,
          f"كمية مسجلة: {nfmt(glue_types[kind])} | عقود: {glue_type_counts[kind]}"))
    extras.extend([
        ("الألواح",f"إجمالي الألواح — {b_valid}",nfmt(numeric_b)),
        ("الهانيكام",f"إجمالي الهانيكام — {h_valid}",nfmt(numeric_h)),
    ])
    if unknown_b:
        extras.append(("الألواح","قيم لا يمكن اعتبارها كميات",
                       "؛ ".join(f"سجل {id}: {txt}" for id,txt in unknown_b)))
    if unknown_h:
        extras.append(("الهانيكام","قيم لا يمكن اعتبارها كميات",
                       "؛ ".join(f"سجل {id}: {txt}" for id,txt in unknown_h)))
    extras+=details
    extras.append(("تنبيه","طبيعة البيانات",
      "هذه كميات وأوصاف العقود المسجلة وليست إثبات صرف مواد من المستودع أو استهلاك فعلي. مبالغ الفواتير ليست مبالغ محصلة."))
    return {
        "sqm":sqm,"linear":linear,"amount":money,"glue":glue,
        "boards":numeric_b,"honeycomb":numeric_h,"unknown_boards":len(unknown_b),
        "unknown_honeycomb":len(unknown_h),"extras":extras,
    }

def short_summary(metrics):
    return (
        f"م²: {nfmt(metrics['sqm'])} | م/ط: {nfmt(metrics['linear'])} | "
        f"الغراء: {nfmt(metrics['glue'])} | "
        f"الألواح (رقمي): {nfmt(metrics['boards'])} | "
        f"الهانيكام (رقمي): {nfmt(metrics['honeycomb'])} | "
        f"الفواتير: {metrics['amount']:,.2f} ر.س"
    )
