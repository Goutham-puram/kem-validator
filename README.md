# Multi-Court Document Validator 🏛️

A powerful, extensible document validation system supporting multiple court systems with flexible validation rules, web interface, and comprehensive processing capabilities.

## 🌟 Overview

Originally designed for KEM (Kirkland Court) document validation, this system now supports multiple court systems while maintaining **100% backward compatibility**. Your existing KEM workflows continue to work exactly as before - multi-court functionality is an optional enhancement.

## 🏛️ Supported Courts

| Court Code | Court Name | Validation Rule | Status |
|------------|------------|-----------------|--------|
| **KEM** | **Kirkland Court** | **9-13 digits** | **✅ Primary (Always Available)** |
| SEA | Seattle Court | 8-12 digits | ✅ Available |
| TAC | Tacoma Court | 10-14 digits | 🔧 Configurable |

## ✨ Key Features

### Core Functionality
- **🔍 Multi-Court Validation**: Supports multiple court systems with unique validation rules
- **📁 Flexible File Processing**: Process TXT, PDF, and images (PNG, JPG, TIFF, BMP)
- **🤖 OCR Integration**: Three OCR options (Tesseract, OpenAI Vision, Azure Document Intelligence)
- **🌐 Modern Web Interface**: Beautiful Streamlit dashboard with court selection and analytics
- **📊 Real-time Monitoring**: File watcher for automatic processing
- **💾 Robust Database**: SQLite with court-specific tracking

### Multi-Court Capabilities
- **🏛️ Court-Specific Processing**: Each court has its own validation rules and directories
- **📈 Cross-Court Analytics**: Compare performance and trends across courts
- **📦 Unified Batch Processing**: Process multiple courts simultaneously
- **🔄 Seamless Migration**: Zero-breaking-change upgrade from single-court systems
- **⚙️ Flexible Configuration**: Enable/disable courts as needed

### Advanced Features
- **📥 CSV Export**: Detailed reports with court-specific data
- **📂 Smart Archive Organization**: Court-specific retention policies
- **🌐 FTP Integration**: Court-specific FTP paths and routing
- **🔧 Extensible Architecture**: Easy to add new courts

## 🚀 Quick Start

### For Existing KEM Users
**Your existing setup works unchanged!** No migration required.

```bash
# Continue using as before
streamlit run streamlit_app.py
# or
python kem_validator_local.py
```

### For New Multi-Court Installations

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/kem-validator.git
cd kem-validator

# Install dependencies
pip install -r requirements.txt

# Run with multi-court support
streamlit run streamlit_app.py
```

Open browser to: http://localhost:8501

## 📊 Validation Rules

### KEM Court (Primary - Always Available)
- ✅ **Valid**: 9-13 digits (e.g., `KEM 123456789`, `KEM 1234567890123`)
- ❌ **Invalid**: <9 or >13 digits, non-numeric characters

### SEA Court (Seattle)
- ✅ **Valid**: 8-12 digits (e.g., `SEA 12345678`, `SEA 123456789012`)
- ❌ **Invalid**: <8 or >12 digits, non-numeric characters

### TAC Court (Tacoma)
- ✅ **Valid**: 10-14 digits (e.g., `TAC 1234567890`, `TAC 12345678901234`)
- ❌ **Invalid**: <10 or >14 digits, non-numeric characters

## ⚙️ Configuration

### Basic Setup (courts_config.json)

Create this file to enable multi-court functionality. **If it doesn't exist, the system defaults to KEM-only mode** for backward compatibility.

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
    }
  },
  "SEA": {
    "enabled": true,
    "name": "Seattle Court",
    "validation_rules": {
      "min_digits": 8,
      "max_digits": 12,
      "prefix_required": true
    },
    "directories": {
      "input_dir": "sea-inbox",
      "output_dir": "sea-output",
      "invalid_dir": "sea-invalid",
      "processed_dir": "sea-processed"
    }
  },
  "global_settings": {
    "default_court": "KEM",
    "archive_base_dir": "archive",
    "database_path": "kem_validator.db"
  }
}
```

### Adding New Courts

Simply add a new court entry and restart the application:

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

## 📝 File Format Examples

### Traditional KEM Format (Still Works!)
```
Equipment Inventory Report
Generated: 2025-09-18

KEM	123456789	Office Chair Model A
KEM	1234567890123	Conference Table B
KEM	12345678	File Cabinet C (Invalid - too short)
```

### Multi-Court Format
```
Multi-Court Equipment Processing
Generated: 2025-09-18

KEM	123456789	KEM Equipment 1
SEA	12345678	SEA Equipment 1
TAC	1234567890	TAC Equipment 1
```

### Legacy Format (No Prefixes)
**Still works perfectly!** Defaults to KEM processing:
```
Equipment Inventory
Date: 2025-09-18

123456789	Legacy Equipment 1
1234567890123	Legacy Equipment 2
```

