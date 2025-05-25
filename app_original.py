import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from data_sanitizer import DataSanitizer, validate_data
from check_inactive import InactiveRidersChecker
from evaluated import EvaluatedProcessor
from sheets_connector import SheetsConnector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Shift Management Dashboard", layout="wide")

def apply_custom_table_styling():
    """Apply custom CSS styling for tables with blue headers and no borders."""
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
            padding: 12px 8px !important;
            border: none !important;
            font-size: 14px !important;
        }
        
        .stDataFrame tbody tr td {
            text-align: center !important;
            padding: 10px 8px !important;
            border: none !important;
            border-radius: 8px !important;
        }
        
        .stDataFrame tbody tr:nth-child(even) td {
            background-color: #b8d4f0 !important;
        }
        
        .stDataFrame tbody tr:nth-child(odd) td {
            background-color: white !important;
        }
        
        .stDataFrame tbody tr:hover td {
            background-color: #e3f2fd !important;
            transform: scale(1.02) !important;
            transition: all 0.2s ease !important;
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

def style_dataframe(df, percentage_columns=None, add_grand_total=False):
    """Apply professional styling to dataframes with blue headers and no borders."""
    if percentage_columns is None:
        percentage_columns = []
    
    def format_percentage(val):
        """Format percentage values as plain text"""
        if pd.isna(val):
            return ""
        try:
            return f"{float(val):.1f}%"
        except (ValueError, TypeError):
            return str(val)
    
    # Create styler object
    styler = df.style
    
    # Format percentage columns
    for col in percentage_columns:
        if col in df.columns:
            styler = styler.format({col: format_percentage})
    
    # Apply table styling with blue headers and no borders
    styler = styler.set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#007BFF'),
            ('color', 'white'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '12px 8px'),
            ('border', 'none'),
            ('font-size', '14px')
        ]},
        {'selector': 'td', 'props': [
            ('text-align', 'center'),
            ('padding', '10px 8px'),
            ('border', 'none'),
            ('border-radius', '8px')
        ]},
        {'selector': 'table', 'props': [
            ('border-collapse', 'separate'),
            ('border-spacing', '0'),
            ('border', 'none'),
            ('border-radius', '10px'),
            ('overflow', 'hidden'),
            ('box-shadow', '0 4px 12px rgba(0,0,0,0.1)')
        ]},
        {'selector': 'tr:nth-child(even)', 'props': [
            ('background-color', '#b8d4f0')
        ]},
        {'selector': 'tr:nth-child(odd)', 'props': [
            ('background-color', 'white')
        ]},
        {'selector': 'tr:hover', 'props': [
            ('background-color', '#e3f2fd'),
            ('transform', 'scale(1.02)'),
            ('transition', 'all 0.2s ease')
        ]}
    ])
    
    # Center align all content
    def center_align(val):
        return 'text-align: center'
    
    styler = styler.map(center_align)
    
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

def display_overview(employee_df, shift_df, contract_report_df, city_report_df):
    """Display overview with metrics and charts."""
    # Apply styling again to ensure it's active for this display
    apply_custom_table_styling()
    
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
