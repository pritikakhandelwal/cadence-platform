@echo off
cd /d "%~dp0"
call .venv-cadence\Scripts\activate.bat
streamlit run app.py
pause
