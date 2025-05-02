/**************************************[ Settings ]**************************************/
const CONTRACTS = [
  'Al Abtal', 'Al Alamia', 'bad El rahman', 'El Tohami',
  'MTA', 'Stop Car', 'Tanta Car', 'Tantawy',
  'Team mh for Delivery', 'Wasaly', 'Zero Zero Seven'
];

const CITIES = ['Assiut', 'Hurghada', 'Ismalia', 'Minya', 'Port said', 'Suez'];
const DATE_FORMAT = "dd-MMM-yyyy";
const TIME_ZONE = "GMT+2";

/**************************************[ Main Menu ]**************************************/
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🚀 Shifts System")
    .addItem("Generate Report", "showDateRangePicker")
    .addSeparator()
    .addItem("Help", "showHelp")
    .addToUi();
}

/**************************************[ Date Picker UI ]**************************************/
function showDateRangePicker() {
  const html = HtmlService.createHtmlOutput(`
    <div style="padding:20px; text-align:center;">
      <h3>Select Date Range</h3>
      <div style="margin:10px;">
        <label>Start Date:</label>
        <input type="date" id="startDate" required style="padding:5px; width:200px;">
      </div>
      <div style="margin:10px;">
        <label>End Date:</label>
        <input type="date" id="endDate" required style="padding:5px; width:200px;">
      </div>
      <button onclick="handleDates()" 
        style="padding:10px 20px; background:#4285f4; color:white; border:none; border-radius:5px; cursor:pointer;">
        Run
      </button>
    </div>
    <script>
      function handleDates() {
        const start = document.getElementById('startDate').value;
        const end = document.getElementById('endDate').value;
        
        if(!start || !end) {
          alert('Please select both dates');
          return;
        }
        
        google.script.run.processSelectedDates(start, end);
        google.script.host.close();
      }
    </script>
  `).setWidth(450).setHeight(280);
  
  SpreadsheetApp.getUi().showModalDialog(html, "📅 Date Range Selection");
}

/**************************************[ Core Processing ]**************************************/
function processSelectedDates(startDate, endDate) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    // Validate dates
    if (start > end) throw new Error("Start date must be before end date");
    
    // Clear existing sheets except city sheets and 'All' sheet
    clearExistingSheets(ss);
    
    // Process data
    const rawData = prepareRawData(ss);
    if (rawData.length === 0) {
      throw new Error("No valid shift data found in city sheets");
    }
    
    const dates = getDateRange(start, end);
    const masterData = getMasterData(ss);
    if (masterData.length === 0) {
      throw new Error("No employee data found in 'All' sheet");
    }
    
    // Generate daily reports
    dates.forEach(date => {
      const dailyData = processDailyData(rawData, date, masterData);
      createDailySheets(ss, date, dailyData);
    });
    
    // Generate final report
    generateMasterReport(ss, dates, masterData, rawData);
    
    showSuccessNotification(dates);
    
  } catch (error) {
    handleError(error);
  }
}

function clearExistingSheets(ss) {
  const protectedSheets = [...CITIES, 'All'];
  const sheets = ss.getSheets();
  
  // First, collect all sheets to delete
  const sheetsToDelete = sheets.filter(sheet => {
    const sheetName = sheet.getName();
    return !protectedSheets.includes(sheetName) && 
           (sheetName.startsWith('Shifts_') || 
            sheetName.startsWith('Unassigned_') || 
            sheetName === 'Master_Report');
  });
  
  // Then delete them one by one with error handling
  sheetsToDelete.forEach(sheet => {
    try {
      ss.deleteSheet(sheet);
    } catch (error) {
      console.log(`Could not delete sheet ${sheet.getName()}: ${error.message}`);
    }
  });
}

/**************************************[ Data Preparation ]**************************************/
function prepareRawData(ss) {
  let allData = [];
  
  CITIES.forEach(city => {
    const sheet = ss.getSheetByName(city);
    if (!sheet || sheet.getLastRow() < 2) return;
    
    const lastRow = sheet.getLastRow();
    const data = sheet.getRange(2, 1, lastRow - 1, 16).getValues();
    
    data.forEach(row => {
      if (row[1] && isValidShift(row[5])) { // [1] = Employee ID, [5] = Shift Status
        allData.push({
          employeeId: String(row[1]).trim(),
          shiftStatus: String(row[5]).trim(),
          plannedStartDate: row[7], // [7] = Planned Start Date
          plannedStartTime: formatTime(row[9]), // [9] = Planned Start Time
          plannedEndTime: formatTime(row[10]), // [10] = Planned End Time
          city: city
        });
      }
    });
  });
  
  console.log(`Raw data count: ${allData.length}`);
  return allData;
}

function isValidShift(status) {
  if (!status) return false;
  return !/(NO_SHOW|EXCUSED)/i.test(String(status).trim());
}

/**************************************[ Daily Processing ]**************************************/
function processDailyData(rawData, targetDate, masterData) {
  const targetDateStr = Utilities.formatDate(targetDate, TIME_ZONE, "yyyy-MM-dd");
  
  // Get assigned employees for the day
  const assigned = rawData.filter(row => {
    const rowDate = new Date(row.plannedStartDate);
    const rowDateStr = Utilities.formatDate(rowDate, TIME_ZONE, "yyyy-MM-dd");
    return rowDateStr === targetDateStr;
  });
  
  // Get unassigned employees
  const assignedIds = new Set(assigned.map(row => row.employeeId));
  const unassigned = masterData.filter(emp => !assignedIds.has(emp.id));
  
  return { assigned, unassigned };
}

