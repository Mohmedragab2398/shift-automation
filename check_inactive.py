import streamlit as st
import pandas as pd
from datetime import datetime
from sheets_connector import SheetsConnector

class InactiveRidersChecker:
    def __init__(self):
        self.sheets_connector = SheetsConnector()
        self.spreadsheet_id = st.secrets["spreadsheet_id"]  # Use the spreadsheet ID from secrets.toml
        self.cities = ['Cairo', 'Assiut', 'Hurghada', 'Minya', 'Port Said', 'Mansoura', 'Damanhour', 'Al Mahallah Al Kubra', 'Alexandria']

    def get_all_employees(self):
        """Get all employees from the all sheet with standardized columns."""
        try:
            # Use the get_all_sheet_data method which is more reliable
            all_data = self.sheets_connector.get_all_sheet_data()

            # Check if data is None, empty, or only contains headers
            if all_data is None or all_data.empty or len(all_data) <= 1:
                st.error("No data found or insufficient data in all sheet")
                return None

            # Standardize column names
            all_data.columns = [str(col).strip().lower().replace(' ', '_') for col in all_data.columns]
            all_data['employee_id'] = all_data['employee_id'].astype(str)

            # Print column names for debugging
            print("Available columns in all_data:", all_data.columns.tolist())

            # Map common column name variations to our expected names
            column_mapping = {
                'name': 'full_name',
                'employee_name': 'full_name',
                'rider_name': 'full_name',
                'contract': 'contract_name',
                'contract_type': 'contract_name'
            }

            # Apply column mapping if needed
            for old_col, new_col in column_mapping.items():
                if old_col in all_data.columns and new_col not in all_data.columns:
                    all_data[new_col] = all_data[old_col]

            return all_data
        except Exception as e:
            st.error(f"Error fetching employee data: {str(e)}")
            return None

    def get_active_employees(self, start_date, end_date):
        """Get all active employees across all city sheets for the given date range."""
        active_ids = set()

        for city in self.cities:
            try:
                # Use the read_sheet method with proper error handling
                city_data = self.sheets_connector.read_sheet(
                    spreadsheet_id=self.spreadsheet_id,
                    range_name=f"{city}!A1:Z"
                )

                if city_data is None or city_data.empty or len(city_data) < 2:
                    # Skip silently if no data
                    continue

                # Standardize column names
                city_data.columns = [str(col).strip().lower().replace(' ', '_') for col in city_data.columns]

                # Filter out invalid shift statuses first (NO_SHOW statuses)
                if 'shift_status' in city_data.columns:
                    # Remove NO_SHOW(UNEXCUSED) and NO_SHOW_EXCUSED(EXCUSED) statuses
                    city_data = city_data[
                        ~city_data['shift_status'].str.contains('NO_SHOW', na=False, case=False)
                    ]

                # Check for date columns - both planned and actual dates
                planned_date_col = None
                actual_date_col = None

                # Look for planned date column
                planned_date_columns = ['planned_start_date', 'planned_date', 'date']
                for col in planned_date_columns:
                    if col in city_data.columns:
                        planned_date_col = col
                        break

                # Look for actual date column
                actual_date_columns = ['actual_start_date', 'actual_date']
                for col in actual_date_columns:
                    if col in city_data.columns:
                        actual_date_col = col
                        break

                # Filter by date range - check both planned and actual dates
                date_filtered = False

                if planned_date_col:
                    # Convert to datetime and filter by planned date range
                    city_data[planned_date_col] = pd.to_datetime(city_data[planned_date_col], errors='coerce')
                    planned_mask = (city_data[planned_date_col] >= start_date) & (city_data[planned_date_col] <= end_date)
                    city_data = city_data[planned_mask]
                    date_filtered = True

                if actual_date_col and not date_filtered:
                    # If no planned date filtering was done, filter by actual date
                    city_data[actual_date_col] = pd.to_datetime(city_data[actual_date_col], errors='coerce')
                    actual_mask = (city_data[actual_date_col] >= start_date) & (city_data[actual_date_col] <= end_date)
                    city_data = city_data[actual_mask]
                    date_filtered = True

                # If we have valid data after filtering
                if date_filtered and 'employee_id' in city_data.columns and not city_data.empty:
                    # Remove duplicates based on employee_id for this city
                    city_data = city_data.drop_duplicates(subset=['employee_id'])

                    # Add employee IDs to the active set
                    employee_ids = city_data['employee_id'].astype(str).dropna().unique()
                    active_ids.update(employee_ids)

                    print(f"Found {len(employee_ids)} active employees in {city} for date range {start_date.date()} to {end_date.date()}")

            except Exception as e:
                # Just log the error without showing it to the user
                import traceback
                print(f"Error processing {city} sheet: {str(e)}")
                print(f"Error details for {city}: {traceback.format_exc()}")
                continue

        print(f"Total active employees found across all cities: {len(active_ids)}")
        return active_ids

    def check_inactive_riders(self, start_date_str, end_date_str):
        """Main function to check for inactive riders in the given date range."""
        try:
            # Convert string dates to datetime objects
            start_date = pd.to_datetime(start_date_str)
            end_date = pd.to_datetime(end_date_str)

            # Get all employees from the all sheet
            with st.spinner("Fetching employee data..."):
                all_employees = self.get_all_employees()
                if all_employees is None:
                    st.error("Failed to fetch employee data")
                    return None

            # Get active employees from city sheets
            with st.spinner("Checking active employees..."):
                active_ids = self.get_active_employees(start_date, end_date)

                all_ids = set(all_employees['employee_id'].dropna().unique())
                inactive_ids = all_ids - active_ids

            # Create DataFrame with inactive employees
            inactive_df = all_employees[all_employees['employee_id'].isin(inactive_ids)]

            # Define output columns with friendly names - reordered to match requirements
            output_columns = {
                'employee_id': 'Employee ID',
                'full_name': 'Employee Name',
                'contract_name': 'Contract Name',
                'city': 'City'
            }

            # Check if all required columns exist in the data
            missing_cols = []
            for col in output_columns.keys():
                if col not in inactive_df.columns:
                    missing_cols.append(col)

            if missing_cols:
                st.error(f"Required columns not found in employee data: {', '.join(missing_cols)}")

                # Try to use available columns instead
                available_cols = [col for col in output_columns.keys() if col in inactive_df.columns]
                if available_cols:
                    st.warning(f"Using available columns: {', '.join(available_cols)}")
                    result_df = inactive_df[available_cols].rename(columns={col: output_columns[col] for col in available_cols})
                    return result_df
                return None

            # Create final result DataFrame with renamed columns
            result_df = inactive_df[list(output_columns.keys())].rename(columns=output_columns)
            return result_df

        except Exception as e:
            st.error(f"Error checking inactive riders: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            return None

    def display_results(self, results_df, show_messages=True, source="sheets"):
        """
        Display the results without filtering options.

        Parameters:
        - results_df: DataFrame containing the results
        - show_messages: Whether to show success messages
        - source: Source of the data ('sheets' or 'csv') to use for unique keys
        """
        if results_df is None or results_df.empty:
            st.info("No inactive riders found for the selected date range")
            return

        st.markdown("## Inactive Riders Report")

        # Only show success message if show_messages is True
        if show_messages:
            st.success(f"Found {len(results_df)} inactive riders")

        # Use the original dataframe directly
        filtered_df = results_df.copy()

        # Display the filtered dataframe
        display_df = filtered_df.copy()

        # Ensure the Employee Name column is present
        if 'Employee Name' not in display_df.columns and 'name' in display_df.columns:
            display_df['Employee Name'] = display_df['name']

        # Reorder columns to ensure Employee ID, Employee Name, Contract Name, City order
        desired_columns = ['Employee ID', 'Employee Name', 'Contract Name', 'City']
        available_columns = [col for col in desired_columns if col in display_df.columns]
        other_columns = [col for col in display_df.columns if col not in desired_columns]

        # Only include columns that exist
        final_columns = [col for col in available_columns + other_columns if col in display_df.columns]
        if final_columns:  # Make sure we have columns to display
            display_df = display_df[final_columns]

        # Display the dataframe
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Add download button if there's data
        if not display_df.empty:
            csv = display_df.to_csv(index=False)
            # Use different keys based on the source
            download_key = f"download_inactive_riders_{source}"
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="inactive_riders_report.csv",
                mime="text/csv",
                key=download_key
            )

    def send_email_alerts(self, results_df):
        """Send email alerts grouped by contract name."""
        # TODO: Implement email functionality
        if results_df is not None and not results_df.empty:
            st.info(f"Email alert functionality would send notifications about {len(results_df)} inactive riders")
        else:
            st.info("No inactive riders to send alerts for")

    def process_uploaded_files(self, uploaded_files, selected_dates):
        """Process uploaded CSV files and combine them into a single DataFrame."""
        try:
            all_dfs = []
            for file in uploaded_files:
                # Read the CSV file
                df = pd.read_csv(file)

                # Standardize column names
                df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]

                # Add city information from filename
                city_name = file.name.split('.')[0]
                df['city'] = city_name

                # Filter out invalid shift statuses (NO_SHOW statuses)
                if 'shift_status' in df.columns:
                    df = df[~df['shift_status'].str.contains('NO_SHOW', na=False, case=False)]

                # Drop unnecessary columns if they exist
                columns_to_drop = [
                    'shift_id', 'employee_name', 'starting_point_id',
                    'starting_point', 'shift_tag', 'planned_duration',
                    'actual_duration'
                ]
                df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')

                # Convert date columns to datetime
                date_columns = ['planned_start_date', 'actual_start_date']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')

                # Filter for selected dates - both planned and actual dates should be in range
                if 'planned_start_date' in df.columns and 'actual_start_date' in df.columns:
                    mask = (
                        df['planned_start_date'].dt.date.isin(selected_dates) &
                        df['actual_start_date'].dt.date.isin(selected_dates)
                    )
                    df = df[mask]
                elif 'planned_start_date' in df.columns:
                    mask = df['planned_start_date'].dt.date.isin(selected_dates)
                    df = df[mask]
                elif 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    mask = df['date'].dt.date.isin(selected_dates)
                    df = df[mask]

                # Ensure employee_id is a string
                if 'employee_id' in df.columns:
                    df['employee_id'] = df['employee_id'].astype(str)

                    # Remove duplicates based on employee_id
                    df = df.drop_duplicates(subset=['employee_id'])

                    all_dfs.append(df)

            if not all_dfs:
                st.error("No valid data found in uploaded files")
                return None

            # Combine all DataFrames
            combined_df = pd.concat(all_dfs, ignore_index=True)
            return combined_df

        except Exception as e:
            st.error(f"Error processing uploaded files: {str(e)}")
            return None

    def process_inactive_riders(self, combined_df):
        """Process the combined data to find inactive riders."""
        try:
            if combined_df is None or combined_df.empty:
                return None

            # Get all employees from the all sheet
            with st.spinner("Fetching employee data..."):
                all_employees = self.get_all_employees()
                if all_employees is None:
                    return None

            # Get active employees from the combined data
            active_ids = set(combined_df['employee_id'].astype(str).dropna().unique())

            # Get all employee IDs from the all sheet
            all_ids = set(all_employees['employee_id'].astype(str).dropna().unique())

            # Find inactive IDs (those in all_ids but not in active_ids)
            inactive_ids = all_ids - active_ids

            # Get inactive employees data
            inactive_df = all_employees[all_employees['employee_id'].isin(inactive_ids)]

            # Prepare output columns - reordered to match requirements
            output_columns = {
                'employee_id': 'Employee ID',
                'full_name': 'Employee Name',
                'contract_name': 'Contract Name',
                'city': 'City'
            }

            # Check if all required columns exist
            missing_cols = []
            for col in output_columns.keys():
                if col not in inactive_df.columns:
                    missing_cols.append(col)

            if missing_cols:
                # Try to use available columns instead
                available_cols = [col for col in output_columns.keys() if col in inactive_df.columns]
                if available_cols:
                    result_df = inactive_df[available_cols].rename(columns={col: output_columns[col] for col in available_cols})
                    return result_df
                return None

            # Create final result DataFrame
            result_df = inactive_df[list(output_columns.keys())].rename(columns=output_columns)
            return result_df

        except Exception as e:
            print(f"Error processing inactive riders: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            return None


