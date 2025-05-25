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
