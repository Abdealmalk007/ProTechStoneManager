"""ProTech Marble & Porcelain Manager - bilingual-friendly, RTL desktop workflow."""
from __future__ import annotations
import csv, datetime as dt, html, json, os, shutil, sqlite3, sys, zipfile
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QUrl, QDate, QTimer, QEvent, QPoint
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
 QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
 QLineEdit,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QFileDialog,
 QDialog,QDialogButtonBox,QTextEdit,QFrame,QSplitter,QStackedWidget,QAbstractItemView,
 QCheckBox,QDateEdit,QScrollArea,QGridLayout,QTabWidget,QListWidget,QListWidgetItem,
 QInputDialog,QSizePolicy,QProgressBar,QMenu,QSpinBox,QToolBar
)
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtGui import QTextDocument
import storage as db
import inventory_storage as inv
import company_settings as company
import live_metrics

STATES=['غير محدد','جديد','مجدول','قيد التنفيذ','مكتمل','مؤجل','ملغى']
STYLE='''
QWidget{color:#172B49;font-family:Tahoma;font-size:10pt}
QMainWindow,QDialog{background:#F5F7FB;color:#172B49;font-family:Tahoma;font-size:11pt}
QFrame#sidebar{background:#13253F;border:none}
QFrame#card{background:white;border:1px solid #E2E8F0;border-radius:12px}
QLabel#cardValue{font-size:22pt;font-weight:700;color:#117F7A}
QLabel#cardTitle{color:#67768D;font-size:10pt}
QPushButton{background:#147C84;color:white;border:0;border-radius:7px;padding:9px 14px;font-weight:600}
QPushButton:hover{background:#10626A}
QPushButton#side{background:transparent;text-align:right;padding:12px 14px;color:#DBE9F7;border-radius:7px}
QPushButton#side:hover,QPushButton#side:checked{background:#214866;color:#FFFFFF}
QPushButton#secondary{background:#E9F1F7;color:#163B57}
QPushButton#danger{background:#A93E4A}
QLineEdit,QComboBox,QDateEdit,QTextEdit{background:white;border:1px solid #CCD8E5;border-radius:6px;padding:7px;color:#17324B;selection-background-color:#136C88}
QTableWidget{background:white;border:1px solid #DFE7F0;gridline-color:#EBEFF5;alternate-background-color:#F5FAFC;selection-background-color:#D9EEF0;selection-color:#113550;border-radius:8px}
QHeaderView::section{background:#E8EFF7;color:#203952;padding:9px;border:0;border-left:1px solid #D3E0EA;font-weight:600}
QLabel#heading{font-size:19pt;font-weight:700;color:#183353}
QLabel#muted{color:#60738C}
QPushButton#safe_exit{background:#176F68;color:white;text-align:center;border-radius:8px;padding:11px;font-weight:700}
QPushButton#safe_exit:hover{background:#105A55}
QPushButton:disabled{background:#B8CBD6;color:#536577}
QLineEdit:focus,QComboBox:focus,QDateEdit:focus{border:2px solid #188B97}
QScrollBar:vertical{background:#EEF3F7;width:13px;margin:0;border:0}
QScrollBar::handle:vertical{background:#A5BCC9;min-height:32px;border-radius:5px}
QScrollBar::handle:vertical:hover{background:#527A8F}
QToolTip{background:#FFFFFF;color:#17324B;border:1px solid #9EB7C7}
QDialog,QMessageBox{background-color:#F5F7FB;color:#172B49}
QTabWidget::pane{background:#FFFFFF;border:1px solid #CCD8E5;border-radius:7px}
QTabBar::tab{background:#E8EFF7;color:#1B3954;padding:10px 18px;border:1px solid #CCD8E5;border-bottom:0}
QTabBar::tab:selected{background:#FFFFFF;color:#116C77;font-weight:700}
QTabBar::tab:hover{background:#D8ECF2}
QComboBox,QLineEdit,QDateEdit,QTextEdit,QListWidget{background:#FFFFFF;color:#172B49;selection-background-color:#BFE4E8;selection-color:#102C42;min-height:22px}
QComboBox QAbstractItemView{background:#FFFFFF;color:#172B49;border:1px solid #8FAABB;selection-background-color:#D3ECF0;selection-color:#112D44;outline:0}
QComboBox QAbstractItemView::item{background:#FFFFFF;color:#172B49;padding:8px;min-height:24px}
QComboBox QAbstractItemView::item:selected{background:#D3ECF0;color:#112D44}
QComboBox::drop-down{background:#E6F1F5;border:0;border-left:1px solid #B3C5D2;width:24px}
QTableWidget{color:#172B49;selection-color:#113550;selection-background-color:#CCE7EC}
QTableWidget::item{color:#172B49;padding:4px}
QTableWidget::item:selected{background:#C5E6EA;color:#132C46}
QTableCornerButton::section{background:#E8EFF7}
QListWidget::item{color:#172B49;padding:6px}
QListWidget::item:selected{background:#C5E6EA;color:#132C46}
QCalendarWidget QWidget{background:#FFFFFF;color:#172B49}
QCalendarWidget QAbstractItemView{background:#FFFFFF;color:#172B49;selection-background-color:#B6DDE3;selection-color:#172B49}
QScrollArea{background:#FFFFFF;border:0}
QWidget#orderForm{background:#FFFFFF}
QCheckBox{color:#172B49}
QStatusBar{background:#E8EFF7;color:#17324B}
QLabel{color:#172B49}
QFrame#sidebar QLabel{color:#ECF5FB}
QLabel#reportTotals{color:#0E616E;background:#E4F4F4;padding:8px;border:1px solid #BDDDE1;border-radius:7px;font-weight:700}
QToolBar#primaryToolbar{background:#F2F8FA;border-bottom:1px solid #B9D4DE;spacing:4px;padding:4px}
QToolBar#primaryToolbar QToolButton{background:#E0F0F3;color:#13425D;border:1px solid #C0D9E1;border-radius:5px;padding:5px 8px;font-weight:600}
QToolBar#primaryToolbar QToolButton:hover{background:#BCE5EB;color:#103C51}
QToolBar#summaryToolbar{background:#E4F1F4;border-bottom:1px solid #C3DBE3;padding:3px;spacing:12px}
QLabel#toolbarMetric{background:#FFFFFF;color:#116F79;font-weight:700;padding:4px 7px;border:1px solid #D0E2E7;border-radius:5px}
'''

def nice_num(v):
    if v is None:return ''
    if isinstance(v,(int,float)):return f'{v:,.2f}' if isinstance(v,float) else str(v)
    return str(v)

def btn(text,callback,kind=''):
    b=QPushButton(text)
    if kind:b.setObjectName(kind)
    b.clicked.connect(callback)
    return b

def alert(parent,title,msg,critical=False):
    (QMessageBox.critical if critical else QMessageBox.information)(parent,title,str(msg))

def choose_path(parent,caption,suggest,filter_text):
    return QFileDialog.getSaveFileName(parent,caption,str(db.EXPORT_DIR/suggest),filter_text)[0]

