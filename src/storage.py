"""SQLite persistence layer for ProTech Marble & Porcelain Manager. Python standard library only."""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, os, shutil, sqlite3, sys, zipfile
from pathlib import Path

APP_NAME = 'ProTech Marble & Porcelain Manager'
PKG = Path(__file__).resolve().parent
# User-writable and completely independent from the developer's machine.
# STONE_MANAGER_HOME is an explicit QA/administration override only.
if os.environ.get('STONE_MANAGER_HOME'):
    BASE=Path(os.environ['STONE_MANAGER_HOME']).expanduser().resolve()
elif os.name=='nt':
    BASE=Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'AppData'/'Local'))/'ProTech'/'StoneManager'
else:
    BASE=Path.home()/'.local'/'share'/'ProTech'/'StoneManager'
DB_DIR = BASE / 'Database'
ATTACH_DIR = BASE / 'Attachments'
BACKUP_DIR = BASE / 'Backups'
EXPORT_DIR = BASE / 'Exports'
DB = DB_DIR / 'porcelain.db'
COLUMNS = ('id','client_name','porcelain_color','sqm','linear_m','phone','invoice_amount','install_date','invoice_no','contract_no','boards','glue_type','glue_qty','honeycomb','status','notes','material_type','thickness_mm')
HEADERS_AR = ('الرقم','اسم العميل','لون / نوع المادة','م²','م/ط','رقم التواصل','مبلغ الفاتورة','تاريخ التركيب','رقم الفاتورة','رقم العقد','الألواح','نوع الغراء','كمية الغراء','هانيكام','الحالة','ملاحظات','نوع المادة','السماكة (مم)')


def connect():
    for d in (DB_DIR, ATTACH_DIR, BACKUP_DIR, EXPORT_DIR): d.mkdir(parents=True,exist_ok=True)
    cx=sqlite3.connect(DB)
    cx.row_factory=sqlite3.Row
    cx.execute('PRAGMA foreign_keys=ON')
    cx.execute('PRAGMA journal_mode=WAL')
    cx.execute('PRAGMA busy_timeout=5000')
    return cx


def setup(cx):
    cx.executescript('''
    CREATE TABLE IF NOT EXISTS imports(id INTEGER PRIMARY KEY,source_name TEXT NOT NULL,sha256 TEXT NOT NULL UNIQUE,imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,total_source_rows INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS source_rows(id INTEGER PRIMARY KEY,import_id INTEGER NOT NULL REFERENCES imports(id),excel_row INTEGER NOT NULL,raw_json TEXT NOT NULL,row_type TEXT NOT NULL,order_id INTEGER,UNIQUE(import_id,excel_row));
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT NOT NULL, porcelain_color TEXT,
      sqm REAL, linear_m REAL, phone TEXT,invoice_amount REAL,install_date TEXT,
      invoice_no TEXT,contract_no TEXT,boards TEXT,glue_type TEXT,glue_qty REAL,
      honeycomb TEXT,status TEXT NOT NULL DEFAULT 'غير محدد',notes TEXT NOT NULL DEFAULT '',
      source_excel_row INTEGER,material_type TEXT NOT NULL DEFAULT 'بورسلان',thickness_mm REAL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS attachments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
      original_reference TEXT,stored_path TEXT,display_name TEXT NOT NULL,sha256 TEXT,added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,action TEXT NOT NULL,details TEXT,event_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_order_name ON orders(client_name COLLATE NOCASE);
    CREATE INDEX IF NOT EXISTS idx_order_color ON orders(porcelain_color);
    CREATE INDEX IF NOT EXISTS idx_order_date ON orders(install_date);
    CREATE INDEX IF NOT EXISTS idx_order_invoice ON orders(invoice_no);
    CREATE INDEX IF NOT EXISTS idx_order_contract ON orders(contract_no);
    ''')
    # Tolerant schema migration for legitimate older public-edition user databases.
    existing={record['name'] for record in cx.execute('PRAGMA table_info(orders)')}
    if 'material_type' not in existing:
        cx.execute("ALTER TABLE orders ADD COLUMN material_type TEXT NOT NULL DEFAULT 'بورسلان'")
    if 'thickness_mm' not in existing:
        cx.execute('ALTER TABLE orders ADD COLUMN thickness_mm REAL')
    cx.commit()


