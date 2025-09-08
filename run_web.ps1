# Run KEM Validator Web Interface
Write-Host 'Starting KEM Validator Web Interface...' -ForegroundColor Green
streamlit run streamlit_app.py --server.port 8501 --server.address localhost
