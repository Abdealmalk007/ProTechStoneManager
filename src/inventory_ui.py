"""Catalog, audited stock transactions, and inventory drill-down for Qt."""
from __future__ import annotations
from decimal import Decimal
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
    QLineEdit,QComboBox,QCheckBox,QTextEdit,QTableWidget,QTableWidgetItem,
    QHeaderView,QAbstractItemView,QDialogButtonBox,QMessageBox,QDateEdit,
    QSplitter
)
import inventory_storage as inv

def button(text,func,secondary=False):
    b=QPushButton(text)
    if secondary:b.setObjectName('secondary')
    b.clicked.connect(func)
    return b

def table(columns):
    t=QTableWidget()
    t.setColumnCount(len(columns))
    t.setHorizontalHeaderLabels(columns)
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    t.horizontalHeader().setDefaultSectionSize(145)
    return t

def fill(t,rows):
    t.setSortingEnabled(False)
    t.setRowCount(len(rows))
    for ri,(id,values) in enumerate(rows):
        for col,value in enumerate(values):
            cell=QTableWidgetItem(str(value) if value is not None else '')
            cell.setForeground(QColor('#172B49'))
            cell.setToolTip(str(value) if value is not None else '')
            if col==0:cell.setData(Qt.ItemDataRole.UserRole,id)
            t.setItem(ri,col,cell)
    t.setSortingEnabled(True)

def selected(t):
    row=t.currentRow()
    if row<0:
        rows=t.selectionModel().selectedRows() if t.selectionModel() else []
        row=rows[0].row() if rows else -1
    if row<0:return None
    item=t.item(row,0)
    return item.data(Qt.ItemDataRole.UserRole) if item else None

class CatalogEditor(QDialog):
    def __init__(self,parent,entry=None):
        super().__init__(parent);self.setWindowTitle('بيانات الصنف');self.resize(455,270)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout=QVBoxLayout(self);form=QFormLayout();layout.addLayout(form)
        self.category=QComboBox();self.category.addItems(inv.KINDS)
        self.name=QLineEdit()
        self.unit=QComboBox();self.unit.addItems(inv.UNITS)
        self.active=QCheckBox('الصنف نشط ومتاح للاستخدام');self.active.setChecked(True)
        for label,widget in [('التصنيف',self.category),('اسم اللون / النوع / الصنف',self.name),('وحدة القياس',self.unit)]:
            form.addRow(label,widget)
        form.addRow('',self.active)
        if entry:
            self.category.setCurrentText(entry['category'])
            self.category.setEnabled(False)
            self.name.setText(entry['name']);self.unit.setCurrentText(entry['unit'])
            self.active.setChecked(bool(entry['active']))
        foot=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        foot.button(QDialogButtonBox.StandardButton.Save).setText('حفظ')
        foot.button(QDialogButtonBox.StandardButton.Cancel).setText('إلغاء')
        foot.accepted.connect(self.accept);foot.rejected.connect(self.reject)
        layout.addWidget(foot)