## 🌐 Web Interface Features

### Dashboard
- **Court Selection**: Dropdown to choose active court
- **Multi-Court Metrics**: Success rates and volumes across courts
- **Real-time Processing**: Live status updates

### Court Management Page
- **Court Overview**: View all configured courts
- **Court Statistics**: Processing metrics per court
- **Configuration Viewer**: Read-only court settings
- **Queue Status**: Processing queue by court

### Analytics
- **Court Comparison**: Bar charts comparing success rates
- **Time Series**: Processing trends per court
- **Distribution Charts**: File volumes across courts
- **Error Analysis**: Top failures by court

## 🚀 Usage Examples

### Web Interface
1. **Select Court**: Choose from dropdown (defaults to KEM)
2. **Upload Files**: Drag and drop court-specific files
3. **Batch Processing**: Process multiple courts simultaneously
4. **View Analytics**: Compare performance across courts

### Command Line
```bash
# Traditional KEM processing (unchanged)
python kem_validator_local.py

# Process specific court
python kem_validator_local.py --court SEA

# Multi-court batch processing
python kem_validator_local.py --all-courts
```

## 📂 Directory Structure

### Legacy (KEM Only)
```
kem-validator/
├── kem-inbox/          # Input files
├── kem-output/         # Valid results
├── kem-invalid/        # Invalid results
└── archive/            # Archived files
```

### Multi-Court Structure
```
kem-validator/
├── kem-inbox/          # KEM input files
├── kem-output/         # KEM results
├── sea-inbox/          # SEA input files (if enabled)
├── sea-output/         # SEA results (if enabled)
├── tac-inbox/          # TAC input files (if enabled)
├── tac-output/         # TAC results (if enabled)
└── archive/            # Court-organized archives
    ├── KEM/2025/09/    # KEM archived files
    ├── SEA/2025/09/    # SEA archived files
    └── TAC/2025/09/    # TAC archived files
```

## 🔄 Migration & Compatibility

### For Existing KEM Users
**Nothing changes!** Your existing setup continues working:
- ✅ Same file formats
- ✅ Same validation rules
- ✅ Same directories
- ✅ Same interfaces
- ✅ Same workflows

### Migration Benefits
- **Zero Downtime**: Upgrade without interruption
- **Gradual Adoption**: Add courts when ready
- **Risk-Free**: Existing functionality preserved
- **Optional Features**: Use only what you need

## 🔧 Installation & Setup

### Prerequisites
```bash
# Python 3.8+ required
python --version

# Install Tesseract for OCR (optional)
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# Mac: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

### Installation
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/kem-validator.git
cd kem-validator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration
```bash
# Optional: Enable multi-court (otherwise defaults to KEM-only)
cp courts_config.json.example courts_config.json

# Edit configuration as needed
nano courts_config.json
```

## 🧪 Testing

### Run Test Suite
```bash
# Basic functionality tests
python test_multi_court_basic.py

# Comprehensive multi-court tests
python test_multi_court.py

# Migration compatibility tests
python test_migration.py

# Integration tests
python test_integration_multi_court.py
```

### Generate Sample Files
```bash
# Create test files for all courts
python create_samples.py
```

Sample files will be created in `sample-files/` directory for testing all court validation scenarios.

## 🔧 Troubleshooting

### Common Issues

**Q: My existing KEM files stopped working**
A: This shouldn't happen! Ensure:
- Original directories exist
- `courts_config.json` has KEM enabled (or delete the file)
- Default court is set to "KEM"

**Q: How do I disable multi-court features?**
A: Delete or rename `courts_config.json` - system reverts to KEM-only mode

**Q: Can courts have different validation rules?**
A: Yes! Each court can have unique min/max digit requirements

**Q: How are files without court prefixes handled?**
A: They automatically use the default court (KEM)

### Getting Help
- Use the web interface for real-time validation feedback
- Check CSV reports for detailed error messages
- Test with sample files from `sample-files/` directory
- Enable debug logging for detailed troubleshooting

## 🤝 Contributing

### Adding New Courts
1. Update `courts_config.json` with new court configuration
2. Add court-specific validation rules
3. Create necessary directories
4. Update tests to include the new court
5. Test thoroughly before deployment

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Code formatting
black .
flake8 .
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 💡 Quick Start Guide

### For Current KEM Users
1. **Keep using as normal** - everything works unchanged
2. **Optional**: Enable multi-court when ready
3. **No rush** - migrate at your own pace

### For New Users
1. **Start with KEM** - it's fully featured and stable
2. **Add courts gradually** - enable additional courts as needed
3. **Use provided examples** - sample files and configurations included

---

*Multi-Court Document Validator: Supporting multiple court systems while preserving 100% backward compatibility with existing KEM workflows.*