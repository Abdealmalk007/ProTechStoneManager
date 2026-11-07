"""Windows-safe export names and consistent, readable column sizing."""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path

_WINDOWS_BAD=re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED={*('CON','PRN','AUX','NUL'),*(f'COM{i}' for i in range(1,10)),
          *(f'LPT{i}' for i in range(1,10))}

def clean_component(value,maxlen=85):
    value=unicodedata.normalize('NFC',str(value or '').strip())
    value=_WINDOWS_BAD.sub(' ',value)
    value=re.sub(r'\s+',' ',value).strip(' .')
    if not value:value='غير مسجل'
    if value.upper() in _RESERVED:value='_'+value
    return value[:maxlen].rstrip(' .')

def export_name(kind,format_name,metadata=None,stamp=''):
    if metadata and kind=='client':
        customer=clean_component(metadata.get('name'),95)
        phone=clean_component(metadata.get('phone') or 'بدون رقم',40)
        return f'{customer} - {phone}.{format_name}'
    return 'ProTech_Report_'+clean_component(kind,45)+'_'+str(stamp)+'.'+format_name

def preferred_widths(headers, rows, font_metrics=None):
    """Readable table widths in pixels; never hide original text."""
    widths=[]
    samples=rows[:60]
    for i,title in enumerate(headers):
        label=str(title)
        textmax=max([len(label)]+[len(str(r[i] or '')) for r in samples])
        if any(x in label for x in ('اسم العميل','لون البورسلان','ملاحظات','الصنف')):
            low,high=185,355
        elif any(x in label for x in ('الجوال','التواصل','الهاتف','العقد','الفاتورة','التاريخ')):
            low,high=132,205
        elif any(x in label for x in ('المبلغ','الفواتير','الألواح','الهانيكام')):
            low,high=125,185
        else:
            low,high=100,195
        suggested=(font_metrics.horizontalAdvance('م'*min(textmax,30))+26) if font_metrics else textmax*8+26
        widths.append(max(low,min(high,suggested)))
    return widths

def excel_char_width(header,sample,width_px=None):
    if width_px is not None:
        # Approximately 7px per character at Excel's default font size.
        return max(11,min(48,round(width_px/7.2)))
    name=str(header)
    if 'ملاحظات' in name:return 39
    if any(x in name for x in ('اسم العميل','لون البورسلان')):return 29
    if any(x in name for x in ('التاريخ','رقم الجوال','رقم التواصل')):return 19
    return max(12,min(32,max(len(name),max((len(str(x)) for x in sample[:60]),default=0))+3))