class CatalogPane(QWidget):
    def __init__(self,main):
        super().__init__(main);self.main=main;self.cx=main.cx
        root=QVBoxLayout(self);root.setContentsMargins(22,18,22,18)
        title=QLabel('كتالوج الرخام والبورسلان والأصناف');title.setObjectName('heading');root.addWidget(title)
        tip=QLabel('إضافة أو تعديل أو تعطيل الألوان وأنواع الغراء والألواح والهانيكام. تعطيل الصنف يحفظ التاريخ بدل حذفه نهائيًا.')
        tip.setWordWrap(True);tip.setObjectName('muted');root.addWidget(tip)
        bar=QHBoxLayout()
        self.category=QComboBox();self.category.addItem('جميع التصنيفات','')
        for k in inv.KINDS:self.category.addItem(k,k)
        self.category.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.category)
        bar.addWidget(button('إضافة صنف / لون',self.add))
        bar.addWidget(button('تعديل الصنف',self.edit,True))
        bar.addWidget(button('تقرير الصنف / اللون',self.report,True))
        bar.addWidget(button('تعطيل / تفعيل',self.toggle,True))
        root.addLayout(bar)
        self.info=QLabel();root.addWidget(self.info)
        self.t=table(['الرقم','التصنيف','الاسم / اللون','الوحدة','الحالة','المصدر'])
        self.t.doubleClicked.connect(self.edit)
        self.t.setWordWrap(True)
        self.t.setColumnWidth(2,345)
        self.t.verticalHeader().setDefaultSectionSize(43)
        root.addWidget(self.t,1)
        self.refresh()

    def refresh(self,*_):
        rows=inv.items(self.cx,self.category.currentData() or '',True)
        fill(self.t,[(r['id'],[r['id'],r['category'],r['name'],r['unit'],
                                'نشط' if r['active'] else 'معطل','Excel' if r['source']=='excel' else 'مضاف يدويًا']) for r in rows])
        self.info.setText(f'{len(rows)} صنف ضمن التصفية — تعديل الأسماء لا يغير بيانات العقود التاريخية')

    def report(self):
        self.main.report_selected_item(selected(self.t))

    def add(self):
        dlg=CatalogEditor(self)
        if not dlg.exec():return
        try:
            inv.add(self.cx,dlg.category.currentText(),dlg.name.text(),dlg.unit.currentText())
            self.main.refresh()
        except Exception as e:QMessageBox.warning(self,'تعذر إضافة الصنف',str(e))

    def edit(self,*_):
        id=selected(self.t)
        if not id:QMessageBox.information(self,'اختر صنفًا','حدد صنفًا من الجدول');return
        item=self.cx.execute('SELECT * FROM catalog_items WHERE id=?',(id,)).fetchone()
        dlg=CatalogEditor(self,item)
        if not dlg.exec():return
        try:
            inv.edit(self.cx,id,dlg.name.text(),dlg.unit.currentText(),dlg.active.isChecked())
            self.main.refresh()
        except Exception as e:QMessageBox.warning(self,'تعذر التعديل',str(e))

    def toggle(self):
        id=selected(self.t)
        if not id:QMessageBox.information(self,'اختر صنفًا','حدد صنفًا من الجدول');return
        item=self.cx.execute('SELECT * FROM catalog_items WHERE id=?',(id,)).fetchone()
        new=not bool(item['active'])
        if QMessageBox.question(self,'تغيير حالة الصنف',('تفعيل' if new else 'تعطيل')+' هذا الصنف مع الحفاظ على السجلات السابقة؟')!=QMessageBox.StandardButton.Yes:return
        try:inv.edit(self.cx,id,item['name'],item['unit'],new);self.main.refresh()
        except Exception as e:QMessageBox.warning(self,'تعذر العملية',str(e))

class MovementEditor(QDialog):
    def __init__(self,parent,cx,selected_id=None):
        super().__init__(parent);self.cx=cx
        self.setWindowTitle('تسجيل حركة مخزون موثقة');self.resize(560,420)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        root=QVBoxLayout(self);form=QFormLayout();root.addLayout(form)
        self.item=QComboBox()
        for r in inv.items(cx):
            self.item.addItem(f"{r['category']} | {r['name']} ({r['unit']})",r['id'])
        i=self.item.findData(selected_id)
        if i>=0:self.item.setCurrentIndex(i)
        self.kind=QComboBox();self.kind.addItems(inv.SIGNS.keys())
        self.qty=QLineEdit();self.qty.setPlaceholderText('مثال: 12.500 — حتى 3 منازل عشرية')
        self.cost=QLineEdit();self.cost.setPlaceholderText('سعر الوحدة الفعلي إن كان معروفًا (اختياري)')
        self.ref=QLineEdit();self.ref.setPlaceholderText('رقم المستند أو فاتورة الشراء')
        self.day=QDateEdit();self.day.setCalendarPopup(True);self.day.setDisplayFormat('yyyy-MM-dd');self.day.setDate(QDate.currentDate())
        self.notes=QTextEdit();self.notes.setMaximumHeight(75)
        for label,w in [('الصنف',self.item),('نوع الحركة',self.kind),('الكمية',self.qty),
                        ('تكلفة الوحدة ر.س',self.cost),('رقم المستند',self.ref),
                        ('تاريخ الحركة',self.day),('ملاحظات',self.notes)]:
            form.addRow(label,w)
        info=QLabel('تنبيه: رصيد المخزون لا يُعتبر موثقًا قبل تسجيل جرد افتتاحي فعلي لكل صنف. لا تُستنتج الأرصدة من Excel.')
        info.setWordWrap(True);info.setObjectName('muted');root.addWidget(info)
        foot=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        foot.button(QDialogButtonBox.StandardButton.Save).setText('حفظ الحركة')
        foot.button(QDialogButtonBox.StandardButton.Cancel).setText('إلغاء')
        foot.accepted.connect(self.save);foot.rejected.connect(self.reject);root.addWidget(foot)

    def save(self):
        try:
            inv.movement(self.cx,self.item.currentData(),self.kind.currentText(),self.qty.text(),
                         self.cost.text(),self.ref.text(),self.day.date().toString('yyyy-MM-dd'),
                         self.notes.toPlainText())
            self.accept()
        except Exception as e:QMessageBox.warning(self,'بيانات غير صحيحة',str(e))