def serial_date(val):
    if val is None or str(val).strip()=='':return None
    if isinstance(val,(int,float)):
        return (dt.datetime(1899,12,30)+dt.timedelta(days=float(val))).date().isoformat()
    if isinstance(val,str):
        try:return dt.datetime.fromisoformat(val.strip()).date().isoformat()
        except ValueError:return val.strip()
    return str(val)


def phone_value(v):
    if v is None:return None
    x=str(int(v)) if isinstance(v,float) and v.is_integer() else str(v).strip()
    if len(x)==9 and x.startswith('5') and x.isdigit():return '0'+x
    return x or None


def plain(v):return str(v).strip() if v is not None and str(v).strip() else None


def numeric(v):
    if v is None or v=='':return None
    try:return float(v)
    except (ValueError,TypeError):return None


def all_orders(cx, filter_text='',color='',status='',date_from='',date_to='',min_amount=None,max_amount=None):
    sql='SELECT '+','.join('o.'+k for k in COLUMNS)+' FROM orders o WHERE 1=1'; args=[]
    if filter_text:
        sql+=' AND (o.client_name LIKE ? OR o.phone LIKE ? OR o.invoice_no LIKE ? OR o.contract_no LIKE ? OR o.porcelain_color LIKE ? OR CAST(o.id AS TEXT) LIKE ? OR o.glue_type LIKE ? OR o.boards LIKE ?)'
        args.extend(['%'+filter_text+'%']*8)
    if color:sql+=' AND o.porcelain_color=?';args.append(color)
    if status:sql+=' AND o.status=?';args.append(status)
    if date_from:sql+=' AND o.install_date>=?';args.append(date_from)
    if date_to:sql+=' AND o.install_date<=?';args.append(date_to)
    if min_amount is not None:sql+=' AND o.invoice_amount>=?';args.append(float(min_amount))
    if max_amount is not None:sql+=' AND o.invoice_amount<=?';args.append(float(max_amount))
    sql+=' ORDER BY o.id DESC'
    return cx.execute(sql,args).fetchall()


