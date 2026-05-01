# نظام إدارة الفواتير والمدفوعات
## تعليمات التشغيل والتوزيع

---

## تشغيل مباشر (للتطوير والاختبار)

```bash
pip install flask
python app.py
```

يفتح المتصفح تلقائياً على http://localhost:5000

---

## بناء ملف .exe لـ Windows 10

### المتطلبات (مرة واحدة فقط على جهاز التطوير)
```bash
pip install pyinstaller flask
```

### أمر البناء
```bash
pyinstaller --onefile --noconsole --name "نظام_الفواتير" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "localization-ar.json;." ^
  app.py
```

الناتج في مجلد dist — ملف واحد نظام_الفواتير.exe

---

## هيكل الملفات على جهاز العميل

D:\InvoicesApp\
  نظام_الفواتير.exe        (الملف التنفيذي)
  localization-ar.json      (ملف النصوص - قابل للتعديل)
  invoices.db               (قاعدة البيانات - تنشأ تلقائياً)
  backups\                  (نسخ احتياطية - تنشأ تلقائياً)

---

## التعريب - تعديل النصوص

افتح localization-ar.json بالمفكرة وعدل اي نص.
لا حاجة لاعادة بناء الملف التنفيذي.
التغييرات تظهر فور اعادة تشغيل البرنامج.

---

## النسخ الاحتياطي

- تلقائي: كل 10 عمليات حفظ في مجلد backups\
- USB: عند توصيل USB ينسخ تلقائياً الى InvoicesBackup\ على الـ USB
- يدوي: زر نسخ احتياطي في القائمة الجانبية
- توصية اسبوعية: انسخ مجلد backups\ الى USB او هاتف

---

## استعادة البيانات

انسخ ملف .db من مجلد backups\ الى نفس مجلد البرنامج باسم invoices.db