class StockPane(QWidget):
    def __init__(self,main):
        super().__init__(main);self.main=main;self.cx=main.cx
        root=QVBoxLayout(self);root.setContentsMargins(22,18,22,18)
        title=QLabel('حركة المخزون والأرصدة');title.setObjectName('heading');root.addWidget(title)
        subtitle=QLabel('الأرصدة تظهر «غير معتمدة» حتى إدخال جرد افتتاحي لكل صنف. جميع الحركات محفوظة بتاريخ ووحدة ومرجع.')
        subtitle.setObjectName('muted');subtitle.setWordWrap(True);root.addWidget(subtitle)
        bar=QHBoxLayout()
        self.cat=QComboBox();self.cat.addItem('كل الأصناف','')
        for c in inv.KINDS:self.cat.addItem(c,c)
        self.cat.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.cat)
        bar.addWidget(button('تسجيل وارد / صرف / جرد',self.add))
        bar.addWidget(button('تحديث المخزون',self.refresh,True))
        bar.addWidget(button('تقرير حركة الصنف',self.report,True))
        root.addLayout(bar)
        self.info=QLabel();root.addWidget(self.info)
        splitter=QSplitter(Qt.Orientation.Vertical)
        self.t=table(['الرقم','الفئة','الصنف','الوحدة','الرصيد المُوثق','حركات','الحالة'])
        self.t.itemSelectionChanged.connect(self.refresh_ledger)
        splitter.addWidget(self.t)
        self.moves=table(['التاريخ','الصنف','الحركة','الكمية','التكلفة للوحدة ر.س','المرجع','ملاحظات'])
        splitter.addWidget(self.moves)
        splitter.setSizes([350,230]);root.addWidget(splitter,1)
        self.refresh()

    def refresh(self,*_):
        rows=inv.balances(self.cx,self.cat.currentData() or '')
        fill(self.t,[(r['id'],[r['id'],r['category'],r['name'],r['unit'],
                        f"{r['quantity']:,.3f}" if r['confirmed'] else 'غير معتمد',
                        r['movements'],'نشط' if r['active'] else 'معطل']) for r in rows])
        self.info.setText(f'الأصناف: {len(rows)}  |  أرصدة بجرد افتتاحي: {sum(r["confirmed"] for r in rows)}  |  أرصدة غير معتمدة: {sum(not r["confirmed"] for r in rows)}')
        self.refresh_ledger()

    def refresh_ledger(self):
        rows=inv.ledger(self.cx,self.cat.currentData() or '',selected(self.t))
        fill(self.moves,[(r['id'],[r['occurred_on'],r['item_name'],r['movement_type'],r['quantity'],
                                 r['unit_cost'] or 'غير مسجل',r['doc_ref'] or '',r['notes'] or '']) for r in rows])

    def report(self):
        self.main.report_selected_item(selected(self.t),stock=True)

    def add(self):
        dlg=MovementEditor(self,self.cx,selected(self.t))
        if dlg.exec():self.main.refresh()
