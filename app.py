# Force redeploy with openpyxl dependency
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from data_sanitizer import DataSanitizer, validate_data
import io
import numpy as np
import logging
from data_processor import DataProcessor
from sheets_connector import SheetsConnector
import os
import gspread
from google.oauth2.service_account import Credentials
import pprint

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Shift Management Dashboard", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        margin-bottom: 30px;
    }
    .logo-text {
        color: #FF5A00;
        font-family: Arial, sans-serif;
        font-weight: 900;
        font-size: 72px;
        line-height: 1;
        letter-spacing: -1px;
    }
    .team-text {
        color: #FF5A00;
        font-family: Arial, sans-serif;
        font-weight: 900;
        font-size: 36px;
        margin-left: 360px;
        margin-top: -25px;
        display: inline-block;
    }
    @keyframes wobble {
        0% { transform: rotate(0deg); }
        25% { transform: rotate(-1deg); }
        75% { transform: rotate(1deg); }
        100% { transform: rotate(0deg); }
    }
    .wobble {
        animation: wobble 2s ease-in-out infinite;
        display: inline-block;
    }
    .stDataFrame {
        font-size: 14px;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 15px;
        margin: 5px;
    }
    .header-style {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 10px;
        color: #1f77b4;
    }
    .file-upload-info {
        font-size: 14px;
        color: #666;
        margin-bottom: 10px;
    }
    .file-upload-error {
        color: #721c24;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
    }
    /* Table Styling */
    .metric-table {
        font-size: 14px;
        width: 100%;
        margin: 10px 0;
    }
    .metric-table th {
        background-color: #f0f2f6;
        padding: 8px;
        text-align: center;
        font-weight: bold;
    }
    .metric-table td {
        padding: 8px;
        text-align: center;
    }
    .total-row {
        background-color: #e6e9ef;
        font-weight: bold;
    }
    .date-header {
        font-size: 18px;
        font-weight: bold;
        color: #1f77b4;
        margin: 20px 0 10px 0;
    }
    .summary-header {
        font-size: 20px;
        font-weight: bold;
        color: #2c3e50;
        margin: 30px 0 15px 0;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Create a container for the header section
header_container = st.container()

# Create two columns for logo and credit text
with header_container:
    left_col, right_col = st.columns([1, 1])
    
    # Logo on the left
    with left_col:
        st.markdown(
            '<div class="logo-container wobble">'
            '<div class="logo-text">talabat ESM</div>'
            '<div class="team-text">Team</div>'
            '</div>',
            unsafe_allow_html=True
        )
        
    # Credit text on the right
    with right_col:
        st.markdown(
            "<div style='text-align: right; color: #666666; padding: 20px 0;'>"
            "Designed by Mohamed Ragab"
            "</div>",
            unsafe_allow_html=True
        )

# Main title
st.markdown(
    '<h1 style="text-align: center; margin: 20px 0;">Shift Management Dashboard</h1>',
    unsafe_allow_html=True
)

def style_percentage(val):
    """Style percentage values with color thresholds"""
    try:
        if pd.isna(val):
            return ''
        val = float(str(val).strip('%')) if isinstance(val, str) else float(val)
        if val >= 80:
            return 'background-color: #28a745; color: white; font-weight: bold'
        elif val >= 70:
            return 'background-color: #ffc107; color: black; font-weight: bold'
        else:
            return 'background-color: #dc3545; color: white; font-weight: bold'
    except (ValueError, TypeError):
        return ''

def style_dataframe(df, percentage_cols=None, add_grand_total=False):
    """Display percentage values without conditional formatting, and optionally add a Grand Total row."""
    if percentage_cols is None:
        percentage_cols = []
    
    if df.empty:
        return df.style

    # Create a copy to avoid modifying the original dataframe
    df = df.copy()

    # Only apply formatting to columns that exist in the DataFrame
    existing_percentage_cols = [col for col in percentage_cols if col in df.columns]
    numeric_cols = [col for col in df.columns if df[col].dtype in [int, float] or pd.api.types.is_numeric_dtype(df[col])]
    
    # Calculate percentages for all rows before adding Grand Total
    for col in df.columns:
        if 'Percentage' in col:
            # Get the corresponding Assigned and Total columns
            date_prefix = col.split('_Percentage')[0]
            assigned_col = f"{date_prefix}_Assigned" if date_prefix else "Assigned"
            total_col = "Total"
            
            if assigned_col in df.columns and total_col in df.columns:
                # Calculate percentage for each row
                df[col] = (df[assigned_col].apply(pd.to_numeric, errors='coerce') / 
                          df[total_col].apply(pd.to_numeric, errors='coerce') * 100)
    
    # Optionally add Grand Total row
    if add_grand_total:
        total_row = {}
        for col in df.columns:
            if col in numeric_cols and 'percentage' not in col.lower():
                # For numeric columns (excluding percentage columns), sum the values
                total_row[col] = df[col].apply(pd.to_numeric, errors='coerce').sum()
            elif 'Percentage' in col:
                # Calculate the average of the percentage values
                percentage_values = df[col].dropna()
                if not percentage_values.empty:
                    avg_percentage = percentage_values.mean()
                    total_row[col] = avg_percentage
                else:
                    total_row[col] = 0.0
            elif col.lower() in ['city', 'contract']:
                total_row[col] = 'Grand Total'
            else:
                total_row[col] = ''
        
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

    # Create format dictionary
    format_dict = {col: '{:,.0f}' for col in numeric_cols if 'percentage' not in col.lower()}
    format_dict.update({col: '{:.1f}%' for col in df.columns if 'Percentage' in col})

    styler = df.style.format(format_dict)
    styler = styler.set_properties(**{
        'text-align': 'center',
        'font-size': '14px',
        'padding': '8px'
    })
    styler = styler.set_table_styles([{
        'selector': 'th',
        'props': [
            ('background-color', '#f0f2f6'),
            ('color', '#333'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '8px'),
            ('white-space', 'nowrap')
        ]
    }])
    return styler

def display_overview(employee_df, shift_df, contract_report_df, city_report_df):
    """Display overview metrics and charts."""
    st.header("Overview")
    
    # Only consider valid shift statuses for assignment
    valid_statuses = ["EVALUATED", "PUBLISHED"]
    filtered_shift_df = shift_df[shift_df['shift_status'].isin(valid_statuses)] if 'shift_status' in shift_df.columns else shift_df

    # Calculate overall metrics using only filtered shifts
    total_employees = len(employee_df)
    total_assigned = len(filtered_shift_df['employee_id'].unique()) if not filtered_shift_df.empty else 0
    overall_percentage = (total_assigned / total_employees * 100) if total_employees > 0 else 0
    
    # Display overall metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Employees", total_employees)
    with col2:
        st.metric("Total Assigned", total_assigned)
    with col3:
        st.metric("Overall Assignment Rate", f"{overall_percentage:.1f}%")
    
    # Display contract-wise metrics
    st.subheader("Contract-wise Distribution")
    if not contract_report_df.empty:
        contract_fig = px.bar(
            contract_report_df,
            x='Contract',
            y=['Total', 'Assigned'],
            barmode='group',
            title='Employee Distribution by Contract'
        )
        st.plotly_chart(contract_fig, use_container_width=True)
    
    # Display city-wise metrics
    st.subheader("City-wise Distribution")
    if not city_report_df.empty:
        city_fig = px.pie(
            city_report_df,
            values='Total',
            names='City',
            title='Employee Distribution by City'
        )
        st.plotly_chart(city_fig, use_container_width=True)

def display_daily_shifts(df, date):
    """Display daily shifts with improved formatting."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        st.warning(f"No shift data available for {date}")
        return
    
    # Defensive filter: only show shifts for the exact date
    df = df[df['planned_start_date'] == date] if 'planned_start_date' in df.columns else df
    
    # Add header
    st.markdown(f"<div class='header-style'>Daily Shifts - {date}</div>", unsafe_allow_html=True)
    
    # Display metrics
    total_shifts = len(df)
    unique_employees = len(df['employee'].unique()) if 'employee' in df.columns else len(df['employee_id'].unique())
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Shifts", total_shifts)
    with col2:
        st.metric("Unique Employees", unique_employees)
    
    # Add All Shifts Update button
    if st.button("All Shifts Update", key=f"all_shifts_{date}"):
        # Display all shifts in one table
        display_df = df.copy()
        if 'employee_id' in display_df.columns:
            display_df['employee'] = display_df['employee_id']
        
        display_df = display_df[[
            'employee', 'planned_start_time', 'planned_end_time'
        ]].sort_values('planned_start_time')
        
        # Format planned_start_time and planned_end_time as Time (HH:MM)
        for col in ['planned_start_time', 'planned_end_time']:
            if col in display_df.columns:
                display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.strftime('%H:%M')
        
        # Display table with styling
        st.dataframe(style_dataframe(display_df, ['Assigned_Percentage']), use_container_width=True)

def display_unassigned_employees(employees_df: pd.DataFrame, shifts_df: pd.DataFrame, selected_date: str):
    """Display employees who have no shifts assigned for the selected date."""
    if employees_df is None or shifts_df is None:
        st.warning("No data available to display unassigned employees.")
        return
    if employees_df.empty or shifts_df.empty:
        st.warning("No employee or shift data available.")
        return
    try:
        # Validate required columns exist
        required_employee_cols = ['employee_id', 'employee_name', 'contract_name', 'city']
        required_shift_cols = ['employee_id', 'planned_start_date']
        missing_emp_cols = [col for col in required_employee_cols if col not in employees_df.columns]
        missing_shift_cols = [col for col in required_shift_cols if col not in shifts_df.columns]
        if missing_emp_cols or missing_shift_cols:
            st.error(f"Missing required columns: {', '.join(missing_emp_cols + missing_shift_cols)}")
            return

        employees_df = employees_df.copy()
        shifts_df = shifts_df.copy()
        shifts_df['planned_start_date'] = pd.to_datetime(shifts_df['planned_start_date']).dt.date
        selected_date = pd.to_datetime(selected_date).date()
        filtered_shifts = shifts_df[shifts_df['planned_start_date'] == selected_date]
        assigned_employees = filtered_shifts['employee_id'].unique()
        unassigned_df = employees_df[~employees_df['employee_id'].isin(assigned_employees)].copy()
        unassigned_df = unassigned_df.sort_values('employee_name')

        total_employees = len(employees_df)
        unassigned_count = len(unassigned_df)
        assigned_count = total_employees - unassigned_count

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Employees", total_employees)
        with col2:
            st.metric("Assigned", assigned_count)
        with col3:
            st.metric("Unassigned", unassigned_count)

        if not unassigned_df.empty:
            st.subheader(f"Unassigned Employees for {selected_date}")
            
            # Add contract filter dropdown with unique key based on date
            contracts = ['All Contracts'] + sorted(unassigned_df['contract_name'].unique().tolist())
            selected_contract = st.selectbox(
                'Filter by Contract:', 
                contracts,
                key=f"contract_select_{selected_date}"  # Unique key for each date
            )
            
            # Filter by selected contract
            if selected_contract != 'All Contracts':
                display_df = unassigned_df[unassigned_df['contract_name'] == selected_contract]
            else:
                display_df = unassigned_df
            
            # Display data without styling
            display_columns = ['employee_id', 'employee_name', 'contract_name', 'city']
            st.dataframe(display_df[display_columns], use_container_width=True)
        else:
            st.success(f"All employees are assigned shifts for {selected_date}")

    except Exception as e:
        st.error(f"Error displaying unassigned employees: {str(e)}")
        logger.error(f"Error in display_unassigned_employees: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def display_contract_report(data, employee_data):
    """Display contract-wise report with enhanced validation and styling."""
    st.header("Contract Report")
    try:
        if data is None or employee_data is None or data.empty or employee_data.empty:
            st.warning("No data available for contract report")
            return
        
        # Get unique dates and contracts
        dates = sorted(data['planned_start_date'].unique())
        contracts = sorted(employee_data['contract_name'].unique())
        
        # Create tabs for each contract
        tabs = st.tabs(contracts)
        for i, contract in enumerate(contracts):
            with tabs[i]:
                # Get contract employees
                contract_employees = employee_data[employee_data['contract_name'] == contract]
                total = len(contract_employees)
                
                # Calculate overall metrics for the selected date range
                contract_shifts = data[data['employee_id'].isin(contract_employees['employee_id'])]
                if not contract_shifts.empty:
                    # Remove duplicates to count each employee only once
                    assigned = len(contract_shifts.drop_duplicates('employee_id')['employee_id'])
                else:
                    assigned = 0
                    
                unassigned = total - assigned
                assignment_rate = (assigned / total * 100) if total > 0 else 0
                
                # Display overall metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Employees", int(total))
                with col2:
                    st.metric("Total Assigned", int(assigned))
                with col3:
                    st.metric("Total Unassigned", int(unassigned))
                with col4:
                    st.metric("Overall Assignment Rate", f"{assignment_rate:.1f}%")
                
                # Per-day tables
                for date in dates:
                    date_str = pd.to_datetime(date).strftime('%d-%m')
                    date_data = data[data['planned_start_date'] == date]
                    if date_data.empty:
                        continue
                    
                    # Generate report for this date
                    mini_report = DataSanitizer.generate_contract_report(date_data, contract_employees)
                    if mini_report.empty:
                        continue
                        
                    mini_report = mini_report[mini_report['Contract'] == contract]
                    if mini_report.empty:
                        continue
                        
                    mini_report = mini_report.sort_values('City')
                    st.markdown(f"#### {date_str}")
                    styled_report = style_dataframe(
                        mini_report[['City', 'Total', 'Assigned', 'Unassigned', 'Assigned_Percentage']],
                        ['Assigned_Percentage']
                    )
                    st.dataframe(styled_report, use_container_width=True)
                
                # Summary table (side-by-side, like City Report)
                st.markdown("### Summary View (All Dates)")
                summary_data = []
                cities = sorted(contract_employees['city'].unique())
                
                for city in cities:
                    row = {'City': city}
                    for date in dates:
                        date_str = pd.to_datetime(date).strftime('%d-%m')
                        date_data = data[data['planned_start_date'] == date]
                        if date_data.empty:
                            row[f'{date_str}_Assigned'] = 0
                            row[f'{date_str}_Unassigned'] = 0
                            row[f'{date_str}_Percentage'] = 0.0
                            continue
                            
                        city_employees = contract_employees[contract_employees['city'] == city]
                        date_data = date_data[date_data['employee_id'].isin(city_employees['employee_id'])]
                        
                        total_employees = len(city_employees)
                        assigned = len(date_data.drop_duplicates('employee_id'))
                        unassigned = total_employees - assigned
                        percentage = (assigned / total_employees * 100) if total_employees > 0 else 0.0
                        
                        row[f'{date_str}_Assigned'] = assigned
                        row[f'{date_str}_Unassigned'] = unassigned
                        row[f'{date_str}_Percentage'] = percentage
                        
                    summary_data.append(row)
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    percentage_cols = [col for col in summary_df.columns if col.endswith('_Percentage')]
                    styled_summary = style_dataframe(summary_df, percentage_cols, add_grand_total=True)
                    st.dataframe(styled_summary, use_container_width=True)
    except Exception as e:
        st.error(f"Error in contract report display: {str(e)}")
        print(f"Error in contract report display: {str(e)}")

def display_city_report(data, employee_data):
    """Display city-wise report with enhanced validation and styling."""
    st.header("City Report")
    try:
        # Input validation
        if data is None or employee_data is None or data.empty or employee_data.empty:
            st.warning("No data available for city report")
            return

        # Generate city report
        report = DataSanitizer.generate_city_report(data, employee_data)
        if report.empty:
            st.warning("No data available for city report")
            return

        # Get unique dates and cities
        dates = sorted(data['planned_start_date'].unique())
        cities = sorted(report['City'].unique())

        # Create tabs for each city
        tabs = st.tabs(cities)
        for i, city in enumerate(cities):
            with tabs[i]:
                city_data = report[report['City'] == city].copy()
                
                # Create a table for each date
                for date in dates:
                    date_str = pd.to_datetime(date).strftime('%d-%m')
                    date_data = city_data[city_data['Date'] == date].copy()
                    
                    if not date_data.empty:
                        st.markdown(f"#### {date_str}")
                        date_data = date_data.sort_values('Contract')
                        styled_report = style_dataframe(
                            date_data[['Contract', 'Total', 'Assigned', 'Unassigned', 'Assigned_Percentage']],
                            ['Assigned_Percentage'],
                            add_grand_total=True
                        )
                        st.dataframe(styled_report, use_container_width=True)
                
                # Create side-by-side summary table
                if not city_data.empty:
                    st.markdown("### Summary View (All Dates)")
                    summary_data = []
                    contracts = sorted(city_data['Contract'].unique())
                    
                    for contract in contracts:
                        row = {'Contract': contract}
                        for date in dates:
                            date_str = pd.to_datetime(date).strftime('%d-%m')
                            date_contract_data = city_data[
                                (city_data['Date'] == date) & 
                                (city_data['Contract'] == contract)
                            ]
                            
                            if not date_contract_data.empty:
                                row[f'{date_str}_Assigned'] = date_contract_data['Assigned'].iloc[0]
                                row[f'{date_str}_Unassigned'] = date_contract_data['Unassigned'].iloc[0]
                                row[f'{date_str}_Percentage'] = date_contract_data['Assigned_Percentage'].iloc[0]
                            else:
                                row[f'{date_str}_Assigned'] = 0
                                row[f'{date_str}_Unassigned'] = 0
                                row[f'{date_str}_Percentage'] = 0.0
                        
                        summary_data.append(row)
                    
                    if summary_data:
                        summary_df = pd.DataFrame(summary_data)
                        percentage_cols = [col for col in summary_df.columns if col.endswith('_Percentage')]
                        styled_summary = style_dataframe(summary_df, percentage_cols, add_grand_total=True)
                        st.dataframe(styled_summary, use_container_width=True)
                
    except Exception as e:
        st.error(f"Error in city report display: {str(e)}")
        print(f"Error in city report display: {str(e)}")

def main():
    st.title("Shift Management Dashboard")
    
    # Initialize Google Sheets connector
    try:
        sheets_connector = SheetsConnector()
        SPREADSHEET_ID = st.secrets["spreadsheet_id"]
        
        if 'sheets_connector' not in st.session_state:
            st.session_state['sheets_connector'] = sheets_connector
            
    except Exception as e:
        st.error(f"Error initializing Google Sheets: {str(e)}")
        st.markdown("""
        Please check:
        1. The sheet is shared with: `sheet-accessa@shift-automation-458000.iam.gserviceaccount.com`
        2. The sheet contains data in the 'all2' tab
        3. The sheet ID is correct in .streamlit/secrets.toml
        4. You have enabled the Google Sheets API in your Google Cloud Console
        """)
        return

    col1, col2 = st.columns(2)

    # Employee data from Google Sheets
    with col1:
        st.subheader("Employee Data (auto-loaded from Google Sheets)")
        if st.button("Refresh Employee Data"):
            st.session_state['employee_refresh'] = True

        employee_df = None  # Initialize to avoid unbound error

        if 'employee_df' not in st.session_state or st.session_state.get('employee_refresh', False):
            with st.spinner("Loading employee data from Google Sheets..."):
                try:
                    employee_df = st.session_state.sheets_connector.read_sheet(
                        spreadsheet_id=SPREADSHEET_ID,
                        range_name='all2!A1:Z'  # Load all columns
                    )
                    if employee_df is not None and not employee_df.empty:
                        employee_df.columns = [str(col).strip().lower().replace(' ', '_') for col in employee_df.columns]
                        st.session_state['employee_df'] = employee_df
                        st.session_state['employee_refresh'] = False
                        st.success(f"Successfully loaded {len(employee_df)} employee records from Google Sheets.")
                    else:
                        st.error("No data was returned from Google Sheets. Please check:")
                        st.markdown("""
                        1. The sheet is shared with: `sheet-accessa@shift-automation-458000.iam.gserviceaccount.com`
                        2. The sheet contains data in the 'all2' tab
                        3. The sheet ID is correct
                        """)
                except Exception as e:
                    st.error(f"Error loading employee data: {str(e)}")
        else:
            employee_df = st.session_state.get('employee_df', None)
            if employee_df is not None and not employee_df.empty:
                st.success(f"Displaying {len(employee_df)} employee records.")

        if employee_df is not None and not employee_df.empty:
            st.dataframe(employee_df, use_container_width=True)

    # City file upload remains the same and is always visible
    with col2:
        st.subheader("Upload City Files")
        st.markdown(
            '<div class="file-upload-info">'
            'Upload city-specific CSV files containing shift information<br>'
            'Required columns: Employee ID, Employee Name, Contract Name, Shift Status, '
            'Planned Start/End Date, Planned Start/End Time'
            '</div>',
            unsafe_allow_html=True
        )
        city_files = st.file_uploader(
            "Upload city files (CSV)",
            type=['csv'],
            accept_multiple_files=True,
            key="city_files"
        )

    if not city_files:
        st.warning("⚠️ Please upload at least one city file")
        return

    try:
        # Step 1: Process and merge city files
        with st.spinner("Processing city files..."):
            merged_shifts = DataSanitizer.merge_shift_files(city_files)
            if merged_shifts is None or merged_shifts.empty:
                st.error("No valid data found in city files")
                return
            merged_shifts.columns = merged_shifts.columns.str.strip().str.lower().str.replace(' ', '_')
            validate_data(merged_shifts, 'shift_file')
            st.success(f"✅ Successfully processed {len(city_files)} city files")

        # Date selection
        min_date = merged_shifts['planned_start_date'].min()
        max_date = merged_shifts['planned_start_date'].max()
        st.markdown("### Select Date Range")
        st.markdown(
            f'<div class="file-upload-info">'
            f'Available dates: {min_date} to {max_date}'
            '</div>',
            unsafe_allow_html=True
        )
        selected_dates = st.date_input(
            "Select dates to analyze",
            value=(min_date, min(max_date, min_date + timedelta(days=6))),
            min_value=min_date,
            max_value=max_date
        )
        if len(selected_dates) != 2:
            st.warning("Please select both start and end dates")
            return
        date_range = pd.date_range(selected_dates[0], selected_dates[1])
        filtered_shifts = DataSanitizer.filter_by_dates(merged_shifts, date_range)
        if filtered_shifts is None:
            st.error("No data found for selected dates")
            return
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Overview",
            "Daily Shifts",
            "Unassigned Employees",
            "Contract Report",
            "City Report"
        ])
        with tab1:
            filtered_shifts_df = pd.concat(filtered_shifts.values()) if filtered_shifts else pd.DataFrame()
            display_overview(
                employee_df,
                filtered_shifts_df,
                DataSanitizer.generate_contract_report(filtered_shifts_df, employee_df),
                DataSanitizer.generate_city_report(filtered_shifts_df, employee_df)
            )
        with tab2:
            for date in date_range:
                date_shifts = filtered_shifts.get(date.date(), pd.DataFrame())
                display_daily_shifts(date_shifts, date.date())
        with tab3:
            for date in date_range:
                date_shifts = filtered_shifts.get(date.date(), pd.DataFrame())
                display_unassigned_employees(employee_df, date_shifts, date.date())
        with tab4:
            display_contract_report(filtered_shifts_df, employee_df)
        with tab5:
            display_city_report(filtered_shifts_df, employee_df)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()