def save_order(cx, data, order_id=None):
    name=plain(data.get('client_name'))
    if not name:raise ValueError('اسم العميل مطلوب')
    vals=[]; keys=[]
    for key in COLUMNS[1:]:
        if key not in data:continue
        v=data[key]
        if key in ('sqm','linear_m','invoice_amount','glue_qty','thickness_mm'):v=numeric(v)
        if key=='material_type':
            v=str(v or 'بورسلان').strip()
            if v not in ('رخام','بورسلان'):raise ValueError('اختر نوع مادة صالحًا: رخام أو بورسلان')
        if key in ('invoice_no','contract_no','boards','honeycomb','phone'):v=plain(v)
        if key=='notes':v=str(v or '')
        if key=='status':v=str(v or 'غير محدد')
        keys.append(key);vals.append(v)
    if 'client_name' not in keys:keys.insert(0,'client_name');vals.insert(0,name)
    with cx:
        if order_id:
            cx.execute('UPDATE orders SET '+','.join(k+'=?' for k in keys)+',updated_at=CURRENT_TIMESTAMP WHERE id=?',[*vals,order_id]); oid=order_id
            action='update'
        else:
            cur=cx.execute('INSERT INTO orders('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',vals);oid=cur.lastrowid;action='create'
        cx.execute('INSERT INTO audit(order_id,action,details) VALUES(?,?,?)',(oid,action,json.dumps(dict(zip(keys,vals)),ensure_ascii=False)))
    return oid


def delete_order(cx,order_id):
    with cx:
        cx.execute('INSERT INTO audit(order_id,action) VALUES(?,?)',(order_id,'delete'))
        cx.execute('DELETE FROM orders WHERE id=?',(order_id,))


def add_attachment(cx,order_id,path):
    src=Path(path)
    if not src.is_file():raise ValueError('ملف المرفق غير موجود')
    if src.suffix.lower() not in ('.pdf','.png','.jpg','.jpeg','.bmp','.webp','.gif'):
        raise ValueError('الملفات المسموحة: PDF والصور فقط')
    # Chunked hashing avoids loading potentially gigabyte-size PDF attachments into RAM.
    hasher=hashlib.sha256()
    with src.open('rb') as file:
        for block in iter(lambda:file.read(1024*1024),b''):
            hasher.update(block)
    dig=hasher.hexdigest()
    target=ATTACH_DIR/str(order_id)/(dig[:16]+src.suffix.lower())
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(src,target)
    rel=target.relative_to(BASE).as_posix()
    with cx:
        exists=cx.execute('SELECT id FROM attachments WHERE order_id=? AND sha256=?',(order_id,dig)).fetchone()
        if exists:return exists['id']
        cur=cx.execute('INSERT INTO attachments(order_id,display_name,stored_path,sha256) VALUES(?,?,?,?)',(order_id,src.name,rel,dig))
        cx.execute('INSERT INTO audit(order_id,action,details) VALUES(?,?,?)',(order_id,'attachment',src.name))
        return cur.lastrowid


def remove_attachment(cx, attachment_id):
    entry=cx.execute('SELECT * FROM attachments WHERE id=?',(attachment_id,)).fetchone()
    if not entry:raise ValueError('المرفق غير موجود')
    local_file=resolve_attachment(entry)
    with cx:
        cx.execute('DELETE FROM attachments WHERE id=?',(attachment_id,))
        cx.execute('INSERT INTO audit(order_id,action,details) VALUES(?,?,?)',
                   (entry['order_id'],'remove_attachment',entry['display_name']))
    # Keep the physical copy as a recoverable safety net. The UI removes only the database link;
    # old backup archives and files remain available for manual recovery.


def resolve_attachment(row):
    if row['stored_path']:
        path=(BASE/row['stored_path']).resolve()
        if path.is_relative_to(BASE.resolve()) and path.exists():return path
    return None


def make_backup(cx):
    when=dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    out=BACKUP_DIR/f'PorcelainBackup_{when}.zip'
    temp=BACKUP_DIR/f'_snapshot_{when}.db'
    try:
        dest=sqlite3.connect(temp)
        with dest:cx.backup(dest)
        dest.close()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.write(temp,'Database/porcelain.db')
            for folder in (ATTACH_DIR,BASE/'Branding'):
                if folder.exists():
                    for x in folder.rglob('*'):
                        if x.is_file():z.write(x,x.relative_to(BASE).as_posix())
        return out
    finally:temp.unlink(missing_ok=True)


def summary(cx):
    q=lambda s:cx.execute(s).fetchone()[0]
    return dict(orders=q('SELECT COUNT(*) FROM orders'),total=q('SELECT COALESCE(SUM(invoice_amount),0) FROM orders'),invoiced=q('SELECT COUNT(*) FROM orders WHERE invoice_amount IS NOT NULL'),attachments=q('SELECT COUNT(*) FROM attachments'),verified=q('SELECT COUNT(*) FROM attachments WHERE stored_path IS NOT NULL'),reviews=q("SELECT COUNT(*) FROM source_rows WHERE row_type='supplementary'"),completed=q("SELECT COUNT(*) FROM orders WHERE status='مكتمل'"))


def review_rows(cx):return cx.execute("SELECT excel_row,raw_json FROM source_rows WHERE row_type='supplementary' ORDER BY excel_row").fetchall()

if __name__=='__main__':
    cx=connect(); setup(cx);print(json.dumps({'summary':summary(cx),'database':str(DB)},ensure_ascii=False));cx.close()
