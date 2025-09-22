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

## 🏛️ Multi-Court System

This application now supports multiple court systems while maintaining full backward compatibility with existing KEM processing. **Your existing KEM workflows continue to work exactly as before** - the multi-court functionality is an optional enhancement.

### Supported Courts

| Court Code | Court Name | Validation Rule | Status |
|------------|------------|-----------------|--------|
| **KEM** | **Kirkland Court** | **9-13 digits** | **✅ Primary (Always Available)** |
| SEA | Seattle Court | 8-12 digits | ✅ Available |
| TAC | Tacoma Court | 10-14 digits | 🔧 Configurable |

### Key Benefits

- **Zero Breaking Changes**: Existing KEM processing unchanged
- **Optional Enhancement**: Add new courts only when needed
- **Flexible Configuration**: Enable/disable courts as required
- **Court-Specific Processing**: Each court has its own validation rules and directories
- **Unified Interface**: Single application handles all courts seamlessly

### Migration from Single Court

If you're currently using the KEM-only version:
1. **No action required** - your existing setup continues working
2. **Optional**: Add new courts by updating the configuration
3. **Gradual transition**: Enable additional courts at your own pace

## 📊 Validation Rules

### KEM Court (Primary)
| Status | Description | Example |
|--------|-------------|---------|
| ✅ Valid | 9-13 digits | `KEM 123456789` (9 digits)
| ✅ Valid | 13 digits (max) | `KEM 1234567890123` (13 digits)
| ❌ Invalid | Less than 9 digits | `KEM 12345678` (8 digits)
| ❌ Invalid | More than 13 digits | `KEM 12345678901234` (14 digits)
| ❌ Invalid | Non-numeric | `KEM ABC123DEF` (contains letters)

### Multi-Court Validation Rules

#### SEA Court (Seattle)
| Status | Description | Example |
|--------|-------------|---------|
| ✅ Valid | 8-12 digits | `SEA 12345678` (8 digits minimum)
| ✅ Valid | 12 digits (max) | `SEA 123456789012` (12 digits)
| ❌ Invalid | Less than 8 digits | `SEA 1234567` (7 digits)
| ❌ Invalid | More than 12 digits | `SEA 1234567890123` (13 digits)

#### TAC Court (Tacoma)
| Status | Description | Example |
|--------|-------------|---------|
| ✅ Valid | 10-14 digits | `TAC 1234567890` (10 digits minimum)
| ✅ Valid | 14 digits (max) | `TAC 12345678901234` (14 digits)
| ❌ Invalid | Less than 10 digits | `TAC 123456789` (9 digits)
| ❌ Invalid | More than 14 digits | `TAC 123456789012345` (15 digits)

## ⚙️ Court Configuration

### Basic Configuration (courts_config.json)

The system uses a JSON configuration file to manage multiple courts. **If this file doesn't exist, the system defaults to KEM-only mode** for backward compatibility.

```json
{
  "KEM": {
    "enabled": true,
    "name": "Kirkland Court",
    "validation_rules": {
      "min_digits": 9,
      "max_digits": 13,
      "prefix_required": true
    },
    "directories": {
      "input_dir": "kem-inbox",
      "output_dir": "kem-output",
      "invalid_dir": "kem-invalid",
      "processed_dir": "kem-processed"
    },
    "archive": {
      "enabled": true,
      "retention_months": 6
    }
  },
  "SEA": {
    "enabled": false,
    "name": "Seattle Court",
    "validation_rules": {
      "min_digits": 8,
      "max_digits": 12,
      "prefix_required": true
    }
  },
  "global_settings": {
    "default_court": "KEM",
    "archive_base_dir": "archive",
    "database_path": "kem_validator.db"
  }
}
```

### Configuration Options

#### Court Settings
- `enabled`: Whether the court is active (true/false)
- `name`: Human-readable court name
- `validation_rules`: Court-specific validation parameters
- `directories`: Input/output paths for the court
- `archive`: Archive settings and retention policies

#### Global Settings
- `default_court`: Fallback court for files without court identifiers
- `archive_base_dir`: Base directory for archived files
- `database_path`: SQLite database location

### Adding a New Court

1. **Edit Configuration**: Add court entry to `courts_config.json`
2. **Set Validation Rules**: Define min/max digits for the court
3. **Configure Directories**: Set up input/output paths
4. **Enable Court**: Set `"enabled": true`
5. **Restart Application**: Changes take effect on restart

```json
{
  "NEW": {
    "enabled": true,
    "name": "New Court System",
    "validation_rules": {
      "min_digits": 8,
      "max_digits": 15,
      "prefix_required": true
    },
    "directories": {
      "input_dir": "new-inbox",
      "output_dir": "new-output",
      "invalid_dir": "new-invalid",
      "processed_dir": "new-processed"
    }
  }
}
```

## 📝 Multi-Court File Examples

### Single Court File (KEM - Traditional Format)
```
Equipment Inventory Report
Generated: 2025-09-18
Department: Facilities

KEM	123456789	Office Chair Model A - Valid (9 digits)
KEM	1234567890123	Conference Table B - Valid (13 digits)
KEM	12345678	File Cabinet C - Invalid (too short)
```