class BarChart(QFrame):
    """Accessible chart rows that wrap complete names instead of clipping at 21 characters."""
    def __init__(self,title,parent=None):
        super().__init__(parent)
        self.setObjectName('card')
        self.title=title
        self.data=[]
        self.setMinimumWidth(330)
        self._root=QVBoxLayout(self)
        self._root.setContentsMargins(15,13,15,14)
        self._root.setSpacing(9)
        heading=QLabel(title)
        heading.setStyleSheet('color:#183353;font-weight:700;font-size:11pt')
        heading.setWordWrap(True)
        self._root.addWidget(heading)
        self._list=QVBoxLayout()
        self._list.setSpacing(9)
        self._root.addLayout(self._list)
        self._root.addStretch()

    def set_data(self, rows):
        self.data=list(rows)
        while self._list.count():
            item=self._list.takeAt(0)
            child_widget=item.widget()
            if child_widget:
                child_widget.hide()
                child_widget.setParent(None)
                child_widget.deleteLater()
            elif item.layout():
                while item.layout().count():
                    child=item.layout().takeAt(0)
                    if child.widget():child.widget().deleteLater()
        maxval=max((float(v or 0) for _,v in self.data[:8]),default=0) or 1
        if not self.data:
            msg=QLabel('لا توجد بيانات')
            msg.setObjectName('muted')
            self._list.addWidget(msg)
            return
        for name,quantity in self.data[:8]:
            line=QWidget(self)
            line.setObjectName('chartLine')
            layout=QHBoxLayout(line)
            layout.setContentsMargins(0,0,0,0)
            layout.setSpacing(10)
            full_name=str(name)
            text=QLabel(full_name)
            text.setWordWrap(True)
            text.setToolTip(full_name)
            text.setMinimumWidth(180)
            text.setMaximumWidth(285)
            text.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.MinimumExpanding)
            text.setStyleSheet('color:#233B52;font-size:9pt;')
            # Allow several lines on long product names; never truncate the original name.
            fm=text.fontMetrics()
            box=fm.boundingRect(0,0,190,2000,int(Qt.TextFlag.TextWordWrap),full_name)
            text.setMinimumHeight(max(29,min(140,box.height()+9)))
            progress=QProgressBar()
            progress.setRange(0,1000)
            progress.setValue(round(max(0,float(quantity or 0))/maxval*1000))
            progress.setTextVisible(False)
            progress.setFixedHeight(12)
            progress.setStyleSheet('QProgressBar{border:0;border-radius:5px;background:#E8F3F6;}QProgressBar::chunk{background:#159B98;border-radius:5px;}')
            amount=QLabel(nice_num(quantity))
            amount.setMinimumWidth(62)
            amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
            amount.setStyleSheet('color:#116F79;font-weight:600')
            layout.addWidget(text,4)
            layout.addWidget(progress,3)
            layout.addWidget(amount,1)
            self._list.addWidget(line)
        self.updateGeometry()

