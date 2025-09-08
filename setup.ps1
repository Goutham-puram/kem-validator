# KEM Validator - Local Setup Script for Windows
# This script sets up the complete environment

param(
    [switch]$InstallTesseract,
    [switch]$CreateSampleData,
    [switch]$SkipDependencies
)

# Colors for output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️ $Message" -ForegroundColor Cyan }
function Write-Step { param($Message) Write-Host "🔧 $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

Write-Host ""
Write-Host "════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   KEM Validator - Local Setup                      " -ForegroundColor White
Write-Host "════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Step "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+\.\d+)") {
        $version = [version]$matches[1]
        if ($version -ge [version]"3.8") {
            Write-Success "Python $version found"
        } else {
            Write-Error "Python 3.8+ required. Found: $version"
            exit 1
        }
    }
} catch {
    Write-Error "Python is not installed or not in PATH"
    Write-Info "Download from: https://www.python.org/downloads/"
    exit 1
}

# Create virtual environment
Write-Step "Creating virtual environment..."
if (Test-Path "venv") {
    Write-Info "Virtual environment already exists"
} else {
    python -m venv venv
    Write-Success "Virtual environment created"
}

# Activate virtual environment
Write-Step "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"
Write-Success "Virtual environment activated"

# Install Python dependencies
if (-not $SkipDependencies) {
    Write-Step "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    Write-Success "Dependencies installed"
}

# Install Tesseract OCR if requested
if ($InstallTesseract) {
    Write-Step "Installing Tesseract OCR..."
    
    # Check if Chocolatey is installed
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install tesseract -y
        Write-Success "Tesseract installed via Chocolatey"
    } else {
        Write-Info "Chocolatey not found. Please install Tesseract manually:"
        Write-Info "Download from: https://github.com/UB-Mannheim/tesseract/wiki"
        Write-Info "Or install Chocolatey first: https://chocolatey.org/install"
    }
}

# Create necessary directories
Write-Step "Creating directory structure..."
$directories = @(
    "kem-inbox",
    "kem-results", 
    "processed-archive",
    "invalid-archive"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Success "Created directory: $dir"
    } else {
        Write-Info "Directory exists: $dir"
    }
}

# Create configuration file if it doesn't exist
if (-not (Test-Path "config.json")) {
    Write-Step "Creating default configuration..."
    
    $defaultConfig = @{
        input_dir = "kem-inbox"
        output_dir = "kem-results"
        processed_dir = "processed-archive"
        invalid_dir = "invalid-archive"
        ocr_provider = "tesseract"
        openai_api_key = ""
        azure_endpoint = ""
        azure_key = ""
        db_path = "kem_validator.db"
        auto_watch = $true
        process_interval = 5
    }
    
    $defaultConfig | ConvertTo-Json -Depth 10 | Out-File -FilePath "config.json" -Encoding UTF8
    Write-Success "Configuration file created"
}

# Create .env file from template if it doesn't exist
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success "Created .env file from template"
        Write-Info "Edit .env file to add your API keys if using cloud OCR"
    }
}

# Create sample data if requested
if ($CreateSampleData) {
    Write-Step "Creating sample data files..."
    
    # Sample TXT file
    $sampleContent = @"
HEADER: Sample KEM Data File
Date: $(Get-Date -Format "yyyy-MM-dd")
================================
KEM	4152500182618	Equipment Type A - Valid (13 digits)
KEM	41525000142927	Equipment Type B - Invalid (14 digits)
KEM	230471171	Equipment Type C - Valid (9 digits)
KEM	12345678	Equipment Type D - Invalid (8 digits)
This is an informational line without KEM prefix
KEM	5A0185948B	Equipment Type E - Alphanumeric (9 digits extracted)
KEM	ABCDEFGH	Equipment Type F - Invalid (no digits)
KEM	9876543210	Equipment Type G - Valid (10 digits)
Another informational line
KEM	1234567890123	Equipment Type H - Valid (13 digits)
KEM	123456789012	Equipment Type I - Valid (12 digits)
KEM	12345678901	Equipment Type J - Valid (11 digits)
FOOTER: End of sample data
"@
    
    $sampleContent | Out-File -FilePath "kem-inbox\sample_data.txt" -Encoding UTF8
    Write-Success "Created sample_data.txt in kem-inbox"
    
    # Sample CSV for testing
    $csvContent = @"
kem_id,description,quantity
KEM	123456789,Sample Item 1,10
KEM	987654321,Sample Item 2,5
KEM	111222333,Sample Item 3,7
"@
    
    $csvContent | Out-File -FilePath "kem-inbox\sample_data.csv" -Encoding UTF8
    Write-Success "Created sample_data.csv in kem-inbox"
}

# Test imports
Write-Step "Testing Python imports..."
$testScript = @"
import sys
try:
    import pandas
    import streamlit
    import plotly
    import PyPDF2
    import pytesseract
    print('SUCCESS: All imports working')
    sys.exit(0)
except ImportError as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@

$testScript | python
if ($LASTEXITCODE -eq 0) {
    Write-Success "All Python imports successful"
} else {
    Write-Error "Some imports failed. Check error messages above"
}

# Create run scripts
Write-Step "Creating run scripts..."

# PowerShell run script
$psRunScript = @"
# Run KEM Validator Web Interface
Write-Host 'Starting KEM Validator Web Interface...' -ForegroundColor Green
streamlit run streamlit_app.py --server.port 8501 --server.address localhost
"@
$psRunScript | Out-File -FilePath "run_web.ps1" -Encoding UTF8

# Batch file for Windows
$batchScript = @"
@echo off
echo Starting KEM Validator Web Interface...
call venv\Scripts\activate
streamlit run streamlit_app.py --server.port 8501 --server.address localhost
pause
"@
$batchScript | Out-File -FilePath "run_web.bat" -Encoding ASCII

Write-Success "Run scripts created"

# Summary
Write-Host ""
Write-Host "════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "   Setup Complete!" -ForegroundColor White
Write-Host "════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Success "Environment is ready!"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run the web interface:" -ForegroundColor White
Write-Host "   streamlit run streamlit_app.py" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Or run the CLI version:" -ForegroundColor White
Write-Host "   python kem_validator_local.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Access the web interface at:" -ForegroundColor White
Write-Host "   http://localhost:8501" -ForegroundColor Cyan
Write-Host ""

if ($CreateSampleData) {
    Write-Host "Sample files created in kem-inbox/" -ForegroundColor Green
    Write-Host "Upload them in the web interface to test!" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "For help, check README_LOCAL.md" -ForegroundColor Cyan