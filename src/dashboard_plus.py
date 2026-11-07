"""Filterable live dashboard: real invoices; stock only after physical opening count."""
from collections import Counter,defaultdict
from decimal import Decimal
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QComboBox,QDateEdit,QCheckBox,QFrame,QScrollArea
import inventory_storage as inv
import live_metrics
FIELDS={'رخام':'porcelain_color','بورسلان':'porcelain_color','ألواح':'boards','غراء':'glue_type','هانيكام':'honeycomb'}
class Dashboard(QWidget):
    def __init__(self,main):
        super().__init__(main);self.main=main;self.cx=main.cx
        shell=QVBoxLayout(self);shell.setContentsMargins(0,0,0,0)
        scroll=QScrollArea();scroll.setWidgetResizable(True);shell.addWidget(scroll)
        panel=QWidget();scroll.setWidget(panel)
        root=QVBoxLayout(panel);root.setContentsMargins(20,16,20,16)
        heading=QLabel('لوحة التحكم والتحليل');heading.setObjectName('heading');root.addWidget(heading)
        line=QHBoxLayout();self.cat=QComboBox();self.cat.addItem('جميع الأصناف','')
        for k in FIELDS:self.cat.addItem(k,k)
        self.name=QComboBox();self.name.addItem('جميع الألوان والأنواع','')
        self.state=QComboBox();self.state.addItem('جميع الحالات','')
        for k in ('غير محدد','جديد','مجدول','قيد التنفيذ','مكتمل','مؤجل','ملغى'):self.state.addItem(k,k)
        self.period=QCheckBox('من وإلى')
        self.from_date=QDateEdit();self.from_date.setCalendarPopup(True);self.from_date.setDate(QDate(2026,1,1));self.from_date.setDisplayFormat('yyyy-MM-dd')
        self.to_date=QDateEdit();self.to_date.setCalendarPopup(True);self.to_date.setDate(QDate.currentDate());self.to_date.setDisplayFormat('yyyy-MM-dd')
        for w in (self.cat,self.name,self.state,self.period,self.from_date,self.to_date):line.addWidget(w)
        root.addLayout(line)
        grid=QGridLayout();self.kpis={}
        for idx,(key,title) in enumerate([('orders','العقود المسجلة'),('amount','إجمالي قيم الفواتير (ر.س)'),('invoiced','عقود لها مبالغ'),('missing','عقود بلا مبلغ فاتورة'),
            ('area','المساحات المسجلة (م²)'),('linear','الأطوال المسجلة (م/ط)'),('glue','كمية الغراء المسجلة'),('stock','أصناف لديها جرد افتتاحي'),
            ('dated','عقود ذات تاريخ تركيب'),('attachments','ملفات مرفقات متاحة')]):
            card=QFrame();card.setObjectName('card');v=QVBoxLayout(card)
            label=QLabel(title);label.setObjectName('cardTitle');value=QLabel('—');value.setObjectName('cardValue')
            v.addWidget(label);v.addWidget(value);grid.addWidget(card,idx//3,idx%3);self.kpis[key]=value
        root.addLayout(grid)
        import sys
        BarChart=sys.modules[main.__class__.__module__].BarChart
        charts=QHBoxLayout();self.plot_a=BarChart('ألوان وأنواع الرخام والبورسلان في العقود');self.plot_b=BarChart('قيمة الفواتير بحسب شهر التركيب')
        charts.addWidget(self.plot_a);charts.addWidget(self.plot_b);root.addLayout(charts)
        self.plot_status=BarChart('توزيع حالات التركيب حسب العقود')
        root.addWidget(self.plot_status)
        self.note=QLabel();self.note.setObjectName('muted');self.note.setWordWrap(True);root.addWidget(self.note)
        self.cat.currentIndexChanged.connect(self.rebuild_names)
        for w,signal in ((self.name,self.name.currentIndexChanged),(self.state,self.state.currentIndexChanged),(self.period,self.period.toggled),(self.from_date,self.from_date.dateChanged),(self.to_date,self.to_date.dateChanged)):
            signal.connect(self.refresh)
        self.rebuild_names()
    def rebuild_names(self,*_):
        self.name.blockSignals(True);self.name.clear();self.name.addItem('جميع الألوان والأنواع','')
        for r in inv.items(self.cx,self.cat.currentData() or '',True) if self.cat.currentData() else []:
            self.name.addItem(r['name'],r['name'])
        self.name.blockSignals(False);self.refresh()
    def refresh(self,*_):
        cat=self.cat.currentData() or '';name=self.name.currentData() or ''
        sql='SELECT * FROM orders WHERE 1=1';params=[]
        if cat in ('رخام','بورسلان'):
            sql+=' AND material_type=?'
            params.append(cat)
        if cat in FIELDS and name:
            sql+=f' AND {FIELDS[cat]}=?'
            params.append(name)
        if self.state.currentData():sql+=' AND status=?';params.append(self.state.currentData())
        if self.period.isChecked():
            sql+=' AND install_date BETWEEN ? AND ?';params += [self.from_date.date().toString('yyyy-MM-dd'),self.to_date.date().toString('yyyy-MM-dd')]
        rows=self.cx.execute(sql,params).fetchall()
        totals=live_metrics.summarize_orders(rows)
        stock_records=inv.balances(self.cx,cat)
        if cat and name:
            stock_records=[record for record in stock_records if record['name']==name]
        registered_ids=[r['id'] for r in rows]
        verified_files=0
        if registered_ids:
            for r in self.cx.execute('SELECT stored_path FROM attachments WHERE order_id IN ('+
                ','.join('?' for _ in registered_ids)+') AND stored_path IS NOT NULL',registered_ids):
                from pathlib import Path
                import storage as db
                stored=(db.BASE/r['stored_path']).resolve()
                if stored.is_relative_to(db.BASE.resolve()) and stored.is_file():
                    verified_files+=1
        values={'orders':str(totals['count']),'amount':live_metrics.pretty(totals['amount']),
                'invoiced':str(totals['priced']),
                'missing':str(totals['count']-totals['priced']),
                'area':live_metrics.pretty(totals['sqm']),
                'linear':live_metrics.pretty(totals['linear']),
                'glue':live_metrics.pretty(totals['glue'],3),
                'stock':str(sum(record['confirmed'] for record in stock_records)),
                'dated':str(totals['dated']),'attachments':str(verified_files)}
        for key,v in values.items():self.kpis[key].setText(v)
        col=FIELDS.get(cat,'porcelain_color')
        cnt=Counter((str(r['material_type'])+' | '+str(r['porcelain_color'] or 'غير محدد'))
             if not cat else (r[col] or 'غير محدد') for r in rows)
        self.plot_a.set_data(cnt.most_common(8))
        by_month=defaultdict(Decimal)
        for r in rows:
            if r['install_date'] and r['invoice_amount'] is not None:by_month[str(r['install_date'])[:7]]+=Decimal(str(r['invoice_amount']))
        self.plot_b.set_data([(k,float(v)) for k,v in sorted(by_month.items())[-8:]])
        status=Counter(r['status'] or 'غير محدد' for r in rows)
        self.plot_status.set_data(status.most_common(8))
        pending=sum(not x['confirmed'] for x in stock_records)
        self.note.setText(
            f'المؤشرات محسوبة من {len(rows)} سجلًا حسب الفلاتر الحالية. '
            f'فواتير بلا مبلغ: {values["missing"]}. '
            f'أصناف بلا جرد افتتاحي معتمد: {pending}. '
            'مجموع الفواتير لا يثبت التحصيل، وحالة غير محدد لا تعني تركيبًا مكتملًا. '
            'الكميات المسجلة بالعقود لا تُخصم آليًا من المخزون.')
