"""Attachment preview and native opening, with multi-page PDF navigation."""
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
                               QScrollArea,QSpinBox,QMessageBox)
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView

SUPPORTED_PICTURES={'.png','.jpg','.jpeg','.bmp','.webp','.gif'}

def open_native(parent,path):
    path=Path(path)
    if not path.is_file():
        QMessageBox.warning(parent,'الملف غير متاح','الملف غير موجود على القرص.')
        return False
    ok=QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    if not ok:QMessageBox.warning(parent,'تعذر الفتح','لم يتم العثور على برنامج مناسب لفتح الملف.')
    return ok

def preview(parent,path):
    path=Path(path)
    if not path.is_file():
        QMessageBox.warning(parent,'الملف غير متاح','الملف الأصلي غير موجود. اربط الملف أولًا.')
        return False
    if path.suffix.lower()=='.pdf':
        document=QPdfDocument(parent)
        error=document.load(str(path))
        if error!=QPdfDocument.Error.None_ or document.pageCount()<1:
            document.deleteLater()
            return open_native(parent,path)
        dlg=QDialog(parent)
        dlg.setWindowTitle(f'معاينة PDF — {path.name}')
        dlg.resize(1050,760)
        layout=QVBoxLayout(dlg)
        bar=QHBoxLayout()
        count=document.pageCount()
        pages=QSpinBox(dlg);pages.setRange(1,count);pages.setValue(1)
        bar.addWidget(QLabel('الصفحة'));bar.addWidget(pages)
        bar.addWidget(QLabel(f'من {count} صفحة'))
        view=QPdfView(dlg)
        view.setDocument(document)
        view.setPageMode(QPdfView.PageMode.MultiPage)
        view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        navigator=view.pageNavigator()
        def jump(index):
            navigator.jump(index-1,navigator.currentLocation(),navigator.currentZoom())
        pages.valueChanged.connect(jump)
        def go(delta):
            pages.setValue(min(count,max(1,pages.value()+delta)))
        def change_zoom(factor):
            view.setZoomMode(QPdfView.ZoomMode.Custom)
            view.setZoomFactor(max(0.2,min(5.0,view.zoomFactor()*factor)))
        for title,callback in [
            ('السابق',lambda:go(-1)),('التالي',lambda:go(1)),
            ('−',lambda:change_zoom(0.8)),('+',lambda:change_zoom(1.25)),
            ('احتواء العرض',lambda:view.setZoomMode(QPdfView.ZoomMode.FitToWidth)),
            ('فتح بالبرنامج الافتراضي',lambda:open_native(dlg,path))
        ]:
            b=QPushButton(title);b.clicked.connect(callback);bar.addWidget(b)
        bar.addStretch();layout.addLayout(bar)
        layout.addWidget(view,1)
        dlg.exec()
        document.close()
        return True
    if path.suffix.lower() in SUPPORTED_PICTURES:
        # Extremely large images can require several GiB decoded memory; native viewer is a safe fallback.
        if path.stat().st_size>60_000_000:
            return open_native(parent,path)
        picture=QPixmap(str(path))
        if picture.isNull():return open_native(parent,path)
        dlg=QDialog(parent);dlg.setWindowTitle(f'معاينة الصورة — {path.name}');dlg.resize(1000,700)
        outer=QVBoxLayout(dlg);scroll=QScrollArea(dlg)
        scroll.setWidgetResizable(True);label=QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(picture.scaled(QSize(960,650),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        scroll.setWidget(label);outer.addWidget(scroll)
        outer.addWidget(QPushButton('فتح بالبرنامج الافتراضي',clicked=lambda:open_native(dlg,path)))
        dlg.exec()
        return True
    return open_native(parent,path)
