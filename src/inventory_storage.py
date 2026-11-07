"""Catalog and inventory movements. No stock is inferred from historic invoices."""
from decimal import Decimal, InvalidOperation
from datetime import date
KINDS=('رخام','بورسلان','ألواح','غراء','هانيكام','أخرى')
UNITS=('م²','م/ط','لوح','قطعة','كجم','لتر','عبوة','وحدة')
SIGNS={'رصيد افتتاحي':1,'وارد':1,'مرتجع':1,'صرف':-1,'تسوية زيادة':1,'تسوية نقص':-1}
SEED={'بورسلان':('porcelain_color','م²'),'غراء':('glue_type','عبوة'),'ألواح':('boards','لوح'),'هانيكام':('honeycomb','قطعة')}

def number(raw,places=3,allow_zero=False):
    try:d=Decimal(str(raw).strip().replace(',',''))
    except (InvalidOperation,TypeError):raise ValueError('أدخل قيمة رقمية صحيحة')
    if not d.is_finite() or d<0 or (d==0 and not allow_zero):raise ValueError('القيمة يجب أن تكون موجبة')
    if d!=d.quantize(Decimal(1).scaleb(-places)):raise ValueError(f'الحد الأقصى {places} خانات عشرية')
    if d>Decimal('999999999999'):raise ValueError('القيمة كبيرة')
    return format(d,'f')

def init(cx):
    with cx:
        cx.executescript("""CREATE TABLE IF NOT EXISTS catalog_items(
          id INTEGER PRIMARY KEY,category TEXT NOT NULL,name TEXT NOT NULL,unit TEXT NOT NULL,
          active INTEGER DEFAULT 1,source TEXT DEFAULT 'manual',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(category,name COLLATE NOCASE));
        CREATE TABLE IF NOT EXISTS stock_movements(
          id INTEGER PRIMARY KEY,item_id INTEGER NOT NULL REFERENCES catalog_items(id),
          movement_type TEXT NOT NULL,quantity TEXT NOT NULL,unit_cost TEXT,doc_ref TEXT,
          occurred_on TEXT NOT NULL,notes TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_movements(occurred_on,item_id);""")
        cx.execute("CREATE TABLE IF NOT EXISTS catalog_meta (key TEXT PRIMARY KEY,value TEXT)")
        if not cx.execute("SELECT 1 FROM catalog_meta WHERE key='seed_complete'").fetchone():
            for cat,(field,unit) in SEED.items():
                for (v,) in cx.execute(f"SELECT DISTINCT {field} FROM orders WHERE {field} IS NOT NULL AND TRIM({field})!=''"):
                    if str(v).strip():
                        cx.execute("INSERT OR IGNORE INTO catalog_items(category,name,unit,source) VALUES(?,?,?,'excel')",(cat,str(v).strip(),unit))
            cx.execute("INSERT INTO catalog_meta(key,value) VALUES('seed_complete','1')")

def items(cx,category='',include_disabled=False):
    q="SELECT * FROM catalog_items WHERE 1=1";args=[]
    if category:q+=" AND category=?";args.append(category)
    if not include_disabled:q+=" AND active=1"
    return cx.execute(q+" ORDER BY category,name COLLATE NOCASE",args).fetchall()

def add(cx,category,name,unit):
    name=name.strip()
    if category not in KINDS or unit not in UNITS or not name:raise ValueError('الفئة والاسم والوحدة مطلوبة')
    try:
        with cx: return cx.execute("INSERT INTO catalog_items(category,name,unit) VALUES(?,?,?)",(category,name,unit)).lastrowid
    except Exception as exc:raise ValueError('الصنف مسجل سابقًا في هذه الفئة') from exc

def edit(cx,id,name,unit,active):
    item=cx.execute("SELECT * FROM catalog_items WHERE id=?",(id,)).fetchone()
    if not item:raise ValueError('الصنف غير موجود')
    if not name.strip() or unit not in UNITS:raise ValueError('الاسم أو وحدة القياس غير صحيح')
    count=cx.execute("SELECT COUNT(*) FROM stock_movements WHERE item_id=?",(id,)).fetchone()[0]
    if count and unit!=item['unit']:raise ValueError('لا يمكن تغيير وحدة صنف لديه حركات، أنشئ صنفًا منفصلًا')
    try:
        with cx:cx.execute("UPDATE catalog_items SET name=?,unit=?,active=? WHERE id=?",(name.strip(),unit,int(active),id))
    except Exception as exc:raise ValueError('اسم الصنف مكرر') from exc

def balance(cx,id):
    rows=cx.execute("SELECT movement_type,quantity FROM stock_movements WHERE item_id=? ORDER BY occurred_on,id",(id,)).fetchall()
    total=sum((Decimal(row['quantity'])*SIGNS[row['movement_type']] for row in rows),Decimal('0'))
    has_open=any(row['movement_type']=='رصيد افتتاحي' for row in rows)
    return total,has_open,len(rows)

def movement(cx,id,kind,qty,cost='',ref='',day='',notes=''):
    item=cx.execute("SELECT * FROM catalog_items WHERE id=?",(id,)).fetchone()
    if item is None or not item['active']:raise ValueError('اختر صنفًا نشطًا')
    if kind not in SIGNS:raise ValueError('نوع الحركة غير صالح')
    qty=number(qty)
    cost=number(cost,2,True) if str(cost).strip() else None
    day=day or date.today().isoformat()
    try:date.fromisoformat(day)
    except ValueError:raise ValueError('التاريخ غير صحيح')
    bal,known,count=balance(cx,id)
    if kind=='رصيد افتتاحي' and count:raise ValueError('الرصيد الافتتاحي يجب أن يكون أول حركة')
    if known and kind in ('صرف','تسوية نقص') and bal<Decimal(qty):raise ValueError('الرصيد المعتمد لا يكفي')
    with cx:
        return cx.execute("""INSERT INTO stock_movements
          (item_id,movement_type,quantity,unit_cost,doc_ref,occurred_on,notes)
          VALUES(?,?,?,?,?,?,?)""",(id,kind,qty,cost,ref.strip() or None,day,notes.strip() or None)).lastrowid

def ledger(cx,category='',item_id=None,from_date='',to_date=''):
    q="""SELECT m.*,i.name item_name,i.category,i.unit FROM stock_movements m
         JOIN catalog_items i ON i.id=m.item_id WHERE 1=1""";args=[]
    for cond,val in [('i.category=?',category),('m.item_id=?',item_id),('m.occurred_on>=?',from_date),('m.occurred_on<=?',to_date)]:
        if val:q+=' AND '+cond;args.append(val)
    return cx.execute(q+' ORDER BY m.occurred_on DESC,m.id DESC',args).fetchall()

def balances(cx,category=''):
    out=[]
    for item in items(cx,category,True):
        qty,known,n=balance(cx,item['id'])
        out.append(dict(id=item['id'],category=item['category'],name=item['name'],unit=item['unit'],active=bool(item['active']),quantity=qty,confirmed=known,movements=n))
    return out
