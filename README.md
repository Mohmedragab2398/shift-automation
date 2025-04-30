# Shift Management System 📊

A streamlined web application for managing and analyzing employee shift data across multiple cities and contracts.

## Features

- 📈 Interactive data visualization and reporting
- 📁 Support for multiple file formats (Excel, CSV)
- 🔄 Automatic column name detection and normalization
- 📊 Contract-wise and city-wise reports
- 📅 Date-based shift analysis
- ⬇️ Export reports to Excel

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone this repository or download the files
2. Open a terminal/command prompt in the project directory
3. Install the required packages:

```bash
pip install -r requirements.txt
```

## Running the Application

1. Open a terminal/command prompt in the project directory
2. Run the following command:

```bash
streamlit run app.py
```

3. Your default web browser will open automatically with the application

## Using the Application

1. **Upload Employee Data**
   - Use the sidebar to upload your employee master data file (All.xlsx)
   - Required columns: employee_id, employee_name, contract_name, city
   - Supports Excel (.xlsx, .xls, .xlsb, .xlsm) and CSV formats

2. **Upload City Files**
   - Upload one or more city shift files
   - Required columns: employee_id, shift_status, planned_start_time, planned_end_time
   - The system will automatically merge and process all files

3. **Select Dates**
   - Choose one or more dates to analyze from the calendar in the sidebar

4. **Process Data**
   - Click the "Process Data" button to generate reports
   - The system will validate your data and display any errors

5. **View Reports**
   - Contract Reports: Shows metrics by contract and city
   - City Reports: Displays city-wise statistics with visualizations
   - Shifts Update: Provides detailed shift information for selected dates

6. **Download Reports**
   - Each report can be downloaded as an Excel file
   - Click the download button below each report

## Troubleshooting

If you encounter any issues:

1. Ensure all required columns are present in your files
2. Check that date formats are consistent
3. Verify that employee IDs match between files
4. Make sure you have selected at least one date

## Support

For any questions or issues, please open an issue in the repository or contact the development team.

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