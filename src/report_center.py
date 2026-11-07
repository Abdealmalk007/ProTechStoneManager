"""Interactive report workbench for ProTech Marble & Porcelain Manager 1.1."""
from __future__ import annotations

import csv
import datetime as dt
import json
from decimal import Decimal, InvalidOperation
import html
from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QSettings
from PySide6.QtGui import QColor, QDesktopServices, QTextDocument
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QFileDialog,
    QMessageBox, QAbstractItemView, QCompleter
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
import storage as db
import inventory_storage as inv
import premium_reports
import live_metrics
import target_reports
import client_materials
import export_layout

REPORTS = [
    ('العملاء والعقود - تفصيلي', 'orders'),
    ('الرخام والبورسلان: الألوان والمساحات والمبيعات', 'colors'),
    ('استهلاك الغراء', 'glue'),
    ('حالات التركيب', 'status'),
    ('الفواتير حسب الشهر', 'months'),
    ('السجلات الناقصة', 'missing'),
    ('جرد المخزون حسب الصنف', 'stock'),
    ('حركة المخزون الوارد والصرف', 'movements'),
    ('تقرير عميل محدد (عقوده)', 'client'),
    ('تقرير صنف / لون - العقود', 'item_orders'),
    ('تقرير صنف / لون - حركة المخزون', 'item_stock'),
]

def _number(value):
    if value is None:
        return ''
    if isinstance(value, float):
        return f'{value:,.2f}'
    return str(value)

def _html_table(title, headers, rows, count, total):
    head = ''.join('<th>' + html.escape(str(h)) + '</th>' for h in headers)
    body = ''.join('<tr>' + ''.join('<td>' + html.escape(_number(cell)) + '</td>' for cell in row) + '</tr>' for row in rows)
    return (
        '<html dir="rtl"><head><meta charset="utf-8"></head><body dir="rtl" '
        'style="font-family:Tahoma,Segoe UI,Arial;font-size:9pt;color:#172B49">'
        '<h2 style="color:#116C77">' + html.escape(title) + '</h2>'
        '<p>ProTech Marble & Porcelain Manager | ' + dt.date.today().isoformat()
        + ' | عدد السجلات ضمن الفلتر: ' + str(count)
        + ' | إجمالي الفواتير: ' + f'{total:,.2f}' + ' ر.س</p>'
        '<table width="100%" cellspacing="0" cellpadding="5" border="1" '
        'style="border-collapse:collapse;border-color:#CCD8E5">'
        '<thead><tr bgcolor="#D5E9ED">' + head + '</tr></thead><tbody>'
        + body + '</tbody></table></body></html>'
    )

