@echo off
echo Starting KEM Validator Web Interface...
call venv\Scripts\activate
streamlit run streamlit_ftp_app.py --server.port 8501 --server.address localhost
pause