class OrderDialog(QDialog):
    def __init__(self,parent, cx, oid=None):
        super().__init__(parent);self.cx=cx;self.oid=oid;self.setWindowTitle('بيانات العميل والعقد');self.resize(760,680)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout=QVBoxLayout(self); tabs=QTabWidget();layout.addWidget(tabs)
        editor=QWidget();editor.setObjectName('orderForm');form=QFormLayout(editor);form.setSpacing(9);form.setContentsMargins(17,17,17,17);self.fields={}
        labels={
            'client_name':'اسم العميل *','material_type':'نوع المادة *','porcelain_color':'لون / نوع الرخام أو البورسلان','sqm':'المساحة م²','linear_m':'الطول م/ط','thickness_mm':'السماكة (مم)','phone':'رقم التواصل',
            'invoice_amount':'مبلغ الفاتورة','install_date':'تاريخ التركيب (YYYY-MM-DD)','invoice_no':'رقم الفاتورة',
            'contract_no':'رقم العقد','boards':'الألواح','glue_type':'نوع الغراء','glue_qty':'كمية الغراء','honeycomb':'هانيكام','status':'حالة التركيب','notes':'ملاحظات'
        }
        values=dict(cx.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()) if oid else {}
        for k,label in labels.items():
            if k=='notes':w=QTextEdit();w.setMaximumHeight(90);w.setPlainText(values.get(k,'') or '')
            elif k=='material_type':
                w=QComboBox()
                w.addItems(['رخام','بورسلان'])
                w.setCurrentText(values.get(k) or 'بورسلان')
            elif k=='status':w=QComboBox();w.addItems(STATES);w.setCurrentText(values.get(k) or 'غير محدد')
            elif k=='install_date':
                w=QDateEdit();w.setCalendarPopup(True);w.setDisplayFormat('yyyy-MM-dd')
                w.setMinimumDate(QDate(1900,1,1));w.setSpecialValueText('غير محدد')
                value=values.get(k)
                w.setDate(QDate.fromString(value,'yyyy-MM-dd') if value else w.minimumDate())
            elif k in ('porcelain_color','glue_type','boards','honeycomb'):
                cat={'porcelain_color':'بورسلان','glue_type':'غراء','boards':'ألواح','honeycomb':'هانيكام'}[k]
                w=QComboBox();w.setEditable(True);w.addItem('')
                for item in inv.items(cx,cat):w.addItem(item['name'])
                if values.get(k):w.setCurrentText(str(values[k]))
                w.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            else:
                w=QLineEdit();value=values.get(k)
                w.setText(str(value) if value is not None else '')
                if k in ('sqm','linear_m','invoice_amount','glue_qty','thickness_mm'):w.setPlaceholderText('مثال: 12.50')
            self.fields[k]=w;form.addRow(label,w)
        self.fields['material_type'].currentTextChanged.connect(
            lambda _unused: self.refresh_material_color_options(clear=True))
        self.refresh_material_color_options(clear=False)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(editor);tabs.addTab(scroll,'البيانات الأساسية')
        att_widget=QWidget();att_layout=QVBoxLayout(att_widget)
        self.att_list=QListWidget()
        self.att_list.itemDoubleClicked.connect(lambda *_:self.preview())
        att_layout.addWidget(self.att_list)
        actions=QHBoxLayout()
        actions.addWidget(btn('إضافة ملف PDF أو صورة',self.attach))
        actions.addWidget(btn('معاينة المرفق',self.preview,'secondary'))
        actions.addWidget(btn('فتح الملف',self.open_attachment,'secondary'))
        actions.addWidget(btn('إزالة المرفق المحدد',self.remove_attachment,'danger'))
        att_layout.addLayout(actions)
        self.att_status=QLabel('يمكن حفظ مرفقات متعددة لكل عقد ومعاينة جميع صفحات PDF أو فتح الملف بتطبيق النظام.')
        self.att_status.setObjectName('muted')
        self.att_status.setWordWrap(True)
        att_layout.addWidget(self.att_status)
        tabs.addTab(att_widget,'المرفقات')
        self.reload_attachments()
        foot=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        foot.button(QDialogButtonBox.StandardButton.Save).setText('حفظ');foot.button(QDialogButtonBox.StandardButton.Cancel).setText('إلغاء')
        foot.accepted.connect(self.save);foot.rejected.connect(self.reject);layout.addWidget(foot)

    def refresh_material_color_options(self,clear=False):
        color_box=self.fields['porcelain_color']
        previous='' if clear else color_box.currentText()
        cat=self.fields['material_type'].currentText()
        color_box.blockSignals(True)
        try:
            color_box.clear()
            color_box.addItem('')
            for record in inv.items(self.cx,cat):
                color_box.addItem(record['name'])
            color_box.setCurrentText(previous)
        finally:
            color_box.blockSignals(False)

    def values(self):
        d={}
        for key,w in self.fields.items():
            raw=(('' if w.date()==w.minimumDate() else w.date().toString('yyyy-MM-dd')) if isinstance(w,QDateEdit) else
                 w.currentText() if isinstance(w,QComboBox) else
                 w.toPlainText() if isinstance(w,QTextEdit) else w.text())
            raw=raw.strip()
            if key in ('sqm','linear_m','invoice_amount','glue_qty','thickness_mm'):
                if not raw:d[key]=None
                else:
                    from decimal import Decimal, InvalidOperation
                    try:
                        amount=Decimal(raw.replace(',',''))
                        maximum=2 if key=='invoice_amount' else 3
                        if not amount.is_finite() or amount<0 or amount != amount.quantize(Decimal(1).scaleb(-maximum)):
                            raise ValueError(f'القيمة في {key} لا تقبل رقمًا سالبًا أو أكثر من {maximum} خانات عشرية')
                        d[key]=float(amount)
                    except (InvalidOperation,ValueError) as e:raise ValueError('القيمة غير صحيحة في '+key+': '+str(e))
            else:d[key]=raw if raw else ('' if key=='notes' else None)
        if not d['client_name']:raise ValueError('يرجى كتابة اسم العميل')
        if d['install_date']:
            try:dt.date.fromisoformat(d['install_date'])
            except ValueError:raise ValueError('اكتب تاريخ التركيب بصيغة YYYY-MM-DD')
        return d

    def save(self):
        try:self.oid=db.save_order(self.cx,self.values(),self.oid);self.accept()
        except (ValueError,sqlite3.Error) as e:alert(self,'تنبيه',e,True)

    def reload_attachments(self):
        self.att_list.clear()
        if not self.oid:return
        for row in self.cx.execute('SELECT * FROM attachments WHERE order_id=? ORDER BY id',(self.oid,)).fetchall():
            found=db.resolve_attachment(row)
            item=QListWidgetItem(('✓ ' if found else '⚠ ') + row['display_name'] + ('' if found else ' [الملف الأصلي غير مربوط]'))
            item.setData(Qt.ItemDataRole.UserRole,row['id'])
            item.setToolTip(str(found) if found else 'مرجع قديم: '+str(row['original_reference'] or ''))
            self.att_list.addItem(item)

    def attach(self):
        # Selecting files first avoids saving a new customer when file selection is cancelled.
        paths=QFileDialog.getOpenFileNames(self,'اختر المستندات أو الصور','','Documents (*.pdf *.png *.jpg *.jpeg *.bmp *.webp *.gif)')[0]
        if not paths:return
        try:
            values=self.values()
            # Persist current form edits before attaching; prevents a partly saved customer.
            self.oid=db.save_order(self.cx,values,self.oid)
        except (ValueError,sqlite3.Error) as e:
            alert(self,'يرجى تصحيح بيانات العميل',e,True)
            return
        successes=0;failed=[]
        for path in paths:
            try:
                db.add_attachment(self.cx,self.oid,path)
                successes+=1
            except Exception as e:failed.append(f'{Path(path).name}: {e}')
        self.reload_attachments()
        self.att_status.setText(f'تم حفظ بيانات العميل وإضافة {successes} مرفق. '+('أخطاء: '+'؛ '.join(failed) if failed else 'يمكن المعاينة أو متابعة التحرير.'))
        if failed:alert(self,'تعذر إضافة بعض المرفقات','\n'.join(failed),True)

    def remove_attachment(self):
        item=self.att_list.currentItem()
        if not item:
            alert(self,'المرفقات','اختر مرفقًا لإزالته من القائمة.')
            return
        if QMessageBox.question(self,'تأكيد إزالة المرفق',
            'سيُزال هذا المرفق من سجل العميل. هل تريد الاستمرار؟',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:
            db.remove_attachment(self.cx,item.data(Qt.ItemDataRole.UserRole))
            self.reload_attachments()
            self.att_status.setText('تم حذف ربط المرفق المحدد، مع الحفاظ على الملفات الأخرى.')
        except Exception as exc:alert(self,'تعذرت إزالة المرفق',exc,True)

    def attachment_path(self):
        item=self.att_list.currentItem()
        if not item:
            alert(self,'المرفقات','حدد المرفق أولًا.')
            return None
        row=self.cx.execute('SELECT * FROM attachments WHERE id=?',
                            (item.data(Qt.ItemDataRole.UserRole),)).fetchone()
        path=db.resolve_attachment(row) if row else None
        if not path:
            alert(self,'المرفقات','المرجع محفوظ لكن الملف الأصلي غير موجود؛ يرجى ربط الملف.')
        return path

    def open_attachment(self):
        path=self.attachment_path()
        if path:
            import attachment_viewer
            return attachment_viewer.open_native(self,path)
        return False

    def preview(self):
        path=self.attachment_path()
        if path:
            import attachment_viewer
            return attachment_viewer.preview(self,path)
        return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.cx=db.connect();db.setup(self.cx);inv.init(self.cx);company.init(self.cx)
        self.setWindowTitle('ProTech Stone Manager | إدارة الرخام والبورسلان');self.resize(1420,850)
        self.search_timer=QTimer(self);self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(220);self.search_timer.timeout.connect(self.refresh_table)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        central=QWidget();self.setCentralWidget(central);shell=QHBoxLayout(central);shell.setContentsMargins(0,0,0,0);shell.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(235);sl=QVBoxLayout(sidebar);sl.setContentsMargins(14,22,14,20)
        brand=QLabel('ProTech');brand.setStyleSheet('color:white;font-size:20pt;font-weight:700');brand.setWordWrap(True);brand.setMaximumHeight(100);self.brand_label=brand;sl.addWidget(brand)
        sub=QLabel('Marble & Porcelain Manager');sub.setStyleSheet('color:#94B5C8');sl.addWidget(sub)
        self.company_logo_side=QLabel();self.company_logo_side.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.company_logo_side.setMaximumHeight(90);sl.addWidget(self.company_logo_side);sl.addSpacing(15)
        self.pages=QStackedWidget();self.nav=[]
        for title,fn in [('لوحة التحكم',self.dashboard_page),('العملاء والعقود',self.orders_page),('التقارير والتصدير',self.reports_page),('الأصناف والألوان',self.catalog_page),('حركة المخزون',self.stock_page),('الإعدادات',self.settings_page),('حول البرنامج',self.about_page)]:
            w=fn();self.pages.addWidget(w)
            index=self.pages.count()-1
            b=btn(title,lambda _checked=False,i=index:self.switch(i),'side');b.setCheckable(True);sl.addWidget(b);self.nav.append(b)
        sl.addStretch(1)
        ## Public edition intentionally has no imported private Excel source rows.
        ## Public edition adds attachments directly per customer; no legacy private PDF references.
        sl.addWidget(btn('نسخة احتياطية',self.backup,'side'))
        sl.addWidget(btn('استعادة نسخة',self.restore,'side'))
        sl.addWidget(btn('خروج آمن',self.close,'safe_exit'))
        version=QLabel('الإصدار 2.0.0  •  Offline');version.setStyleSheet('color:#88A6BC;font-size:9pt');sl.addWidget(version)
        shell.addWidget(sidebar);shell.addWidget(self.pages,1)
        self.create_top_toolbar()
        self._last_data_version=self.cx.execute('PRAGMA data_version').fetchone()[0]
        self.data_monitor=QTimer(self)
        self.data_monitor.setInterval(3500)
        self.data_monitor.timeout.connect(self.poll_data_version)
        self.data_monitor.start()
        self.statusBar().showMessage('قاعدة البيانات: '+str(db.DB))
        self.apply_company_identity()
        self.switch(0);self.refresh()

    def create_top_toolbar(self):
        bar=QToolBar('الاختصارات',self)
        bar.setObjectName('primaryToolbar')
        bar.setMovable(False)
        bar.setFloatable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea,bar)
        self.quick_toolbar=bar
        actions=[
            ('الرئيسية',lambda:self.switch(0)),
            ('العملاء',lambda:self.switch(1)),
            ('عميل جديد',lambda:self.open_order(None)),
            ('تعديل المحدد',self.edit_selected),
            ('تقرير العميل',self.report_selected_customer),
            ('معاينة تقرير',lambda:(self.switch(2),self.report_center.preview_pdf())),
            ('حفظ PDF',lambda:(self.switch(2),self.report_center.export('pdf'))),
            ('تصدير Excel',lambda:(self.switch(2),self.report_center.export('xlsx'))),
            ('الأصناف',lambda:self.switch(3)),
            ('المخزون',lambda:self.switch(4)),
            ('تحديث',self.refresh),
            ('نسخة احتياطية',self.backup)
        ]
        for label,call in actions:
            action=QAction(label,self)
            action.triggered.connect(lambda checked=False,fn=call:fn())
            bar.addAction(action)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        totals=QToolBar('المجاميع المباشرة',self)
        totals.setObjectName('summaryToolbar')
        totals.setMovable(False)
        totals.setFloatable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea,totals)
        self.totals_toolbar=totals
        self.summary_widgets={}
        for key,title in [('count','العقود'),('sqm','م²'),('linear','م/ط'),('amount','ر.س')]:
            widget=QLabel(title+': —')
            widget.setObjectName('toolbarMetric')
            widget.setMinimumWidth(90)
            totals.addWidget(widget)
            self.summary_widgets[key]=widget
        # The main filter controls the quick-summary. Changes on every page also refresh it.

    def poll_data_version(self):
        current=self.cx.execute('PRAGMA data_version').fetchone()[0]
        if current!=self._last_data_version:
            self._last_data_version=current
            self.refresh()

    def switch(self,idx):
        self.pages.setCurrentIndex(idx)
        for j,b in enumerate(self.nav):b.setChecked(j==idx)
        if idx==0:self.refresh_dashboard()
        if idx==2:self.refresh_report_label()
        if idx==3:self.catalog.refresh()
        if idx==4:self.stock.refresh()

    def catalog_page(self):
        from inventory_ui import CatalogPane
        self.catalog=CatalogPane(self)
        return self.catalog

    def stock_page(self):
        from inventory_ui import StockPane
        self.stock=StockPane(self)
        return self.stock

    def settings_page(self):
        from company_settings import SettingsPane
        self.settings=SettingsPane(self)
        return self.settings

    def apply_company_identity(self):
        profile=company.get(self.cx)
        name=profile['company_name'] or 'ProTech'
        self.brand_label.setText(name)
        self.setWindowTitle(f'{name} | ProTech Marble & Porcelain Manager')
        logo=company.logo_path(self.cx)
        if hasattr(self,'company_logo_side'):
            if logo:
                pix=QPixmap(str(logo))
                self.company_logo_side.setPixmap(pix.scaled(QSize(160,90),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            else:self.company_logo_side.setPixmap(QPixmap())

    def about_page(self):
        p=QWidget();root=QVBoxLayout(p);root.setContentsMargins(32,24,32,24)
        brand=QLabel('ProTech');brand.setStyleSheet('font-size:32pt;font-weight:800;color:#157C84')
        root.addWidget(brand)
        root.addWidget(QLabel('ProTech Marble & Porcelain Manager — الإصدار 2.0.0'))
        root.addWidget(QLabel('المطور: Abu Omar — ProTech'))
        developer_email=QLabel('البريد الإلكتروني للمطور: protech.2025.2026@gmail.com')
        developer_phone=QLabel('هاتف المطور: +966 50 327 6927')
        for lbl in (developer_email,developer_phone):
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lbl.setStyleSheet('font-size:12pt;font-weight:600;color:#172B49;padding:5px')
            root.addWidget(lbl)
        root.addWidget(QLabel('إدارة الرخام والبورسلان: العملاء والعقود والأصناف والمخزون والتقارير'))
        root.addSpacing(35)
        rights=QLabel('حقوق التصميم والتطوير محفوظة: Abu Omar — ProTech')
        rights.setStyleSheet('font-size:11pt;font-weight:700;color:#163F53;background:#EAF3F5;padding:15px')
        root.addWidget(rights)
        root.addStretch()
        return p

    def card(self,label):
        c=QFrame();c.setObjectName('card');l=QVBoxLayout(c)
        t=QLabel(label);t.setObjectName('cardTitle');value=QLabel('—');value.setObjectName('cardValue')
        l.addWidget(t);l.addWidget(value);l.addStretch(1);return c,value

    def dashboard_page(self):
        from dashboard_plus import Dashboard
        self.dashboard_plus=Dashboard(self)
        return self.dashboard_plus

    def dashboard_page_legacy(self):
        p=QWidget();root=QVBoxLayout(p);root.setContentsMargins(22,18,22,22);root.setSpacing(14)
        root.addWidget(self.heading('لوحة التحكم','ملخص مباشر لجميع العقود والفواتير والمواد'))
        grid=QGridLayout();grid.setSpacing(12)
        self.cards={}
        for i,(key,title) in enumerate([('orders','إجمالي سجلات العملاء'),('total','قيمة الفواتير (ر.س)'),('invoiced','فواتير بقيم مسجلة'),('attachments','مراجع المرفقات'),('verified','ملفات مربوطة فعليًا'),('reviews','صفوف بحاجة للمراجعة')]):
            card,val=self.card(title);self.cards[key]=val;grid.addWidget(card,i//3,i%3)
        root.addLayout(grid)
        row=QHBoxLayout();self.colors_plot=BarChart('الألوان الأكثر استخدامًا');self.months_plot=BarChart('قيمة الفواتير حسب شهر التركيب')
        row.addWidget(self.colors_plot);row.addWidget(self.months_plot);root.addLayout(row,1)
        hint=QLabel('ملاحظة: حالة التركيبات غير محددة في Excel؛ لا يتم اعتبارها مكتملة تلقائيًا.');hint.setObjectName('muted');root.addWidget(hint)
        return p

    def heading(self,title,description):
        f=QFrame();v=QVBoxLayout(f);v.setContentsMargins(0,0,0,5)
        h=QLabel(title);h.setObjectName('heading');v.addWidget(h)
        s=QLabel(description);s.setObjectName('muted');v.addWidget(s);return f

    def orders_page(self):
        p=QWidget();root=QVBoxLayout(p);root.setContentsMargins(22,18,22,22);root.setSpacing(12)
        root.addWidget(self.heading('العملاء والعقود','بحث وفلترة وتحرير وتوثيق لجميع السجلات'))
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('ابحث بالاسم أو رقم العميل أو العقد أو الهاتف أو الفاتورة أو اللون...')
        self.search.textChanged.connect(self.queue_refresh_table);filters.addWidget(self.search,3)
        self.color=QComboBox();self.color.addItem('جميع الألوان','');self.color.currentIndexChanged.connect(self.refresh_table);filters.addWidget(self.color,2)
        self.state=QComboBox();self.state.addItem('جميع الحالات','');
        for st in STATES:self.state.addItem(st,st)
        self.state.currentIndexChanged.connect(self.refresh_table);filters.addWidget(self.state,1)
        root.addLayout(filters)
        datefilters=QHBoxLayout();self.use_dates=QCheckBox('تفعيل فترة التركيب');self.use_dates.toggled.connect(self.refresh_table);datefilters.addWidget(self.use_dates)
        self.from_date=QDateEdit();self.from_date.setCalendarPopup(True);self.from_date.setDate(QDate(2026,1,1));self.from_date.setDisplayFormat('yyyy-MM-dd');self.from_date.dateChanged.connect(self.refresh_table)
        self.to_date=QDateEdit();self.to_date.setCalendarPopup(True);self.to_date.setDate(QDate.currentDate());self.to_date.setDisplayFormat('yyyy-MM-dd');self.to_date.dateChanged.connect(self.refresh_table)
        datefilters.addWidget(QLabel('من'));datefilters.addWidget(self.from_date);datefilters.addWidget(QLabel('إلى'));datefilters.addWidget(self.to_date)
        self.min_amount=QLineEdit();self.min_amount.setPlaceholderText('أقل مبلغ');self.min_amount.setFixedWidth(100);self.min_amount.textChanged.connect(self.refresh_table)
        self.max_amount=QLineEdit();self.max_amount.setPlaceholderText('أعلى مبلغ');self.max_amount.setFixedWidth(100);self.max_amount.textChanged.connect(self.refresh_table)
        datefilters.addWidget(self.min_amount);datefilters.addWidget(self.max_amount);datefilters.addStretch();root.addLayout(datefilters)
        toolbar=QHBoxLayout();toolbar.addWidget(btn('إضافة عميل / طلب',lambda:self.open_order(None)))
        toolbar.addWidget(btn('تعديل السجل',self.edit_selected,'secondary'))
        toolbar.addWidget(btn('تقرير العميل المحدد',self.report_selected_customer,'secondary'))
        toolbar.addWidget(btn('خيارات العميل ▾',self.show_selected_context_menu,'secondary'))
        toolbar.addWidget(btn('حذف السجل',self.delete_selected,'danger'))
        toolbar.addWidget(btn('تحديث',self.refresh,'secondary'));toolbar.addStretch()
        self.count_label=QLabel('');toolbar.addWidget(self.count_label);root.addLayout(toolbar)
        self.table=QTableWidget();self.table.setColumnCount(len(db.HEADERS_AR));self.table.setHorizontalHeaderLabels(db.HEADERS_AR)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True);self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(120)
        self.table.setColumnWidth(1,245)
        self.table.setColumnWidth(2,230)
        self.table.setColumnWidth(11,190)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.doubleClicked.connect(self.edit_selected)
        # Handle the viewport directly: QAbstractScrollArea can swallow the
        # table-level customContextMenuRequested signal on right mouse press.
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.table.viewport().setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.table.viewport().installEventFilter(self)
        self.table.setMinimumHeight(300)
        root.addWidget(self.table,1)
        return p

    def reports_page(self):
        from report_center import ReportCenter
        self.report_center=ReportCenter(self)
        return self.report_center

    def reports_page_legacy(self):
        p=QWidget();root=QVBoxLayout(p);root.setContentsMargins(22,18,22,22);root.setSpacing(15)
        root.addWidget(self.heading('التقارير والتصدير','تصدير البيانات المفلترة أو إعداد تقرير ملخص كامل'))
        self.rep_label=QLabel('');root.addWidget(self.rep_label)
        root.addWidget(btn('تصدير السجلات المفلترة إلى Excel',lambda:self.export('xlsx')))
        root.addWidget(btn('تصدير السجلات المفلترة إلى PDF',lambda:self.export('pdf')))
        root.addWidget(btn('تصدير السجلات المفلترة إلى CSV',lambda:self.export('csv')))
        root.addWidget(btn('تصدير ملخص الألوان والمواد (Excel)',self.export_materials))
        root.addWidget(QLabel('يتم تطبيق فلاتر صفحة العملاء والعقود على التقارير التفصيلية.'))
        root.addStretch();return p

    def selected_id(self):
        items=self.table.selectedItems()
        if not items:return None
        first=self.table.item(items[0].row(),0)
        return int(first.data(Qt.ItemDataRole.UserRole)) if first else None

    def eventFilter(self,obj,event):
        if (hasattr(self,'table') and obj is self.table.viewport()
            and event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.ContextMenu)):
            is_right_press=(event.type()==QEvent.Type.MouseButtonPress
                            and event.button()==Qt.MouseButton.RightButton)
            if is_right_press or event.type()==QEvent.Type.ContextMenu:
                # A menu already visible prevents duplicate menus on Windows
                # when it dispatches ContextMenu after MouseButtonPress.
                if getattr(self,'_customer_popup',None) is not None and self._customer_popup.isVisible():
                    return True
                pos=event.position().toPoint() if is_right_press else event.pos()
                self.customer_context_menu(pos)
                return True
        return super().eventFilter(obj,event)

    def customer_context_menu(self,pos):
        # Right-click on *any* cell of a row, including an unselected row.
        index=self.table.indexAt(pos)
        if index.isValid():
            row=index.row()
            self.table.setCurrentCell(row,0)
            self.table.selectRow(row)
        else:
            row=self.table.currentRow()
            if row<0:return False
        item=self.table.item(row,0)
        if not item:return False
        oid=item.data(Qt.ItemDataRole.UserRole)
        if oid is None:return False
        self._context_order_id=int(oid)
        menu=self.build_customer_menu(int(oid))
        self._customer_popup=menu
        menu.aboutToHide.connect(lambda m=menu:QTimer.singleShot(0,lambda:self.clear_customer_popup(m)))
        # Non-modal popup avoids the nested event loop that had prevented
        # the context menu from appearing on some Windows / Qt combinations.
        menu.popup(self.table.viewport().mapToGlobal(pos))
        return True

    def clear_customer_popup(self,menu):
        if getattr(self,'_customer_popup',None) is menu:
            self._customer_popup=None
        menu.deleteLater()

    def show_selected_context_menu(self):
        row=self.table.currentRow()
        if row<0 or not self.table.item(row,0):
            alert(self,'اختر العميل','حدد العميل من الجدول أولًا لعرض خياراته.')
            return False
        self.table.scrollTo(self.table.model().index(row,0))
        return self.customer_context_menu(self.table.visualRect(self.table.model().index(row,0)).center())

    def build_customer_menu(self,oid):
        menu=QMenu(self)
        menu.setObjectName('customerContextMenu')
        menu.setStyleSheet('QMenu{background:#FFFFFF;color:#19324B;border:1px solid #AEC9D4;'
                           'padding:5px;min-width:260px;font-size:10pt}'
                           'QMenu::item{padding:9px 24px;background:#FFFFFF;color:#19324B}'
                           'QMenu::item:selected{background:#D5ECF1;color:#0E4D65}'
                           'QMenu::separator{height:1px;background:#C9DDE5;margin:6px 8px}')
        actions=[
            ('تعديل بيانات العميل',lambda:self.open_order(oid)),
            ('عرض مرفقات العميل',lambda:self.open_customer_attachments(oid)),
            ('عرض تفاصيل المواد والكميات',lambda:self.customer_report_action(oid,'materials')),
            ('معاينة تقرير PDF',lambda:self.customer_report_action(oid,'preview')),
            ('حفظ تقرير PDF',lambda:self.customer_report_action(oid,'pdf')),
            ('تصدير تقرير Excel',lambda:self.customer_report_action(oid,'xlsx')),
            ('تصدير تقرير CSV',lambda:self.customer_report_action(oid,'csv')),
            ('طباعة تقرير العميل',lambda:self.customer_report_action(oid,'print')),
            ('نسخ بيانات العميل',lambda:self.copy_customer_summary(oid)),
            ('تحديث البيانات',self.refresh),
            ('نسخة احتياطية',self.backup),
            ('حذف السجل بعد التأكيد',lambda:self.delete_selected(oid))
        ]
        for i,(label,callback) in enumerate(actions):
            if i in (2,3,8,10):menu.addSeparator()
            action=menu.addAction(label)
            action.triggered.connect(lambda checked=False,fn=callback:fn())
        return menu

    def open_customer_attachments(self,oid):
        dlg=OrderDialog(self,self.cx,oid)
        dlg.findChild(QTabWidget).setCurrentIndex(1)
        dlg.exec()
        self.refresh()

    def customer_report_action(self,oid,kind):
        self.report_center.select_customer(oid)
        self.switch(2)
        if kind=='preview':self.report_center.preview_pdf()
        elif kind=='materials':self.report_center.refresh_table()
        elif kind=='print':self.report_center.print_report()
        else:self.report_center.export(kind)

    def copy_customer_summary(self,oid):
        r=self.cx.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if r:
            QApplication.clipboard().setText(
                f"العميل: {r['client_name']}\nالهاتف: {r['phone'] or ''}\n"
                f"العقد: {r['contract_no'] or ''}\nالفاتورة: {r['invoice_no'] or ''}"
            )

    def report_selected_customer(self):
        oid=self.selected_id()
        if not oid:
            alert(self,'اختر العميل','حدد سجل العميل أولًا ثم اطبع أو صدّر تقريره.')
            return
        self.switch(2)
        self.report_center.select_customer(oid)

    def report_selected_item(self,item_id,stock=False):
        if not item_id:
            alert(self,'اختر الصنف','حدد صنفًا من القائمة لإنشاء تقريره.')
            return
        self.switch(2)
        self.report_center.select_item(item_id,stock)

    def edit_selected(self,*_):
        oid=self.selected_id()
        if not oid:alert(self,'تحديد السجل','اختر عميلًا من الجدول أولًا');return
        self.open_order(oid)

    def open_order(self,oid):
        dlg=OrderDialog(self,self.cx,oid)
        dlg.exec()
        # Attachments may have been saved before the user closes the editor.
        self.refresh()

    def delete_selected(self,oid=None):
        if isinstance(oid,bool):oid=None
        oid=oid or self.selected_id()
        if not oid:alert(self,'تحديد السجل','اختر سجلًا من الجدول أولًا');return
        if QMessageBox.question(self,'تأكيد الحذف','سيُحذف السجل ومراجع المرفقات من قاعدة البيانات. هل تريد الاستمرار؟')==QMessageBox.StandardButton.Yes:
            db.delete_order(self.cx,oid);self.refresh()

    def queue_refresh_table(self,*_):
        self.search_timer.start()

    def filtered(self):
        dfrom=self.from_date.date().toString('yyyy-MM-dd') if self.use_dates.isChecked() else ''
        dto=self.to_date.date().toString('yyyy-MM-dd') if self.use_dates.isChecked() else ''
        def number(t):
            try:return float(t.replace(',','')) if t.strip() else None
            except ValueError:return None
        return db.all_orders(self.cx,self.search.text().strip(),self.color.currentData() or '',self.state.currentData() or '',dfrom,dto,number(self.min_amount.text()),number(self.max_amount.text()))

    def refresh_table(self,*_):
        if not hasattr(self,'table'):return
        records=self.filtered()
        self.table.setSortingEnabled(False);self.table.setRowCount(len(records))
        for ri,r in enumerate(records):
            for ci,key in enumerate(db.COLUMNS):
                t=QTableWidgetItem(nice_num(r[key]));t.setForeground(QColor('#172B49'));t.setToolTip(nice_num(r[key]));t.setData(Qt.ItemDataRole.UserRole,r['id'] if ci==0 else None)
                if ci in (0,3,4,6,12,13):t.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(ri,ci,t)
        self.table.setSortingEnabled(True)
        stats=live_metrics.summarize_orders(records)
        self.count_label.setText(live_metrics.orders_line(stats))
        if hasattr(self,'summary_widgets'):
            for key,title in [('count','العقود'),('sqm','م²'),('linear','م/ط'),('amount','ر.س')]:
                digits=0 if key=='count' else 2
                value=stats[key]
                self.summary_widgets[key].setText(f'{title}: {value:,.{digits}f}')
            if hasattr(self,'report_center') and self.pages.currentIndex()==2:
                self.report_center.refresh_table()

    def refresh_dashboard(self):
        if hasattr(self,'dashboard_plus'):
            self.dashboard_plus.refresh()
            return
        if not hasattr(self,'cards'):return
        summary=db.summary(self.cx)
        for k,v in summary.items():
            if k in self.cards:self.cards[k].setText(f'{v:,.2f}' if k=='total' else str(v))
        colors=self.cx.execute('SELECT COALESCE(porcelain_color,\'غير محدد\') as c,COUNT(*) n FROM orders GROUP BY c ORDER BY n DESC LIMIT 8').fetchall()
        months=self.cx.execute("SELECT SUBSTR(install_date,1,7) m,ROUND(SUM(invoice_amount),2) a FROM orders WHERE install_date IS NOT NULL AND invoice_amount IS NOT NULL GROUP BY m ORDER BY m DESC LIMIT 8").fetchall()
        self.colors_plot.set_data([(x['c'],x['n']) for x in colors]);self.months_plot.set_data([(x['m'],x['a']) for x in reversed(months)])

    def refresh(self):
        selected_color=self.color.currentData()
        self.color.blockSignals(True);self.color.clear();self.color.addItem('جميع الألوان','')
        for r in self.cx.execute('SELECT DISTINCT porcelain_color FROM orders WHERE porcelain_color IS NOT NULL AND TRIM(porcelain_color)!=\'\' ORDER BY porcelain_color'):
            self.color.addItem(r[0],r[0])
        ind=self.color.findData(selected_color);self.color.setCurrentIndex(ind if ind>=0 else 0);self.color.blockSignals(False)
        self.refresh_table();self.refresh_dashboard();self.refresh_report_label()
        if hasattr(self,'_last_data_version'):
            self._last_data_version=self.cx.execute('PRAGMA data_version').fetchone()[0]
        if hasattr(self,'catalog'):self.catalog.refresh()
        if hasattr(self,'stock'):self.stock.refresh()

    def refresh_report_label(self):
        if hasattr(self,'report_center'):self.report_center.refresh_table()
        if hasattr(self,'rep_label'):
            rows=self.filtered();self.rep_label.setText(f'التقرير الحالي: {len(rows)} سجل | إجمالي الفواتير {sum(r["invoice_amount"] or 0 for r in rows):,.2f} ر.س')

    def export(self,fmt):
        rows=self.filtered();today=dt.date.today().isoformat();target=choose_path(self,'حفظ التقرير',f'Porcelain_Report_{today}.{fmt}',{'xlsx':'Excel (*.xlsx)','pdf':'PDF (*.pdf)','csv':'CSV (*.csv)'}[fmt])
        if not target:return
        try:
            if fmt=='csv':
                with open(target,'w',encoding='utf-8-sig',newline='') as f:
                    out=csv.writer(f);out.writerow(db.HEADERS_AR);out.writerows([r[k] for k in db.COLUMNS] for r in rows)
            elif fmt=='xlsx':
                import xlsxwriter
                with xlsxwriter.Workbook(target) as wb:
                    ws=wb.add_worksheet('العقود');ws.right_to_left();h=wb.add_format({'bold':True,'bg_color':'#157A83','font_color':'white','align':'center'});money=wb.add_format({'num_format':'#,##0.00'})
                    for j,s in enumerate(db.HEADERS_AR):ws.write(0,j,s,h)
                    for i,r in enumerate(rows,1):
                        for j,k in enumerate(db.COLUMNS):
                            v=r[k]
                            if v is None:continue
                            if isinstance(v,(int,float)):ws.write_number(i,j,v,money if k=='invoice_amount' else None)
                            else:ws.write_string(i,j,str(v))
                    ws.set_column(0,0,9);ws.set_column(1,2,27);ws.set_column(3,15,18)
                    if rows:ws.autofilter(0,0,len(rows),len(db.COLUMNS)-1)
                    ws.freeze_panes(1,0)
            else:self.export_pdf(target,rows)
            alert(self,'تم تصدير التقرير',str(target))
        except Exception as e:alert(self,'تعذر التصدير',e,True)

    def export_pdf(self,path,rows):
        printer=QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat);printer.setOutputFileName(str(path))
        from PySide6.QtGui import QPageSize
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        from PySide6.QtGui import QPageLayout
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        head=''.join(f'<th>{html.escape(s)}</th>' for s in db.HEADERS_AR[:12])
        body=''.join('<tr>'+''.join(f'<td>{html.escape(nice_num(r[k]))}</td>' for k in db.COLUMNS[:12])+'</tr>' for r in rows)
        tpl=f'''<html dir="rtl"><head><meta charset="utf-8"><style>
            body{{font-family:Tahoma,'Segoe UI',Arial;font-size:8pt;direction:rtl}}
            h2{{color:#147A84}}table{{width:100%;border-collapse:collapse}}th{{background:#147A84;color:white}}
            td,th{{border:1px solid #CCD8E5;padding:4px}}tr:nth-child(even){{background:#EDF4F8}}
        </style></head><body><h2>تقرير العملاء والعقود - ProTech</h2>
        <p>تاريخ التقرير: {dt.date.today().isoformat()} | عدد السجلات: {len(rows)} | إجمالي الفواتير: {sum(r['invoice_amount'] or 0 for r in rows):,.2f} ر.س</p>
        <table><tr>{head}</tr>{body}</table></body></html>'''
        doc=QTextDocument();doc.setHtml(tpl);doc.print_(printer)

    def export_materials(self):
        path=choose_path(self,'تقرير استهلاك المواد','Porcelain_Materials.xlsx','Excel (*.xlsx)')
        if not path:return
        try:
            import xlsxwriter
            with xlsxwriter.Workbook(path) as w:
                for sheet_name,sql,head in [
                    ('الألوان','SELECT porcelain_color,COUNT(*),COALESCE(SUM(sqm),0),COALESCE(SUM(linear_m),0),COALESCE(SUM(invoice_amount),0) FROM orders GROUP BY porcelain_color ORDER BY COUNT(*) DESC',['اللون','عدد الطلبات','م²','م/ط','مجموع الفواتير']),
                    ('الغراء','SELECT glue_type,COUNT(*),COALESCE(SUM(glue_qty),0) FROM orders GROUP BY glue_type ORDER BY COUNT(*) DESC',['نوع الغراء','الطلبات','الكمية']),
                    ('الحالات','SELECT status,COUNT(*) FROM orders GROUP BY status ORDER BY COUNT(*) DESC',['الحالة','عدد الطلبات'])]:
                    s=w.add_worksheet(sheet_name);s.right_to_left();s.set_column(0,0,30);s.set_column(1,4,20)
                    fmt=w.add_format({'bold':True,'bg_color':'#147A84','font_color':'white'})
                    for col,h in enumerate(head):s.write(0,col,h,fmt)
                    for row,record in enumerate(self.cx.execute(sql).fetchall(),1):
                        for col,value in enumerate(record):s.write(row,col,value if value is not None else '')
            alert(self,'تم التصدير',path)
        except Exception as e:alert(self,'فشل التصدير',e,True)

    def show_review(self):
        dlg=QDialog(self);dlg.resize(990,450);dlg.setWindowTitle('صفوف Excel التي تحتاج للمراجعة')
        l=QVBoxLayout(dlg);l.addWidget(QLabel('الصفوف السبعة التالية تتضمن موادًا دون اسم عميل. حُفظت كما هي دون ربط افتراضي بالعقود.'))
        t=QTableWidget();t.setColumnCount(7);t.setHorizontalHeaderLabels(['صف Excel','لون البورسلان','م²','م/ط','الألواح','الغراء','كمية الغراء'])
        rows=db.review_rows(self.cx);t.setRowCount(len(rows));t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for i,r in enumerate(rows):
            raw=json.loads(r['raw_json'])
            for j,v in enumerate([r['excel_row'],raw[2],raw[3],raw[4],raw[11],raw[12],raw[13]]):t.setItem(i,j,QTableWidgetItem(nice_num(v)))
        l.addWidget(t);l.addWidget(btn('إغلاق',dlg.accept,'secondary'));dlg.exec()

    def match_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'اختر مجلد ملفات العملاء PDF')
        if not folder:return
        candidates={};duplicates=set();cnt=0
        for root,_,files in os.walk(folder):
            for fname in files:
                if Path(fname).suffix.lower() not in ('.pdf','.png','.jpg','.jpeg','.bmp','.webp','.gif'):continue
                key=fname.casefold().strip()
                if key in candidates:duplicates.add(key)
                candidates[key]=Path(root)/fname
                cnt+=1
                if cnt>15000:break
            if cnt>15000:break
        linked=unmatched=0
        source=self.cx.execute('SELECT * FROM attachments WHERE stored_path IS NULL AND original_reference IS NOT NULL').fetchall()
        for entry in source:
            key=Path(entry['original_reference'].replace('\\','/')).name.casefold().strip()
            if key not in candidates or key in duplicates:unmatched+=1;continue
            path=candidates[key]
            try:
                digest=__import__('hashlib').sha256(path.read_bytes()).hexdigest()
                target=db.ATTACH_DIR/str(entry['order_id'])/(digest[:16]+path.suffix.lower());target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():shutil.copy2(path,target)
                with self.cx:self.cx.execute('UPDATE attachments SET stored_path=?,sha256=? WHERE id=?',(target.relative_to(db.BASE).as_posix(),digest,entry['id']))
                linked+=1
            except Exception:unmatched+=1
        self.refresh();alert(self,'نتائج ربط المرفقات',f'تم ربط {linked} ملف.\nبقي {unmatched} مرجع غير متطابق.\nعند تكرار اسم الملف يتم تجاوزه لتجنب الربط الخاطئ.')

    def backup(self):
        try:path=db.make_backup(self.cx);alert(self,'تم إنشاء النسخة الاحتياطية',str(path))
        except Exception as e:alert(self,'فشل النسخ الاحتياطي',e,True)

    def restore(self):
        file=QFileDialog.getOpenFileName(self,'اختر النسخة الاحتياطية',str(db.BACKUP_DIR),'Backup ZIP (*.zip)')[0]
        if not file:return
        if QMessageBox.question(self,'تأكيد الاستعادة','سيتم إنشاء نسخة احتياطية للحالة الحالية ثم استبدال قاعدة البيانات. هل تريد الاستمرار؟')!=QMessageBox.StandardButton.Yes:return
        try:
            current=db.make_backup(self.cx)
            with zipfile.ZipFile(file) as archive:
                members=archive.namelist()
                if 'Database/porcelain.db' not in members:raise ValueError('هذه ليست نسخة احتياطية صالحة')
                for z in archive.infolist():
                    dest=(db.BASE/z.filename).resolve()
                    if not dest.is_relative_to(db.BASE.resolve()):raise ValueError('ملف أرشيف بمسار غير آمن')
                    if z.is_dir():continue
                    if not (z.filename.startswith('Attachments/') or z.filename.startswith('Branding/') or z.filename=='Database/porcelain.db'):raise ValueError('محتوى غير متوقع في الأرشيف')
                self.cx.close()
                for z in archive.infolist():
                    if z.is_dir():continue
                    dest=db.BASE/z.filename;dest.parent.mkdir(parents=True,exist_ok=True)
                    with archive.open(z) as src,open(dest,'wb') as dst:shutil.copyfileobj(src,dst)
            self.cx=db.connect();db.setup(self.cx);inv.init(self.cx)
            if hasattr(self,'catalog'):self.catalog.cx=self.cx
            if hasattr(self,'stock'):self.stock.cx=self.cx
            if hasattr(self,'dashboard_plus'):self.dashboard_plus.cx=self.cx
            self.refresh()
            alert(self,'نجحت الاستعادة',f'أُنشئت نسخة للحالة السابقة في:\n{current}')
        except Exception as e:
            self.cx=db.connect();alert(self,'تعذرت الاستعادة',e,True)

    def closeEvent(self,event):
        if not getattr(self,'_safe_exit_in_progress',False):
            if os.environ.get('QT_QPA_PLATFORM')!='offscreen' and os.environ.get('PORCELAIN_QA')!='1':
                answer=QMessageBox.question(self,'الخروج الآمن',
                    'هل تريد إغلاق البرنامج بعد حفظ نسخة احتياطية من قاعدة البيانات والمرفقات؟',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes)
                if answer!=QMessageBox.StandardButton.Yes:
                    event.ignore();return
            self._safe_exit_in_progress=True
        try:
            self.cx.commit()
            db.make_backup(self.cx)
            self.cx.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            self.cx.close()
        except Exception as exc:
            self._safe_exit_in_progress=False
            if os.environ.get('QT_QPA_PLATFORM')!='offscreen':
                QMessageBox.critical(self,'لم يكتمل الخروج الآمن',f'تعذر إنشاء نسخة احتياطية أو حفظ قاعدة البيانات: {exc}')
            event.ignore()
            return
        event.accept()

