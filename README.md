# داشب بورد الشفتات - الوكيل

لوحة تحكم مبسطة لإدارة الشفتات الخاصة بالرايدرز، مبنية باستخدام Streamlit ومتكاملة مع Google Sheets.

![Talabat ESM Team](talabat_logo_wobble.gif)

## المميزات

- 📊 مزامنة فورية للبيانات مع Google Sheets
- 📅 إدارة الشفتات اليومية ونظرة عامة
- 🏢 تقارير حسب العقد وحسب المدينة
- 📈 تتبّع معدل الإسناد
- 🔄 تحديث تلقائي للبيانات
- 📱 تصميم متجاوب

## خطوات الإعداد للمستخدمين الجدد

### 1. تثبيت البرامج المطلوبة

1. حمّل وثبّت Python من [python.org](https://www.python.org/downloads/)
   - أثناء التثبيت تأكد من تفعيل خيار "Add Python to PATH"
   - اضغط "Install Now" بالإعدادات الافتراضية

2. حمّل وثبّت Git من [git-scm.com](https://git-scm.com/downloads)
   - استخدم إعدادات التثبيت الافتراضية

3. حمّل وثبّت GitHub Desktop من [desktop.github.com](https://desktop.github.com/)
   - يوفر واجهة سهلة لإدارة المشروع

### 2. الحصول على المشروع

1. افتح GitHub Desktop
2. اختر "File" → "Clone Repository"
3. أدخل الرابط: `https://github.com/Mohmedragab2398/shift-automation`
4. اختر مكان حفظ المشروع على جهازك
5. اضغط "Clone"

### 3. إعداد المشروع

1. افتح موجه الأوامر في ويندوز:
   - اضغط Win + R
   - اكتب "cmd" ثم Enter

2. انتقل إلى مجلد المشروع:
   ```bash
   cd path/to/your/project
   ```

3. إنشاء بيئة افتراضية:
   ```bash
   python -m venv venv
   ```

4. تفعيل البيئة الافتراضية:
   ```bash
   venv\Scripts\activate
   ```

5. تثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

### 4. إعداد الوصول إلى Google Sheets

1. أنشئ مجلد `.streamlit` داخل المشروع (إذا لم يكن موجودًا)
2. أنشئ ملف `secrets.toml` داخل مجلد `.streamlit`
3. أضف بيانات اعتماد Google Sheets:
   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "your-private-key"
   client_email = "your-client-email"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your-cert-url"

   [google_sheets]
   spreadsheet_id = "your-spreadsheet-id"
   ```

### 5. تشغيل التطبيق

1. داخل موجه الأوامر (بعد تفعيل venv):
```bash
streamlit run app.py
```

2. ستفتح لوحة التحكم في المتصفح الافتراضي

## دليل الاستخدام

### إدارة بيانات الرايدرز

1. يتم تحميل بيانات الرايدرز تلقائيًا من Google Sheets
2. اضغط "تحديث بيانات الرايدرز" لتحديث البيانات
3. يجب مشاركة الشيت مع بريد حساب الخدمة (Service Account)

### رفع ملفات المدن

1. جهّز ملفات CSV بالأعمدة المطلوبة:
   - Employee ID
   - Employee Name
   - Contract Name
   - Shift Status
   - Planned Start/End Date
   - Planned Start/End Time

2. ارفع الملفات من قسم "رفع ملفات المدن"

### التقارير والتحليل

- **نظرة عامة**: إجماليات وتوزيعات
- **الرايدرز غير المسندين**: قائمة بالرايدرز بدون شفتات
- **تقرير العقود**: تحليل حسب العقد
- **تقرير المدن**: تحليل حسب المدينة

## حل المشاكل

إذا واجهتك أي مشكلة:

1. تأكد من تثبيت Python وكل المتطلبات
2. راجع بيانات اعتماد Google Sheets والصلاحيات
3. تأكد أن صيغة CSV مطابقة للمتطلبات
4. جرّب تحديث الصفحة أو إعادة تشغيل التطبيق

## الدعم

للمساعدة أو الاستفسارات تواصل مع:
- Mohamed Ragab (Project Lead)

## التحديثات

للحصول على آخر التحديثات:
1. افتح GitHub Desktop
2. اضغط "Fetch origin"
3. اضغط "Pull origin" إذا كانت هناك تحديثات

# Data Sanitization Module

This module provides robust data handling capabilities for processing Excel files with varying formats and structures.

## Features

- Automatic detection of data sheets in Excel files
- Smart column name normalization based on common patterns
- Data cleaning and validation
- Handling of empty rows and columns
- Required column validation

## Dependencies

Required Python packages are listed in `requirements.txt`. Install them using:

```bash
pip install -r requirements.txt
```

## Usage

```python
from data_sanitizer import DataSanitizer

# Process an Excel file
df = DataSanitizer.process_excel_file('path/to/file.xlsx', required_columns=['Column1', 'Column2'])

# Or use individual methods
sanitizer = DataSanitizer()
sheet = sanitizer.find_data_sheet(workbook)
df = sanitizer.normalize_column_names(df)
df = sanitizer.clean_data(df)
sanitizer.validate_required_columns(df, required_columns)
```

## Column Name Patterns

The module includes common patterns for column name normalization. For example:
- "First Name" -> "first_name"
- "Last Name" -> "last_name"
- "Email Address" -> "email"
- "Phone Number" -> "phone"

Add more patterns by extending the `COLUMN_PATTERNS` dictionary in the `DataSanitizer` class. 