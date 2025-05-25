import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from data_sanitizer import DataSanitizer, validate_data
from check_inactive import InactiveRidersChecker
from evaluated import EvaluatedProcessor

st.set_page_config(page_title="Shift Management Dashboard", layout="wide")

# Basic CSS for styling
st.markdown("""
<style>
    .table-header {
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

st.title("📊 Shift Management Dashboard")

def create_table_header(title, subtitle=None):
    """Create a professional table header"""
    if subtitle:
        header_html = f"""
        <div class="table-header">
            <strong>{title}: {subtitle}</strong>
        </div>
        """
    else:
        header_html = f"""
        <div class="table-header">
            <strong>{title}</strong>
        </div>
        """
    st.markdown(header_html, unsafe_allow_html=True)

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
    """Display contract-wise report with donut charts"""
    st.header("Contract Report")

    try:
        if shift_df.empty or employee_df.empty:
            st.warning("No data available for contract report")
            return

        # Get unique dates and contracts
        dates = sorted(shift_df['planned_start_date'].unique())

        # Process data for each contract
        contract_data = []
        for date in dates:
            date_data = shift_df[shift_df['planned_start_date'] == date]

            # Group by contract
            for contract in employee_df['contract_name'].unique():
                contract_employees = employee_df[employee_df['contract_name'] == contract]
                contract_shifts = date_data[date_data['employee_id'].isin(contract_employees['employee_id'])]

                total_employees = len(contract_employees)
                assigned = len(contract_shifts['employee_id'].unique())
                unassigned = total_employees - assigned
                percentage = (assigned / total_employees * 100) if total_employees > 0 else 0

                contract_data.append({
                    'Date': date,
                    'Contract': contract,
                    'Total': total_employees,
                    'Assigned': assigned,
                    'Unassigned': unassigned,
                    'Assigned_Percentage': percentage
                })

        if not contract_data:
            st.warning("No contract data to display")
            return

        data_df = pd.DataFrame(contract_data)

        # Display per-date tables for each contract
        for contract in data_df['Contract'].unique():
            contract_data_filtered = data_df[data_df['Contract'] == contract]

            if not contract_data_filtered.empty:
                for date in dates:
                    date_str = pd.to_datetime(date).strftime('%d-%m')
                    mini_report = contract_data_filtered[contract_data_filtered['Date'] == date]

                    if not mini_report.empty:
                        # Add professional table header for contract identification
                        create_table_header("Contract", contract)
                        st.markdown(f"**Date: {date_str}**")

                        # Group by city for this contract and date
                        city_data = []
                        for city in employee_df['city'].unique():
                            city_employees = employee_df[
                                (employee_df['contract_name'] == contract) &
                                (employee_df['city'] == city)
                            ]
                            if len(city_employees) > 0:
                                date_data = shift_df[shift_df['planned_start_date'] == date]
                                city_shifts = date_data[date_data['employee_id'].isin(city_employees['employee_id'])]

                                total = len(city_employees)
                                assigned = len(city_shifts['employee_id'].unique())
                                unassigned = total - assigned
                                percentage = (assigned / total * 100) if total > 0 else 0

                                city_data.append({
                                    'City': city,
                                    'Total': total,
                                    'Assigned': assigned,
                                    'Unassigned': unassigned,
                                    'Assigned_Percentage': percentage
                                })

                        if city_data:
                            city_df = pd.DataFrame(city_data)
                            city_df = city_df[city_df['Total'] > 0]  # Only show cities with employees

                            if not city_df.empty:
                                # Create two columns: table and donut chart
                                col1, col2 = st.columns([2, 1])

                                with col1:
                                    # Display table with basic styling
                                    st.dataframe(city_df, use_container_width=True, hide_index=True)

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
                                        st.plotly_chart(donut_fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error in contract report display: {str(e)}")
        print(f"Error in contract report display: {str(e)}")

def main():
    """Main application function"""

    # Sidebar for workflow selection
    st.sidebar.title("Shift Management Dashboard")

    workflow = st.sidebar.selectbox(
        "Select Workflow",
        ["Shifts Update", "Check Inactive Riders", "Evaluated"]
    )

    if workflow == "Shifts Update":
        # --- Shifts Update workflow ---

        # File upload section
        st.sidebar.header("📁 Upload Files")

        employee_file = st.sidebar.file_uploader(
            "Upload Employee File",
            type=['csv', 'xlsx'],
            help="Upload the employee data file containing employee information"
        )

        shift_file = st.sidebar.file_uploader(
            "Upload Shift File",
            type=['csv', 'xlsx'],
            help="Upload the shift data file containing shift assignments"
        )

        if employee_file and shift_file:
            try:
                # Load and process data
                sanitizer = DataSanitizer()

                # Process employee data
                employee_df = sanitizer.load_and_sanitize_employee_data(employee_file)
                if not validate_data(employee_df, 'employee_file'):
                    return

                # Process shift data
                shift_df = sanitizer.load_and_sanitize_shift_data(shift_file)
                if not validate_data(shift_df, 'shift_file'):
                    return

                # Create tabs for different views
                tab1, tab2 = st.tabs(["📋 Contract Report", "🏙️ City Report"])

                with tab1:
                    display_contract_report(shift_df, employee_df)

                with tab2:
                    st.header("City Report")
                    st.info("City report functionality will be implemented here")

            except Exception as e:
                st.error(f"Error processing files: {str(e)}")
                print(f"Error processing files: {str(e)}")
        else:
            st.info("Please upload both employee and shift files to begin analysis.")

    elif workflow == "Check Inactive Riders":
        # --- Check Inactive Riders workflow ---
        try:
            checker = InactiveRidersChecker()
            checker.run()
        except Exception as e:
            st.error(f"Error in Check Inactive Riders workflow: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")

    elif workflow == "Evaluated":
        # --- Evaluated workflow ---
        try:
            processor = EvaluatedProcessor()
            processor.run()
        except Exception as e:
            st.error(f"Error in Evaluated workflow: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")

if __name__ == "__main__":
    main()



# End of file

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
        st.dataframe(style_dataframe(display_df, ['Assigned_Percentage']), use_container_width=True, hide_index=True)

def display_unassigned_employees(employees_df: pd.DataFrame, shifts_df: pd.DataFrame, selected_date: str):
    """Display employees who have no shifts assigned for the selected date."""
    if employees_df is None or shifts_df is None or employees_df.empty or shifts_df.empty:
        st.warning("No data available to display unassigned employees.")
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
            st.dataframe(display_df[display_columns], use_container_width=True, hide_index=True)
        else:
            st.success(f"All employees are assigned shifts for {selected_date}")

    except Exception as e:
        st.error(f"Error displaying unassigned employees: {str(e)}")
        logger.error(f"Error in display_unassigned_employees: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def display_contract_report(data, employee_data):
    """Display contract-wise report with enhanced validation and styling."""
    # Apply styling again to ensure it's active for this display
    apply_custom_table_styling()

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

                    # Add professional table header for contract identification
                    create_table_header("Contract", contract)
                    st.markdown(f"**Date: {date_str}**")

                    # Use pandas styling with updated configuration
                    display_df = mini_report[['City', 'Total', 'Assigned', 'Unassigned', 'Assigned_Percentage']].copy()

                    # Apply styling using pandas styler
                    styler = display_df.style

                    # Format percentage column (no color coding)
                    styler = styler.format({'Assigned_Percentage': '{:.1f}%'})

                    # Apply table styling with blue headers, COMPLETELY no borders, rounded cells
                    styler = styler.set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', '#007BFF'),  # Blue header
                            ('color', 'white'),
                            ('font-weight', 'bold'),
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Rounded headers
                            ('margin', '2px')
                        ]},
                        {'selector': 'td', 'props': [
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '10px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Oval/rounded cells
                            ('margin', '2px')
                        ]},
                        {'selector': 'tr:nth-child(even)', 'props': [
                            ('background-color', '#b8d4f0'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr:nth-child(odd)', 'props': [
                            ('background-color', '#ffffff'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'table', 'props': [
                            ('border', 'none !important'),  # No table border
                            ('border-collapse', 'separate'),
                            ('border-spacing', '4px'),
                            ('outline', 'none !important'),
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important')
                        ]},
                        {'selector': 'thead', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tbody', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': '*', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]}
                    ])

                    st.dataframe(styler, use_container_width=True, hide_index=True)

                # Summary table (side-by-side, like City Report)
                st.markdown("### Summary View (All Dates)")
                summary_data = []
                cities = sorted(contract_employees['city'].unique())

                for city in cities:
                    row = {'City': city}

                    # Get the actual total number of employees for this city (not sum of assignments)
                    city_employees = contract_employees[contract_employees['city'] == city]
                    actual_total_employees = len(city_employees)

                    for date in dates:
                        date_str = pd.to_datetime(date).strftime('%d-%m')
                        date_data = data[data['planned_start_date'] == date]
                        if date_data.empty:
                            row[f'{date_str}_Assigned'] = 0
                            row[f'{date_str}_Unassigned'] = 0
                            row[f'{date_str}_Percentage'] = 0.0
                            continue

                        date_data = date_data[date_data['employee_id'].isin(city_employees['employee_id'])]

                        total_employees = len(city_employees)
                        assigned = len(date_data.drop_duplicates('employee_id'))
                        unassigned = total_employees - assigned
                        percentage = (assigned / total_employees * 100) if total_employees > 0 else 0.0

                        row[f'{date_str}_Assigned'] = assigned
                        row[f'{date_str}_Unassigned'] = unassigned
                        row[f'{date_str}_Percentage'] = percentage

                    # Add Total column showing actual employee count (same as per-date tables)
                    row['Total'] = actual_total_employees
                    summary_data.append(row)

                if summary_data:
                    summary_df = pd.DataFrame(summary_data)

                    # Reorder columns to put Total after City
                    cols = list(summary_df.columns)
                    if 'Total' in cols:
                        cols.remove('Total')
                        cols.insert(1, 'Total')  # Insert Total as second column
                        summary_df = summary_df[cols]

                    percentage_cols = [col for col in summary_df.columns if col.endswith('_Percentage')]

                    # Apply styling using pandas styler
                    styler = summary_df.style

                    # Format percentage columns (no color coding)
                    format_dict = {col: '{:.1f}%' for col in percentage_cols}
                    styler = styler.format(format_dict)

                    # Apply table styling with blue headers, COMPLETELY no borders, rounded cells
                    styler = styler.set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', '#007BFF'),  # Blue header
                            ('color', 'white'),
                            ('font-weight', 'bold'),
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Rounded headers
                            ('margin', '2px')
                        ]},
                        {'selector': 'td', 'props': [
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '10px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Oval/rounded cells
                            ('margin', '2px')
                        ]},
                        {'selector': 'tr:nth-child(even)', 'props': [
                            ('background-color', '#b8d4f0'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr:nth-child(odd)', 'props': [
                            ('background-color', '#ffffff'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'table', 'props': [
                            ('border', 'none !important'),  # No table border
                            ('border-collapse', 'separate'),
                            ('border-spacing', '4px'),
                            ('outline', 'none !important'),
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important')
                        ]},
                        {'selector': 'thead', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tbody', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': '*', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]}
                    ])

                    st.dataframe(styler, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error in contract report display: {str(e)}")
        print(f"Error in contract report display: {str(e)}")

def display_city_report(data, employee_data):
    """Display city-wise report with each city in its own tab, with tables and summary."""
    # Apply styling again to ensure it's active for this display
    apply_custom_table_styling()

    try:
        if data is None or data.empty:
            st.warning("No data available for city report")
            return

        # Process data for city report
        city_data = DataSanitizer.generate_city_report(data, employee_data)
        if city_data.empty:
            st.warning("No data available for city report after processing")
            return

        # Get unique cities and dates
        cities = sorted(employee_data['city'].unique())
        dates = sorted(city_data['Date'].unique())
        tabs = st.tabs(cities)
        for i, city in enumerate(cities):
            with tabs[i]:
                city_employees = employee_data[employee_data['city'] == city]
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

                    # Add professional table header for city identification
                    create_table_header("City", city)
                    st.markdown(f"**Date: {date_str}**")

                    # Use pandas styling with updated configuration
                    display_df = city_report[['Contract', 'Total', 'Assigned', 'Unassigned', 'Assigned_Percentage']].copy()

                    # Apply styling using pandas styler
                    styler = display_df.style

                    # Format percentage column (no color coding)
                    styler = styler.format({'Assigned_Percentage': '{:.1f}%'})

                    # Apply table styling with blue headers, COMPLETELY no borders, rounded cells
                    styler = styler.set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', '#007BFF'),  # Blue header
                            ('color', 'white'),
                            ('font-weight', 'bold'),
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Rounded headers
                            ('margin', '2px')
                        ]},
                        {'selector': 'td', 'props': [
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '10px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Oval/rounded cells
                            ('margin', '2px')
                        ]},
                        {'selector': 'tr:nth-child(even)', 'props': [
                            ('background-color', '#b8d4f0'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr:nth-child(odd)', 'props': [
                            ('background-color', '#ffffff'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'table', 'props': [
                            ('border', 'none !important'),  # No table border
                            ('border-collapse', 'separate'),
                            ('border-spacing', '4px'),
                            ('outline', 'none !important'),
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important')
                        ]},
                        {'selector': 'thead', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tbody', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': '*', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]}
                    ])

                    st.dataframe(styler, use_container_width=True, hide_index=True)

                    # Add donut chart for contract distribution
                    if not city_report.empty:
                        # Create a donut chart showing contract distribution for this city and date
                        fig = px.pie(
                            city_report,
                            values='Assigned',  # Changed from 'Total' to 'Assigned'
                            names='Contract',
                            title=f'Contract Distribution in {city} on {date_str}',
                            hole=0.4,  # This creates the donut effect
                            color_discrete_sequence=px.colors.qualitative.Bold  # Use a distinct color palette
                        )
                        # Update layout for better appearance
                        fig.update_layout(
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.3,
                                xanchor="center",
                                x=0.5
                            ),
                            margin=dict(t=60, b=60, l=20, r=20)
                        )
                        # Display the chart
                        st.plotly_chart(fig, use_container_width=True)
                st.markdown("### Summary View (All Dates)")
                summary_data = []
                contracts = sorted(city_report['Contract'].unique()) if not city_report.empty else []
                for contract in contracts:
                    row = {'Contract': contract}

                    # Get the actual total number of employees for this contract in this city (not sum of assignments)
                    actual_total_employees = 0

                    for date in dates:
                        date_str = pd.to_datetime(date).strftime('%d-%m')
                        date_contract_data = city_data[
                            (city_data['Date'] == date) &
                            (city_data['City'] == city) &
                            (city_data['Contract'] == contract)
                        ]
                        if not date_contract_data.empty:
                            assigned = date_contract_data['Assigned'].iloc[0]
                            unassigned = date_contract_data['Unassigned'].iloc[0]
                            total_for_this_date = assigned + unassigned  # This is the actual employee count

                            row[f'{date_str}_Assigned'] = assigned
                            row[f'{date_str}_Unassigned'] = unassigned
                            row[f'{date_str}_Percentage'] = date_contract_data['Assigned_Percentage'].iloc[0]

                            # Use the total from any date (should be consistent across dates)
                            if actual_total_employees == 0:
                                actual_total_employees = total_for_this_date
                        else:
                            row[f'{date_str}_Assigned'] = 0
                            row[f'{date_str}_Unassigned'] = 0
                            row[f'{date_str}_Percentage'] = 0.0

                    # Add Total column showing actual employee count (same as per-date tables)
                    row['Total'] = actual_total_employees
                    summary_data.append(row)
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)

                    # Reorder columns to put Total after Contract
                    cols = list(summary_df.columns)
                    if 'Total' in cols:
                        cols.remove('Total')
                        cols.insert(1, 'Total')  # Insert Total as second column
                        summary_df = summary_df[cols]

                    percentage_cols = [col for col in summary_df.columns if col.endswith('_Percentage')]

                    # Apply styling using pandas styler
                    styler = summary_df.style

                    # Format percentage columns (no color coding)
                    format_dict = {col: '{:.1f}%' for col in percentage_cols}
                    styler = styler.format(format_dict)

                    # Apply table styling with blue headers, COMPLETELY no borders, rounded cells
                    styler = styler.set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', '#007BFF'),  # Blue header
                            ('color', 'white'),
                            ('font-weight', 'bold'),
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '12px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Rounded headers
                            ('margin', '2px')
                        ]},
                        {'selector': 'td', 'props': [
                            ('text-align', 'center'),
                            ('vertical-align', 'middle'),
                            ('padding', '10px'),
                            ('border', 'none !important'),  # No borders
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important'),
                            ('outline', 'none !important'),
                            ('border-radius', '15px'),  # Oval/rounded cells
                            ('margin', '2px')
                        ]},
                        {'selector': 'tr:nth-child(even)', 'props': [
                            ('background-color', '#b8d4f0'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr:nth-child(odd)', 'props': [
                            ('background-color', '#ffffff'),
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'table', 'props': [
                            ('border', 'none !important'),  # No table border
                            ('border-collapse', 'separate'),
                            ('border-spacing', '4px'),
                            ('outline', 'none !important'),
                            ('border-top', 'none !important'),
                            ('border-bottom', 'none !important'),
                            ('border-left', 'none !important'),
                            ('border-right', 'none !important')
                        ]},
                        {'selector': 'thead', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tbody', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': 'tr', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]},
                        {'selector': '*', 'props': [
                            ('border', 'none !important'),
                            ('outline', 'none !important')
                        ]}
                    ])

                    st.dataframe(styler, use_container_width=True, hide_index=True)

                    # Add a summary donut chart for contract distribution in this city
                    # Create a summary dataframe for the chart
                    chart_data = []
                    for contract in contracts:
                        # Extract assigned values from the summary dataframe
                        contract_row = summary_df[summary_df['Contract'] == contract]
                        if not contract_row.empty:
                            # Calculate the average assigned value across all dates
                            assigned_cols = [col for col in contract_row.columns if col.endswith('_Assigned')]
                            if assigned_cols:
                                assigned_values = [contract_row[col].iloc[0] for col in assigned_cols]
                                avg_assigned = sum(assigned_values) / len(assigned_values)

                                chart_data.append({
                                    'Contract': contract,
                                    'Assigned': avg_assigned
                                })

                    if chart_data:
                        chart_df = pd.DataFrame(chart_data)
                        # Create a donut chart showing overall contract distribution for this city
                        fig = px.pie(
                            chart_df,
                            values='Assigned',  # Changed from 'Total' to 'Assigned'
                            names='Contract',
                            title=f'Overall Contract Distribution in {city}',
                            hole=0.4,  # This creates the donut effect
                            color_discrete_sequence=px.colors.qualitative.Pastel  # Use a different color palette for summary
                        )
                        # Update layout for better appearance
                        fig.update_layout(
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.3,
                                xanchor="center",
                                x=0.5
                            ),
                            margin=dict(t=60, b=60, l=20, r=20)
                        )
                        # Display the chart
                        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error in city report display: {str(e)}")
        print(f"Error in city report display: {str(e)}")

def main():
    # Apply custom table styling for enhanced visual appearance
    apply_custom_table_styling()

    workflow = st.sidebar.selectbox(
        "Select Workflow",
        ["Shifts Update", "Check Inactive Riders", "Evaluated"]
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
            2. The sheet contains data in the 'all2' tab
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
                            range_name='all2!A1:Z'
                        )
                        if employee_df is not None and not employee_df.empty:
                            employee_df.columns = [str(col).strip().lower().replace(' ', '_') for col in employee_df.columns]
                            st.session_state['employee_df'] = employee_df
                            st.session_state['employee_refresh'] = False
                            st.success(f"Successfully loaded {len(employee_df)} employee records from Google Sheets.")
                            try:
                                display_df = employee_df.copy()
                                for col in display_df.columns:
                                    if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                                        display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                                    elif pd.api.types.is_numeric_dtype(display_df[col]):
                                        display_df[col] = display_df[col].fillna('').astype(str)
                                    else:
                                        display_df[col] = display_df[col].fillna('').astype(str).str.strip()
                                display_df = display_df.astype(str)
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
                            2. The sheet contains data in the 'all2' tab
                            3. The sheet ID is correct
                            """)
                    except Exception as e:
                        st.error(f"Error loading employee data: {str(e)}")
            else:
                employee_df = st.session_state.get('employee_df', None)
                if employee_df is not None and not employee_df.empty:
                    try:
                        display_df = employee_df.copy()
                        for col in display_df.columns:
                            if pd.api.types.is_datetime64_any_dtype(display_df[col]):
                                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                            elif pd.api.types.is_numeric_dtype(display_df[col]):
                                display_df[col] = display_df[col].fillna('').astype(str)
                            else:
                                display_df[col] = display_df[col].fillna('').astype(str).str.strip()
                        display_df = display_df.astype(str)
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

    elif workflow == "Check Inactive Riders":
        # --- Check Inactive Riders workflow ---
        st.markdown('<h1 style="text-align: center; margin: 20px 0;">Check Inactive Riders</h1>', unsafe_allow_html=True)

        # Use the same sheets_connector from the session state that Shifts Update uses
        try:
            if 'sheets_connector' not in st.session_state:
                sheets_connector = SheetsConnector()
                st.session_state['sheets_connector'] = sheets_connector

            # Create inactive checker with the session's sheets connector
            inactive_checker = InactiveRidersChecker()
            inactive_checker.sheets_connector = st.session_state['sheets_connector']

            # Use the same spreadsheet ID from secrets.toml
            inactive_checker.spreadsheet_id = st.secrets["spreadsheet_id"]

            # Date range selection
            st.markdown("### Select Date Range")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
            with col2:
                end_date = st.date_input("End Date", value=datetime.now())

            if start_date > end_date:
                st.error("Error: Start date must be before end date")
            else:
                # Create tabs for different data sources
                sheets_tab, csv_tab = st.tabs(["Google Sheets Data", "CSV Upload"])

                with sheets_tab:
                    # Add a button to process Google Sheets data
                    if st.button("Check Inactive Riders from Sheets", key="check_inactive_sheets_btn"):
                        with st.spinner("Processing data from Google Sheets..."):
                            try:
                                results_df = inactive_checker.check_inactive_riders(
                                    start_date.strftime("%Y-%m-%d"),
                                    end_date.strftime("%Y-%m-%d")
                                )

                                if results_df is not None and not results_df.empty:
                                    # Display results without the status messages
                                    # Pass the source parameter to use a unique key for the sheets workflow
                                    inactive_checker.display_results(results_df, show_messages=False, source="sheets")
                                else:
                                    st.info("No inactive riders found for the selected date range")
                            except Exception as e:
                                st.error(f"Error checking inactive riders: {str(e)}")

                with csv_tab:
                    # Option for CSV upload
                    st.markdown("### Upload City CSV Files")
                    st.markdown("""
                    Please upload CSV files for each city:
                    - Assiut
                    - Beni Suef
                    - Hurghada
                    - Ismailia
                    - Minya
                    - Port Said
                    - Suez
                    """)

                    # Move the file uploader inside the CSV tab
                    uploaded_files = st.file_uploader(
                        "Upload CSV files",
                        type=['csv'],
                        accept_multiple_files=True,
                        key="inactive_riders_files"
                    )

                    if uploaded_files and st.button("Process Files", key="process_inactive_files"):
                        with st.spinner("Processing uploaded files..."):
                            try:
                                # Convert date range to list of dates
                                date_list = pd.date_range(start=start_date, end=end_date).date

                                # Process the uploaded files
                                combined_df = inactive_checker.process_uploaded_files(uploaded_files, date_list)

                                if combined_df is not None and not combined_df.empty:
                                    # Process the data to find inactive riders
                                    results_df = inactive_checker.process_inactive_riders(combined_df)

                                    if results_df is not None and not results_df.empty:
                                        # Display results without the status messages
                                        # Pass a unique key for the CSV upload workflow
                                        inactive_checker.display_results(results_df, show_messages=False, source="csv")
                                    else:
                                        st.info("No inactive riders found for the selected date range")
                                else:
                                    st.error("No valid data found in the uploaded files")
                            except Exception as e:
                                st.error(f"Error processing files: {str(e)}")
        except Exception as e:
            st.error(f"Error initializing Google Sheets connection: {str(e)}")
            st.markdown("""
            Please check:
            1. The sheet is shared with: `sheet-accessa@shift-automation-458000.iam.gserviceaccount.com`
            2. The sheet contains data in the 'all2' tab
            3. The sheet ID is correct in .streamlit/secrets.toml
            4. You have enabled the Google Sheets API in your Google Cloud Console
            """)

    elif workflow == "Evaluated":
        # --- Evaluated workflow ---
        st.markdown('<h1 style="text-align: center; margin: 20px 0;">Evaluated</h1>', unsafe_allow_html=True)

        # Use the same sheets_connector from the session state
        try:
            if 'sheets_connector' not in st.session_state:
                sheets_connector = SheetsConnector()
                st.session_state['sheets_connector'] = sheets_connector

            # Create evaluated processor with the session's sheets connector
            evaluated_processor = EvaluatedProcessor()
            evaluated_processor.sheets_connector = st.session_state['sheets_connector']

            # Use the same spreadsheet ID from secrets.toml
            evaluated_processor.spreadsheet_id = st.secrets["spreadsheet_id"]

            # Get employee data from Google Sheets
            with st.spinner("Fetching employee data from Google Sheets..."):
                employee_data = evaluated_processor.get_all_employees()
                if employee_data is None:
                    st.error("Failed to fetch employee data from Google Sheets")

            # File upload section
            st.markdown("### Upload City Files")
            st.markdown("""
            Please upload Excel or CSV files for each city:
            - Assiut
            - Beni Suef
            - Hurghada
            - Ismailia
            - Minya
            - Port Said
            - Suez
            """)

            uploaded_files = st.file_uploader(
                "Upload files",
                type=['xlsx', 'xls', 'csv'],
                accept_multiple_files=True,
                key="evaluated_files"
            )

            if uploaded_files:
                with st.spinner("Processing uploaded files..."):
                    # Process the uploaded files
                    combined_df = evaluated_processor.process_uploaded_files(uploaded_files)

                    if combined_df is not None and not combined_df.empty:
                        st.success(f"Successfully processed {len(uploaded_files)} files with {len(combined_df)} records")

                        # Add contract name and city columns
                        processed_df = evaluated_processor.add_contract_and_city(combined_df, employee_data)

                        if processed_df is not None and not processed_df.empty:
                            # Date selection
                            st.markdown("### Select Dates to Evaluate")

                            # Get unique dates from the data - only use planned dates for simplicity
                            planned_dates = []

                            # Ensure date columns are datetime type
                            if 'planned_start_date' in processed_df.columns:
                                if not pd.api.types.is_datetime64_any_dtype(processed_df['planned_start_date']):
                                    processed_df['planned_start_date'] = pd.to_datetime(processed_df['planned_start_date'], errors='coerce')
                                # Get unique dates
                                planned_dates = sorted(processed_df['planned_start_date'].dropna().dt.date.unique())

                            # Simplified date selection - just use planned dates
                            if planned_dates:
                                selected_planned_dates = st.multiselect(
                                    "Select planned dates to evaluate",
                                    options=planned_dates,
                                    default=planned_dates[:1] if planned_dates else None
                                )
                            else:
                                st.warning("No planned dates found in the data")
                                selected_planned_dates = []

                            # Set actual_dates to empty list since we're only using planned dates
                            selected_actual_dates = []

                            # Filter data by selected dates
                            if selected_planned_dates or selected_actual_dates:
                                filtered_df = evaluated_processor.filter_by_dates(
                                    processed_df,
                                    selected_planned_dates,
                                    selected_actual_dates
                                )

                                if filtered_df is not None and not filtered_df.empty:
                                    # Remove duplicates
                                    unique_df = evaluated_processor.remove_duplicates(filtered_df)

                                    if unique_df is not None and not unique_df.empty:
                                        # Use only planned dates
                                        all_selected_dates = sorted(selected_planned_dates)

                                        if all_selected_dates:
                                            for date in all_selected_dates:
                                                st.markdown(f"## Evaluation Report for {date.strftime('%Y-%m-%d')}")

                                                # Get all data for this date
                                                date_df = evaluated_processor.get_data_for_date(unique_df, date)

                                                if date_df is not None and not date_df.empty:
                                                    # Get unique shift statuses
                                                    shift_statuses = date_df['shift_status'].dropna().unique()

                                                    # Create tabs for different shift statuses
                                                    status_tabs = []

                                                    # Always include "ALL" tab
                                                    status_tabs.append("ALL")

                                                    # Add a combined "NO-SHOW" tab instead of individual NO-SHOW statuses
                                                    status_tabs.append("NO-SHOW")

                                                    # Add other statuses (excluding NO-SHOW related ones)
                                                    for status in shift_statuses:
                                                        if 'NO' not in str(status).upper() or 'SHOW' not in str(status).upper():
                                                            if status not in status_tabs:
                                                                status_tabs.append(status)

                                                    # Create tabs
                                                    status_result_tabs = st.tabs(status_tabs)

                                                    # ALL tab - show all data
                                                    with status_result_tabs[0]:
                                                        pivot_df = evaluated_processor.generate_pivot_summary(date_df, date)
                                                        if pivot_df is not None and not pivot_df.empty:
                                                            st.markdown("#### Total Employees by Contract and City")
                                                            evaluated_processor.display_results(
                                                                pivot_df,
                                                                date,
                                                                show_messages=False,
                                                                source=f"all_{date.strftime('%Y%m%d')}"
                                                            )

                                                    # Status-specific tabs
                                                    for i, status in enumerate(status_tabs):
                                                        if i > 0:  # Skip the ALL tab which we already handled
                                                            with status_result_tabs[i]:
                                                                # Special handling for the combined NO-SHOW tab
                                                                if status == "NO-SHOW":
                                                                    # Create a mask for all NO-SHOW related statuses
                                                                    no_show_mask = date_df['shift_status'].apply(
                                                                        lambda x: 'NO' in str(x).upper() and 'SHOW' in str(x).upper()
                                                                    )
                                                                    status_filtered_df = date_df[no_show_mask].copy()
                                                                    tab_title = "#### Employees with NO-SHOW Status by Contract and City"
                                                                else:
                                                                    # Regular status filtering
                                                                    status_filtered_df = date_df[date_df['shift_status'] == status].copy()
                                                                    tab_title = f"#### Employees with Status '{status}' by Contract and City"

                                                                if not status_filtered_df.empty:
                                                                    # Normalize contract names before creating the pivot
                                                                    status_filtered_df['contract_name'] = status_filtered_df['contract_name'].apply(
                                                                        evaluated_processor.normalize_contract_name
                                                                    )

                                                                    # Filter out invalid contract-city combinations
                                                                    valid_rows = []
                                                                    for idx, row in status_filtered_df.iterrows():
                                                                        if evaluated_processor.is_valid_contract_city(row['contract_name'], row['city']):
                                                                            valid_rows.append(idx)

                                                                    # Keep only valid contract-city combinations
                                                                    status_filtered_df = status_filtered_df.loc[valid_rows]

                                                                    if status_filtered_df.empty:
                                                                        st.info(f"No valid contract-city combinations found for status '{status}'")
                                                                        continue

                                                                    # Use the regular pivot summary method since we already filtered the data
                                                                    pivot_df = pd.pivot_table(
                                                                        status_filtered_df,
                                                                        index='contract_name',
                                                                        columns='city',
                                                                        values='employee_id',
                                                                        aggfunc='count',
                                                                        fill_value=0
                                                                    ).reset_index()

                                                                    # Add a total column
                                                                    if not pivot_df.empty and len(pivot_df.columns) > 1:
                                                                        pivot_df['Total'] = pivot_df.iloc[:, 1:].sum(axis=1)

                                                                    if pivot_df is not None and not pivot_df.empty:
                                                                        st.markdown(tab_title)
                                                                        evaluated_processor.display_results(
                                                                            pivot_df,
                                                                            date,
                                                                            show_messages=False,
                                                                            source=f"{status.replace('-', '_')}_{date.strftime('%Y%m%d')}"
                                                                        )
                                                                else:
                                                                    st.info(f"No employees with {status} status found for {date.strftime('%Y-%m-%d')}")
                                                else:
                                                    st.info(f"No data found for {date.strftime('%Y-%m-%d')}")
                                        else:
                                            st.warning("Please select at least one date to evaluate")
                                    else:
                                        st.error("No unique records found after filtering")
                                else:
                                    st.error("No data found for the selected dates")
                            else:
                                st.warning("Please select at least one date to evaluate")
                        else:
                            st.error("Failed to process data with contract and city information")
                    else:
                        st.error("No valid data found in the uploaded files")
            else:
                st.info("Please upload Excel files to evaluate")

        except Exception as e:
            st.error(f"Error in Evaluated workflow: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")

if __name__ == "__main__":
    main()





