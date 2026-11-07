"""Specific customer and catalog-item reporting (read-only, source-backed)."""
from __future__ import annotations
from decimal import Decimal
from datetime import date
import storage as db
import inventory_storage as inv
import client_materials

ORDER_HEADERS=['رقم السجل','اسم العميل','رقم التواصل','رقم العقد','رقم الفاتورة',
               'تاريخ التركيب','لون البورسلان','م²','م/ط','مبلغ الفاتورة (ر.س)',
               'الألواح المسجلة','نوع الغراء','كمية الغراء المسجلة',
               'الهانيكام المسجل','حالة التركيب','ملاحظات','نوع المادة','السماكة (مم)','عدد المرفقات','ملفات متاحة']
ORDER_COLUMNS=('id','client_name','phone','contract_no','invoice_no',
               'install_date','porcelain_color','sqm','linear_m','invoice_amount',
               'boards','glue_type','glue_qty','honeycomb','status','notes','material_type','thickness_mm')

ITEM_TO_ORDER_FIELD={'رخام':'porcelain_color','بورسلان':'porcelain_color','غراء':'glue_type','ألواح':'boards','هانيكام':'honeycomb'}

def client_choices(cx):
    return cx.execute("""SELECT id,client_name,COALESCE(phone,'') phone,
                                 COALESCE(contract_no,'') contract_no
                        FROM orders ORDER BY client_name COLLATE NOCASE,id""").fetchall()

def customer_report(cx,order_id):
    one=cx.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
    if one is None:raise ValueError('لم يتم العثور على العميل')
    # Same full name plus same nonblank phone: avoid joining unrelated customers by name alone.
    if one['phone'] and one['client_name']:
        matched=cx.execute("""SELECT * FROM orders
                 WHERE client_name=? AND phone=? ORDER BY install_date DESC,id DESC""",
                 (one['client_name'],one['phone'])).fetchall()
    else:
        matched=[one]
    ids=[r['id'] for r in matched]
    headers=ORDER_HEADERS
    rows=[]
    for r in matched:
        atts=cx.execute("""SELECT stored_path FROM attachments WHERE order_id=?""",(r['id'],)).fetchall()
        rows.append([r[k] for k in ORDER_COLUMNS]+[
            len(atts),sum(bool(a['stored_path']) and
                          bool(db.resolve_attachment(a)) for a in atts)])
    materials=client_materials.summarize(matched)
    color_list=list(dict.fromkeys(str(r['porcelain_color']).strip()
              for r in matched if r['porcelain_color'] and str(r['porcelain_color']).strip()))
    installation_dates=list(dict.fromkeys(str(r['install_date']).strip()
              for r in matched if r['install_date']))
    customer_meta={
        'name':str(one['client_name']).strip(),
        'phone':str(one['phone'] or 'غير مسجل').strip(),
        'report_date':date.today().isoformat(),
        'porcelain_color':'، '.join(color_list) if color_list else 'غير مسجل',
        'install_dates':'، '.join(installation_dates) if installation_dates else 'غير مسجل',
    }
    return {'title':f"تقرير العميل — {one['client_name']}",'customer_meta':customer_meta,
            'headers':headers,'rows':rows,'count':len(rows),'invoice_total':materials['amount'],
            'note':'العقود المتطابقة بالاسم ورقم الهاتف؛ الكميات بحسب ما سُجل في العقود وليست إثبات صرف مخزني',
            'materials_summary':client_materials.short_summary(materials),
            'extra_rows':materials['extras'],
            'ids':ids}

def catalog_choices(cx,cat=''):
    return inv.items(cx,cat,True)

def catalog_order_report(cx,item_id):
    item=cx.execute('SELECT * FROM catalog_items WHERE id=?',(item_id,)).fetchone()
    if not item:raise ValueError('الصنف غير موجود')
    field=ITEM_TO_ORDER_FIELD.get(item['category'])
    if not field:
        matches=[]
    else:
        if item['category'] in ('رخام','بورسلان'):
            matches=cx.execute("""SELECT * FROM orders
                WHERE material_type=? AND porcelain_color=?
                ORDER BY install_date DESC,id DESC""",
                (item['category'],item['name'])).fetchall()
        else:
            matches=cx.execute(f"""SELECT * FROM orders WHERE {field}=?
                          ORDER BY install_date DESC,id DESC""",(item['name'],)).fetchall()
    headers=['اسم العميل','رقم العقد','رقم الفاتورة','تاريخ التركيب',
             'نوع المادة','اللون / النوع','السماكة (مم)','م²','م/ط','الألواح','نوع الغراء',
             'كمية الغراء المسجلة','مبلغ الفاتورة (ر.س)']
    rows=[[r['client_name'],r['contract_no'],r['invoice_no'],r['install_date'],
           r['material_type'],r['porcelain_color'],r['thickness_mm'],r['sqm'],r['linear_m'],r['boards'],
           r['glue_type'],r['glue_qty'],r['invoice_amount']] for r in matches]
    total=sum((Decimal(str(r['invoice_amount'])) for r in matches if r['invoice_amount'] is not None),Decimal('0'))
    return {'title':f"تقرير عقود {item['category']}: {item['name']}",
            'headers':headers,'rows':rows,'count':len(rows),'invoice_total':total,
            'note':'ظهور الصنف في عقود العملاء لا يعني صرفًا من المخزون؛ الفواتير ليست تحصيلات'}

def item_ledger_report(cx,item_id,from_date='',to_date=''):
    item=cx.execute('SELECT * FROM catalog_items WHERE id=?',(item_id,)).fetchone()
    if not item:raise ValueError('الصنف غير موجود')
    movements=inv.ledger(cx,item_id=item_id,from_date=from_date,to_date=to_date)
    headers=['رقم الحركة','التاريخ','الصنف','نوع الحركة','الكمية','الوحدة',
             'تكلفة الوحدة (ر.س)','رقم المستند','ملاحظات']
    rows=[[r['id'],r['occurred_on'],item['name'],r['movement_type'],
           Decimal(r['quantity']),r['unit'],Decimal(r['unit_cost']) if r['unit_cost'] is not None else None,
           r['doc_ref'],r['notes']] for r in movements]
    b,opened,n=inv.balance(cx,item_id)
    return {'title':f"كشف حركة المخزون: {item['category']} / {item['name']}",
            'headers':headers,'rows':rows,'count':len(rows),'invoice_total':None,
            'note':f"الرصيد الحالي: {b} {item['unit']}" if opened else 'لم يسجل جرد افتتاحي لهذا الصنف — الرصيد غير معتمد'}
