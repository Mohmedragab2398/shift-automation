# Remove existing virtual environment
if (Test-Path ven) {
    Remove-Item -Recurse -Force ven
}

# Create new virtual environment
python -m venv ven

# Activate virtual environment
.\ven\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install all required packages
pip install streamlit==1.31.0
pip install numpy==1.24.0
pip install pandas==2.0.0
pip install plotly==5.18.0
pip install openpyxl==3.1.0
pip install pyxlsb==1.0.10
pip install xlrd==2.0.1
pip install python-dateutil==2.8.2
pip install pytz==2024.1

# Run the app
streamlit run app.py 