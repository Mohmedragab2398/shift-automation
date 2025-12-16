import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from data_sanitizer import DataSanitizer, validate_data
from sheets_connector import SheetsConnector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Shift Management Dashboard", layout="wide")

def apply_custom_table_styling():
    """Apply custom CSS styling for tables with blue headers and no borders."""
    # Only apply CSS once per session to prevent accumulation
    if 'css_applied' not in st.session_state:
        st.session_state.css_applied = True
        st.markdown("""
    <style>
        /* Remove all table borders and apply professional styling */
        .stDataFrame > div {
            border: none !important;
        }

        .stDataFrame table {
            border-collapse: separate !important;
            border-spacing: 0 !important;
            border: none !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        }

        .stDataFrame thead tr th {
            background: linear-gradient(135deg, #007BFF, #0056b3) !important;
            color: white !important;
            font-weight: bold !important;
            text-align: center !important;
            padding: 8px 6px !important;  /* Reduced padding */
            border: none !important;
            font-size: 12px !important;  /* Smaller font */
        }

        .stDataFrame tbody tr td {
            text-align: center !important;
            padding: 10px 8px !important;
            border: none !important;
            border-radius: 8px !important;
        }

        .stDataFrame tbody tr:nth-child(even) {
            background-color: #b8d4f0 !important;
        }

        .stDataFrame tbody tr:nth-child(odd) {
            background-color: white !important;
        }

        .stDataFrame tbody tr:hover {
            background-color: #e3f2fd !important;
        }

        /* Header styling for contract/city identification */
        .header-style {
            background: linear-gradient(135deg, #4a90a4, #2c5f6f);
            color: white;
            padding: 15px 20px;
            margin: 20px 0 10px 0;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-family: Arial, sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)

# Custom CSS for logo styling
st.markdown("""
<style>
    .logo-container {
        display: flex;
        flex-direction: row;
        align-items: baseline;
        justify-content: center;
        margin-bottom: 30px;
        gap: 20px;
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
        font-size: 48px;
        display: inline-block;
    }
    /* Removed wobble animation for better performance */
</style>
""", unsafe_allow_html=True)

# Display the 007 Team logo at the top
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
    <div class="logo-container">
        <div class="logo-text" style="color: #007BFF;">007</div>
        <div class="team-text">Team</div>
    </div>
    """, unsafe_allow_html=True)

# Define center alignment function once to avoid memory leaks
def _center_align_style(val):
    """Reusable center alignment function"""
    return 'text-align: center'

def normalize_city_name(city):
    """Normalize city name to standard form, especially for Port Said variations."""
    if pd.isna(city) or not isinstance(city, str):
        return city
    
    city_str = str(city).strip()
    city_lower = city_str.lower().replace(' ', '').replace('-', '').replace('_', '')
    
    # Handle Port Said variations (most common issue)
    if 'portsaid' in city_lower or 'portsaid' in city_lower:
        return 'Port Said'
    
    # Handle other cities - normalize to standard form
    city_mappings = {
        'cairo': 'Cairo',
        'assiut': 'Assiut',
        'hurghada': 'Hurghada',
        'minya': 'Minya',
        'mansoura': 'Mansoura',
        'damanhour': 'Damanhour',
        'almahallahalkubra': 'Al Mahallah Al Kubra',
        'al_mahallah_al_kubra': 'Al Mahallah Al Kubra',
        'al-mahallah-al-kubra': 'Al Mahallah Al Kubra',
        'al mahallah al kubra': 'Al Mahallah Al Kubra',
        'alexandria': 'Alexandria'
    }
    
    if city_lower in city_mappings:
        return city_mappings[city_lower]
    
    # Return title case for other cities
    return city_str.title()

def style_dataframe(df, percentage_cols=None, add_grand_total=False):
    """Apply professional styling to dataframes with blue headers and no borders."""
    if df.empty:
        return df

    # Performance optimization: Don't copy for large datasets
    if len(df) > 500:
        st.warning(f"Large dataset ({len(df)} rows). Displaying without advanced styling for better performance.")
        return df

    # Apply table styling with blue headers and no borders
    styler = df.style

    # Simplified table styling for better performance
    styler = styler.set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#007BFF'),
            ('color', 'white'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '8px 6px'),
            ('border', 'none'),
            ('font-size', '12px')
        ]},
        {'selector': 'td', 'props': [
            ('text-align', 'center'),
            ('padding', '10px 8px'),
            ('border', 'none')
        ]},
        {'selector': 'table', 'props': [
            ('border-collapse', 'separate'),
            ('border-spacing', '0'),
            ('border', 'none'),
            ('border-radius', '10px'),
            ('overflow', 'hidden')
        ]},
        {'selector': 'tr:nth-child(even)', 'props': [
            ('background-color', '#b8d4f0')
        ]},
        {'selector': 'tr:nth-child(odd)', 'props': [
            ('background-color', 'white')
        ]}
    ])

    # Use the reusable center alignment function
    styler = styler.map(_center_align_style)

    return styler

def create_table_header(title, subtitle=None):
    """Create a professional table header"""
    if subtitle:
        header_html = f"""
        <div class="header-style">
            <strong>{title}: {subtitle}</strong>
        </div>
        """
    else:
        header_html = f"""
        <div class="header-style">
            <strong>{title}</strong>
        </div>
        """
    st.markdown(header_html, unsafe_allow_html=True)

