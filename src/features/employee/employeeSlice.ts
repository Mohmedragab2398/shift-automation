import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { Employee, EmployeeState } from './types';
import { gapi } from 'gapi-script';

// Initialize Google Sheets API
const initGoogleSheets = async () => {
  try {
    await gapi.client.init({
      apiKey: 'AIzaSyBqQqQqQqQqQqQqQqQqQqQqQqQqQqQqQqQ',
      clientId: '113182195054876303245',
      discoveryDocs: ['https://sheets.googleapis.com/$discovery/rest?version=v4'],
      scope: 'https://www.googleapis.com/auth/spreadsheets'
    });
  } catch (error) {
    console.error('Error initializing Google Sheets:', error);
  }
};

// Load employees from Google Sheets
export const loadEmployees = createAsyncThunk(
  'employees/loadEmployees',
  async (_, { rejectWithValue }) => {
    try {
      await initGoogleSheets();
      const response = await gapi.client.sheets.spreadsheets.values.get({
        spreadsheetId: '1VmWRo_RRM2hxphSrFaZHe8eairN4mTwpw2BYqHuICp4',
        range: 'all!A1:Z'
      });
      return response.result.values.map((row: any[]) => ({
        id: row[0],
        name: row[1],
        position: row[2],
        department: row[3],
        status: row[4]
      }));
    } catch (error) {
      return rejectWithValue('Failed to load employees');
    }
  }
);

// Save employee to Google Sheets
export const saveEmployee = createAsyncThunk(
  'employees/saveEmployee',
  async (employee: Employee, { rejectWithValue }) => {
    try {
      await initGoogleSheets();
      await gapi.client.sheets.spreadsheets.values.append({
        spreadsheetId: '1VmWRo_RRM2hxphSrFaZHe8eairN4mTwpw2BYqHuICp4',
        range: 'all!A1:Z',
        valueInputOption: 'RAW',
        resource: {
          values: [[
            employee.id,
            employee.name,
            employee.position,
            employee.department,
            employee.status
          ]]
        }
      });
      return employee;
    } catch (error) {
      return rejectWithValue('Failed to save employee');
    }
  }
);

// ... existing code ... 