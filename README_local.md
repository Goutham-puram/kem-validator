# KEM Validator - Local Python Edition 🚀

A powerful, fully-featured local application for validating KEM (Key Equipment/Material) identifiers with OCR support, web interface, and batch processing capabilities.

## ✨ Features

- **🔍 KEM Validation**: Validates IDs based on 9-13 digit rule
- **📁 Multi-Format Support**: Process TXT, PDF, and images (PNG, JPG, TIFF, BMP)
- **🤖 OCR Integration**: Three OCR options (Tesseract, OpenAI Vision, Azure Document Intelligence)
- **🌐 Web Interface**: Beautiful Streamlit dashboard with analytics
- **📊 Real-time Monitoring**: File watcher for automatic processing
- **📈 Analytics**: Comprehensive statistics and trends
- **💾 Database**: SQLite for processing history
- **📦 Batch Processing**: Process multiple files at once
- **📥 Export Options**: CSV reports with detailed validation results

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/kem-validator.git
cd kem-validator

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Tesseract (for OCR)

**Windows:**
```powershell
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
# Or use Chocolatey:
choco install tesseract
```

**Mac:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Configure (Optional)

Edit `config.json` or use the web interface Settings page:

```json
{
  "input_dir": "kem-inbox",
  "output_dir": "kem-results",
  "ocr_provider": "tesseract",
  "openai_api_key": "your_key_here"
}
```

### 4. Run the Application

**Web Interface (Recommended):**
```bash
streamlit run streamlit_app.py
```
Open browser to: http://localhost:8501

**Command Line Interface:**
```bash
python kem_validator_local.py
```

## 📋 Usage Guide

### Web Interface

1. **Dashboard**: View overall statistics and recent processing history
2. **Upload & Process**: Drag and drop files or paste text directly
3. **Batch Processing**: Process all files in the input directory
4. **Analytics**: View trends, success rates, and distributions
5. **Settings**: Configure directories and OCR providers

### CLI Options

```
1. Process single file    - Process one file at a time
2. Process all files      - Batch process inbox directory
3. Start file watcher     - Auto-process new files
4. View statistics        - Show overall metrics
5. View history          - Recent processing history
6. Configure settings    - Update configuration
7. Exit
```

### File Formats

**Text Files (.txt)**
- Preferred format: Tab-separated `KEM\t<ID>\t<Description>`
- Alternative: Space-separated `KEM <ID> <Description>`

**Example:**
```
KEM	4152500182618	Equipment A
KEM	230471171	Equipment B
Header information line
KEM	5A0185948	Equipment C
```

## 🔧 OCR Configuration

### Option 1: Tesseract (Free, Local)
```json
{
  "ocr_provider": "tesseract"
}
```

### Option 2: OpenAI Vision (High Quality)
```json
{
  "ocr_provider": "openai",
  "openai_api_key": "sk-..."
}
```

### Option 3: Azure Document Intelligence (Enterprise)
```json
{
  "ocr_provider": "azure",
  "azure_endpoint": "https://your-resource.cognitiveservices.azure.com/",
  "azure_key": "your_key"
}
```

## 📊 Validation Rules

| Status | Description | Example |
|--------|-------------|---------|
| ✅ Valid | 9-13 digits | `KEM 123456789` (9 digits)