class ReportCenter(QWidget):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)
        title = QLabel('مركز التقارير الذكي')
        title.setObjectName('heading')
        root.addWidget(title)
        subtitle = QLabel('معاينة النتائج قبل التصدير أو الطباعة. تنطبق فلاتر صفحة العملاء والعقود على جميع التقارير.')
        subtitle.setObjectName('muted')
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        choose = QHBoxLayout()
        choose.addWidget(QLabel('نوع التقرير:'))
        self.kind = QComboBox()
        self.kind.setMinimumHeight(39)
        for title, key in REPORTS:
            self.kind.addItem(title, key)
        choose.addWidget(self.kind, 1)
        go = QPushButton('تحديث المعاينة')
        go.clicked.connect(self.refresh_table)
        choose.addWidget(go)
        to_filters = QPushButton('تغيير الفلاتر')
        to_filters.setObjectName('secondary')
        to_filters.clicked.connect(lambda: self.main.switch(1))
        choose.addWidget(to_filters)
        root.addLayout(choose)

        self.scope_row=QWidget(self)
        controls=QHBoxLayout(self.scope_row)
        controls.setContentsMargins(0,0,0,0)
        self.client_combo=QComboBox()
        self.client_combo.setEditable(True)
        self.client_combo.setMinimumWidth(350)
        self.client_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.client_combo.setToolTip('اختر اسم العميل أو رقم العقد ثم اعرض التقرير')
        self.cat_combo=QComboBox()
        self.cat_combo.addItem('جميع التصنيفات','')
        for category in inv.KINDS:self.cat_combo.addItem(category,category)
        self.item_combo=QComboBox()
        self.item_combo.setEditable(True)
        self.item_combo.setMinimumWidth(300)
        self.item_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for combo in (self.client_combo,self.item_combo):
            combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            combo.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        controls.addWidget(QLabel('العميل:'))
        controls.addWidget(self.client_combo,3)
        controls.addWidget(QLabel('الفئة:'))
        controls.addWidget(self.cat_combo,1)
        controls.addWidget(QLabel('الصنف / اللون:'))
        controls.addWidget(self.item_combo,3)
        root.addWidget(self.scope_row)
        self.last_title=''
        self.last_note=''
        self.last_extra_rows=[]
        self.last_materials_summary=''
        self.last_customer_meta=None
        self.load_clients()
        self.cat_combo.currentIndexChanged.connect(self.load_items)
        self.load_items()
        self.kind.currentIndexChanged.connect(self.update_scope)
        self.client_combo.currentIndexChanged.connect(self.refresh_table)
        self.item_combo.currentIndexChanged.connect(self.refresh_table)

        self.info = QLabel()
        self.info.setObjectName('muted')
        root.addWidget(self.info)
        self.live_totals=QLabel()
        self.live_totals.setObjectName('reportTotals')
        self.live_totals.setWordWrap(True)
        root.addWidget(self.live_totals)
        self.material_details=QLabel('')
        self.material_details.setObjectName('reportTotals')
        self.material_details.setWordWrap(True)
        root.addWidget(self.material_details)
        self.customer_banner=QLabel('')
        self.customer_banner.setWordWrap(True)
        self.customer_banner.setObjectName('reportTotals')
        root.addWidget(self.customer_banner)

        actions = QHBoxLayout()
        for text, method, secondary in [
            ('معاينة PDF', self.preview_pdf, False),
            ('حفظ PDF', lambda: self.export('pdf'), False),
            ('تصدير Excel', lambda: self.export('xlsx'), False),
            ('تصدير CSV', lambda: self.export('csv'), True),
            ('طباعة', self.print_report, True),
            ('مجلد التقارير', self.open_exports, True),
        ]:
            button = QPushButton(text)
            if secondary:
                button.setObjectName('secondary')
            button.clicked.connect(method)
            actions.addWidget(button)
        root.addLayout(actions)
        sizing_row=QHBoxLayout()
        fit=QPushButton('ضبط عرض الأعمدة تلقائيًا')
        fit.setObjectName('secondary')
        fit.setToolTip('يمكنك أيضًا سحب حدود عناوين الأعمدة لتعديل العرض. تبقى المقاسات محفوظة للتقرير.')
        fit.clicked.connect(self.fit_columns)
        sizing_row.addWidget(fit)
        note=QLabel('لتعديل المقاسات يدويًا: اسحب الحد الفاصل بين عناوين الأعمدة؛ تنعكس المقاسات على PDF وExcel.')
        note.setObjectName('muted')
        note.setWordWrap(True)
        sizing_row.addWidget(note,1)
        root.addLayout(sizing_row)

        self.tabs = QTabWidget()
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(135)
        self._column_settings=QSettings('ProTech','PorcelainManager')
        self._applying_widths=False
        self._visible_columns_kind=None
        self.table.horizontalHeader().sectionResized.connect(self.remember_column_width)
        self.tabs.addTab(self.table, 'معاينة البيانات')
        self.pdf_doc = None
        self.pdf_view = None
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView
            self.pdf_doc = QPdfDocument(self)
            self.pdf_view = QPdfView()
            self.pdf_view.setDocument(self.pdf_doc)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.tabs.addTab(self.pdf_view, 'معاينة صفحات PDF')
        except (ImportError, AttributeError):
            pass
        root.addWidget(self.tabs, 1)

        self.update_scope()
        self.refresh_table()

    def load_clients(self):
        previous=self.client_combo.currentData()
        self.client_combo.blockSignals(True)
        self.client_combo.clear()
        for row in target_reports.client_choices(self.main.cx):
            self.client_combo.addItem(f"{row['client_name']}  | {row['contract_no']} | {row['phone']}",row['id'])
        found=self.client_combo.findData(previous)
        self.client_combo.setCurrentIndex(found if found>=0 else (0 if self.client_combo.count() else -1))
        self.client_combo.blockSignals(False)

    def load_items(self,*_):
        previous=self.item_combo.currentData()
        self.item_combo.blockSignals(True)
        self.item_combo.clear()
        for r in target_reports.catalog_choices(self.main.cx,self.cat_combo.currentData() or ''):
            self.item_combo.addItem(f"{r['category']} | {r['name']} ({r['unit']})",r['id'])
        ix=self.item_combo.findData(previous)
        self.item_combo.setCurrentIndex(ix if ix>=0 else (0 if self.item_combo.count() else -1))
        self.item_combo.blockSignals(False)
        if hasattr(self,'table'):self.refresh_table()

    def update_scope(self,*_):
        customer=self.kind.currentData()=='client'
        item=self.kind.currentData() in ('item_orders','item_stock')
        self.scope_row.setVisible(customer or item)
        for w in (self.client_combo,):
            w.setVisible(customer)
        for w in (self.cat_combo,self.item_combo):
            w.setVisible(item)
        for i in range(self.scope_row.layout().count()):
            obj=self.scope_row.layout().itemAt(i).widget()
            if isinstance(obj,QLabel):
                obj.setVisible((i==0 and customer) or (i in (2,4) and item))
        self.refresh_table()

    def select_customer(self,id):
        self.load_clients()
        ix=self.client_combo.findData(id)
        if ix<0:raise ValueError('لم يتم العثور على العميل المحدد')
        self.client_combo.setCurrentIndex(ix)
        self.kind.setCurrentIndex(self.kind.findData('client'))
        self.refresh_table()

    def select_item(self,id,stock=False):
        self.cat_combo.setCurrentIndex(0)
        self.load_items()
        ix=self.item_combo.findData(id)
        if ix<0:raise ValueError('لم يتم العثور على الصنف المحدد')
        self.item_combo.setCurrentIndex(ix)
        self.kind.setCurrentIndex(self.kind.findData('item_stock' if stock else 'item_orders'))
        self.refresh_table()

    def active_title(self):
        return self.last_title or self.kind.currentText()

    def column_key(self):
        return str(self.kind.currentData() or 'unknown')

    def remembered_widths(self, headers):
        saved=self._column_settings.value('report-columns/'+self.column_key(),'')
        if not saved:return None
        try:
            payload=json.loads(saved)
            widths=payload['widths']
            return widths if payload['headers']==list(headers) and len(widths)==len(headers) else None
        except (ValueError,TypeError,KeyError):return None

    def apply_column_widths(self,headers,rows,reset=False):
        saved=None if reset else self.remembered_widths(headers)
        sizes=saved or export_layout.preferred_widths(headers,rows,self.table.fontMetrics())
        self._applying_widths=True
        try:
            for index,width in enumerate(sizes):
                self.table.setColumnWidth(index,max(75,min(480,int(width))))
        finally:
            self._applying_widths=False
        self._visible_columns_kind=self.column_key()
        if reset:
            self._column_settings.remove('report-columns/'+self.column_key())

    def remember_column_width(self,index,old_size,new_size):
        if self._applying_widths or not hasattr(self,'kind'):return
        if self._visible_columns_kind!=self.column_key():return
        if new_size<=0:return
        headers=[self.table.horizontalHeaderItem(i).text()
                 for i in range(self.table.columnCount())
                 if self.table.horizontalHeaderItem(i) is not None]
        if len(headers)!=self.table.columnCount():return
        widths=[self.table.columnWidth(i) for i in range(len(headers))]
        self._column_settings.setValue('report-columns/'+self.column_key(),
                                        json.dumps({'headers':headers,'widths':widths},ensure_ascii=False))

    def fit_columns(self):
        headers,rows,_,_=self.dataset()
        self.apply_column_widths(headers,rows,reset=True)
        return True

    def exported_column_widths(self):
        if self._visible_columns_kind==self.column_key():
            return [self.table.columnWidth(i) for i in range(self.table.columnCount())]
        return None

    def dataset(self):
        self.last_title=''
        self.last_note=''
        self.last_extra_rows=[]
        self.last_materials_summary=''
        self.last_customer_meta=None
        kind=self.kind.currentData()
        if kind in ('client','item_orders','item_stock'):
            if kind=='client':
                id=self.client_combo.currentData()
                if id is None:
                    return ['اسم العميل'],[],0,None
                result=target_reports.customer_report(self.main.cx,id)
            elif kind=='item_orders':
                id=self.item_combo.currentData()
                if id is None:return ['الصنف'],[],0,None
                result=target_reports.catalog_order_report(self.main.cx,id)
            else:
                id=self.item_combo.currentData()
                if id is None:return ['الصنف'],[],0,None
                dfrom=self.main.from_date.date().toString('yyyy-MM-dd') if self.main.use_dates.isChecked() else ''
                dto=self.main.to_date.date().toString('yyyy-MM-dd') if self.main.use_dates.isChecked() else ''
                result=target_reports.item_ledger_report(self.main.cx,id,dfrom,dto)
            self.last_title=result['title']
            self.last_note=result['note']
            self.last_extra_rows=result.get('extra_rows',[])
            self.last_materials_summary=result.get('materials_summary','')
            self.last_customer_meta=result.get('customer_meta')
            return result['headers'],result['rows'],result['count'],result['invoice_total']
        orders = self.main.filtered()
        kind = self.kind.currentData()
        headers = []
        records = []
        if kind == 'orders':
            headers = list(db.HEADERS_AR)
            records = [[r[key] for key in db.COLUMNS] for r in orders]
        elif kind == 'colors':
            headers = ['نوع المادة','اللون / النوع', 'العقود', 'م²', 'م/ط', 'قيمة الفواتير (ر.س)']
            group = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
            for r in orders:
                x = group[(r['material_type'] or 'بورسلان', r['porcelain_color'] or 'غير محدد')]
                x[0] += 1
                x[1] += r['sqm'] or 0
                x[2] += r['linear_m'] or 0
                x[3] += r['invoice_amount'] or 0
            records = [[material_type, color, *vals] for (material_type,color), vals in sorted(group.items(), key=lambda kv: -kv[1][0])]
        elif kind == 'glue':
            headers = ['نوع الغراء', 'العقود', 'كمية الغراء المسجلة']
            group = defaultdict(lambda: [0, 0.0])
            for r in orders:
                x = group[r['glue_type'] or 'غير محدد']
                x[0] += 1
                x[1] += r['glue_qty'] or 0
            records = [[name, *vals] for name, vals in sorted(group.items(), key=lambda kv: -kv[1][0])]
        elif kind == 'status':
            headers = ['حالة التركيب', 'العقود', 'قيمة الفواتير (ر.س)']
            group = defaultdict(lambda: [0, 0.0])
            for r in orders:
                x = group[r['status'] or 'غير محدد']
                x[0] += 1
                x[1] += r['invoice_amount'] or 0
            records = [[name, *vals] for name, vals in sorted(group.items(), key=lambda kv: -kv[1][0])]
        elif kind == 'months':
            headers = ['شهر التركيب', 'العقود', 'قيمة الفواتير (ر.س)']
            group = defaultdict(lambda: [0, 0.0])
            for r in orders:
                x = group[(r['install_date'] or 'غير محدد')[:7]]
                x[0] += 1
                x[1] += r['invoice_amount'] or 0
            records = [[name, *vals] for name, vals in sorted(group.items(), reverse=True)]
        elif kind == 'missing':
            headers = ['رقم', 'اسم العميل', 'رقم العقد', 'الفاتورة', 'البيانات الناقصة']
            for r in orders:
                missing = [label for key, label in (
                    ('phone', 'رقم التواصل'), ('invoice_no', 'رقم الفاتورة'),
                    ('invoice_amount', 'قيمة الفاتورة'), ('install_date', 'تاريخ التركيب'),
                    ('porcelain_color', 'لون / نوع المادة')
                ) if r[key] is None or str(r[key]).strip() == '']
                if missing:
                    records.append([r['id'], r['client_name'], r['contract_no'], r['invoice_no'], '، '.join(missing)])
        elif kind == 'stock':
            headers=['الفئة','الصنف','الوحدة','الرصيد المسجل','حركات','حالة التوثيق']
            records=[[r['category'],r['name'],r['unit'],str(r['quantity']) if r['confirmed'] else 'غير معتمد',
                      r['movements'],'جرد افتتاحي مسجل' if r['confirmed'] else 'لم يثبت الرصيد'] for r in inv.balances(self.main.cx)]
        elif kind == 'movements':
            headers=['التاريخ','الفئة','الصنف','الحركة','الكمية','الوحدة','تكلفة الوحدة (ر.س)','رقم المستند','ملاحظات']
            start=self.main.from_date.date().toString('yyyy-MM-dd') if self.main.use_dates.isChecked() else ''
            end=self.main.to_date.date().toString('yyyy-MM-dd') if self.main.use_dates.isChecked() else ''
            records=[[r['occurred_on'],r['category'],r['item_name'],r['movement_type'],r['quantity'],
                      r['unit'],r['unit_cost'] or 'غير مسجل',r['doc_ref'] or '',r['notes'] or ''] for r in inv.ledger(self.main.cx,from_date=start,to_date=end)]
        return headers, records, len(orders), sum((Decimal(str(r['invoice_amount'])) for r in orders if r['invoice_amount'] is not None),Decimal('0'))

    def refresh_table(self, *_):
        headers, data, count, total = self.dataset()
        self._applying_widths=True
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                item = QTableWidgetItem(_number(value))
                item.setForeground(QColor('#172B49'))
                self.table.setItem(i, j, item)
        self.table.setSortingEnabled(True)
        self.apply_column_widths(headers,data)
        self.table.resizeRowsToContents()
        total_text=f' | مجموع الفواتير: {total:,.2f} ر.س' if total is not None else ''
        self.info.setText(f'النتائج: {len(data)} | السجلات: {count}{total_text}'+(f' | {self.last_note}' if self.last_note else ''))
        measures=live_metrics.summarize_report(headers,data)
        self.live_totals.setText(live_metrics.report_line(measures) if measures else 'لا توجد مجاميع رقمية موثقة لهذا التقرير.')
        self.material_details.setText(self.last_materials_summary)
        self.material_details.setVisible(bool(self.last_materials_summary))
        if self.last_customer_meta:
            meta=self.last_customer_meta
            self.customer_banner.setText(
                f"العميل: {meta['name']}     |     الجوال: {meta['phone']}     |     "
                f"تاريخ التقرير: {meta['report_date']}     |     "
                f"اللون / نوع المادة: {meta['porcelain_color']}")
            self.customer_banner.setVisible(True)
        else:
            self.customer_banner.clear()
            self.customer_banner.setVisible(False)
        self.tabs.setCurrentIndex(0)

    def document(self):
        headers, rows, count, total = self.dataset()
        name = self.active_title()
        doc = QTextDocument(self)
        doc.setHtml(_html_table(name, headers, rows, count, total if total is not None else Decimal('0')))
        return doc

    def _print_pdf(self, path):
        headers, rows, _, total=self.dataset()
        return premium_reports.pdf(path,self.active_title(),headers,rows,self.main.cx,total,
                                   note=self.last_note,extra_rows=self.last_extra_rows,customer_meta=self.last_customer_meta,column_widths=self.exported_column_widths())

    def preview_pdf(self):
        try:
            path = db.EXPORT_DIR / 'Preview' / 'Porcelain_Preview.pdf'
            path.parent.mkdir(parents=True, exist_ok=True)
            if self.pdf_doc is not None:
                self.pdf_doc.close()
            self._print_pdf(path)
            if self.pdf_doc is not None:
                from PySide6.QtPdf import QPdfDocument
                result = self.pdf_doc.load(str(path))
                if result == QPdfDocument.Error.None_ and self.pdf_doc.pageCount() > 0:
                    self.tabs.setCurrentIndex(1)
                    return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            QMessageBox.critical(self, 'تعذر عرض التقرير', str(exc))

    def export(self, format_name):
        headers, rows, _, _ = self.dataset()
        stamp = dt.date.today().strftime('%Y%m%d')
        name=export_layout.export_name(self.column_key(),format_name,self.last_customer_meta,stamp)
        filters = {'pdf': 'PDF (*.pdf)', 'xlsx': 'Excel (*.xlsx)', 'csv': 'CSV (*.csv)'}
        path, _ = QFileDialog.getSaveFileName(self, 'حفظ التقرير', str(db.EXPORT_DIR / name), filters[format_name])
        if not path:
            return
        try:
            if format_name == 'pdf':
                self._print_pdf(path)
            elif format_name == 'csv':
                with open(path, 'w', encoding='utf-8-sig', newline='') as fp:
                    writer = csv.writer(fp)
                    writer.writerow(headers)
                    writer.writerows(rows)
            else:
                premium_reports.excel(path,self.active_title(),headers,rows,self.main.cx,self.dataset()[3],
                                      note=self.last_note,extra_rows=self.last_extra_rows,customer_meta=self.last_customer_meta,column_widths=self.exported_column_widths())
            if not Path(path).is_file() or Path(path).stat().st_size==0:
                raise OSError('الملف المصدّر غير موجود أو فارغ')
            opened=QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))
            if not opened:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve().parent)))
                QMessageBox.information(self,'تم حفظ التقرير',
                    f'تم حفظ الملف، لكن لم يُعثر على برنامج لفتحه تلقائيًا:\n{path}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطأ أثناء تصدير التقرير', str(exc))

    def print_report(self):
        try:
            report=self.dataset()
            premium_reports.print_dialog(self,self.main.cx,self.active_title(),*report,
                                         note=self.last_note,extra_rows=self.last_extra_rows,customer_meta=self.last_customer_meta,column_widths=self.exported_column_widths())
        except Exception as exc:
            QMessageBox.critical(self,'الطباعة',str(exc))

    def open_exports(self):
        db.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(db.EXPORT_DIR)))