def install_fonts(app):
    from PySide6.QtGui import QFontDatabase, QPalette
    app.setStyle('Fusion')
    palette=QPalette()
    for role,color in (
        (QPalette.ColorRole.Window,'#F5F7FB'),
        (QPalette.ColorRole.WindowText,'#172B49'),
        (QPalette.ColorRole.Base,'#FFFFFF'),
        (QPalette.ColorRole.AlternateBase,'#F5FAFC'),
        (QPalette.ColorRole.Text,'#172B49'),
        (QPalette.ColorRole.Button,'#E9F1F7'),
        (QPalette.ColorRole.ButtonText,'#17324B'),
        (QPalette.ColorRole.Highlight,'#BEDFE5'),
        (QPalette.ColorRole.HighlightedText,'#102C42'),
        (QPalette.ColorRole.ToolTipBase,'#FFFFFF'),
        (QPalette.ColorRole.ToolTipText,'#172B49'),
    ):
        palette.setColor(role,QColor(color))
    app.setPalette(palette)
    if os.name == 'nt':
        for path in ('C:/Windows/Fonts/tahoma.ttf','C:/Windows/Fonts/arial.ttf','C:/Windows/Fonts/segoeui.ttf'):
            if Path(path).is_file():QFontDatabase.addApplicationFont(path)
    app.setFont(QFont('Tahoma',10))

def main():
    app=QApplication(sys.argv);install_fonts(app);app.setStyleSheet(STYLE)
    from PySide6.QtGui import QIcon
    icon=Path(__file__).resolve().parent/'Assets'/'PorcelainManager.ico'
    if icon.is_file():app.setWindowIcon(QIcon(str(icon)))
    if '--smoke-test' in sys.argv:
        window=MainWindow();s=db.summary(window.cx)
        assert len(window.nav)==7
        assert window.cx.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert len(window.filtered())==s['orders']
        print(json.dumps({'gui':'PASS','database':str(db.DB),'summary':s},ensure_ascii=False),flush=True)
        window.close();return 0
    window=MainWindow();window.show();return app.exec()

if __name__=='__main__':sys.exit(main())
