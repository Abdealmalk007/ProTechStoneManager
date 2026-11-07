"""Measured, branded PDF and XLSX outputs with repeatable print geometry."""
from __future__ import annotations
from pathlib import Path
from decimal import Decimal,InvalidOperation
from datetime import date
import html
from PySide6.QtCore import Qt,QRect,QMarginsF
from PySide6.QtGui import QColor,QFont,QFontMetrics,QPainter,QPixmap,QPageSize,QPageLayout
from PySide6.QtPrintSupport import QPrinter
import company_settings as cs
import live_metrics
import export_layout

INK='#151A1E'
NAVY='#102941'
TEAL='#117B83'
GOLD='#C79D59'
PALE='#F8FBFC'
BORDER='#C9D9E3'
TEXT='#1C2A37'
HEADER_FILL='#DDECF1'     # Pale blue header; high contrast with black text
HEADER_TEXT='#101418'
FOOTER_TEXT='#253746'
RIGHTS_TEXT='حقوق التصميم والتطوير محفوظة: Abu Omar - ProTech'
MONEY=('مبلغ الفاتورة','قيمة الفواتير (ر.س)','تكلفة الوحدة (ر.س)','قيمة المخزون','مجموع الفواتير')
QTY=('المساحة','م²','م/ط','كمية','الطول','الرصيد','الغراء')

def ismoney(key):
    return any(x in str(key) for x in MONEY)
def isqty(key):
    return any(x in str(key) for x in QTY) and not ismoney(key)
def isindex(key):
    return key in ('الرقم','العقود','حركات','عدد الطلبات','عدد السجلات')
def display(value,header=''):
    if value is None:return ''
    if isinstance(value,(int,float,Decimal)) and not isindex(header):
        if isinstance(value,float) or isinstance(value,Decimal):
            digits=2 if ismoney(header) else 3 if isqty(header) else 2
            return f'{Decimal(str(value)):,.{digits}f}'
    return str(value)

def _safe_dec(v):
    try:return Decimal(str(v))
    except (InvalidOperation,ValueError):return None

def _qfont(point,bold=False):
    f=QFont('Tahoma');f.setPointSizeF(point);f.setBold(bold)
    return f

def _col_weights(headers,rows):
    weights=[]
    for j,h in enumerate(headers):
        size=max(len(str(h)),max((len(display(row[j],h)) for row in rows[:60]),default=0))
        if 'ملاحظات' in h:weight=2.6
        elif 'اسم العميل' in h or 'الصنف'==h or 'لون البورسلان'==h:weight=1.65
        elif h in ('رقم التواصل','رقم الفاتورة','رقم العقد','تاريخ التركيب','التاريخ'):weight=1.35
        else:weight=0.92+min(size,23)/75
        weights.append(weight)
    return weights

