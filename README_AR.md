# ProTech Marble & Porcelain Manager v2.0.0

**License:** [MIT](LICENSE) for original ProTech-owned code; dependencies retain their own licenses.

**Windows Setup:** The current v2.0.0 installer is unsigned. It is kept in a GitHub draft release until trusted Code Signing and acceptance testing are completed. Do not claim SmartScreen warnings are eliminated.

برنامج إدارة الرخام والبورسلان والعملاء والعقود والمخزون وتقارير PDF وExcel على Windows، باللغة العربية.

**المطور:** Abu Omar — ProTech
**البريد الإلكتروني:** protech.2025.2026@gmail.com
**الجوال:** +966 50 327 6927
**GitHub:** https://github.com/Abdealmalk007

## الميزات
- عقود العملاء تتضمن نوع المادة (رخام أو بورسلان) واللون والسماكة بالملليمتر ومساحة م² وطول م/ط.
- إدارة كتالوج منفصل لأنواع الرخام والبورسلان والغراء والألواح والهانيكام.
- إدارة المخزون الوارد والصرف والجرد مع عدم افتراض وجود رصيد لم يُسجّل فعليًا.
- داشبورد ديناميكي وتقارير PDF / Excel / CSV، وفلاتر بالتقويم، ومعاينة PDF متعددة الصفحات، والطباعة.
- تعديل أعمدة التقارير، خطوط واضحة، هوامش صغيرة، وحفظ التقرير باسم العميل ورقم جواله.
- إضافة شعار واسم الشركة من الإعدادات، ومرفقات PDF والصور لكل عميل.

## حماية خصوصية العملاء
**نسخة النشر تبدأ صفرًا:** العملاء 0، الألوان والأصناف 0، المرفقات 0، حركات المخزون 0، والمبالغ 0.
لا تتضمن نسخة Setup أي سجلات أو ملفات Excel أو صور عملاء أو قواعد بيانات خاصة بالمطور.

تُنشأ قاعدة بيانات منفصلة لكل مستخدم داخل:
%LOCALAPPDATA%\ProTech\StoneManager

مجلدات البيانات: Database وAttachments وBranding وBackups وExports.
لا يحتاج المستخدم إلى القرص E أو إلى Python لتشغيل البرنامج بعد التثبيت.
هذه النسخة العامة لا تقرأ قاعدة بيانات ProTech Porcelain Manager الخاصة ولا تغيّرها، ولا تنقل بياناتها تلقائيًا.

## التثبيت
1. قم بتنزيل Setup.exe من GitHub Releases بعد نشر الإصدار.
2. شغّل Setup.exe على Windows 10/11 بنظام x64.
3. افتح البرنامج، وحدد اسم شركتك وشعارها من الإعدادات.
4. أضف الأصناف والعملاء والطلبات الخاصة بك، وسجّل الجرد الافتتاحي قبل التعامل مع أرصدة المخزون.

## البناء من المصدر
المتطلبات: Windows x64، Python 3.13، Inno Setup 6.

~~~powershell
python -m pip install -r requirements-build.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\installer.iss
~~~

إذا كان Inno Setup مثبتًا في مسار مختلف فاستخدم ISCC.exe من ذلك المسار.
الملف الناتج: Release\Setup.exe

## النشر على GitHub
أنشئ مستودعًا جديدًا مستقلًا لهذا الإصدار، وارفع src وملفات الإعداد والبناء والوثائق فقط.
ارفع Setup.exe وSHA256SUMS.txt في GitHub Releases.
سير العمل .github/workflows/windows-release.yml يبني تلقائيًا عند دفع وسم v2.0.0 ويتيح تنزيل المثبت.

## اعتبارات الأمان والتوزيع
قد يعرض Windows SmartScreen تحذيرًا لأن التطبيق غير موقّع بشهادة Code Signing معترف بها.
لا تعطل SmartScreen للمستخدمين؛ التوقيع الرقمي الصحيح هو الحل المعتمد.

حقوق برنامج ProTech محفوظة للمطور Abu Omar. لم تُحدّد رخصة مفتوحة المصدر بعد.
راجع THIRD_PARTY_NOTICES.md لمكتبات الطرف الثالث ومتطلبات إعادة توزيعها.
