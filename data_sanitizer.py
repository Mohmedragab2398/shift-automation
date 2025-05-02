import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import openpyxl
import re
from datetime import datetime
import io
import csv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add REQUIRED_COLUMNS and validate_data at the top of the file
REQUIRED_COLUMNS = {
    'employee_file': ['employee_id', 'employee_name', 'contract_name', 'city'],
    'shift_file': ['employee_id', 'shift_status', 'planned_start_date']
}

def validate_data(df, data_type):
    missing = [col for col in REQUIRED_COLUMNS[data_type] if col not in df.columns]
    if missing:
        import streamlit as st
        st.error(f"Missing required columns in {data_type}: {', '.join(missing)}")
        st.stop()

class DataSanitizer:
    # Required columns that must be preserved throughout processing
    REQUIRED_COLUMNS = {
        'employee': ['employee_id', 'employee_name', 'contract_name', 'city'],
        'shift': [
            'employee_id', 
            'employee_name', 
            'contract_name', 
            'city',
            'shift_status',
            'planned_start_date',
            'planned_end_date',
            'planned_start_time',
            'planned_end_time'
        ]
    }
    
    # Valid shift statuses to keep
    VALID_STATUSES = ['EVALUATED', 'PUBLISHED']
    
    # Invalid shift statuses to filter out (kept for backward compatibility)
    INVALID_STATUSES = [
        'NO_SHOW(UNEXCUSED)',
        'NO_SHOW_EXCUSED(EXCUSED)'
    ]

    @staticmethod
    def process_employee_file(file) -> Tuple[pd.DataFrame, List[str]]:
        """Process employee file with consistent ID handling"""
        try:
            df = pd.read_excel(file) if isinstance(file, str) else pd.read_excel(file)
            if df.empty:
                logger.error("Employee file is empty")
                return df, ["File is empty"]
            
            # Normalize column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Check for required columns
            required_cols = {'employee_id', 'employee_name', 'contract_name', 'city'}
            missing_cols = list(required_cols - set(df.columns))
            if missing_cols:
                logger.error(f"Missing required columns in employee file: {missing_cols}")
                return None, missing_cols
            
            # Clean and normalize data
            df = df.dropna(subset=['employee_id'])
            
            # Convert all columns to string type and handle special cases
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    # Convert datetime to string format
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                elif pd.api.types.is_numeric_dtype(df[col]):
                    # Convert numeric to string, handling NaN
                    df[col] = df[col].fillna('').astype(str)
                else:
                    # Convert other types to string
                    df[col] = df[col].fillna('').astype(str).str.strip()
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['employee_id'], keep='first')
            
            # Ensure consistent data types for all columns
            df = df.astype({
                'employee_id': str,
                'employee_name': str,
                'contract_name': str,
                'city': str
            })
            
            logger.info(f"Successfully processed employee file. Total employees: {len(df)}")
            return df, []
            
        except Exception as e:
            logger.error(f"Error processing employee file: {str(e)}")
            raise

    @staticmethod
    def process_shift_file(file, city_name: str) -> Tuple[pd.DataFrame, List[str]]:
        """Process individual city shift files."""
        try:
            # Read the file
            df = pd.read_csv(file) if isinstance(file, str) else pd.read_csv(file)
            if df.empty:
                logger.error(f"Shift file is empty: {file}")
                return df, ["File is empty"]
            
            logger.info(f"Original shift file columns: {list(df.columns)}")
            
            # Standardize column names
            df.columns = df.columns.str.lower().str.strip()
            
            # Map columns to standard names
            column_mapping = {
                'shift id': 'shift_id',
                'employee id': 'employee_id',
                'employee': 'employee_id',
                'emp id': 'employee_id',
                'employee name': 'employee_name',
                'emp name': 'employee_name',
                'contract name': 'contract_name',
                'contract': 'contract_name',
                'shift status': 'shift_status',
                'planned start date': 'planned_start_date',
                'planned end date': 'planned_end_date',
                'planned start time': 'planned_start_time',
                'planned end time': 'planned_end_time'
            }
            
            df = df.rename(columns=column_mapping)
            logger.info(f"Columns after mapping: {list(df.columns)}")
            
            # Add contract_name if missing
            if 'contract_name' not in df.columns:
                df['contract_name'] = city_name.replace('-', ' ').title()
            
            # Add city if missing
            if 'city' not in df.columns:
                df['city'] = city_name.replace('-', ' ').title()
            
            # Check for required columns
            missing_cols = [col for col in DataSanitizer.REQUIRED_COLUMNS['shift'] 
                          if col not in df.columns]
            
            if missing_cols:
                logger.error(f"Missing required columns in {file}: {missing_cols}")
                return df, missing_cols
            
            # Convert date columns
            try:
                df['planned_start_date'] = pd.to_datetime(df['planned_start_date']).dt.date
                df['planned_end_date'] = pd.to_datetime(df['planned_end_date']).dt.date
            except Exception as e:
                logger.error(f"Error converting dates in {file}: {str(e)}")
                return df, ["Invalid date format"]
            
            # Convert time columns robustly
            for col in ['planned_start_time', 'planned_end_time']:
                if col in df.columns:
                    # Try to parse as datetime, fallback to string if needed
                    dt_series = pd.to_datetime(df[col], errors='coerce')
                    # If conversion fails, keep as string
                    df[col] = dt_series.dt.strftime('%H:%M').where(~dt_series.isna(), df[col].astype(str))
            
            logger.info(f"Successfully processed file. Shape: {df.shape}")
            return df, []
            
        except Exception as e:
            logger.error(f"Error processing shift file {file}: {str(e)}")
            raise

    @staticmethod
    def preprocess_shifts(df: pd.DataFrame) -> pd.DataFrame:
        """Filter out invalid shift statuses and clean data."""
        if df.empty:
            return df
        
        # Step 1: Filter to keep only valid statuses
        if 'shift_status' in df.columns:
            df = df[df['shift_status'].isin(DataSanitizer.VALID_STATUSES)]
        
        # Step 2: Keep only necessary columns and remove duplicates
        cols_to_keep = [
            'employee_id', 
            'planned_start_date', 
            'planned_end_date',
            'planned_start_time',
            'planned_end_time',
            'shift_status',  # Keep for potential future filtering
            'contract_name', # Keep for reporting
            'city'          # Keep for reporting
        ]
        
        # Only keep columns that exist in the DataFrame
        existing_cols = [col for col in cols_to_keep if col in df.columns]
        df = df[existing_cols]
        
        # Remove duplicate shifts for the same employee on the same day
        dedup_cols = ['employee_id', 'planned_start_date']
        df = df.drop_duplicates(subset=dedup_cols)
        
        return df

    @staticmethod
    def merge_shift_files(files: List) -> pd.DataFrame:
        """Merge shift files with consistent ID handling"""
        if not files:
            logger.error("No city files provided")
            return pd.DataFrame()
        
        all_dfs = []
        for file in files:
            try:
                city_name = file.name.split('.')[0]
                df, missing_cols = DataSanitizer.process_shift_file(file, city_name)
                
                if missing_cols:
                    logger.error(f"Missing columns in {file.name}: {missing_cols}")
                    continue
                
                # Normalize employee IDs
                df['employee_id'] = df['employee_id'].astype(str).str.strip()
                
                # Keep required columns and preprocess
                df = df[DataSanitizer.REQUIRED_COLUMNS['shift']]
                df = DataSanitizer.preprocess_shifts(df)
                
                if not df.empty:
                    all_dfs.append(df)
                    
            except Exception as e:
                logger.error(f"Error processing {file.name}: {str(e)}")
                continue
        
        if not all_dfs:
            logger.error("No valid data found in any city file")
            return pd.DataFrame()
        
        return pd.concat(all_dfs, ignore_index=True)

    @staticmethod
    def filter_by_dates(df: pd.DataFrame, date_range) -> Dict[datetime.date, pd.DataFrame]:
        """Filter shifts by date and valid statuses"""
        if df.empty:
            logger.error("No data to filter")
            return {}
            
        try:
            # 1. Filter valid statuses first
            valid_statuses = ['EVALUATED', 'PUBLISHED']
            df = df[df['shift_status'].isin(valid_statuses)].copy()
            
            if df.empty:
                logger.error("No valid shifts after status filtering")
                return {}
            
            # 2. Convert dates and filter range
            df['planned_start_date'] = pd.to_datetime(df['planned_start_date']).dt.date
            date_range = [d.date() if isinstance(d, pd.Timestamp) else d for d in date_range]
            
            # 3. Deduplicate employees per day
            return {
                date: df[df['planned_start_date'] == date]
                    .sort_values('planned_start_time')
                    .drop_duplicates(subset=['employee_id'])
                    .copy()
                for date in date_range
            }
            
        except Exception as e:
            logger.error(f"Error in filter_by_dates: {str(e)}")
            return {}

    @staticmethod
    def generate_contract_report(shift_data: pd.DataFrame, employee_data: pd.DataFrame) -> pd.DataFrame:
        """Generate contract report with guaranteed 'City' column"""
        if shift_data.empty or employee_data.empty:
            logger.error("Empty data provided for contract report")
            return pd.DataFrame()
            
        try:
            # 1. Validate input columns
            required_employee_cols = {'employee_id', 'contract_name', 'city'}
            if not required_employee_cols.issubset(employee_data.columns):
                missing = required_employee_cols - set(employee_data.columns)
                raise KeyError(f"Employee data missing required columns: {missing}")
            
            if 'employee_id' not in shift_data.columns:
                raise KeyError("Shift data missing 'employee_id' column")
            
            # Ensure consistent ID types and case
            shift_data = shift_data.copy()
            employee_data = employee_data.copy()
            shift_data['employee_id'] = shift_data['employee_id'].astype(str).str.strip()
            employee_data['employee_id'] = employee_data['employee_id'].astype(str).str.strip()
            
            # 2. Core calculation
            assigned_ids = shift_data['employee_id'].unique()
            
            # Calculate totals from employee master
            total = employee_data.groupby(['contract_name', 'city']) \
                               .size() \
                               .reset_index(name='Total')
            
            # Calculate assigned from filtered shifts
            assigned = employee_data[employee_data['employee_id'].isin(assigned_ids)] \
                                  .groupby(['contract_name', 'city']) \
                                  .size() \
                                  .reset_index(name='Assigned')
            
            # 3. Safe merge with validation
            report = pd.merge(
                total,
                assigned,
                on=['contract_name', 'city'],
                how='left',
                validate='one_to_one'
            )
            
            # 4. Ensure required columns exist
            if 'city' not in report.columns:
                raise KeyError("City column missing after merge")
            
            # Fill missing values and calculate metrics
            report['Assigned'] = report['Assigned'].fillna(0).astype(int)
            report['Unassigned'] = report['Total'] - report['Assigned']
            report['Assigned_Percentage'] = (report['Assigned'] / report['Total'] * 100).round(2)
            
            # 5. Final rename with consistent case and column order
            result = report.rename(columns={
                'contract_name': 'Contract',
                'city': 'City'
            })
            
            # Ensure consistent column order
            columns = ['Contract', 'City', 'Total', 'Assigned', 'Unassigned', 'Assigned_Percentage']
            return result.reindex(columns=columns)
            
        except Exception as e:
            logger.error(f"Error generating contract report: {str(e)}")
            raise  # Re-raise to handle in the UI layer

    @staticmethod
    def generate_city_report(shift_data: pd.DataFrame, employee_data: pd.DataFrame) -> pd.DataFrame:
        """Generate city-wise report."""
        if shift_data.empty or employee_data.empty:
            logger.error("Empty data provided for city report")
            return pd.DataFrame()
        
        # Ensure employee_id is string type in both dataframes
        shift_data['employee_id'] = shift_data['employee_id'].astype(str)
        employee_data['employee_id'] = employee_data['employee_id'].astype(str)
        
        # Get unique dates
        dates = sorted(shift_data['planned_start_date'].unique())
        
        # Create report for each city
        city_reports = []
        for city in sorted(employee_data['city'].unique()):
            # Get city employees
            city_employees = employee_data[employee_data['city'] == city]
            
            # Calculate metrics for each contract in the city
            for contract in sorted(city_employees['contract_name'].unique()):
                contract_employees = city_employees[city_employees['contract_name'] == contract]
                total_employees = len(contract_employees)
                
                # Calculate metrics for each date
                for date in dates:
                    date_shifts = shift_data[
                        (shift_data['planned_start_date'] == date) & 
                        (shift_data['employee_id'].isin(contract_employees['employee_id']))
                    ]
                    
                    # Remove duplicates based on employee_id
                    date_shifts = date_shifts.drop_duplicates(subset=['employee_id'], keep='first')
                    
                    assigned = len(date_shifts)
                    unassigned = total_employees - assigned
                    assigned_pct = (assigned / total_employees * 100) if total_employees > 0 else 0
                    
                    city_reports.append({
                        'City': city,
                        'Contract': contract,
                        'Date': date,
                        'Total': total_employees,
                        'Assigned': assigned,
                        'Unassigned': unassigned,
                        'Assigned_Percentage': assigned_pct
                    })
        
        return pd.DataFrame(city_reports)

    @staticmethod
    def detect_unassigned_employees(employees_df: pd.DataFrame, shifts_df: pd.DataFrame, selected_date: str) -> pd.DataFrame:
        """
        Detect employees who have no shifts assigned for the selected date using proper left join.
        """
        if employees_df.empty or shifts_df.empty:
            return pd.DataFrame()
            
        try:
            # Convert selected_date to datetime for comparison
            selected_date = pd.to_datetime(selected_date).date()
            
            # Ensure we're working with copies
            employees_df = employees_df.copy()
            shifts_df = shifts_df.copy()
            
            # Filter shifts for selected date
            shifts_df = shifts_df[pd.to_datetime(shifts_df['planned_start_date']).dt.date == selected_date]
            
            # Perform left join to find unassigned employees
            merged = pd.merge(
                employees_df,
                shifts_df[['employee_id']].drop_duplicates() if not shifts_df.empty else pd.DataFrame(columns=['employee_id']),
                on='employee_id',
                how='left',
                indicator=True
            )
            
            # Get only unassigned employees (left_only from merge)
            unassigned_df = merged[merged['_merge'] == 'left_only'].copy()
            
            if not unassigned_df.empty:
                # Sort by employee name and keep only required columns
                unassigned_df = unassigned_df.sort_values('employee_name')
                return unassigned_df[['employee_id', 'employee_name', 'contract_name', 'city']]
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error detecting unassigned employees: {str(e)}")
            return pd.DataFrame() 