def pdf(path,title,headers,rows,conn,total=None,note='',extra_rows=None,customer_meta=None,column_widths=None):
    """Printable A3/A4 pages with narrow 5mm margins and measured columns."""
    profile=cs.get(conn)
    customer_meta=customer_meta or {}
    order_wide=len(headers)>11
    printer=QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setResolution(144)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(path))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A3 if order_wide else QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    printer.setPageMargins(QMarginsF(5,5,5,6),QPageLayout.Unit.Millimeter)
    size=printer.pageRect(QPrinter.Unit.DevicePixel)
    W,H=int(size.width()),int(size.height())
    if W<500 or H<450:raise RuntimeError('خطأ في مقاس الصفحة')
    painter=QPainter()
    if not painter.begin(printer):raise RuntimeError('تعذر بدء إنشاء PDF')
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    head_h=190 if not order_wide else 200
    table_y=head_h+64
    table_bottom=H-131
    line=46 if order_wide else 49
    pt=8.5 if order_wide else 9.5
    if (column_widths is not None and len(column_widths)==len(headers)
            and all(isinstance(w,(int,float)) and 0<w<5000 for w in column_widths)):
        weights=[max(80,min(480,float(w))) for w in column_widths]
    else:
        weights=_col_weights(headers,rows)
    weights_total=sum(weights) or 1
    widths=[max(1,round((W-4)*w/weights_total)) for w in weights] if headers else []
    if widths:widths[-1]+=(W-sum(widths))
    fm=QFontMetrics(_qfont(pt))
    heights=[]
    for row in rows:
        tallest=line
        for j,cell in enumerate(row):
            text=display(cell,headers[j])
            rect=QRect(0,0,max(18,widths[j]-17),12000)
            text_height=fm.boundingRect(rect,int(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter|Qt.TextFlag.TextWordWrap),text).height()
            tallest=max(tallest,text_height+17)
        heights.append(tallest)
    pages=[[]];current=table_y+line
    for ri,h in enumerate(heights):
        if current+h>table_bottom and pages[-1]:
            pages.append([]);current=table_y+line
        pages[-1].append(ri);current+=h
    rowslen=len(rows)
    extra_rows=[(str(a),str(b),str(c)) for a,b,c in (extra_rows or [])]
    extra_pages=[]
    extra_heights=[]
    if extra_rows:
        cols=[int(W*.19),int(W*.29),W-int(W*.19)-int(W*.29)]
        detail_font=QFontMetrics(_qfont(8))
        for row in extra_rows:
            row_h=48
            for col,content in enumerate(row):
                width=max(40,cols[col]-16)
                rect=QRect(0,0,width,9999)
                wrapped=detail_font.boundingRect(rect,int(Qt.TextFlag.TextWordWrap),content).height()
                row_h=max(row_h,wrapped+18)
            extra_heights.append(min(row_h,table_bottom-table_y-line))
        extra_pages=[[]]
        at=table_y+line
        for i,row_h in enumerate(extra_heights):
            if at+row_h>table_bottom and extra_pages[-1]:
                extra_pages.append([]);at=table_y+line
            extra_pages[-1].append(i);at+=row_h
    total_pages=len(pages)+len(extra_pages)
    c=QColor
    def rect(x,y,w,h,color):
        painter.fillRect(QRect(int(x),int(y),int(w),int(h)),c(color))
    def label(text,x,y,w,h,points=9,fg=INK,bold=False,align=None):
        painter.setFont(_qfont(points,bold));painter.setPen(c(fg))
        flags=align if align is not None else int(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight|Qt.TextFlag.TextWordWrap)
        painter.drawText(QRect(int(x),int(y),int(w),int(h)),flags,str(text))
    def header(page_n):
        rect(0,0,W,18,NAVY)
        rect(0,19,W,4,GOLD)
        name=profile['company_name'] or 'ProTech'
        label(name,130,38,W-155,45,17,NAVY,True)
        label(profile.get('company_name_en') or 'ProTech Marble & Porcelain Manager',130,80,W-155,31,10,'#244B65',True)
        logo=cs.logo_path(conn)
        if logo:
            pix=QPixmap(str(logo))
            if not pix.isNull():
                pix=pix.scaled(112,102,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(5,33,pix)
        else:
            default=Path(__file__).resolve().parent/'Assets'/'PorcelainManagerIcon.png'
            if default.exists():
                pix=QPixmap(str(default)).scaled(105,105,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(7,32,pix)
        if customer_meta:
            label('تقرير العميل  |  '+customer_meta['name'],10,110,W-20,40,13,'#153046',True)
            label(f"اسم العميل: {customer_meta['name']}     |     "
                  f"رقم الجوال: {customer_meta['phone']}     |     "
                  f"تاريخ التقرير: {customer_meta['report_date']}",
                  10,151,W-20,33,10,HEADER_TEXT,True)
            label(f"اللون / نوع المادة: {customer_meta['porcelain_color']}     |     "
                  f"تاريخ/تواريخ التركيب: {customer_meta['install_dates']}",
                  10,181,W-20,37,9,'#234C5F',True)
        else:
            label(title,10,123,W-20,40,13,TEAL,True)
            line_text=(f'التاريخ: {date.today().isoformat()}   |   السجلات: {rowslen}   |   صفحة {page_n} من {total_pages}')
            if total is not None and 'مخزون' not in title and 'حركة' not in title:line_text+=f'   |   مجموع الفواتير: {total:,.2f} ر.س'
            label(line_text,12,163,W-25,31,8,TEXT)
        aggregates=live_metrics.summarize_report(headers,rows)
        if aggregates:
            label(live_metrics.report_line(aggregates),12,218 if customer_meta else 198,
                  W-24,32 if customer_meta else 40,7.5 if customer_meta else 8,TEAL,True)
        rect(0,table_y-3,W,3,GOLD)
    def footer(page_n):
        # Three separate text bands prevent contact, rights and notes overlapping.
        rect(0,H-110,W,2,BORDER)
        contact='  |  '.join(x for x in (profile.get('phone',''),profile.get('email',''),profile.get('website','')) if x)
        label(contact or 'ProTech Marble & Porcelain Manager',140,H-104,W-153,27,9,FOOTER_TEXT,True)
        label(f'{page_n} / {total_pages}',5,H-104,125,27,9,'#165465',True,
              int(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft))
        label(RIGHTS_TEXT,8,H-75,W-16,27,9,HEADER_TEXT,True)
        label(note or 'القيم حسب البيانات المسجلة، وليست إثباتًا للتحصيل أو الجرد الفعلي',
              8,H-46,W-16,28,8,FOOTER_TEXT,True)
    def cell(txt,x,y,width,height,h,isheading=False):
        label(txt,x+7,y+3,width-14,height-6,
              pt+(0.7 if isheading else 0),
              HEADER_TEXT if isheading else INK,isheading)
    for pagen,indices in enumerate(pages,1):
        if pagen>1:printer.newPage()
        painter.fillRect(QRect(0,0,W,H),QColor('#FFFFFF'))
        header(pagen)
        rect(0,table_y,W,line,HEADER_FILL)
        px=W
        for j,h in enumerate(headers):
            px-=widths[j];cell(h,px,table_y,widths[j],line,h,True)
        y=table_y+line
        for ri in indices:
            r=rows[ri];height=heights[ri]
            rect(0,y,W,height,'#FFFFFF' if ri%2==0 else PALE)
            px=W
            for j,text in enumerate(r):
                px-=widths[j]
                rect(px,y+height-1,widths[j],1,BORDER)
                cell(display(text,headers[j]),px,y,widths[j],height,headers[j])
            y+=height
        footer(pagen)
    for appendix_number,indices in enumerate(extra_pages,len(pages)+1):
        printer.newPage()
        painter.fillRect(QRect(0,0,W,H),QColor('#FFFFFF'))
        header(appendix_number)
        rect(0,table_y,W,line,HEADER_FILL)
        widths_extra=[int(W*.19),int(W*.29),W-int(W*.19)-int(W*.29)]
        px=W
        for label_text,width in zip(('القسم','البيان','القيمة / التفاصيل'),widths_extra):
            px-=width
            cell(label_text,px,table_y,width,line,label_text,True)
        y=table_y+line
        for ri in indices:
            record=extra_rows[ri]
            h=extra_heights[ri]
            rect(0,y,W,h,'#FFFFFF' if ri%2==0 else PALE)
            px=W
            for key,width in zip(record,widths_extra):
                px-=width
                rect(px,y+h-1,width,1,BORDER)
                cell(key,px,y,width,h,key)
            y+=h
        footer(appendix_number)
    painter.end()
    if not Path(path).exists() or Path(path).stat().st_size<1100:raise RuntimeError('ملف PDF غير صالح')
    return total_pages

def excel(path,title,headers,rows,conn,total=None,note='',extra_rows=None,customer_meta=None,column_widths=None):
    import xlsxwriter
    profile=cs.get(conn)
    customer_meta=customer_meta or {}
    ncols=len(headers)
    if not ncols:raise ValueError('التقرير فارغ من الأعمدة')
    with xlsxwriter.Workbook(str(path)) as wb:
        ws=wb.add_worksheet('التقرير')
        ws.right_to_left()
        wb.set_properties({'title':title,'author':'ProTech / Abu Omar','subject':'تقرير الرخام والبورسلان'})
        wide=ncols>11
        ws.set_paper(8 if wide else 9) # A3=8, A4=9
        ws.set_landscape()
        ws.fit_to_pages(1,0)
        ws.set_margins(0.20,0.20,0.24,0.25)
        ws.set_header('&C'+'ProTech Marble & Porcelain Manager',{'margin':0.10})
        ws.set_footer('&LAbu Omar - ProTech&Cصفحة &P من &N'+'&R'+date.today().isoformat(),{'margin':0.12})
        title_fmt=wb.add_format({'font_name':'Tahoma','font_size':20,'font_color':'#0E2940','bold':True,
                                'valign':'vcenter','align':'right','bg_color':'#E8F2F5'})
        subtitle_fmt=wb.add_format({'font_name':'Tahoma','font_size':12,'font_color':'#111111','bold':True,
                                   'align':'right','valign':'vcenter','bg_color':'#F1F7F9'})
        note_fmt=wb.add_format({'font_name':'Tahoma','font_size':9,'font_color':'#526D83','align':'right','text_wrap':True,'valign':'vcenter'})
        meta_fmt=wb.add_format({'font_name':'Tahoma','font_size':11,'font_color':'#101820','bold':True,
                               'align':'right','valign':'vcenter','text_wrap':True,
                               'bg_color':'#EEF6F8','border':1,'border_color':'#D0E0E6'})
        head_fmt=wb.add_format({'font_name':'Tahoma','font_size':11,'font_color':'#111111',
                               'bg_color':'#DDECF1','bold':True,'align':'center','valign':'vcenter',
                               'text_wrap':True,'border':1,'border_color':'#B5D0DA'})
        base={'font_name':'Tahoma','font_size':10.5,'font_color':'#1D2832','valign':'vcenter',
              'align':'right','text_wrap':True,'border':1,'border_color':'#D7E3E8'}
        texts=[wb.add_format(dict(base,bg_color=('#FFFFFF' if i==0 else '#F1F6FA'))) for i in (0,1)]
        amounts=[wb.add_format(dict(base,bg_color=('#FFFFFF' if i==0 else '#F1F6FA'),num_format='#,##0.00')) for i in (0,1)]
        qtys=[wb.add_format(dict(base,bg_color=('#FFFFFF' if i==0 else '#F1F6FA'),num_format='#,##0.000')) for i in (0,1)]
        integers=[wb.add_format(dict(base,bg_color=('#FFFFFF' if i==0 else '#F1F6FA'),num_format='#,##0')) for i in (0,1)]
        foot=wb.add_format({'font_name':'Tahoma','font_size':11,'font_color':'#111111','bold':True,'bg_color':'#DDECF1','align':'right','num_format':'#,##0.00','top':2,'top_color':'#C79D59'})
        ws.set_row(0,32);ws.set_row(1,27);ws.set_row(2,23);ws.set_row(3,18)
        ws.merge_range(0,0,0,ncols-1,profile['company_name'],title_fmt)
        ws.merge_range(1,0,1,ncols-1,title,subtitle_fmt)
        desc=f"التاريخ: {date.today().isoformat()}   |   عدد السجلات: {len(rows)}"
        if total is not None and 'مخزون' not in title and 'حركة' not in title:desc+=f"   |   الفواتير: {total:,.2f} ر.س"
        if customer_meta:
            ws.set_row(2,36)
            ws.merge_range(2,0,2,ncols-1,
                f"اسم العميل: {customer_meta['name']}  |  رقم الجوال: {customer_meta['phone']}  |  "
                f"تاريخ التقرير: {customer_meta['report_date']}",meta_fmt)
            ws.set_row(3,40)
            ws.merge_range(3,0,3,ncols-1,
                f"اللون / نوع المادة: {customer_meta['porcelain_color']}  |  "
                f"تاريخ/تواريخ التركيب: {customer_meta['install_dates']}",meta_fmt)
        else:
            ws.merge_range(2,0,2,ncols-1,desc,note_fmt)
            if profile.get('address') or profile.get('phone'):
                ws.merge_range(3,0,3,ncols-1,profile.get('address','')+'   '+profile.get('phone',''),note_fmt)
        if note:
            ws.set_row(4,34)
            ws.merge_range(4,0,4,ncols-1,note,note_fmt)
        aggregate=live_metrics.summarize_report(headers,rows)
        if aggregate:
            ws.set_row(5,26)
            ws.merge_range(5,0,5,ncols-1,live_metrics.report_line(aggregate),subtitle_fmt)
        logo=cs.logo_path(conn)
        if logo:
            # fit logo without covering header cells: floating image positioned alongside title.
            try:ws.insert_image(0,ncols-1,str(logo),{'x_scale':0.32,'y_scale':0.32,'object_position':1})
            except Exception:pass
        headerrow=6
        ws.set_row(headerrow,49)
        valid_widths=(column_widths is not None and len(column_widths)==len(headers)
                      and all(isinstance(w,(int,float)) and 0<w<5000 for w in column_widths))
        excel_widths=[]
        for j,h in enumerate(headers):
            ws.write_string(headerrow,j,h,head_fmt)
            sample=[record[j] for record in rows[:60]]
            width_px=column_widths[j] if valid_widths else None
            char_w=export_layout.excel_char_width(h,sample,width_px)
            excel_widths.append(char_w)
            ws.set_column(j,j,char_w)
        for i,r in enumerate(rows):
            row_idx=headerrow+1+i
            # Word wrap + calculated height prevents long customer, color and notes
            # from being clipped in saved Excel or printed output.
            max_lines=1
            for j,value in enumerate(r):
                if value is None:continue
                wrap_width=max(7,excel_widths[j]-2)
                max_lines=max(max_lines,(len(str(value))+wrap_width-1)//wrap_width)
            ws.set_row(row_idx,min(108,max(27,max_lines*19+7)))
            for j,val in enumerate(r):
                if val is None:continue
                h=headers[j];group=i%2
                if ismoney(h) or isqty(h) or (isindex(h) and not isinstance(val,str)):
                    d=_safe_dec(val)
                    if d is not None and d.is_finite():
                        fmt=amounts[group] if ismoney(h) else qtys[group] if isqty(h) else integers[group]
                        ws.write_number(row_idx,j,float(d),fmt)
                        continue
                ws.write_string(row_idx,j,str(val),texts[group])
        last=headerrow+1+len(rows)
        amount_cols=[j for j,h in enumerate(headers) if 'مبلغ الفاتورة' in h or 'قيمة الفواتير (ر.س)' in h]
        if total is not None and amount_cols:
            money_col=amount_cols[0]
            if money_col>1:ws.merge_range(last,0,last,money_col-1,'إجمالي قيمة الفواتير المسجلة (ر.س)',foot)
            elif money_col==1:ws.write_string(last,0,'الإجمالي',foot)
            ws.write_number(last,money_col,float(total),foot)
        ws.freeze_panes(headerrow+1,0)
        if rows:ws.autofilter(headerrow,0,headerrow+len(rows),ncols-1)
        ws.repeat_rows(headerrow,headerrow)
        ws.print_area(0,0,last,ncols-1)
        # Display copyright/attribution visibly in the worksheet, and print it too.
        rights_row=last+2
        rights_fmt=wb.add_format({'font_name':'Tahoma','font_size':10,'font_color':'#111111',
                                  'bold':True,'align':'right','valign':'vcenter',
                                  'bg_color':'#F1F7F9','top':1,'top_color':'#B5D0DA'})
        ws.set_row(rights_row,28)
        if ncols>1:
            ws.merge_range(rights_row,0,rights_row,ncols-1,RIGHTS_TEXT,rights_fmt)
        else:
            ws.write_string(rights_row,0,RIGHTS_TEXT,rights_fmt)
        ws.print_area(0,0,rights_row,ncols-1)
        ws.set_zoom(90)
        if extra_rows:
            extra=wb.add_worksheet('ملخص مواد العميل')
            extra.right_to_left()
            extra.set_landscape()
            extra.set_paper(9)
            extra.fit_to_pages(1,0)
            extra.set_margins(0.20,0.20,0.24,0.25)
            extra.set_column(0,0,24)
            extra.set_column(1,1,46)
            extra.set_column(2,2,85)
            extra.merge_range(0,0,0,2,profile['company_name']+' — '+title,title_fmt)
            extra.set_row(0,38)
            if customer_meta:
                extra.merge_range(1,0,1,2,
                    f"اسم العميل: {customer_meta['name']}  |  الجوال: {customer_meta['phone']}  |  "
                    f"التاريخ: {customer_meta['report_date']}  |  اللون / نوع المادة: {customer_meta['porcelain_color']}",
                    meta_fmt)
                extra.set_row(1,40)
            for j,label_text in enumerate(('القسم','البيان','الكمية / التفاصيل')):
                extra.write(2,j,label_text,head_fmt)
            extra.set_row(2,31)
            material_number=wb.add_format(dict(base,num_format='#,##0.###'))
            for i,record in enumerate(extra_rows,3):
                section,label_text,value=[str(x) for x in record]
                extra.write_string(i,0,section,texts[i%2])
                extra.write_string(i,1,label_text,texts[i%2])
                dec=_safe_dec(value.replace(',',''))
                if dec is not None and dec.is_finite():
                    extra.write_number(i,2,float(dec),material_number)
                else:
                    extra.write_string(i,2,value,texts[i%2])
                extra.set_row(i,min(125,max(25,(len(value)//85+1)*23)))
            extra.freeze_panes(3,0)
            extra.repeat_rows(2,2)
            # Repeat rights statement on the material-detail worksheet.
            rights_detail_row=4+len(extra_rows)
            extra.merge_range(rights_detail_row,0,rights_detail_row,2,RIGHTS_TEXT,rights_fmt)
            extra.set_row(rights_detail_row,27)
            extra.print_area(0,0,rights_detail_row,2)
    return path

def print_dialog(parent,conn,title,headers,rows,count,total,note='',extra_rows=None,customer_meta=None,column_widths=None):
    """Print exact report pages via Qt PDF renderer and OS print dialog."""
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtCore import QSize
    from PySide6.QtPrintSupport import QPrintDialog
    from PySide6.QtWidgets import QDialog
    from pathlib import Path
    import storage
    file=storage.EXPORT_DIR/'Preview'/'Print_Preflight.pdf'
    file.parent.mkdir(parents=True,exist_ok=True)
    pdf(file,title,headers,rows,conn,total,note=note,extra_rows=extra_rows,customer_meta=customer_meta,column_widths=column_widths)
    printer=QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A3 if len(headers)>11 else QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    printer.setPageMargins(QMarginsF(5,5,5,6),QPageLayout.Unit.Millimeter)
    dialog=QPrintDialog(printer,parent)
    if dialog.exec()!=QDialog.DialogCode.Accepted:return False
    doc=QPdfDocument(parent)
    result=doc.load(str(file))
    if doc.pageCount()<1:raise RuntimeError('تعذر قراءة صفحات المعاينة للطباعة')
    painter=QPainter(printer)
    target=printer.pageRect(QPrinter.Unit.DevicePixel)
    for i in range(doc.pageCount()):
        if i:printer.newPage()
        img=doc.render(i,QSize(int(target.width()),int(target.height())))
        if img.isNull():raise RuntimeError('فشل رسم الصفحة للطباعة')
        painter.drawImage(0,0,img)
    painter.end()
    doc.close()
    return True
