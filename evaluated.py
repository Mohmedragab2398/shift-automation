import streamlit as st
import pandas as pd
from datetime import datetime
from sheets_connector import SheetsConnector
import traceback

class EvaluatedProcessor:
    def __init__(self):
        """Initialize the Evaluated Processor with necessary configurations."""
        self.sheets_connector = SheetsConnector()
        self.spreadsheet_id = st.secrets["spreadsheet_id"]  # Use the spreadsheet ID from secrets.toml
        self.cities = ['Assiut', 'Beni Suef', 'Hurghada', 'Ismailia', 'Minya', 'Port Said', 'Suez']

        # Mapping for starting points to cities
        self.starting_point_to_city = {
            'Assiut SP': 'Assiut',
            'Old beni suef': 'Beni Suef',
            'Hurghada downtown sp': 'Hurghada',
            'Sheraton road sp': 'Hurghada',
            'Al dahar sp': 'Hurghada',
            'Ismalia downtown': 'Ismailia',
            'Old minya sp': 'Minya',
            'New minya sp': 'Minya',
            'Port fouad sp': 'Port Said',
            'Portsaid sp': 'Port Said',
            'Suez': 'Suez',
            'Faisal sp': 'Suez'
        }

        # Standard contract names (canonical forms)
        self.contract_names = [
            'Al Abtal',
            'Al Alamia',
            'Ebad El rahman',
            'El Tohami',
            'MTA',
            'Stop Car',
            'Tanta Car',  # Standardized to this form
            'Tanta',      # Added as a separate contract from Tantawy
            'Tantawy',
            'Team mh for Delivery',
            'Wasaly',
            'Zero Zero Seven'
        ]

        # Equipment types to exclude from contract names
        self.equipment_types = ['BC', 'WLK']

        # Contract name normalization mapping - all variations map to standard names
        self.contract_name_mapping = {
            # Al Abtal variations
            'AL ABTAL': 'Al Abtal',
            'EL ABTAL': 'Al Abtal',
            'ALABTAL': 'Al Abtal',

            # Al Alamia variations
            'AL ALAMIA': 'Al Alamia',
            'ELALAMIA': 'Al Alamia',
            'ALAMIA': 'Al Alamia',
            'ALALAMIA': 'Al Alamia',
            'AL ALMIA': 'Al Alamia',

            # Ebad El rahman variations
            'EBAD EL RAHMAN': 'Ebad El rahman',
            'EBADELRAHMAN': 'Ebad El rahman',
            'EBAD ELRAHMAN': 'Ebad El rahman',
            'ELRAHMAN': 'Ebad El rahman',

            # El Tohami variations
            'EL TOHAMI': 'El Tohami',
            'ELTOHAMI': 'El Tohami',
            'ELTOHAMY': 'El Tohami',
            'TOHAMI': 'El Tohami',

            # MTA variations
            'MTA': 'MTA',
            'M.T.A': 'MTA',
            'M T A': 'MTA',

            # Stop Car variations
            'STOP CAR': 'Stop Car',
            'STOPCAR': 'Stop Car',
            'STOP': 'Stop Car',

            # Tanta Car variations - standardize all to Tanta Car
            'TANTA CAR': 'Tanta Car',
            'TANTACAR': 'Tanta Car',
            'TAN CAR': 'Tanta Car',
            'TANCAR': 'Tanta Car',

            # Tanta variations (all map to Tantawy since Tanta is Tantawy)
            'TANTA': 'Tantawy',

            # Tantawy variations
            'TANTAWY': 'Tantawy',

            # Team mh for Delivery variations
            'TEAM MH FOR DELIVERY': 'Team mh for Delivery',
            'TEAM MH': 'Team mh for Delivery',
            'TEAMMH': 'Team mh for Delivery',

            # Wasaly variations
            'WASALY': 'Wasaly',

            # Zero Zero Seven variations
            'ZERO ZERO SEVEN': 'Zero Zero Seven',
            '007': 'Zero Zero Seven',
            'ZEROZERO7': 'Zero Zero Seven',
            'ZERO ZERO 7': 'Zero Zero Seven',

            # Equipment types - map to None so they're not treated as contract names
            'BC': None,
            'WLK': None
        }

        # Contract to cities mapping (for reference)
        self.contract_to_cities = {
            'Al Abtal': ['Hurghada', 'Port Said'],
            'Al Alamia': ['Ismailia', 'Port Said', 'Suez'],
            'Ebad El rahman': ['Hurghada', 'Minya'],
            'El Tohami': ['Assiut', 'Beni Suef', 'Hurghada', 'Minya', 'Suez'],
            'MTA': ['Hurghada', 'Port Said'],
            'Stop Car': ['Hurghada', 'Beni Suef', 'Ismailia', 'Port Said', 'Suez'],
            'Tanta Car': ['Ismailia', 'Port Said', 'Suez'],  # Tanta Car operates in these cities
            'Tantawy': ['Assiut', 'Hurghada', 'Ismailia', 'Port Said', 'Suez'],  # Tanta is Tantawy
            'Team mh for Delivery': ['Hurghada', 'Suez'],
            'Wasaly': ['Assiut'],
            'Zero Zero Seven': ['Assiut', 'Hurghada']
        }

    def get_all_employees(self):
        """Get all employees from the all2 sheet with standardized columns."""
        try:
            # Use the get_all_sheet_data method which is more reliable
            all_data = self.sheets_connector.get_all_sheet_data()

            # Check if data is None, empty, or only contains headers
            if all_data is None or all_data.empty or len(all_data) <= 1:
                st.error("No data found or insufficient data in all2 sheet")
                return None

            # Standardize column names
            all_data.columns = [str(col).strip().lower().replace(' ', '_') for col in all_data.columns]

            # Ensure required columns exist
            required_cols = ['employee_id', 'full_name', 'contract_name', 'city']
            missing_cols = [col for col in required_cols if col not in all_data.columns]

            if missing_cols:
                # Try to find alternative column names
                if 'employee_id' in missing_cols and 'id' in all_data.columns:
                    all_data['employee_id'] = all_data['id']
                    missing_cols.remove('employee_id')

                if 'full_name' in missing_cols and 'employee_name' in all_data.columns:
                    all_data['full_name'] = all_data['employee_name']
                    missing_cols.remove('full_name')

                # If still missing columns, report error
                if missing_cols:
                    st.error(f"Required columns not found in employee data: {', '.join(missing_cols)}")
                    return None

            # Clean and normalize data
            all_data = all_data.dropna(subset=['employee_id'])
            all_data['employee_id'] = all_data['employee_id'].astype(str).str.strip()

            return all_data
        except Exception as e:
            st.error(f"Error fetching employee data: {str(e)}")
            return None

    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files (Excel or CSV) and combine them into a single DataFrame."""
        try:
            all_dfs = []
            first_file = True

            for file in uploaded_files:
                try:
                    # Determine file type from extension
                    file_extension = file.name.split('.')[-1].lower()

                    # Read the file based on its extension
                    if file_extension == 'csv':
                        # Try different encodings for CSV files
                        try:
                            df = pd.read_csv(file, encoding='utf-8')
                        except UnicodeDecodeError:
                            try:
                                df = pd.read_csv(file, encoding='latin1')
                            except:
                                df = pd.read_csv(file, encoding='cp1252')
                    else:
                        # Read Excel file
                        df = pd.read_excel(file)

                    # Standardize column names
                    df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]

                    # Convert date columns to datetime
                    date_cols = ['planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date']
                    for col in date_cols:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors='coerce')

                    # Add city information from filename
                    city_name = file.name.split('.')[0].capitalize()
                    df['city_from_file'] = city_name

                    # Add to list of dataframes (skip header for all files after the first)
                    if not first_file:
                        # Skip the header row for all files after the first one
                        df = df.iloc[1:].reset_index(drop=True)
                    else:
                        first_file = False

                    all_dfs.append(df)

                except Exception as e:
                    st.error(f"Error processing file {file.name}: {str(e)}")
                    st.error(f"Traceback: {traceback.format_exc()}")
                    continue

            if not all_dfs:
                st.error("No valid data found in uploaded files")
                return None

            # Combine all DataFrames
            combined_df = pd.concat(all_dfs, ignore_index=True)

            # Keep only the specified columns
            columns_to_keep = [
                'employee_id', 'employee_name', 'starting_point', 'shift_status',
                'planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date',
                'city_from_file'  # Keep this for later use
            ]

            # Only keep columns that exist
            columns_to_keep = [col for col in columns_to_keep if col in combined_df.columns]

            # If any required columns are missing, report them
            required_cols = ['employee_id', 'employee_name', 'shift_status', 'planned_start_date', 'actual_start_date']
            missing_cols = [col for col in required_cols if col not in combined_df.columns]
            if missing_cols:
                st.error(f"Missing required columns in uploaded files: {', '.join(missing_cols)}")
                st.error("Please ensure all files have the required columns.")
                return None

            # Keep only the specified columns
            combined_df = combined_df[columns_to_keep]

            return combined_df

        except Exception as e:
            st.error(f"Error processing uploaded files: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            return None

    def filter_by_dates(self, df, selected_planned_dates, selected_actual_dates):
        """
        Filter the DataFrame by selected planned and actual dates.
        Keep rows with dates in the selected values and blank rows.
        """
        if df is None or df.empty:
            return None

        try:
            # Create a copy to avoid modifying the original
            filtered_df = df.copy()

            # Ensure date columns are datetime type
            date_cols = ['planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date']
            for col in date_cols:
                if col in filtered_df.columns:
                    # Convert to datetime if not already
                    if not pd.api.types.is_datetime64_any_dtype(filtered_df[col]):
                        filtered_df[col] = pd.to_datetime(filtered_df[col], errors='coerce')

            # Create combined mask for filtering
            keep_rows = pd.Series(True, index=filtered_df.index)

            # Filter by planned dates if selected
            if selected_planned_dates and 'planned_start_date' in filtered_df.columns:
                # Create a mask for planned dates (keep NaN values)
                planned_mask = filtered_df['planned_start_date'].isna()

                # Add each date to the mask
                for date in selected_planned_dates:
                    # Convert date to pandas Timestamp for comparison
                    pd_date = pd.Timestamp(date)
                    # Add condition for this date (comparing only the date part)
                    date_match = filtered_df['planned_start_date'].dt.date == pd_date.date()
                    # Update mask with OR condition
                    planned_mask = planned_mask | date_match

                # Update the combined mask
                keep_rows = keep_rows & planned_mask

            # Filter by actual dates if selected
            if selected_actual_dates and 'actual_start_date' in filtered_df.columns:
                # Create a mask for actual dates (keep NaN values)
                actual_mask = filtered_df['actual_start_date'].isna()

                # Add each date to the mask
                for date in selected_actual_dates:
                    # Convert date to pandas Timestamp for comparison
                    pd_date = pd.Timestamp(date)
                    # Add condition for this date (comparing only the date part)
                    date_match = filtered_df['actual_start_date'].dt.date == pd_date.date()
                    # Update mask with OR condition
                    actual_mask = actual_mask | date_match

                # Update the combined mask
                keep_rows = keep_rows & actual_mask

            # Apply the combined mask
            filtered_df = filtered_df[keep_rows]

            # Log the filtering results
            st.info(f"Filtered from {len(df)} to {len(filtered_df)} rows based on selected dates")

            return filtered_df

        except Exception as e:
            st.error(f"Error filtering by dates: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            return None

    def extract_contract_from_name(self, employee_name):
        """Extract contract name from employee name (after underscore)."""
        if pd.isna(employee_name) or not isinstance(employee_name, str):
            return None

        # Try to extract contract name after underscore
        if '_' in employee_name:
            parts = employee_name.split('_')
            if len(parts) > 1:
                # Get the part after the first underscore
                contract_part = parts[1].strip()

                # Check if this part contains BC or WLK and remove them
                if 'BC' in contract_part or 'WLK' in contract_part:
                    # Remove BC and WLK from the contract part
                    contract_part = contract_part.replace('_BC', '').replace('BC', '')
                    contract_part = contract_part.replace('_WLK', '').replace('WLK', '')
                    contract_part = contract_part.strip('_').strip()

                # If we have multiple underscores, check all parts for a valid contract name
                if not contract_part and len(parts) > 2:
                    for i in range(1, len(parts)):
                        potential_contract = parts[i].strip()
                        # Skip BC and WLK
                        if potential_contract in ['BC', 'WLK', '_BC', '_WLK']:
                            continue
                        # Remove BC and WLK if they're part of the string
                        potential_contract = potential_contract.replace('_BC', '').replace('BC', '')
                        potential_contract = potential_contract.replace('_WLK', '').replace('WLK', '')
                        potential_contract = potential_contract.strip('_').strip()
                        if potential_contract:
                            contract_part = potential_contract
                            break

                # First try direct lookup in our mapping
                if contract_part in self.contract_name_mapping:
                    return self.contract_name_mapping[contract_part]

                # Try case-insensitive lookup
                contract_part_upper = contract_part.upper()
                if contract_part_upper in self.contract_name_mapping:
                    return self.contract_name_mapping[contract_part_upper]

                # Special handling for TANTA (should be Tantawy)
                if contract_part_upper == 'TANTA':
                    return 'Tantawy'

                # Try partial matching
                for pattern, normalized in self.contract_name_mapping.items():
                    if pattern and normalized and pattern.upper() in contract_part_upper:
                        return normalized

                # Special handling for common contract patterns
                if 'STOP' in contract_part_upper:
                    return 'Stop Car'
                if 'MTA' in contract_part_upper:
                    return 'MTA'
                if 'TOHAMI' in contract_part_upper or 'TOHAMY' in contract_part_upper:
                    return 'El Tohami'

                # If still no match, return one of our standard contract names if it's contained
                for contract_name in self.contract_names:
                    if contract_name.upper() in contract_part_upper or contract_part_upper in contract_name.upper():
                        return contract_name

                # Return as is if no match found but not if it's BC or WLK
                if contract_part.upper() not in ['BC', 'WLK']:
                    return contract_part

        # If no underscore, try to find any contract name in the employee name
        employee_name_upper = employee_name.upper()

        # Try direct lookup in our mapping
        if employee_name in self.contract_name_mapping:
            return self.contract_name_mapping[employee_name]

        # Try case-insensitive lookup
        if employee_name_upper in self.contract_name_mapping:
            return self.contract_name_mapping[employee_name_upper]

        # Try partial matching
        for pattern, normalized in self.contract_name_mapping.items():
            if pattern.upper() in employee_name_upper:
                return normalized

        for contract_name in self.contract_names:
            if contract_name.upper() in employee_name_upper:
                return contract_name

        # Don't return BC or WLK as contract names
        if employee_name_upper in ['BC', 'WLK']:
            return None

        return None

    def map_city_from_starting_point(self, starting_point):
        """Map starting point to city using the predefined mapping."""
        if pd.isna(starting_point) or not isinstance(starting_point, str):
            return None

        # Normalize the starting point string
        starting_point = starting_point.strip().lower()

        # Check against each key in the mapping
        for sp, city in self.starting_point_to_city.items():
            if sp.lower() in starting_point:
                return city

        # Try more flexible matching if exact match not found
        if 'assiut' in starting_point:
            return 'Assiut'
        elif 'beni' in starting_point or 'suef' in starting_point:
            return 'Beni Suef'
        elif 'hurghada' in starting_point or 'sheraton' in starting_point or 'dahar' in starting_point:
            return 'Hurghada'
        elif 'isma' in starting_point:
            return 'Ismailia'
        elif 'minya' in starting_point:
            return 'Minya'
        elif 'port' in starting_point or 'fouad' in starting_point:
            return 'Port Said'
        elif 'suez' in starting_point or 'faisal' in starting_point:
            return 'Suez'

        return None

    def normalize_contract_name(self, contract_name):
        """Normalize contract name to standard form."""
        if pd.isna(contract_name) or not isinstance(contract_name, str):
            return None

        # Convert to uppercase for case-insensitive comparison
        contract_upper = contract_name.upper().strip()

        # Check if it's in our mapping
        if contract_upper in self.contract_name_mapping:
            return self.contract_name_mapping[contract_upper]

        # Special handling for Tanta Car vs Tantawy (Tanta is Tantawy)
        if 'TANTA' in contract_upper:
            if 'CAR' in contract_upper:
                return 'Tanta Car'
            else:
                # All other TANTA variations map to Tantawy (since Tanta is Tantawy)
                return 'Tantawy'

        # Check for TAN CAR and TANCAR variations - be more specific to avoid false matches
        if ('TAN CAR' in contract_upper or 'TANCAR' in contract_upper):
            return 'Tanta Car'

        # Check for partial matches
        for pattern, normalized in self.contract_name_mapping.items():
            if pattern.upper() in contract_upper or contract_upper in pattern.upper():
                return normalized

        # Return as is if no match found
        return contract_name

    def normalize_city_name(self, city):
        """Normalize city name to standard form to prevent duplicates."""
        if pd.isna(city) or not isinstance(city, str):
            return None

        # Convert to title case and strip whitespace
        normalized = city.strip().title()

        # Handle specific city name variations
        city_mappings = {
            'Port Said': 'Port Said',
            'Port said': 'Port Said',
            'PORT SAID': 'Port Said',
            'Portsaid': 'Port Said',
            'Ismailia': 'Ismailia',
            'Ismalia': 'Ismailia',  # Common misspelling
            'ISMAILIA': 'Ismailia',
            'ISMALIA': 'Ismailia',  # Another misspelling
            'Beni Suef': 'Beni Suef',
            'Beni suef': 'Beni Suef',
            'BENI SUEF': 'Beni Suef',
            'Assiut': 'Assiut',
            'ASSIUT': 'Assiut',
            'Hurghada': 'Hurghada',
            'HURGHADA': 'Hurghada',
            'Minya': 'Minya',
            'MINYA': 'Minya',
            'Suez': 'Suez',
            'SUEZ': 'Suez'
        }

        return city_mappings.get(normalized, normalized)

    def is_valid_contract_city(self, contract_name, city):
        """Check if a contract operates in a given city based on the contract_to_cities mapping."""
        if pd.isna(contract_name) or pd.isna(city):
            return False

        # Normalize contract name and city for comparison
        normalized_contract = self.normalize_contract_name(contract_name)
        normalized_city = self.normalize_city_name(city)

        # Check if the contract exists in our mapping
        if normalized_contract in self.contract_to_cities:
            # Check if the city is in the list of cities for this contract
            return normalized_city in self.contract_to_cities[normalized_contract]

        # If contract not in mapping, return False
        return False

    def add_contract_and_city(self, df, employee_data):
        """Add contract name and city columns using vlookup logic from master data."""
        if df is None or df.empty:
            return None

        try:
            # Create a copy to avoid modifying the original
            result_df = df.copy()

            # Add debugging info
            print(f"Processing {len(result_df)} records for contract and city assignment")

            # PRIORITY 1: Extract contract name from employee name FIRST (more reliable)
            if 'employee_name' in result_df.columns:
                result_df['contract_from_name'] = result_df['employee_name'].apply(
                    self.extract_contract_from_name
                )
                # Use this as the primary contract name
                result_df['contract_name'] = result_df['contract_from_name']

                # Count how many we got from names
                name_contracts = result_df['contract_from_name'].notna().sum()
                print(f"Extracted contract names from {name_contracts} employee names")

            # PRIORITY 2: For missing contract names, try vlookup from Google Sheets
            if employee_data is not None and not employee_data.empty:
                print(f"Google Sheets employee data has {len(employee_data)} records")
                print(f"Sample employee IDs from Google Sheets: {list(employee_data['employee_id'].head())}")
                print(f"Sample employee IDs from shift data: {list(result_df['employee_id'].head())}")

                # Ensure both are strings for proper matching and remove any leading zeros
                employee_data['employee_id'] = employee_data['employee_id'].astype(str).str.strip().str.lstrip('0')
                result_df['employee_id'] = result_df['employee_id'].astype(str).str.strip().str.lstrip('0')

                # Also try without leading zero removal for backup matching
                employee_data['employee_id_original'] = employee_data['employee_id'].astype(str).str.strip()
                result_df['employee_id_original'] = result_df['employee_id'].astype(str).str.strip()

                emp_contract_dict = dict(zip(employee_data['employee_id'], employee_data['contract_name']))
                emp_city_dict = dict(zip(employee_data['employee_id'], employee_data['city']))

                print(f"Created lookup dictionaries with {len(emp_contract_dict)} contract entries and {len(emp_city_dict)} city entries")

                # Only use vlookup for missing contract names
                mask = result_df['contract_name'].isna()
                if mask.any():
                    print(f"Trying to lookup {mask.sum()} missing contract names")
                    result_df.loc[mask, 'contract_name'] = result_df.loc[mask, 'employee_id'].map(emp_contract_dict)
                    vlookup_contracts = result_df.loc[mask, 'contract_name'].notna().sum()
                    print(f"Added {vlookup_contracts} contract names from Google Sheets vlookup")

                # Add city using vlookup (primary method for city)
                print(f"Trying to lookup cities for all {len(result_df)} records")
                result_df['city'] = result_df['employee_id'].map(emp_city_dict)
                vlookup_cities = result_df['city'].notna().sum()
                print(f"Added {vlookup_cities} cities from Google Sheets vlookup")

                # Normalize cities from Google Sheets
                result_df['city'] = result_df['city'].apply(self.normalize_city_name)

            # Normalize all contract names to ensure consistency
            result_df['contract_name'] = result_df['contract_name'].apply(self.normalize_contract_name)

            # Show contract distribution AFTER normalization
            print("Contract distribution (after normalization):")
            contract_counts = result_df['contract_name'].value_counts()
            for contract, count in contract_counts.items():
                print(f"  {contract}: {count}")

            # For missing cities, try to map from starting point
            mask = result_df['city'].isna()
            if mask.any() and 'starting_point' in result_df.columns:
                result_df.loc[mask, 'city'] = result_df.loc[mask, 'starting_point'].apply(
                    self.map_city_from_starting_point
                )
                sp_cities = result_df.loc[mask, 'city'].notna().sum()
                print(f"Added {sp_cities} cities from starting point mapping")

            # If city is still missing, use city from file
            mask = result_df['city'].isna()
            if mask.any() and 'city_from_file' in result_df.columns:
                result_df.loc[mask, 'city'] = result_df.loc[mask, 'city_from_file']
                file_cities = result_df.loc[mask, 'city'].notna().sum()
                print(f"Added {file_cities} cities from file names")

            # Normalize all cities to prevent duplicates
            result_df['city'] = result_df['city'].apply(self.normalize_city_name)

            # Final statistics
            final_contracts = result_df['contract_name'].notna().sum()
            final_cities = result_df['city'].notna().sum()
            print(f"Final result: {final_contracts} records with contract names, {final_cities} records with cities")



            return result_df

        except Exception as e:
            st.error(f"Error adding contract and city: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            return None

    def remove_duplicates(self, df):
        """Remove duplicate employees based on employee_id."""
        if df is None or df.empty:
            return None

        try:
            # Drop duplicates based on employee_id
            result_df = df.drop_duplicates(subset=['employee_id'])
            return result_df

        except Exception as e:
            st.error(f"Error removing duplicates: {str(e)}")
            return None

    def generate_pivot_summary(self, df, date):
        """Generate a pivot table summary for the given date."""
        if df is None or df.empty:
            return None

        try:
            # Get data for the specific date using our helper method
            date_df = self.get_data_for_date(df, date)

            if date_df is None or date_df.empty:
                return None

            # Make a copy to avoid modifying the original
            date_df = date_df.copy()

            # Normalize contract names to ensure consistency
            date_df['contract_name'] = date_df['contract_name'].apply(self.normalize_contract_name)

            # Filter out invalid contract-city combinations
            print(f"Before contract-city validation: {len(date_df)} records")

            valid_rows = []
            invalid_combinations = []

            for idx, row in date_df.iterrows():
                if self.is_valid_contract_city(row['contract_name'], row['city']):
                    valid_rows.append(idx)
                else:
                    invalid_combinations.append(f"{row['contract_name']} in {row['city']}")

            # Keep only valid contract-city combinations
            date_df = date_df.loc[valid_rows]

            print(f"After contract-city validation: {len(date_df)} records")
            if invalid_combinations:
                print(f"Filtered out {len(invalid_combinations)} invalid contract-city combinations:")
                for combo in set(invalid_combinations):  # Remove duplicates
                    print(f"  - {combo}")

            if date_df.empty:
                st.warning("No valid contract-city combinations found after filtering")
                return None

            # Create pivot table
            pivot_df = pd.pivot_table(
                date_df,
                index='contract_name',
                columns='city',
                values='employee_id',
                aggfunc='count',
                fill_value=0
            ).reset_index()

            # Add a total column
            pivot_df['Total'] = pivot_df.iloc[:, 1:].sum(axis=1)

            return pivot_df

        except Exception as e:
            st.error(f"Error generating pivot summary: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_data_for_date(self, df, date):
        """Get all data for a specific date."""
        if df is None or df.empty:
            return None

        try:
            # Convert input date to pandas Timestamp for comparison
            pd_date = pd.Timestamp(date)

            # Create mask for planned date matching (we're only using planned dates now)
            planned_date_mask = False

            # Check if planned_start_date column exists and create mask
            if 'planned_start_date' in df.columns:
                # Ensure it's datetime type
                if not pd.api.types.is_datetime64_any_dtype(df['planned_start_date']):
                    df['planned_start_date'] = pd.to_datetime(df['planned_start_date'], errors='coerce')
                # Create mask for matching dates
                planned_date_mask = df['planned_start_date'].dt.date == pd_date.date()

            # Filter data for the specific date
            date_df = df[planned_date_mask].copy()

            # Ensure shift_status is a string
            if 'shift_status' in date_df.columns:
                date_df['shift_status'] = date_df['shift_status'].astype(str)

            return date_df

        except Exception as e:
            st.error(f"Error getting data for date: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            return None

    def generate_pivot_for_status(self, df, status):
        """Generate a pivot table for a specific shift status."""
        if df is None or df.empty:
            return None

        try:
            # Make a copy to avoid modifying the original
            df_copy = df.copy()

            # Normalize contract names to ensure consistency
            df_copy['contract_name'] = df_copy['contract_name'].apply(self.normalize_contract_name)

            # Filter out invalid contract-city combinations
            valid_rows = []
            for idx, row in df_copy.iterrows():
                if self.is_valid_contract_city(row['contract_name'], row['city']):
                    valid_rows.append(idx)

            # Keep only valid contract-city combinations
            df_copy = df_copy.loc[valid_rows]

            if df_copy.empty:
                return None

            # Create pivot table
            pivot_df = pd.pivot_table(
                df_copy,
                index='contract_name',
                columns='city',
                values='employee_id',
                aggfunc='count',
                fill_value=0
            ).reset_index()

            # Add a total column
            pivot_df['Total'] = pivot_df.iloc[:, 1:].sum(axis=1)

            return pivot_df

        except Exception as e:
            st.error(f"Error generating pivot for status {status}: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            return None

    def generate_no_show_summary(self, df, date):
        """Generate a summary of no-show employees for the given date."""
        if df is None or df.empty:
            return None

        try:
            # Get data for the specific date
            date_df = self.get_data_for_date(df, date)

            if date_df is None or date_df.empty:
                return None

            # Filter for no-show statuses
            no_show_statuses = ["NO-SHOW", "NO_SHOW", "NO_SHOW(UNEXCUSED)"]

            # Check if shift_status column exists
            if 'shift_status' not in date_df.columns:
                return pd.DataFrame(columns=['contract_name', 'city', 'no_show_count'])

            # Handle potential non-string values in shift_status
            date_df['shift_status'] = date_df['shift_status'].astype(str)

            # Filter for no-show statuses
            no_show_df = date_df[date_df['shift_status'].str.contains('|'.join(no_show_statuses), case=False, na=False)]

            if no_show_df.empty:
                return pd.DataFrame(columns=['contract_name', 'city', 'no_show_count'])

            # Normalize contract names to ensure consistency
            no_show_df['contract_name'] = no_show_df['contract_name'].apply(self.normalize_contract_name)

            # Filter out invalid contract-city combinations
            valid_rows = []
            for idx, row in no_show_df.iterrows():
                if self.is_valid_contract_city(row['contract_name'], row['city']):
                    valid_rows.append(idx)

            # Keep only valid contract-city combinations
            no_show_df = no_show_df.loc[valid_rows]

            if no_show_df.empty:
                return pd.DataFrame(columns=['contract_name', 'city', 'no_show_count'])

            # Create pivot table for no-shows
            pivot_df = pd.pivot_table(
                no_show_df,
                index='contract_name',
                columns='city',
                values='employee_id',
                aggfunc='count',
                fill_value=0
            ).reset_index()

            # Add a total column
            pivot_df['Total'] = pivot_df.iloc[:, 1:].sum(axis=1)

            return pivot_df

        except Exception as e:
            st.error(f"Error generating no-show summary: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            return None

    def export_debug_data(self, df, date, source="evaluated"):
        """Export detailed debugging data to help identify discrepancies."""
        if df is None or df.empty:
            return

        try:
            # Create detailed debug information
            debug_data = df.copy()

            # Add debugging columns
            debug_data['debug_contract_from_name'] = debug_data['employee_name'].apply(
                self.extract_contract_from_name
            ) if 'employee_name' in debug_data.columns else None

            debug_data['debug_normalized_contract'] = debug_data['contract_name'].apply(
                self.normalize_contract_name
            )

            debug_data['debug_valid_contract_city'] = debug_data.apply(
                lambda row: self.is_valid_contract_city(row['contract_name'], row['city']), axis=1
            )

            # Export to CSV for analysis
            csv = debug_data.to_csv(index=False)
            download_key = f"download_debug_{source}_{date.strftime('%Y%m%d')}"
            st.download_button(
                label=f"📊 Download Debug Data for {date}",
                data=csv,
                file_name=f"debug_evaluation_{date.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=download_key,
                help="Download detailed data for debugging discrepancies"
            )

        except Exception as e:
            print(f"Error creating debug export: {str(e)}")

    def display_results(self, df, date, show_messages=True, source="evaluated"):
        """Display the results for a specific date."""
        if df is None or df.empty:
            st.info(f"No data found for {date}")
            return

        st.markdown(f"## Evaluation Report for {date}")

        # Only show success message if show_messages is True
        if show_messages:
            st.success(f"Found {len(df)} records for {date}")

        # Display the pivot table
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Add download button if there's data
        if not df.empty:
            csv = df.to_csv(index=False)
            # Use different keys based on the date
            download_key = f"download_evaluated_{source}_{date.strftime('%Y%m%d')}"
            st.download_button(
                label=f"Download CSV for {date}",
                data=csv,
                file_name=f"evaluation_report_{date.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=download_key
            )
