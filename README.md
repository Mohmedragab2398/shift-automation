# Shift Management Dashboard

A streamlined dashboard for managing employee shifts, built with Streamlit and Google Sheets integration.

![Talabat ESM Team](talabat_logo_wobble.gif)

## Features

- 📊 Real-time data synchronization with Google Sheets
- 📅 Daily shift management and overview
- 🏢 Contract-wise and city-wise reports
- 📈 Assignment rate tracking
- 🔄 Automatic data refresh
- 📱 Responsive design

## Setup Instructions for New Users

### 1. Install Required Software

1. Download and install Python from [python.org](https://www.python.org/downloads/)
   - During installation, make sure to check "Add Python to PATH"
   - Click "Install Now" with recommended options

2. Download and install Git from [git-scm.com](https://git-scm.com/downloads)
   - Use default installation options

3. Download and install GitHub Desktop from [desktop.github.com](https://desktop.github.com/)
   - This provides an easy-to-use interface for managing the project

### 2. Get the Project

1. Open GitHub Desktop
2. Click on "File" → "Clone Repository"
3. Enter URL: `https://github.com/Mohmedragab2398/shift-automation`
4. Choose where to save it on your computer
5. Click "Clone"

### 3. Set Up the Project

1. Open Command Prompt (Windows):
   - Press Win + R
   - Type "cmd" and press Enter

2. Navigate to project folder:
   ```bash
   cd path/to/your/project
   ```

3. Create virtual environment:
   ```bash
   python -m venv venv
   ```

4. Activate virtual environment:
   ```bash
   venv\Scripts\activate
   ```

5. Install requirements:
```bash
pip install -r requirements.txt
```

### 4. Configure Google Sheets Access

1. Create `.streamlit` folder in project directory (if not exists)
2. Create `secrets.toml` file inside `.streamlit` folder
3. Add your Google Sheets credentials:
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

### 5. Run the Application

1. In Command Prompt (with venv activated):
```bash
streamlit run app.py
```

2. The dashboard will open in your default web browser

## Usage Guide

### Employee Data Management

1. Employee data is automatically loaded from Google Sheets
2. Click "Refresh Employee Data" to update the data
3. The sheet must be shared with the service account email

### City Files Upload

1. Prepare CSV files with required columns:
   - Employee ID
   - Employee Name
   - Contract Name
   - Shift Status
   - Planned Start/End Date
   - Planned Start/End Time

2. Upload files using the "Upload City Files" section

### Reports and Analysis

- **Overview**: Shows total metrics and distributions
- **Daily Shifts**: Detailed view of shifts for each date
- **Unassigned Employees**: Lists employees without shifts
- **Contract Report**: Analysis by contract
- **City Report**: Analysis by city

## Troubleshooting

If you encounter any issues:

1. Make sure Python and all requirements are installed
2. Check Google Sheets credentials and permissions
3. Verify CSV file format matches requirements
4. Try refreshing the page or restarting the application

## Support

For help or questions, contact:
- Mohamed Ragab (Project Lead)

## Updates

To get the latest updates:
1. Open GitHub Desktop
2. Click "Fetch origin"
3. Click "Pull origin" if updates are available

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