function createDailySheets(ss, date, dailyData) {
  const dateStr = Utilities.formatDate(date, TIME_ZONE, DATE_FORMAT);
  
  // Create Assigned Sheet
  const assignedSheet = ss.insertSheet(`Shifts_${dateStr}`);
  assignedSheet.getRange(1, 1, 1, 5).setValues([['Employee ID', 'Start Time', 'End Time', 'City', 'Status']]);
  if (dailyData.assigned.length > 0) {
    assignedSheet.getRange(2, 1, dailyData.assigned.length, 5).setValues(
      dailyData.assigned.map(row => [
        row.employeeId,
        row.plannedStartTime,
        row.plannedEndTime,
        row.city,
        'Assigned'
      ])
    );
  }
  
  // Create Unassigned Sheet
  const unassignedSheet = ss.insertSheet(`Unassigned_${dateStr}`);
  unassignedSheet.getRange(1, 1, 1, 4).setValues([['Employee ID', 'Name', 'Contract', 'City']]);
  if (dailyData.unassigned.length > 0) {
    unassignedSheet.getRange(2, 1, dailyData.unassigned.length, 4).setValues(
      dailyData.unassigned.map(emp => [emp.id, emp.name, emp.contract, emp.city])
    );
  }
}

/**************************************[ Master Report ]**************************************/
function generateMasterReport(ss, dates, masterData, rawData) {
  const reportSheet = ss.getSheetByName('Master_Report') || ss.insertSheet('Master_Report');
  reportSheet.clear();
  
  // Prepare headers
  const headers = ['Contract', 'City', 'Total Employees'];
  dates.forEach(date => {
    const dateStr = Utilities.formatDate(date, TIME_ZONE, "dd-MMM");
    headers.push(`${dateStr} Assigned`, `${dateStr} Unassigned`, `${dateStr} %`);
  });
  
  reportSheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
  
  // Group data by Contract and City
  const contractMap = new Map();
  
  // Initialize contract map with all contracts and cities
  CONTRACTS.forEach(contract => {
    CITIES.forEach(city => {
      const key = `${contract}_${city}`;
      contractMap.set(key, {
        contract: contract,
        city: city,
        total: 0,
        dates: new Map()
      });
    });
  });
  
  // Count total employees per contract and city
  masterData.forEach(emp => {
    const key = `${emp.contract}_${emp.city}`;
    if (contractMap.has(key)) {
      contractMap.get(key).total++;
    }
  });
  
  // Count assigned employees for each date
  dates.forEach(date => {
    const dateStr = Utilities.formatDate(date, TIME_ZONE, "yyyy-MM-dd");
    const dateData = rawData.filter(row => {
      const rowDate = new Date(row.plannedStartDate);
      return Utilities.formatDate(rowDate, TIME_ZONE, "yyyy-MM-dd") === dateStr;
    });
    
    // Count assignments per contract and city
    dateData.forEach(row => {
      const key = `${row.contract}_${row.city}`;
      if (contractMap.has(key)) {
        const data = contractMap.get(key);
        if (!data.dates.has(dateStr)) {
          data.dates.set(dateStr, { assigned: 0 });
        }
        data.dates.get(dateStr).assigned++;
      }
    });
  });
  
  // Populate data
  let rowIndex = 2;
  contractMap.forEach((value, key) => {
    if (value.total > 0) { // Only include rows with employees
      const row = [value.contract, value.city, value.total];
      
      dates.forEach(date => {
        const dateStr = Utilities.formatDate(date, TIME_ZONE, "yyyy-MM-dd");
        const assigned = value.dates.get(dateStr)?.assigned || 0;
        const unassigned = value.total - assigned;
        const percentage = value.total > 0 ? (assigned / value.total * 100).toFixed(2) + '%' : '0%';
        
        row.push(assigned, unassigned, percentage);
      });
      
      reportSheet.getRange(rowIndex, 1, 1, row.length).setValues([row]);
      rowIndex++;
    }
  });
  
  reportSheet.autoResizeColumns(1, headers.length);
}

/**************************************[ Utilities ]**************************************/
function getDateRange(start, end) {
  const dates = [];
  let current = new Date(start);
  while (current <= end) {
    dates.push(new Date(current));
    current.setDate(current.getDate() + 1);
  }
  return dates;
}

function formatTime(time) {
  try {
    if (!time) return "Invalid Time";
    return Utilities.formatDate(new Date(time), TIME_ZONE, "HH:mm");
  } catch {
    return "Invalid Time";
  }
}

function getMasterData(ss) {
  const sheet = ss.getSheetByName('All');
  if (!sheet || sheet.getLastRow() < 2) return [];
  
  return sheet.getRange(2, 1, sheet.getLastRow() - 1, 4).getValues()
    .map(row => ({
      id: String(row[0]).trim(),
      name: String(row[1]),
      contract: String(row[2]),
      city: String(row[3])
    }));
}

/**************************************[ Notifications ]**************************************/
function showSuccessNotification(dates) {
  const start = Utilities.formatDate(dates[0], TIME_ZONE, DATE_FORMAT);
  const end = Utilities.formatDate(dates[dates.length - 1], TIME_ZONE, DATE_FORMAT);
  
  SpreadsheetApp.getUi().alert(
    '✅ Report Generated',
    `Processed ${dates.length} days\nFrom ${start} to ${end}`,
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

function handleError(error) {
  console.error(error);
  SpreadsheetApp.getUi().alert(
    '🚨 Error',
    error.message || 'Unknown error',
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

function showHelp() {
  const helpText = `User Guide:
1. Select date range from the menu
2. Wait for processing
3. Find results in new sheets:
   - Shifts_Date: Assigned employees
   - Unassigned_Date: Available employees
   - Master_Report: Summary statistics`;
  
  SpreadsheetApp.getUi().alert('Help Center', helpText, SpreadsheetApp.getUi().ButtonSet.OK);
} 