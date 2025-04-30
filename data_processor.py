import pandas as pd
from datetime import datetime, time
import os
from config import CONFIG
import numpy as np

class DataProcessor:
    def __init__(self):
        self.raw_data = pd.DataFrame()
        self.processed_data = {}
        self.employee_data = pd.DataFrame()
        self.cities = []
        self.contract_cities = {}
        self.city_contracts = {}
        self.daily_shifts = {}
        self.contract_reports = {}
        self.has_employee_data = False
        self.daily_data = {}
        self.city_data = {}
        self.start_date = None
        self.end_date = None

    def _convert_to_time(self, time_str):
        """Convert string or number to time object"""
        try:
            if isinstance(time_str, time):
                return time_str
            if pd.isna(time_str):
                return None
            
            # If it's a float/number (Excel time format)
            if isinstance(time_str, (float, int)):
                # Convert Excel time (fraction of day) to hours and minutes
                total_seconds = int(float(time_str) * 24 * 3600)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return time(hour=hours % 24, minute=minutes, second=seconds)
            
            # If it's a string, try different formats
            time_str = str(time_str).strip()
            for fmt in ['%H:%M:%S', '%I:%M:%S %p', '%H:%M', '%I:%M %p', '%H.%M.%S', '%H.%M']:
                try:
                    return datetime.strptime(time_str, fmt).time()
                except:
                    continue
                    
            return None
        except:
            return None

    def process_file(self, file):
        """Process a single file"""
        try:
            # Read the file based on its extension
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension == '.csv':
                df = pd.read_csv(file)
            else:  # .xlsx or .xls
                df = pd.read_excel(file, engine='openpyxl', na_filter=False)
            
            # Check if this is the All.xlsx file
            if file.name.lower() == 'all.xlsx' or 'contract name' in [str(col).lower() for col in df.columns]:
                return self._process_employee_file(df, file.name)
            else:
                return self._process_city_file(df, file.name)
            
        except Exception as e:
            raise Exception(f"Error processing file {file.name}: {str(e)}")

    def _process_employee_file(self, df, filename):
        """Process the All.xlsx file containing employee data"""
        try:
            # Standardize column names
            df.columns = [col.lower().strip() for col in df.columns]
            
            # Define the exact column names from the sheet
            id_columns = ['employee id']
            name_columns = ['employee name']
            contract_columns = ['contract name', 'starting point']  # Try both contract name and starting point
            city_columns = ['city']
            
            # Find matching columns
            employee_id_col = next((col for col in id_columns if col in df.columns), None)
            employee_name_col = next((col for col in name_columns if col in df.columns), None)
            contract_col = next((col for col in contract_columns if col in df.columns), None)
            city_col = next((col for col in city_columns if col in df.columns), None)
            
            # Check if required columns exist
            missing_fields = []
            if not employee_id_col:
                missing_fields.append("Employee ID")
            if not employee_name_col:
                missing_fields.append("Employee Name")
            if not contract_col:
                missing_fields.append("Contract Name/Starting Point")
            if not city_col:
                missing_fields.append("City")
            
            if missing_fields:
                raise Exception(f"Missing required columns: {', '.join(missing_fields)}")
            
            # Rename columns to standard names
            column_mapping = {
                employee_id_col: 'employee_id',
                employee_name_col: 'employee_name',
                contract_col: 'contract',
                city_col: 'city'
            }
            df = df.rename(columns=column_mapping)
            
            # Store employee data
            self.employee_data = df
            self.has_employee_data = True
            return True
            
        except Exception as e:
            raise Exception(f"Error processing employee file: {str(e)}")

    def _process_city_file(self, df, filename):
        """Process a city-specific file containing shift data"""
        try:
            if not self.has_employee_data:
                raise Exception("Please upload the All.xlsx file first")
            
            # Standardize column names
            df.columns = [str(col).lower().strip() for col in df.columns]
            
            # Map common column variations to standard names
            column_mapping = {
                'shift id': 'shift_id',
                'employee id': 'employee_id',
                'employee name': 'employee_name',
                'shift status': 'shift_status',
                'planned start': 'planned_start_time',
                'planned end': 'planned_end_time',
                'actual start': 'actual_start_time',
                'actual end': 'actual_end_time',
                'starting point': 'starting_point',
                'shift tag': 'shift_tag'
            }
            
            # Try to match columns even if spaces are removed
            for col in df.columns:
                col_no_space = col.replace(" ", "")
                for pattern, standard in column_mapping.items():
                    if pattern.replace(" ", "") in col_no_space:
                        df = df.rename(columns={col: standard})
                        break
            
            # Ensure required columns exist
            required_columns = ['employee_id', 'shift_status']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise Exception(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Convert time columns
            time_columns = ['planned_start_time', 'planned_end_time', 'actual_start_time', 'actual_end_time']
            for col in time_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self._convert_to_time)
            
            # Remove specified shift statuses if configured
            if hasattr(CONFIG, 'shift_status_to_remove'):
                df = df[~df['shift_status'].isin(CONFIG['shift_status_to_remove'])]
            
            # Remove rows with invalid times
            required_time_cols = ['planned_start_time', 'planned_end_time']
            df = df.dropna(subset=[col for col in required_time_cols if col in df.columns])
            
            # Add city information from filename
            city_name = os.path.splitext(filename)[0]
            df['city'] = city_name
            
            # Append to raw data
            self.raw_data = pd.concat([self.raw_data, df], ignore_index=True)
            return True
            
        except Exception as e:
            raise Exception(f"Error processing city file {filename}: {str(e)}")

    def get_available_dates(self):
        """Get list of available dates from the processed data"""
        if self.raw_data.empty:
            return []
        try:
            dates = self.raw_data['planned start date'].unique()
            return sorted([d for d in dates if pd.notna(d)])
        except:
            return []

    def generate_reports(self, selected_dates):
        """Generate reports for selected dates"""
        try:
            if not selected_dates:
                return {}
            
            # Process each date separately
            self.daily_data = {}
            for date in selected_dates:
                # Filter data for this date
                date_data = self.raw_data[self.raw_data['planned start date'] == date].copy()
                
                # Keep only employee_id and times
                shift_data = date_data[['employee id', 'planned start time', 'planned end time', 'city']].drop_duplicates()
                
                # Get all employees from employee_data
                all_employees = self.employee_data[['employee id', 'contract', 'city']].copy()
                
                # Find unassigned employees (those in all_employees but not in shift_data)
                assigned_ids = set(shift_data['employee id'])
                all_employees['assigned'] = all_employees['employee id'].isin(assigned_ids)
                
                # Group by contract and city
                contract_reports = {}
                for contract in sorted(all_employees['contract'].unique()):
                    contract_data = []
                    
                    for city in self.city_order:
                        city_data = all_employees[
                            (all_employees['contract'] == contract) & 
                            (all_employees['city'] == city)
                        ]
                        
                        if not city_data.empty:
                            total = len(city_data)
                            assigned = city_data['assigned'].sum()
                            unassigned = total - assigned
                            percentage = (assigned / total * 100) if total > 0 else 0
                            
                            contract_data.append({
                                'city': city,
                                'hq': total,
                                'assigned': assigned,
                                'unassigned': unassigned,
                                'percentage': percentage
                            })
                    
                    if contract_data:
                        # Create DataFrame for this contract
                        contract_df = pd.DataFrame(contract_data)
                        # Add grand total row
                        total_row = {
                            'city': 'Grand Total',
                            'hq': contract_df['hq'].sum(),
                            'assigned': contract_df['assigned'].sum(),
                            'unassigned': contract_df['unassigned'].sum(),
                            'percentage': (contract_df['assigned'].sum() / contract_df['hq'].sum() * 100) 
                                if contract_df['hq'].sum() > 0 else 0
                        }
                        contract_df = pd.concat([
                            contract_df, 
                            pd.DataFrame([total_row])
                        ], ignore_index=True)
                        
                        contract_reports[contract] = contract_df
                
                self.daily_data[date] = contract_reports
            
            return self.daily_data
            
        except Exception as e:
            raise Exception(f"Error generating reports: {str(e)}")

    def get_unassigned_employees(self, date, contract):
        """Get list of unassigned employees for a given date and contract"""
        try:
            # Get all employees for this contract
            contract_employees = self.employee_data[
                self.employee_data['Contract Name'] == contract
            ].copy()
            
            if date in self.daily_shifts:
                # Get assigned employee IDs for this date
                assigned_ids = self.daily_shifts[date]['employee id'].unique()
                
                # Filter out assigned employees
                unassigned = contract_employees[
                    ~contract_employees['Employee ID'].isin(assigned_ids)
                ]
            else:
                # If no shifts for this date, all employees are unassigned
                unassigned = contract_employees
            
            # Select and rename columns for output
            result = unassigned[['Employee ID', 'Employee Name', 'City']]
            
            return result.sort_values('Employee ID').reset_index(drop=True)
            
        except Exception as e:
            print(f"Error getting unassigned employees: {str(e)}")
            return pd.DataFrame()

    def create_contract_report(self, contract, dates):
        """Create a formatted report for a contract across multiple dates"""
        try:
            if not dates:
                return pd.DataFrame()
            
            # Create the report
            report_data = []
            for city in self.city_order:
                row_data = {'City': city, 'HQ': 0}
                
                # Get data for each date
                for date in sorted(dates):
                    if date in self.daily_data and contract in self.daily_data[date]:
                        city_row = self.daily_data[date][contract][
                            self.daily_data[date][contract]['city'] == city
                        ]
                        
                        if not city_row.empty:
                            # Store HQ value
                            row_data['HQ'] = int(city_row['hq'].iloc[0])
                            
                            # Format date as day only (e.g., "25" from "2025-04-25")
                            day = pd.to_datetime(date).strftime('%d')
                            
                            # Add columns for this date
                            row_data[f'Assigned_{day}'] = int(city_row['assigned'].iloc[0])
                            row_data[f'Unassigned_{day}'] = int(city_row['unassigned'].iloc[0])
                            row_data[f'% of Assigned_{day}'] = city_row['percentage'].iloc[0]
                
                if row_data['HQ'] > 0:  # Only add rows with actual data
                    report_data.append(row_data)
            
            if report_data:
                # Calculate grand total
                total_row = {'City': 'Grand Total', 'HQ': sum(row['HQ'] for row in report_data)}
                for date in sorted(dates):
                    day = pd.to_datetime(date).strftime('%d')
                    assigned_col = f'Assigned_{day}'
                    unassigned_col = f'Unassigned_{day}'
                    pct_col = f'% of Assigned_{day}'
                    
                    if assigned_col in report_data[0]:
                        total_assigned = sum(row[assigned_col] for row in report_data)
                        total_unassigned = sum(row[unassigned_col] for row in report_data)
                        total_row[assigned_col] = total_assigned
                        total_row[unassigned_col] = total_unassigned
                        total_row[pct_col] = (total_assigned / total_row['HQ'] * 100) if total_row['HQ'] > 0 else 0
                
                report_data.append(total_row)
                
                # Create DataFrame
                df = pd.DataFrame(report_data)
                
                # Format percentage columns
                for col in df.columns:
                    if col.startswith('% of Assigned'):
                        df[col] = df[col].apply(lambda x: f"{x:.2f}%")
                
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error creating contract report: {str(e)}")
            return pd.DataFrame()

    def get_employee_details(self, employee_id):
        """Get employee details from the employee data"""
        try:
            if self.employee_data.empty:
                return None
            
            employee = self.employee_data[self.employee_data['employee id'] == employee_id]
            if not employee.empty:
                return {
                    'employee_name': employee['employee name'].iloc[0],
                    'contract': employee['contract'].iloc[0],
                    'city': employee['city'].iloc[0]
                }
            return None
        except Exception as e:
            raise Exception(f"Error getting employee details: {str(e)}")

    def process_data(self, employee_data=None, city_files=None):
        """Process uploaded employee data and city files."""
        try:
            if employee_data is not None:
                if isinstance(employee_data, pd.DataFrame):
                    self.employee_data = employee_data
                else:
                    self.employee_data = pd.read_excel(employee_data)

                # Standardize column names
                self.employee_data.columns = [col.lower().replace(' ', '_') for col in self.employee_data.columns]
                
                # Initialize processed data with required columns
                self.processed_data = pd.DataFrame({
                    'employee_id': self.employee_data['employee_id'],
                    'employee_name': self.employee_data['employee_name'],
                    'total_shifts': 0,
                    'completed_shifts': 0,
                    'scheduled_shifts': 0,
                    'attended_shifts': 0
                })

            if city_files:
                for city, file in city_files.items():
                    if isinstance(file, pd.DataFrame):
                        city_data = file
                    else:
                        city_data = pd.read_excel(file)
                    
                    # Standardize column names
                    city_data.columns = [col.lower().replace(' ', '_') for col in city_data.columns]
                    
                    # Convert date columns to datetime
                    date_columns = ['date', 'start_time', 'end_time']
                    for col in date_columns:
                        if col in city_data.columns:
                            city_data[col] = pd.to_datetime(city_data[col])
                    
                    self.city_data[city] = city_data

            # Calculate metrics
            self._calculate_metrics()
            return True

        except Exception as e:
            error_msg = f"Error processing data: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)

    def _calculate_metrics(self):
        """Calculate performance metrics for each employee."""
        try:
            # Reset metrics
            self.processed_data['total_shifts'] = 0
            self.processed_data['completed_shifts'] = 0
            self.processed_data['scheduled_shifts'] = 0
            self.processed_data['attended_shifts'] = 0

            # Process data for each city
            for city, data in self.city_data.items():
                for _, row in data.iterrows():
                    employee_id = row['employee_id']
                    if employee_id in self.processed_data['employee_id'].values:
                        idx = self.processed_data.index[
                            self.processed_data['employee_id'] == employee_id
                        ].values[0]
                        
                        # Update shift counts
                        self.processed_data.at[idx, 'total_shifts'] += 1
                        
                        if row['status'].lower() == 'completed':
                            self.processed_data.at[idx, 'completed_shifts'] += 1
                        
                        if pd.notna(row['start_time']):
                            self.processed_data.at[idx, 'scheduled_shifts'] += 1
                        
                        if row['attended'].lower() == 'yes':
                            self.processed_data.at[idx, 'attended_shifts'] += 1

            # Calculate completion and attendance rates
            self.processed_data['completion_rate'] = (
                self.processed_data['completed_shifts'] / 
                                               self.processed_data['total_shifts']
            ).fillna(0)

            self.processed_data['attendance_rate'] = (
                self.processed_data['attended_shifts'] / 
                                               self.processed_data['scheduled_shifts']
            ).fillna(0)

            return True

        except Exception as e:
            error_msg = f"Error calculating metrics: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)

    def _calculate_city_metrics(self, city_data):
        """Calculate metrics for a specific city."""
        try:
            metrics = city_data.groupby('employee_id').agg({
                'shift_status': 'count',  # Count total shifts
            }).reset_index()
            metrics.columns = ['employee_id', 'total_shifts']
            return metrics
        except Exception as e:
            print(f"Warning: Error calculating city metrics: {str(e)}")
            return pd.DataFrame()

    def get_contracts(self):
        """Return list of unique contracts."""
        # First try to get contracts from processed_data if it's a DataFrame
        if isinstance(self.processed_data, pd.DataFrame):
            if 'contract' in self.processed_data.columns:
                contracts = self.processed_data['contract'].unique().tolist()
                if contracts:
                    return sorted(contracts)
        
        # If no contracts found in processed_data, try employee_data
        if isinstance(self.employee_data, pd.DataFrame):
            # Try 'contract' column first
            if 'contract' in self.employee_data.columns:
                contracts = self.employee_data['contract'].unique().tolist()
                if contracts:
                    return sorted(contracts)
            # Try 'starting point' column as fallback
            elif 'starting point' in self.employee_data.columns:
                contracts = self.employee_data['starting point'].unique().tolist()
                if contracts:
                    return sorted(contracts)
        
        return []

    def get_contract_report(self, contract):
        """Generate report for a specific contract."""
        contract_data = self.processed_data[self.processed_data['contract'] == contract]
        
        # Calculate summary metrics
        summary = {
            'total_shifts': contract_data['total_shifts'].sum(),
            'completion_rate': contract_data['completion_rate'].mean(),
            'avg_rating': contract_data['customer_rating'].mean()
        }
        
        # Create performance table
        performance_table = contract_data.groupby('employee_id').agg({
            'completion_rate': 'mean',
            'attendance_rate': 'mean',
            'customer_rating': 'mean',
            'response_time': 'mean'
        }).reset_index()
        
        # Create attendance table
        attendance_table = contract_data.groupby('employee_id').agg({
            'scheduled_shifts': 'sum',
            'attended_shifts': 'sum',
            'completed_shifts': 'sum',
            'cancelled_shifts': 'sum'
        }).reset_index()
        
        # Format column names
        performance_table.columns = ['Employee ID', 'Completion Rate', 'Attendance Rate', 
                                   'Avg Rating', 'Avg Response Time (min)']
        attendance_table.columns = ['Employee ID', 'Scheduled', 'Attended', 
                                  'Completed', 'Cancelled']
        
        return {
            'total_shifts': summary['total_shifts'],
            'completion_rate': summary['completion_rate'],
            'avg_rating': summary['avg_rating'],
            'performance_table': performance_table,
            'attendance_table': attendance_table
        } 

    def process_shift_data(self, shift_files, selected_dates):
        """Process shift data files for multiple cities"""
        combined_data = pd.DataFrame()
        
        # Process each city's shift file
        for file in shift_files:
            df = pd.read_excel(file) if file.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
            
            # Keep only required columns
            required_cols = ['employee id', 'shift status', 'planned start date', 
                           'planned end date', 'planned start time', 'planned end time']
            
            # Convert column names to lowercase
            df.columns = [col.lower().strip() for col in df.columns]
            
            # Check if all required columns exist
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                available_cols = ", ".join(df.columns)
                raise ValueError(f"Missing columns in shift file {file.name}: {missing_cols}. Available columns: {available_cols}")
            
            df = df[required_cols]
            
            # Convert time columns - handle both string and time objects
            for time_col in ['planned start time', 'planned end time']:
                # Convert to string first to handle both string and time objects
                df[time_col] = df[time_col].astype(str)
                
                # Try parsing with different formats
                def parse_time(x):
                    if pd.isna(x) or x == 'nan':
                        return None
                    try:
                        # Try parsing as time first
                        return pd.to_datetime(x).time()
                    except:
                        # Try common time formats
                        for fmt in ['%H:%M:%S', '%I:%M:%S %p', '%H:%M', '%I:%M %p']:
                            try:
                                return datetime.strptime(x.strip(), fmt).time()
                            except:
                                continue
                    return None
                
                df[time_col] = df[time_col].apply(parse_time)
            
            # Convert date columns
            for date_col in ['planned start date', 'planned end date']:
                df[date_col] = pd.to_datetime(df[date_col]).dt.date
            
            # Filter out unwanted shift statuses
            df = df[~df['shift status'].isin(['NO_SHOW(UNEXCUSED)', 'NO_SHOW_EXCUSED(EXCUSED)'])]
            
            # Filter for selected dates
            if selected_dates:
                df = df[df['planned start date'].isin(selected_dates)]
            
            combined_data = pd.concat([combined_data, df], ignore_index=True)
        
        # Process data for each date
        self.daily_shifts = {}
        if not combined_data.empty:
            all_dates = combined_data['planned start date'].unique()
            for date in all_dates:
                date_data = combined_data[combined_data['planned start date'] == date].copy()
                
                # Remove duplicates based on employee ID
                date_data = date_data.drop_duplicates(subset=['employee id'])
                
                # Keep only required columns for final output
                date_data = date_data[['employee id', 'planned start time', 'planned end time']]
                
                self.daily_shifts[date] = date_data
        
        return combined_data

    def process_employee_data(self, data):
        """Process employee data from either a DataFrame or an Excel file"""
        # If data is a DataFrame, use it directly, otherwise read the Excel file
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            df = pd.read_excel(data)
        
        # Convert all column names to lowercase for case-insensitive matching
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Define possible variations of column names
        column_variations = {
            'Employee ID': ['employee id', 'employeeid', 'id', 'employee_id', 'emp id', 'emp_id'],
            'Employee Name': ['employee name', 'employeename', 'name', 'employee_name', 'emp name', 'emp_name'],
            'Contract Name': ['contract name', 'contractname', 'contract', 'starting point', 'contract_name'],
            'City': ['city', 'location', 'branch', 'office']
        }
        
        # Find matching columns
        column_mapping = {}
        missing_fields = []
        
        for required_col, variations in column_variations.items():
            found_col = next((col for col in df.columns if col in variations), None)
            if found_col:
                column_mapping[found_col] = required_col
            else:
                missing_fields.append(required_col)
        
        if missing_fields:
            # Print available columns to help debugging
            available_cols = ", ".join(df.columns)
            raise ValueError(f"Missing required columns: {missing_fields}. Available columns are: {available_cols}")
        
        # Rename columns to standard names
        df = df.rename(columns=column_mapping)
        
        # Store employee data
        self.employee_data = df
        
        return df

    def generate_contract_reports(self, selected_dates):
        """Generate reports for each contract and date"""
        try:
            self.contract_reports = {}
            
            for contract in self.contract_cities.keys():
                # Get all cities for this contract
                contract_cities = self.contract_cities[contract]
                
                # Initialize the DataFrame columns
                columns = ['City', 'HQ']
                
                # Add columns for each date
                for date in selected_dates:
                    date_str = date.strftime('%d-%b')  # Format date as '01-Jan'
                    columns.extend([
                        f'{date_str} Assigned',
                        f'{date_str} Unassigned',
                        f'{date_str} %'
                    ])
                
                # Initialize data for this contract
                report_data = []
                
                # Process each city
                for city in contract_cities:
                    # Get employees for this contract and city
                    city_employees = self.employee_data[
                        (self.employee_data['Contract Name'] == contract) & 
                        (self.employee_data['City'] == city)
                    ]
                    
                    # Initialize row with city and HQ
                    row_data = {
                        'City': city,
                        'HQ': len(city_employees)
                    }
                    
                    # Add data for each date
                    for date in selected_dates:
                        date_str = date.strftime('%d-%b')
                        
                        if date in self.daily_shifts:
                            date_shifts = self.daily_shifts[date]
                            
                            # Count assigned employees for this city
                            assigned = len(set(city_employees['Employee ID']) & 
                                        set(date_shifts['employee id']))
                            
                            unassigned = row_data['HQ'] - assigned
                            pct_assigned = (assigned / row_data['HQ'] * 100) if row_data['HQ'] > 0 else 0
                            
                            # Add data for this date
                            row_data[f'{date_str} Assigned'] = assigned
                            row_data[f'{date_str} Unassigned'] = unassigned
                            row_data[f'{date_str} %'] = f"{pct_assigned:.2f}%"
                        else:
                            # If no data for this date, set defaults
                            row_data[f'{date_str} Assigned'] = 0
                            row_data[f'{date_str} Unassigned'] = row_data['HQ']
                            row_data[f'{date_str} %'] = "0.00%"
                    
                    report_data.append(row_data)
                
                # Add grand total row
                if report_data:
                    total_row = {
                        'City': 'Grand Total',
                        'HQ': sum(row['HQ'] for row in report_data)
                    }
                    
                    # Calculate totals for each date
                    for date in selected_dates:
                        date_str = date.strftime('%d-%b')
                        
                        total_assigned = sum(row[f'{date_str} Assigned'] for row in report_data)
                        total_row[f'{date_str} Assigned'] = total_assigned
                        total_row[f'{date_str} Unassigned'] = total_row['HQ'] - total_assigned
                        total_row[f'{date_str} %'] = f"{(total_assigned / total_row['HQ'] * 100):.2f}%" if total_row['HQ'] > 0 else "0.00%"
                    
                    report_data.append(total_row)
                
                # Create DataFrame with ordered columns
                if report_data:
                    df = pd.DataFrame(report_data)
                    df = df[columns]  # Reorder columns
                    self.contract_reports[contract] = df
            
            return self.contract_reports
            
        except Exception as e:
            print(f"Error generating contract reports: {str(e)}")
            return {}

    def get_shifts_for_date(self, date, contract):
        """Get shifts for a specific date and contract"""
        try:
            if date not in self.daily_shifts:
                return pd.DataFrame()
            
            # Get shifts for the date
            shifts = self.daily_shifts[date].copy()
            
            # Get employees for this contract
            contract_employees = self.employee_data[
                self.employee_data['Contract Name'] == contract
            ]['Employee ID'].tolist()
            
            # Filter shifts for employees in this contract
            shifts = shifts[shifts['employee id'].isin(contract_employees)]
            
            # Sort by employee id
            shifts = shifts.sort_values('employee id')
            
            # Reset index
            shifts = shifts.reset_index(drop=True)
            
            return shifts
            
        except Exception as e:
            print(f"Error getting shifts for date {date}: {str(e)}")
            return pd.DataFrame()