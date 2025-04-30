import pandas as pd
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class SheetsConnector:
    def __init__(self, credentials_path=None):
        """Initialize the Google Sheets connector with service account credentials."""
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials_path = credentials_path
        self.credentials = None
        self.service = None
        if credentials_path:
            self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Sheets API using service account."""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=self.credentials)
        except Exception as e:
            print(f"Warning: Authentication failed: {str(e)}")
            self.service = None

    def read_sheet(self, spreadsheet_id=None, range_name=None, local_file=None):
        """Read data from either Google Sheet or local Excel file."""
        try:
            # Try reading from local file first
            if local_file:
                return pd.read_excel(local_file)
            
            # If no local file, try Google Sheets
            if self.service and spreadsheet_id and range_name:
                sheet = self.service.spreadsheets()
                result = sheet.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                if not values:
                    return pd.DataFrame()
                
                # Convert to DataFrame
                df = pd.DataFrame(values[1:], columns=values[0])
                return df
            
            raise Exception("No valid input source provided")
            
        except Exception as e:
            print(f"Warning: Error reading sheet: {str(e)}")
            return pd.DataFrame()

    def update_sheet(self, spreadsheet_id, range_name, df):
        """Update a Google Sheet with data from a pandas DataFrame."""
        try:
            # Convert DataFrame to values list
            values = [df.columns.tolist()]  # Header row
            values.extend(df.values.tolist())
            
            body = {
                'values': values
            }
            
            # Update the sheet
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return result
            
        except HttpError as e:
            raise Exception(f"Error updating sheet: {str(e)}")

    def append_to_sheet(self, spreadsheet_id, range_name, df):
        """Append data from a pandas DataFrame to a Google Sheet."""
        try:
            # Convert DataFrame to values list
            values = df.values.tolist()
            
            body = {
                'values': values
            }
            
            # Append to the sheet
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return result
            
        except HttpError as e:
            raise Exception(f"Error appending to sheet: {str(e)}")

    def clear_range(self, spreadsheet_id, range_name):
        """Clear a range in a Google Sheet."""
        try:
            result = self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            return result
            
        except HttpError as e:
            raise Exception(f"Error clearing range: {str(e)}")

    def get_sheet_metadata(self, spreadsheet_id):
        """Get metadata about the spreadsheet."""
        try:
            if not self.service:
                return None
                
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            return spreadsheet
            
        except Exception as e:
            print(f"Warning: Error getting metadata: {str(e)}")
            return None

    def create_sheet(self, title):
        """Create a new Google Sheet."""
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            return spreadsheet.get('spreadsheetId')
            
        except HttpError as e:
            raise Exception(f"Error creating sheet: {str(e)}")