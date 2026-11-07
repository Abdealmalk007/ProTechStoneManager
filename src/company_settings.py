"""ProTech identity and editable company metadata; settings stay in SQLite."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import math, shutil
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImageReader
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QPushButton,
                               QLabel,QFileDialog,QMessageBox,QFrame,QScrollArea)
import storage as db

FIELDS={'company_name':'اسم الشركة (عربي)','company_name_en':'اسم الشركة (إنجليزي)',
        'address':'العنوان','phone':'رقم الهاتف','email':'البريد الإلكتروني',
        'website':'الموقع الإلكتروني','tax_no':'الرقم الضريبي'}
DEFAULTS={'company_name':'اسم شركتك','company_name_en':'My Company',
          'address':'','phone':'','email':'','website':'','tax_no':'','logo':''}

def init(cx):
    with cx:
        cx.execute('CREATE TABLE IF NOT EXISTS company_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL)')

def get(cx):
    init(cx)
    out=DEFAULTS.copy()
    out.update({r['key']:r['value'] for r in cx.execute('SELECT key,value FROM company_settings')})
    return out

def save(cx,items):
    name=(items.get('company_name') or '').strip()
    if not name: raise ValueError('اسم الشركة مطلوب')
    if len(name)>140: raise ValueError('اسم الشركة طويل')
    for k,value in items.items():
        if k not in DEFAULTS:continue
        if len(str(value))>500:raise ValueError('القيمة في الإعدادات طويلة')
    with cx:
        for key,value in items.items():
            if key in DEFAULTS:cx.execute('INSERT OR REPLACE INTO company_settings(key,value) VALUES(?,?)',(key,(value or '').strip()))

def logo_path(cx):
    rel=get(cx)['logo']
    if not rel:return None
    p=(db.BASE/rel).resolve()
    return p if p.is_file() and p.is_relative_to(db.BASE.resolve()) else None

def import_logo(src):
    src=Path(src)
    if src.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.bmp'):raise ValueError('اختر صورة PNG أو JPG أو WEBP أو BMP')
    if src.stat().st_size>12_000_000:raise ValueError('صورة الشعار كبيرة جدًا (الحد 12 ميجابايت)')
    reader=QImageReader(str(src))
    if not reader.canRead():raise ValueError('تعذر قراءة الشعار')
    image=reader.read()
    if image.isNull():raise ValueError('ملف الصورة غير صالح')
    dest=db.BASE/'Branding'/'company_logo.png'
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_name('company_logo_new.png')
    if not image.save(str(tmp),'PNG'):raise ValueError('تعذر نسخ صورة الشعار')
    tmp.replace(dest)
    return dest.relative_to(db.BASE).as_posix()

class SettingsPane(QWidget):
    def __init__(self,main):
        super().__init__(main);self.main=main;self.cx=main.cx
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        area=QScrollArea();area.setWidgetResizable(True);outer.addWidget(area)
        body=QWidget();area.setWidget(body)
        root=QVBoxLayout(body);root.setContentsMargins(25,24,25,24);root.setSpacing(14)
        header=QLabel('إعدادات الشركة والهوية');header.setObjectName('heading');root.addWidget(header)
        note=QLabel('تظهر بيانات الشركة وشعارها في التقارير وواجهة البرنامج. يمكن تحديثها دون تعديل بيانات العملاء.')
        note.setObjectName('muted');note.setWordWrap(True);root.addWidget(note)
        card=QFrame();card.setObjectName('card');form=QFormLayout(card);form.setContentsMargins(20,18,20,18)
        self.inputs={}
        for key,label in FIELDS.items():
            line=QLineEdit();line.setMaxLength(500 if key!='company_name' else 140)
            self.inputs[key]=line;form.addRow(label,line)
        root.addWidget(card)
        row=QHBoxLayout()
        self.logo_label=QLabel('لم يتم اختيار شعار الشركة')
        self.logo_label.setMinimumSize(180,105)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet('background:white;color:#294057;border:1px solid #C9D9E1;border-radius:10px')
        row.addWidget(self.logo_label)
        buttons=QVBoxLayout()
        select=QPushButton('اختيار شعار الشركة');select.clicked.connect(self.choose_logo);buttons.addWidget(select)
        remove=QPushButton('إزالة الشعار');remove.setObjectName('secondary');remove.clicked.connect(self.remove_logo);buttons.addWidget(remove)
        buttons.addStretch();row.addLayout(buttons);row.addStretch();root.addLayout(row)
        self.logo_selected=None
        save_button=QPushButton('حفظ إعدادات الشركة');save_button.clicked.connect(self.persist)
        root.addWidget(save_button);root.addStretch()
        self.load()

    def load(self):
        values=get(self.cx)
        for key,widget in self.inputs.items():widget.setText(values.get(key,''))
        self.logo_selected=None
        self.logo_removed=False
        self.refresh_logo()

    def refresh_logo(self):
        path=Path(self.logo_selected) if self.logo_selected else (None if self.logo_removed else logo_path(self.cx))
        if path and path.is_file():
            pix=QPixmap(str(path))
            if not pix.isNull():
                self.logo_label.setPixmap(pix.scaled(200,105,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
                return
        self.logo_label.setPixmap(QPixmap())
        self.logo_label.setText('لم يتم اختيار شعار الشركة')

    def choose_logo(self):
        filename,_=QFileDialog.getOpenFileName(self,'اختر شعار الشركة','','Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if filename:self.logo_selected=filename;self.logo_removed=False;self.refresh_logo()

    def remove_logo(self):
        self.logo_selected=None;self.logo_removed=True;self.refresh_logo()

    def persist(self):
        try:
            values={key:edit.text().strip() for key,edit in self.inputs.items()}
            if self.logo_selected:values['logo']=import_logo(self.logo_selected)
            elif self.logo_removed:values['logo']=''
            save(self.cx,values)
            self.load()
            self.main.apply_company_identity()
            QMessageBox.information(self,'تم الحفظ','حُفظت بيانات الشركة وستظهر في التقارير الجديدة.')
        except Exception as exc:QMessageBox.warning(self,'تعذر حفظ الإعدادات',str(exc))

def generate_icon(base:Path):
    """Original vector-like app icon: porcelain tile, gold joint, and data bars."""
    base.mkdir(parents=True,exist_ok=True)
    s=1024
    im=Image.new('RGBA',(s,s),(0,0,0,0))
    draw=ImageDraw.Draw(im,'RGBA')
    # dark navy rounded shell with measured highlight
    draw.rounded_rectangle((45,45,979,979),radius=220,fill=(13,39,69,255))
    for k in range(90):
        v=int(20 + 38*k/90)
        draw.rounded_rectangle((53+k//3,53+k//3,971-k//3,971-k//3),radius=210-k//4,outline=(15,88+min(k,70),107+min(k,85),1))
    # inset luminous teal tile frame
    draw.rounded_rectangle((150,145,870,875),radius=115,fill=(16,93,109,255))
    draw.rounded_rectangle((187,182,835,837),radius=90,fill=(235,246,246,255))
    # isometric porcelain tile: three trapezoids
    draw.polygon([(253,419),(502,257),(757,418),(505,579)],fill=(39,177,184,255))
    draw.polygon([(253,419),(505,579),(505,742),(253,584)],fill=(14,97,128,255))
    draw.polygon([(505,579),(757,418),(757,584),(505,742)],fill=(18,61,107,255))
    # polished gold central seam
    draw.line([(505,579),(505,736)],fill=(246,190,86,255),width=18,joint='curve')
    draw.line([(259,424),(503,581),(751,425)],fill=(244,195,99,255),width=16,joint='curve')
    # glint
    draw.polygon([(463,335),(487,286),(511,337),(560,362),(511,389),(487,439),(463,389),(414,362)],fill=(255,255,255,205))
    # glossy stripe
    draw.rounded_rectangle((250,804,753,831),radius=13,fill=(209,165,88,245))
    out=base/'PorcelainManagerIcon.png';im.save(out)
    ico=base/'PorcelainManager.ico'
    im.save(ico,format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    return out,ico