### Mixed Court File (Multiple Courts)
```
Multi-Court Equipment Processing
Generated: 2025-09-18
Processing Date: September 18, 2025

KEM COURT ENTRIES:
KEM	123456789	KEM Equipment 1 - Valid
KEM	1234567890123	KEM Equipment 2 - Valid

SEA COURT ENTRIES:
SEA	12345678	SEA Equipment 1 - Valid
SEA	123456789012	SEA Equipment 2 - Valid

TAC COURT ENTRIES:
TAC	1234567890	TAC Equipment 1 - Valid
TAC	12345678901234	TAC Equipment 2 - Valid
```

### Legacy Format (No Court Prefix)
**Still works perfectly!** Files without court prefixes default to KEM processing:

```
Equipment Inventory
Date: 2025-09-18

123456789	Legacy Equipment 1 - Processed as KEM
1234567890123	Legacy Equipment 2 - Processed as KEM
987654321	Legacy Equipment 3 - Processed as KEM
```

## 🚀 Multi-Court Usage Examples

### Web Interface

1. **Court Selection**: Choose your court from the dropdown (defaults to KEM)
2. **Upload Files**: Drag and drop court-specific files
3. **Batch Processing**: Process multiple courts simultaneously
4. **Analytics**: View performance across all courts
5. **Court Management**: Configure courts through the web interface

### Command Line Interface

**Process KEM Files (Traditional):**
```bash
# Existing KEM processing - unchanged
python kem_validator_local.py
```

**Process Specific Court:**
```bash
# Process SEA court files
python kem_validator_local.py --court SEA

# Process TAC court files
python kem_validator_local.py --court TAC
```

**Multi-Court Batch Processing:**
```bash
# Process all enabled courts
python kem_validator_local.py --all-courts

# Process specific courts
python kem_validator_local.py --courts KEM,SEA
```

## 📂 Directory Structure

### Single Court (KEM Only - Legacy)
```
kem-validator/
├── kem-inbox/          # Input files
├── kem-output/         # Valid results
├── kem-invalid/        # Invalid results
├── kem-processed/      # Processed files
└── archive/            # Archived files
```

### Multi-Court Structure
```
kem-validator/
├── kem-inbox/          # KEM input files
├── kem-output/         # KEM valid results
├── kem-invalid/        # KEM invalid results
├── kem-processed/      # KEM processed files
├── sea-inbox/          # SEA input files (if enabled)
├── sea-output/         # SEA valid results (if enabled)
├── tac-inbox/          # TAC input files (if enabled)
├── tac-output/         # TAC valid results (if enabled)
└── archive/            # Court-organized archives
    ├── KEM/            # KEM archived files
    │   └── 2025/09/    # Year/Month organization
    ├── SEA/            # SEA archived files (if enabled)
    └── TAC/            # TAC archived files (if enabled)
```

## 🔄 Backward Compatibility

### For Existing KEM Users

**Nothing Changes!** Your existing setup continues working exactly as before:

- ✅ Same file formats supported
- ✅ Same validation rules (9-13 digits)
- ✅ Same directory structure
- ✅ Same command line interface
- ✅ Same web interface
- ✅ Same database structure
- ✅ All existing scripts and workflows unchanged

### Migration Benefits

- **Zero downtime**: Upgrade without service interruption
- **Gradual adoption**: Add courts when ready
- **Risk-free**: Existing functionality preserved
- **Optional features**: Use only what you need

## 🔧 Troubleshooting

### Common Issues

**Q: My existing KEM files stopped working**
**A: This shouldn't happen! If you experience issues, ensure:**
- Original directories still exist
- `courts_config.json` has KEM enabled
- Default court is set to "KEM"

**Q: How do I disable multi-court features?**
**A: Simply delete or rename `courts_config.json` - the system will revert to KEM-only mode**

**Q: Can I have different validation rules per court?**
**A: Yes! Each court can have unique min/max digit requirements**

**Q: How do I process files without court prefixes?**
**A: Files without court codes automatically use the default court (KEM)**

### Support

- Check the web interface for real-time validation
- Review generated CSV reports for detailed error messages
- Use test files from `sample-files/` directory to verify setup
- Enable debug logging for detailed troubleshooting

## 📈 Advanced Features

### Court-Specific Analytics
- Success rates per court
- Processing volume comparison
- Court-specific error patterns
- Time-series analysis across courts

### Archive Management
- Court-specific retention policies
- Automated cleanup by court
- Archive migration tools
- Historical data preservation

### FTP Integration
- Court-specific FTP paths
- Automated routing by court
- Batch processing across courts
- Court-based file organization

---

## 💡 Quick Migration Guide

### For Current KEM Users

1. **Continue as usual** - your setup works unchanged
2. **Optional**: Copy `courts_config.json.example` to enable multi-court
3. **Optional**: Configure additional courts when needed
4. **No rush** - migrate at your own pace

### For New Installations

1. **Start with KEM** - it's the primary, fully-featured court
2. **Add courts gradually** - enable SEA, TAC, or custom courts as needed
3. **Use configuration examples** - provided templates make setup easy

---

*The KEM Validator now supports multiple court systems while maintaining 100% backward compatibility. Your existing KEM processing workflows continue unchanged.*