def display_overview(employee_df, shift_df, contract_report_df, city_report_df):
    """Display overview with metrics and charts."""
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
        st.plotly_chart(contract_fig, use_container_width=True, key="overview_contract_chart")

    # Display city-wise metrics
    st.subheader("City-wise Distribution")
    if not city_report_df.empty:
        city_fig = px.pie(
            city_report_df,
            values='Total',
            names='City',
            title='Employee Distribution by City'
        )
        st.plotly_chart(city_fig, use_container_width=True, key="overview_city_chart")

def display_unassigned_employees(employees_df: pd.DataFrame, shifts_df: pd.DataFrame, selected_date: str):
    """Display employees who have no shifts assigned for the selected date."""
    if employees_df is None or employees_df.empty:
        st.warning("No employee data available to display unassigned employees.")
        return

    # Handle case where shifts_df might be empty (no shifts uploaded yet)
    if shifts_df is None or shifts_df.empty:
        # If no shifts, all employees are unassigned
        unassigned_df = employees_df.copy()
        unassigned_df = unassigned_df.sort_values('employee_name')
        
        total_employees = len(employees_df)
        unassigned_count = len(unassigned_df)
        assigned_count = 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Employees", total_employees)
        with col2:
            st.metric("Assigned", assigned_count)
        with col3:
            st.metric("Unassigned", unassigned_count)
        
        st.subheader(f"Unassigned Employees for {selected_date}")
        st.info("No shift data uploaded yet. All employees are shown as unassigned.")

        # Add city filter dropdown with unique key based on date
        # Normalize city names to ensure "Port Said" appears correctly
        city_list = unassigned_df['city'].dropna().astype(str).apply(normalize_city_name).unique().tolist()
        cities = ['All Cities'] + sorted(city_list)
        selected_city = st.selectbox(
            'Filter by City:',
            cities,
            key=f"city_select_{selected_date}"
        )
        
        # Filter by selected city (normalize for comparison)
        if selected_city != 'All Cities':
            # Normalize city column for comparison
            unassigned_df_normalized = unassigned_df.copy()
            unassigned_df_normalized['city_normalized'] = unassigned_df_normalized['city'].astype(str).apply(normalize_city_name)
            display_df = unassigned_df_normalized[unassigned_df_normalized['city_normalized'] == selected_city].copy()
            display_df = display_df.drop(columns=['city_normalized'], errors='ignore')
        else:
            display_df = unassigned_df
        
        # Create doughnut chart showing city distribution of unassigned employees
        if not display_df.empty:
            city_counts = display_df['city'].value_counts()
            if len(city_counts) > 0:
                fig = px.pie(
                    values=city_counts.values,
                    names=city_counts.index,
                    title='Unassigned Employees by City',
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig.update_layout(
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5
                    ),
                    margin=dict(t=60, b=60, l=20, r=20)
                )
                # Add unique key to prevent duplicate chart ID error
                st.plotly_chart(fig, use_container_width=True, key=f"unassigned_chart_{selected_date}")
        
        # Display data
        display_columns = ['employee_id', 'employee_name', 'contract_name', 'city']
        display_columns = [col for col in display_columns if col in display_df.columns]
        st.dataframe(display_df[display_columns], use_container_width=True, hide_index=True)
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

        # Optimize: Normalize employee IDs once for better matching
        employees_df = employees_df.copy()
        employees_df['employee_id'] = employees_df['employee_id'].astype(str).str.strip()
        
        shifts_df = shifts_df.copy()
        shifts_df['employee_id'] = shifts_df['employee_id'].astype(str).str.strip()
        
        # Convert date and filter shifts for the selected date
        if 'planned_start_date' in shifts_df.columns:
            shifts_df['planned_start_date'] = pd.to_datetime(shifts_df['planned_start_date'], errors='coerce').dt.date
        selected_date_obj = pd.to_datetime(selected_date).date() if isinstance(selected_date, str) else selected_date
        
        # Filter shifts for the specific date - only consider valid statuses
        valid_statuses = ["EVALUATED", "PUBLISHED"]
        if 'shift_status' in shifts_df.columns:
            filtered_shifts = shifts_df[
                (shifts_df['planned_start_date'] == selected_date_obj) &
                (shifts_df['shift_status'].isin(valid_statuses))
            ]
        else:
            filtered_shifts = shifts_df[shifts_df['planned_start_date'] == selected_date_obj]
        
        # Get assigned employee IDs (only those with valid shifts for this date)
        if not filtered_shifts.empty:
            assigned_employee_ids = set(filtered_shifts['employee_id'].unique())
        else:
            assigned_employee_ids = set()
        
        # Filter to get only unassigned employees
        unassigned_df = employees_df[~employees_df['employee_id'].isin(assigned_employee_ids)].copy()
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

            # Add city filter dropdown with unique key based on date
            # Normalize city names to ensure "Port Said" appears correctly
            city_list = unassigned_df['city'].dropna().astype(str).apply(normalize_city_name).unique().tolist()
            cities = ['All Cities'] + sorted(city_list)
            selected_city = st.selectbox(
                'Filter by City:',
                cities,
                key=f"city_select_{selected_date}"
            )

            # Filter by selected city (normalize for comparison)
            if selected_city != 'All Cities':
                # Normalize city column for comparison
                unassigned_df_normalized = unassigned_df.copy()
                unassigned_df_normalized['city_normalized'] = unassigned_df_normalized['city'].astype(str).apply(normalize_city_name)
                display_df = unassigned_df_normalized[unassigned_df_normalized['city_normalized'] == selected_city].copy()
                display_df = display_df.drop(columns=['city_normalized'], errors='ignore')
            else:
                display_df = unassigned_df.copy()

            # Create doughnut chart showing city distribution of unassigned employees
            if not display_df.empty and 'city' in display_df.columns:
                city_counts = display_df['city'].value_counts()
                if len(city_counts) > 0:
                    fig = px.pie(
                        values=city_counts.values,
                        names=city_counts.index,
                        title='Unassigned Employees by City',
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig.update_layout(
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(t=60, b=60, l=20, r=20)
                    )
                    # Add unique key to prevent duplicate chart ID error
                    st.plotly_chart(fig, use_container_width=True, key=f"unassigned_chart_{selected_date}")

            # Display data - only show unassigned employees
            display_columns = ['employee_id', 'employee_name', 'contract_name', 'city']
            display_columns = [col for col in display_columns if col in display_df.columns]
            if not display_df.empty:
                st.dataframe(display_df[display_columns], use_container_width=True, hide_index=True)
        else:
            st.success(f"All employees are assigned shifts for {selected_date}")

    except Exception as e:
        st.error(f"Error displaying unassigned employees: {str(e)}")
        logger.error(f"Error in display_unassigned_employees: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def display_supervisors_report(employees_df: pd.DataFrame, shifts_df: pd.DataFrame, date_range):
    """Display supervisors report with sub-tabs for each supervisor showing assigned and unassigned employees."""
    try:
        if employees_df is None or employees_df.empty:
            st.warning("No employee data available for supervisors report.")
            return
        
        if shifts_df is None or shifts_df.empty:
            st.warning("No shift data available for supervisors report.")
            return

        # Check if supervisor column exists (handle both singular and plural)
        supervisor_col = None
        if 'supervisor' in employees_df.columns:
            supervisor_col = 'supervisor'
        elif 'supervisors' in employees_df.columns:
            supervisor_col = 'supervisors'
        else:
            # Try to find any column that might be supervisor (case insensitive)
            for col in employees_df.columns:
                if 'supervisor' in str(col).lower():
                    supervisor_col = col
                    break
        
        if supervisor_col is None:
            st.warning("Supervisor column not found in employee data. Please ensure column E contains supervisor names.")
            st.info(f"Available columns: {', '.join(employees_df.columns.tolist())}")
            return

        # Filter out employees without supervisor names
        employees_with_supervisor = employees_df[employees_df[supervisor_col].notna() & (employees_df[supervisor_col].astype(str).str.strip() != '')].copy()
        
        if employees_with_supervisor.empty:
            st.warning("No employees with supervisor information found.")
            return

        # Get unique supervisors
        supervisors = sorted(employees_with_supervisor[supervisor_col].unique().tolist())
        
        if not supervisors:
            st.warning("No supervisors found in the data.")
            return

        # Create tabs for each supervisor
        supervisor_tabs = st.tabs(supervisors)

        for i, supervisor in enumerate(supervisors):
            with supervisor_tabs[i]:
                # Get employees for this supervisor
                supervisor_employees = employees_with_supervisor[employees_with_supervisor[supervisor_col] == supervisor].copy()
                
                # Process each date in the range
                for date in date_range:
                    date_str = pd.to_datetime(date).strftime('%Y-%m-%d')
                    date_display = date.date() if hasattr(date, 'date') else date
                    
                    st.markdown(f"### {supervisor} - {date_str}")
                    
                    # Filter shifts for this date
                    shifts_df_copy = shifts_df.copy()
                    if 'planned_start_date' in shifts_df_copy.columns:
                        shifts_df_copy['planned_start_date'] = pd.to_datetime(shifts_df_copy['planned_start_date']).dt.date
                        date_shifts = shifts_df_copy[shifts_df_copy['planned_start_date'] == date_display]
                    else:
                        date_shifts = pd.DataFrame()
                    
                    # Get assigned and unassigned employees for this supervisor and date
                    if not date_shifts.empty:
                        assigned_employee_ids = date_shifts['employee_id'].unique()
                        assigned_employees = supervisor_employees[supervisor_employees['employee_id'].isin(assigned_employee_ids)].copy()
                        unassigned_employees = supervisor_employees[~supervisor_employees['employee_id'].isin(assigned_employee_ids)].copy()
                    else:
                        assigned_employees = pd.DataFrame()
                        unassigned_employees = supervisor_employees.copy()
                    
                    # Calculate metrics
                    total = len(supervisor_employees)
                    assigned_count = len(assigned_employees)
                    unassigned_count = len(unassigned_employees)
                    assignment_rate = (assigned_count / total * 100) if total > 0 else 0
                    
                    # Display metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Employees", total)
                    with col2:
                        st.metric("Assigned", assigned_count)
                    with col3:
                        st.metric("Unassigned", unassigned_count)
                    with col4:
                        st.metric("Assignment Rate", f"{assignment_rate:.1f}%")
                    
                    # Create two columns for assigned and unassigned
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"#### ✅ Assigned Employees ({assigned_count})")
                        if not assigned_employees.empty:
                            display_cols = ['employee_id', 'employee_name', 'city', 'contract_name']
                            display_cols = [col for col in display_cols if col in assigned_employees.columns]
                            st.dataframe(
                                assigned_employees[display_cols].sort_values('employee_name'),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("No assigned employees for this date.")
                    
                    with col2:
                        st.markdown(f"#### ❌ Unassigned Employees ({unassigned_count})")
                        if not unassigned_employees.empty:
                            display_cols = ['employee_id', 'employee_name', 'city', 'contract_name']
                            display_cols = [col for col in display_cols if col in unassigned_employees.columns]
                            st.dataframe(
                                unassigned_employees[display_cols].sort_values('employee_name'),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.success("All employees are assigned for this date.")
                    
                    st.markdown("---")  # Separator between dates

    except Exception as e:
        st.error(f"Error displaying supervisors report: {str(e)}")
        logger.error(f"Error in display_supervisors_report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def display_city_report(data, employee_data):
    """Display city-wise report with each city in its own tab, with tables and summary."""
    try:
        if data is None or data.empty:
            st.warning("No data available for city report")
            return

        # Process data for city report
        city_data = DataSanitizer.generate_city_report(data, employee_data)
        if city_data.empty:
            st.warning("No data available for city report after processing")
            return

        # Get unique cities and dates - normalize to ensure "Port Said" appears correctly
        cities = sorted(employee_data['city'].dropna().astype(str).apply(normalize_city_name).unique())
        dates = sorted(city_data['Date'].unique())
        tabs = st.tabs(cities)
        for i, city in enumerate(cities):
            with tabs[i]:
                # Normalize city column for comparison
                employee_data_normalized = employee_data.copy()
                employee_data_normalized['city_normalized'] = employee_data_normalized['city'].astype(str).apply(normalize_city_name)
                city_employees = employee_data_normalized[employee_data_normalized['city_normalized'] == city].copy()
                city_employees = city_employees.drop(columns=['city_normalized'], errors='ignore')
                total = len(city_employees)
                city_shifts = data[data['employee_id'].isin(city_employees['employee_id'])]
                assigned = len(city_shifts.drop_duplicates('employee_id')['employee_id']) if not city_shifts.empty else 0
                unassigned = total - assigned
                assignment_rate = (assigned / total * 100) if total > 0 else 0
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Employees", int(total))
                with col2:
                    st.metric("Total Assigned", int(assigned))
                with col3:
                    st.metric("Total Unassigned", int(unassigned))
                with col4:
                    st.metric("Overall Assignment Rate", f"{assignment_rate:.1f}%")
                for date in dates:
                    date_str = pd.to_datetime(date).strftime('%d-%m')
                    date_data = city_data[city_data['Date'] == date]
                    if date_data.empty:
                        continue
                    city_report = date_data[date_data['City'] == city]
                    if city_report.empty:
                        continue

                    # Add dark blue square headers
                    st.markdown(f"""
                    <div style="
                        background-color: #1e3a8a;
                        color: white;
                        padding: 8px 12px;
                        margin: 10px 0 5px 0;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 14px;
                        display: inline-block;
                        border: 2px solid #1e40af;
                    ">City: {city}</div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                    <div style="
                        background-color: #1e3a8a;
                        color: white;
                        padding: 8px 12px;
                        margin: 5px 0 10px 0;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 14px;
                        display: inline-block;
                        border: 2px solid #1e40af;
                    ">Date: {date_str}</div>
                    """, unsafe_allow_html=True)

                    # Use pandas styling with updated configuration
                    display_df = city_report[['Contract', 'Total', 'Assigned', 'Unassigned', 'Assigned_Percentage']].copy()

                    # Apply styling using pandas styler
                    styler = display_df.style

                    # Format percentage column properly
                    styler = styler.format({'Assigned_Percentage': '{:.2f}%'})

                    # Apply table styling with bigger tables
                    styler = styler.set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', '#007BFF'),  # Blue header
                            ('color', 'white'),
                            ('font-weight', 'bold'),
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px 10px'),  # Increased padding
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '10px'),
                            ('margin', '1px'),
                            ('font-size', '16px')  # Bigger font
                        ]},
                        {'selector': 'td', 'props': [
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '14px 12px'),  # Increased padding
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '10px'),  # Rounded cells
                            ('margin', '1px'),
                            ('font-size', '14px')  # Bigger font
                        ]},
                        {'selector': 'table', 'props': [
                            ('border-collapse', 'separate'),
                            ('border-spacing', '3px'),
                            ('border', 'none !important'),
                            ('border-radius', '15px'),
                            ('overflow', 'hidden'),
                            ('box-shadow', '0 4px 12px rgba(0,0,0,0.1)'),
                            ('width', '100%'),  # Make table wider
                            ('min-width', '600px')  # Minimum width
                        ]},
                        {'selector': 'tr:nth-child(even) td', 'props': [
                            ('background-color', '#b8d4f0'),  # Alternating row colors
                            ('border-radius', '10px')
                        ]},
                        {'selector': 'tr:nth-child(odd) td', 'props': [
                            ('background-color', 'white'),
                            ('border-radius', '10px')
                        ]},
                        {'selector': 'tr:hover td', 'props': [
                            ('background-color', '#e3f2fd'),
                            ('transform', 'scale(1.02)'),
                            ('transition', 'all 0.2s ease'),
                            ('border-radius', '10px')
                        ]}
                    ])

                    # Center align all content using reusable function
                    styler = styler.map(_center_align_style)

                    st.dataframe(styler, use_container_width=True, hide_index=True)

                    # Add donut chart showing Assigned vs Unassigned employees percentage
                    if not city_report.empty:
                        # Calculate total assigned and unassigned for this city and date
                        total_assigned = city_report['Assigned'].sum()
                        total_unassigned = city_report['Unassigned'].sum()
                        total_employees = total_assigned + total_unassigned
                        
                        if total_employees > 0:
                            # Create a donut chart showing Assigned vs Unassigned percentage
                            fig = go.Figure(data=[go.Pie(
                                labels=['Assigned', 'Unassigned'],
                                values=[total_assigned, total_unassigned],
                                hole=0.6,  # This creates the donut effect
                                marker_colors=['#28a745', '#dc3545'],
                                textinfo='label+percent',
                                textposition='outside'
                            )])
                            
                            # Calculate percentage
                            assigned_percentage = (total_assigned / total_employees * 100) if total_employees > 0 else 0
                            
                            # Add title and center text
                            fig.update_layout(
                                title=f'Assignment Status in {city} on {date_str}',
                                annotations=[dict(
                                    text=f'<b>{assigned_percentage:.1f}%<br>Assigned</b>',
                                    x=0.5,
                                    y=0.5,
                                    font=dict(size=20),
                                    showarrow=False
                                )],
                                showlegend=True,
                                legend=dict(
                                    orientation="h",
                                    yanchor="bottom",
                                    y=-0.2,
                                    xanchor="center",
                                    x=0.5
                                ),
                                height=400,
                                margin=dict(t=60, b=60, l=20, r=20)
                            )
                            # Display the chart with unique key
                            st.plotly_chart(fig, use_container_width=True, key=f"city_report_chart_{city}_{date_str}")

                # Add Summary Table for All Dates (side by side)
                st.markdown("### Summary View (All Dates)")

                # Add dark blue headers for City and Date range
                st.markdown(f"""
                <div style="
                    background-color: #1e3a8a;
                    color: white;
                    padding: 8px 12px;
                    margin: 10px 0 5px 0;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 14px;
                    display: inline-block;
                    border: 2px solid #1e40af;
                ">City: {city}</div>
                """, unsafe_allow_html=True)

                # Create date range string
                date_range_str = f"{pd.to_datetime(dates[0]).strftime('%d-%m')} to {pd.to_datetime(dates[-1]).strftime('%d-%m')}" if len(dates) > 1 else pd.to_datetime(dates[0]).strftime('%d-%m')
                st.markdown(f"""
                <div style="
                    background-color: #1e3a8a;
                    color: white;
                    padding: 8px 12px;
                    margin: 5px 0 10px 0;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 14px;
                    display: inline-block;
                    border: 2px solid #1e40af;
                ">Date: {date_range_str}</div>
                """, unsafe_allow_html=True)
                summary_data = []
                contracts = sorted(employee_data[employee_data['city'] == city]['contract_name'].unique())

                for contract in contracts:
                    row = {'Contract': contract}

                    # Get contract employees for this city (normalize for comparison)
                    employee_data_normalized = employee_data.copy()
                    employee_data_normalized['city_normalized'] = employee_data_normalized['city'].astype(str).apply(normalize_city_name)
                    contract_city_employees = employee_data_normalized[
                        (employee_data_normalized['contract_name'] == contract) &
                        (employee_data_normalized['city_normalized'] == city)
                    ].copy()
                    contract_city_employees = contract_city_employees.drop(columns=['city_normalized'], errors='ignore')

                    if len(contract_city_employees) > 0:
                        total_employees = len(contract_city_employees)
                        row['Total'] = total_employees

                        # Add data for each date side by side
                        for date in dates:
                            date_str = pd.to_datetime(date).strftime('%d-%m')
                            date_data = data[data['planned_start_date'] == date]

                            # Calculate assigned for this specific date
                            contract_city_date_shifts = date_data[
                                data['employee_id'].isin(contract_city_employees['employee_id'])
                            ]
                            assigned_for_date = len(contract_city_date_shifts['employee_id'].unique())
                            unassigned_for_date = total_employees - assigned_for_date
                            percentage_for_date = (assigned_for_date / total_employees * 100) if total_employees > 0 else 0

                            row[f'{date_str}_Assigned'] = assigned_for_date
                            row[f'{date_str}_Unassigned'] = unassigned_for_date
                            row[f'{date_str}_Percentage'] = percentage_for_date

                        summary_data.append(row)

                if summary_data:
                    summary_df = pd.DataFrame(summary_data)

                    # Apply styling to summary table
                    summary_styler = summary_df.style

                    # Format percentage columns
                    percentage_cols = [col for col in summary_df.columns if col.endswith('_Percentage')]
                    format_dict = {col: '{:.1f}%' for col in percentage_cols}
                    summary_styler = summary_styler.format(format_dict)

                    # Apply bigger table styling
                    summary_styler = summary_styler.set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', '#007BFF'),
                            ('color', 'white'),
                            ('font-weight', 'bold'),
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px 8px'),  # Bigger padding
                            ('border', 'none !important'),
                            ('border-radius', '10px'),
                            ('margin', '1px'),
                            ('font-size', '14px')  # Bigger font
                        ]},
                        {'selector': 'td', 'props': [
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px 8px'),  # Bigger padding
                            ('border', 'none !important'),
                            ('border-radius', '8px'),
                            ('margin', '1px'),
                            ('font-size', '13px')  # Bigger font
                        ]},
                        {'selector': 'table', 'props': [
                            ('border-collapse', 'separate'),
                            ('border-spacing', '2px'),
                            ('border', 'none !important'),
                            ('border-radius', '10px'),
                            ('overflow', 'hidden'),
                            ('box-shadow', '0 2px 8px rgba(0,0,0,0.1)'),
                            ('width', '100%'),  # Make table wider
                            ('min-width', '800px')  # Minimum width for side-by-side data
                        ]},
                        {'selector': 'tr:nth-child(even) td', 'props': [
                            ('background-color', '#b8d4f0'),
                            ('border-radius', '8px')
                        ]},
                        {'selector': 'tr:nth-child(odd) td', 'props': [
                            ('background-color', 'white'),
                            ('border-radius', '8px')
                        ]},
                        {'selector': 'tr:hover td', 'props': [
                            ('background-color', '#e3f2fd'),
                            ('transform', 'scale(1.01)'),
                            ('transition', 'all 0.2s ease'),
                            ('border-radius', '8px')
                        ]}
                    ])

                    # Center align all content using reusable function
                    summary_styler = summary_styler.map(_center_align_style)

                    st.dataframe(summary_styler, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error in city report display: {str(e)}")
        print(f"Error in city report display: {str(e)}")

def create_donut_chart(assigned, unassigned, title):
    """Create a donut chart for assignment visualization"""
    total = assigned + unassigned
    if total == 0:
        return None

    # Create donut chart
    fig = go.Figure(data=[go.Pie(
        labels=['Assigned', 'Unassigned'],
        values=[assigned, unassigned],
        hole=0.6,
        marker_colors=['#28a745', '#dc3545']
    )])

    # Add title and center text
    fig.update_layout(
        title=title,
        annotations=[dict(text=f'{assigned}<br>Assigned', x=0.5, y=0.5, font_size=16, showarrow=False)],
        showlegend=True,
        height=300,
        margin=dict(t=50, b=0, l=0, r=0)
    )

    return fig

def display_contract_report(shift_df, employee_df):
    """Display contract-wise report with each contract in its own tab, similar to city report"""
    st.header("Contract Report")

    try:
        if shift_df.empty or employee_df.empty:
            st.warning("No data available for contract report")
            return

        # Get unique dates and contracts
        dates = sorted(shift_df['planned_start_date'].unique())
        contracts = sorted(employee_df['contract_name'].unique())

        # Create tabs for each contract
        tabs = st.tabs(contracts)

        for i, contract in enumerate(contracts):
            with tabs[i]:
                # Get contract employees
                contract_employees = employee_df[employee_df['contract_name'] == contract]
                total = len(contract_employees)

                # Calculate overall metrics for the selected date range
                contract_shifts = shift_df[shift_df['employee_id'].isin(contract_employees['employee_id'])]
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
                    date_data = shift_df[shift_df['planned_start_date'] == date]
                    if date_data.empty:
                        continue

                    # Add dark blue square headers
                    st.markdown(f"""
                    <div style="
                        background-color: #1e3a8a;
                        color: white;
                        padding: 8px 12px;
                        margin: 10px 0 5px 0;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 14px;
                        display: inline-block;
                        border: 2px solid #1e40af;
                    ">Contract: {contract}</div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                    <div style="
                        background-color: #1e3a8a;
                        color: white;
                        padding: 8px 12px;
                        margin: 5px 0 10px 0;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 14px;
                        display: inline-block;
                        border: 2px solid #1e40af;
                    ">Date: {date_str}</div>
                    """, unsafe_allow_html=True)

                    # Group by city for this contract and date (normalize for comparison)
                    city_data = []
                    employee_df_normalized = employee_df.copy()
                    employee_df_normalized['city_normalized'] = employee_df_normalized['city'].astype(str).apply(normalize_city_name)
                    for city in employee_df_normalized['city_normalized'].unique():
                        city_employees = employee_df_normalized[
                            (employee_df_normalized['contract_name'] == contract) &
                            (employee_df_normalized['city_normalized'] == city)
                        ].copy()
                        city_employees = city_employees.drop(columns=['city_normalized'], errors='ignore')
                        if len(city_employees) > 0:
                            city_shifts = date_data[date_data['employee_id'].isin(city_employees['employee_id'])]

                            total_city = len(city_employees)
                            assigned_city = len(city_shifts['employee_id'].unique())
                            unassigned_city = total_city - assigned_city
                            percentage = (assigned_city / total_city * 100) if total_city > 0 else 0

                            city_data.append({
                                'City': city,
                                'Total': total_city,
                                'Assigned': assigned_city,
                                'Unassigned': unassigned_city,
                                'Assigned_Percentage': percentage
                            })

                    if city_data:
                        city_df = pd.DataFrame(city_data)
                        city_df = city_df[city_df['Total'] > 0]  # Only show cities with employees

                        if not city_df.empty:
                            # Apply styling using pandas styler
                            styler = city_df.style

                            # Format percentage column properly
                            styler = styler.format({'Assigned_Percentage': '{:.2f}%'})

                            # Apply table styling with bigger tables
                            styler = styler.set_table_styles([
                                {'selector': 'th', 'props': [
                                    ('background-color', '#007BFF'),
                                    ('color', 'white'),
                                    ('font-weight', 'bold'),
                                    ('text-align', 'center'),
                                    ('vertical-align', 'middle'),
                                    ('padding', '12px 10px'),  # Increased padding
                                    ('border', 'none !important'),
                                    ('border-radius', '10px'),
                                    ('margin', '1px'),
                                    ('font-size', '16px')  # Bigger font
                                ]},
                                {'selector': 'td', 'props': [
                                    ('text-align', 'center'),
                                    ('vertical-align', 'middle'),
                                    ('padding', '14px 12px'),  # Increased padding
                                    ('border', 'none !important'),
                                    ('border-radius', '10px'),
                                    ('margin', '1px'),
                                    ('font-size', '14px')  # Bigger font
                                ]},
                                {'selector': 'table', 'props': [
                                    ('border-collapse', 'separate'),
                                    ('border-spacing', '3px'),
                                    ('border', 'none !important'),
                                    ('border-radius', '15px'),
                                    ('overflow', 'hidden'),
                                    ('box-shadow', '0 4px 12px rgba(0,0,0,0.1)'),
                                    ('width', '100%'),  # Make table wider
                                    ('min-width', '600px')  # Minimum width
                                ]},
                                {'selector': 'tr:nth-child(even) td', 'props': [
                                    ('background-color', '#b8d4f0'),
                                    ('border-radius', '10px')
                                ]},
                                {'selector': 'tr:nth-child(odd) td', 'props': [
                                    ('background-color', 'white'),
                                    ('border-radius', '10px')
                                ]},
                                {'selector': 'tr:hover td', 'props': [
                                    ('background-color', '#e3f2fd'),
                                    ('transform', 'scale(1.02)'),
                                    ('transition', 'all 0.2s ease'),
                                    ('border-radius', '10px')
                                ]}
                            ])

                            # Center align all content using reusable function
                            styler = styler.map(_center_align_style)

                            # Create two columns: table and donut chart
                            col1, col2 = st.columns([2, 1])

                            with col1:
                                st.dataframe(styler, use_container_width=True, hide_index=True)

                            with col2:
                                # Create donut chart for this contract
                                total_assigned = city_df['Assigned'].sum()
                                total_unassigned = city_df['Unassigned'].sum()

                                donut_fig = create_donut_chart(
                                    total_assigned,
                                    total_unassigned,
                                    f"{contract}<br>{date_str}"
                                )

                                if donut_fig:
                                    st.plotly_chart(donut_fig, use_container_width=True, key=f"contract_donut_{contract}_{date_str}")

                # Add Summary Table for All Dates (side by side)
                st.markdown("### Summary View (All Dates)")

                # Add dark blue headers for Contract and Date range
                st.markdown(f"""
                <div style="
                    background-color: #1e3a8a;
                    color: white;
                    padding: 8px 12px;
                    margin: 10px 0 5px 0;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 14px;
                    display: inline-block;
                    border: 2px solid #1e40af;
                ">Contract: {contract}</div>
                """, unsafe_allow_html=True)

                # Create date range string
                date_range_str = f"{pd.to_datetime(dates[0]).strftime('%d-%m')} to {pd.to_datetime(dates[-1]).strftime('%d-%m')}" if len(dates) > 1 else pd.to_datetime(dates[0]).strftime('%d-%m')
                st.markdown(f"""
                <div style="
                    background-color: #1e3a8a;
                    color: white;
                    padding: 8px 12px;
                    margin: 5px 0 10px 0;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 14px;
                    display: inline-block;
                    border: 2px solid #1e40af;
                ">Date: {date_range_str}</div>
                """, unsafe_allow_html=True)
                summary_data = []
                cities = sorted(employee_df['city'].dropna().astype(str).apply(normalize_city_name).unique())

                for city in cities:
                    row = {'City': city}

                    # Get contract employees for this city (normalize for comparison)
                    employee_df_normalized = employee_df.copy()
                    employee_df_normalized['city_normalized'] = employee_df_normalized['city'].astype(str).apply(normalize_city_name)
                    contract_city_employees = employee_df_normalized[
                        (employee_df_normalized['contract_name'] == contract) &
                        (employee_df_normalized['city_normalized'] == city)
                    ].copy()
                    contract_city_employees = contract_city_employees.drop(columns=['city_normalized'], errors='ignore')

                    if len(contract_city_employees) > 0:
                        total_employees = len(contract_city_employees)
                        row['Total'] = total_employees

                        # Add data for each date side by side
                        for date in dates:
                            date_str = pd.to_datetime(date).strftime('%d-%m')
                            date_data = shift_df[shift_df['planned_start_date'] == date]

                            # Calculate assigned for this specific date
                            contract_city_date_shifts = date_data[
                                date_data['employee_id'].isin(contract_city_employees['employee_id'])
                            ]
                            assigned_for_date = len(contract_city_date_shifts['employee_id'].unique())
                            unassigned_for_date = total_employees - assigned_for_date
                            percentage_for_date = (assigned_for_date / total_employees * 100) if total_employees > 0 else 0

                            row[f'{date_str}_Assigned'] = assigned_for_date
                            row[f'{date_str}_Unassigned'] = unassigned_for_date
                            row[f'{date_str}_Percentage'] = percentage_for_date

                        summary_data.append(row)

                if summary_data:
                    summary_df = pd.DataFrame(summary_data)

                    # Apply styling to summary table
                    summary_styler = summary_df.style

                    # Format percentage columns
                    percentage_cols = [col for col in summary_df.columns if col.endswith('_Percentage')]
                    format_dict = {col: '{:.1f}%' for col in percentage_cols}
                    summary_styler = summary_styler.format(format_dict)

                    # Apply bigger table styling
                    summary_styler = summary_styler.set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', '#007BFF'),
                            ('color', 'white'),
                            ('font-weight', 'bold'),
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px 8px'),  # Bigger padding
                            ('border', 'none !important'),
                            ('border-radius', '10px'),
                            ('margin', '1px'),
                            ('font-size', '14px')  # Bigger font
                        ]},
                        {'selector': 'td', 'props': [
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px 8px'),  # Bigger padding
                            ('border', 'none !important'),
                            ('border-radius', '8px'),
                            ('margin', '1px'),
                            ('font-size', '13px')  # Bigger font
                        ]},
                        {'selector': 'table', 'props': [
                            ('border-collapse', 'separate'),
                            ('border-spacing', '2px'),
                            ('border', 'none !important'),
                            ('border-radius', '10px'),
                            ('overflow', 'hidden'),
                            ('box-shadow', '0 2px 8px rgba(0,0,0,0.1)'),
                            ('width', '100%'),  # Make table wider
                            ('min-width', '800px')  # Minimum width for side-by-side data
                        ]},
                        {'selector': 'tr:nth-child(even) td', 'props': [
                            ('background-color', '#b8d4f0'),
                            ('border-radius', '8px')
                        ]},
                        {'selector': 'tr:nth-child(odd) td', 'props': [
                            ('background-color', 'white'),
                            ('border-radius', '8px')
                        ]},
                        {'selector': 'tr:hover td', 'props': [
                            ('background-color', '#e3f2fd'),
                            ('transform', 'scale(1.01)'),
                            ('transition', 'all 0.2s ease'),
                            ('border-radius', '8px')
                        ]}
                    ])

                    # Center align all content using reusable function
                    summary_styler = summary_styler.map(_center_align_style)

                    st.dataframe(summary_styler, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error in contract report display: {str(e)}")
        print(f"Error in contract report display: {str(e)}")

def main():
    # Apply custom table styling for enhanced visual appearance
    apply_custom_table_styling()

    workflow = st.sidebar.selectbox(
        "Select Workflow",
        ["Shifts Update"]
    )

    if workflow == "Shifts Update":
        # --- Shifts Update workflow (untouched) ---
        st.markdown(
            '<h1 style="text-align: center; margin: 20px 0;">Shift Management Dashboard</h1>',
            unsafe_allow_html=True
        )
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
            2. The sheet contains data in the 'all' tab
            3. The sheet ID is correct in .streamlit/secrets.toml
            4. You have enabled the Google Sheets API in your Google Cloud Console
            """)
            return
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Employee Data (auto-loaded from Google Sheets)")
            if st.button("Refresh Employee Data"):
                st.session_state['employee_refresh'] = True

            employee_df = None
            if 'employee_df' not in st.session_state or st.session_state.get('employee_refresh', False):
                with st.spinner("Loading employee data from Google Sheets..."):
                    try:
                        employee_df = st.session_state.sheets_connector.read_sheet(
                            spreadsheet_id=SPREADSHEET_ID,
                            range_name='all!A1:Z'
                        )
                        if employee_df is not None and not employee_df.empty:
                            employee_df.columns = [str(col).strip().lower().replace(' ', '_') for col in employee_df.columns]
                            st.session_state['employee_df'] = employee_df
                            st.session_state['employee_refresh'] = False
                            st.success(f"Successfully loaded {len(employee_df)} employee records from Google Sheets.")
                            try:
                                # Optimize: Only show essential columns and limit display for large datasets
                                essential_cols = ['employee_id', 'employee_name', 'contract_name', 'city', 'supervisors']
                                display_cols = [col for col in essential_cols if col in employee_df.columns]
                                
                                if len(employee_df) > 500:
                                    st.info(f"Large dataset ({len(employee_df)} records). Showing first 500 rows. Use filters to narrow down.")
                                    display_df = employee_df[display_cols].head(500).copy()
                                else:
                                    display_df = employee_df[display_cols].copy()
                                
                                # Only convert to string for display, not all columns
                                for col in display_df.columns:
                                    if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                                        display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                                    else:
                                        display_df[col] = display_df[col].fillna('').astype(str).str.strip()
                                
                                st.success(f"Displaying {len(display_df)} employee records.")
                                st.dataframe(display_df, use_container_width=True, hide_index=True)
                            except Exception as e:
                                st.error(f"Error displaying employee data: {str(e)}")
                                st.write("Data preview (simplified):")
                                st.write(display_df.head().to_dict())
                        else:
                            st.error("No data was returned from Google Sheets. Please check:")
                            st.markdown("""
                            1. The sheet is shared with: `sheet-accessa@shift-automation-458000.iam.gserviceaccount.com`
                            2. The sheet contains data in the 'all' tab
                            3. The sheet ID is correct
                            """)
                    except Exception as e:
                        st.error(f"Error loading employee data: {str(e)}")
            else:
                employee_df = st.session_state.get('employee_df', None)
                if employee_df is not None and not employee_df.empty:
                    try:
                        # Optimize: Only show essential columns and limit display for large datasets
                        essential_cols = ['employee_id', 'employee_name', 'contract_name', 'city', 'supervisors']
                        display_cols = [col for col in essential_cols if col in employee_df.columns]
                        
                        if len(employee_df) > 500:
                            st.info(f"Large dataset ({len(employee_df)} records). Showing first 500 rows. Use filters to narrow down.")
                            display_df = employee_df[display_cols].head(500).copy()
                        else:
                            display_df = employee_df[display_cols].copy()
                        
                        # Only convert to string for display, not all columns
                        for col in display_df.columns:
                            if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                display_df[col] = display_df[col].fillna('').astype(str).str.strip()
                        
                        st.success(f"Displaying {len(display_df)} employee records.")
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error(f"Error displaying employee data: {str(e)}")
                        st.write("Data preview (simplified):")
                        st.write(display_df.head().to_dict())
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
            with st.spinner("Processing city files..."):
                merged_shifts = DataSanitizer.merge_shift_files(city_files)
                if merged_shifts is None or merged_shifts.empty:
                    st.error("No valid data found in city files")
                    return
                merged_shifts.columns = merged_shifts.columns.str.strip().str.lower().str.replace(' ', '_')
                validate_data(merged_shifts, 'shift_file')
                st.success(f"✅ Successfully processed {len(city_files)} city files")

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
                "Unassigned Employees",
                "Contract Report",
                "City Report",
                "Supervisors"
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
                # Optimize: Process dates more efficiently
                if len(date_range) > 7:
                    st.info(f"Showing data for {len(date_range)} dates. This may take a moment...")
                
                for date in date_range:
                    date_key = date.date() if hasattr(date, 'date') else date
                    date_shifts = filtered_shifts.get(date_key, pd.DataFrame())
                    display_unassigned_employees(employee_df, date_shifts, date_key)

            with tab3:
                display_contract_report(filtered_shifts_df, employee_df)

            with tab4:
                display_city_report(filtered_shifts_df, employee_df)

            with tab5:
                display_supervisors_report(employee_df, filtered_shifts_df, date_range)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()





