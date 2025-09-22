# Configuration Templates Guide 📋

A comprehensive guide to the available configuration templates for the multi-court document validation system. These templates provide ready-to-use configurations for common scenarios and industries.

## 📁 Available Configuration Templates

### Quick Reference

| Template | Description | Courts | Use Case |
|----------|-------------|--------|----------|
| `basic_single_court.json` | KEM only (backward compatible) | KEM | Existing users, simple setup |
| `dual_court_regional.json` | KEM + SEA regional processing | KEM, SEA | Regional organizations |
| `full_regional_suite.json` | All regional courts | KEM, SEA, TAC | Complete regional coverage |
| `financial_institution.json` | Financial compliance setup | KEM, FIN | Banks, financial services |
| `high_volume_processing.json` | High-speed optimization | KEM, HVL | High-volume operations |
| `legacy_migration.json` | Legacy document processing | KEM, LEG | Historical document migration |
| `enterprise_multi_site.json` | Full enterprise setup | KEM, SEA, TAC, ENT | Large organizations |

---

## 🚀 Quick Setup Instructions

### 1. Choose Your Template

Select the template that best matches your organization:

```bash
# List available templates
ls court_configs/

# Copy your chosen template
cp court_configs/basic_single_court.json courts_config.json
```

### 2. Create Required Directories

Each template requires specific directories:

```bash
# For basic single court
mkdir -p kem-inbox kem-output kem-invalid kem-processed

# For dual court regional
mkdir -p kem-inbox kem-output kem-invalid kem-processed
mkdir -p sea-inbox sea-output sea-invalid sea-processed

# For full regional suite
mkdir -p kem-inbox kem-output kem-invalid kem-processed
mkdir -p sea-inbox sea-output sea-invalid sea-processed
mkdir -p tac-inbox tac-output tac-invalid tac-processed
```

### 3. Test Configuration

```bash
# Validate JSON syntax
python -c "import json; json.load(open('courts_config.json')); print('✅ Valid configuration')"

# Test with sample files
python create_samples.py
```

### 4. Start Application

```bash
# Start web interface
streamlit run streamlit_app.py

# Or command line interface
python kem_validator_local.py
```

---

## 📋 Template Details

### Basic Single Court (`basic_single_court.json`)

**Perfect for:** Existing KEM users who want to maintain current functionality

```json
{
  "KEM": {
    "enabled": true,
    "validation_rules": {
      "min_digits": 9,
      "max_digits": 13,
      "prefix_required": true
    }
  }
}
```

**Features:**
- ✅ 100% backward compatible with existing KEM setup
- ✅ Same validation rules (9-13 digits)
- ✅ Same directory structure
- ✅ 6-month archive retention

### Dual Court Regional (`dual_court_regional.json`)

**Perfect for:** Organizations handling both Kirkland and Seattle documents

```json
{
  "KEM": { "min_digits": 9, "max_digits": 13 },
  "SEA": { "min_digits": 8, "max_digits": 12 }
}
```

**Features:**
- ✅ KEM court (9-13 digits) for Kirkland documents
- ✅ SEA court (8-12 digits) for Seattle documents
- ✅ Different retention policies per court
- ✅ Court-specific analytics

### Full Regional Suite (`full_regional_suite.json`)

**Perfect for:** Complete regional court coverage

```json
{
  "KEM": { "min_digits": 9, "max_digits": 13 },
  "SEA": { "min_digits": 8, "max_digits": 12 },
  "TAC": { "min_digits": 10, "max_digits": 14 }
}
```

**Features:**
- ✅ All major regional courts enabled
- ✅ Different validation ranges per court
- ✅ Optimized for concurrent processing
- ✅ Performance monitoring enabled

### Financial Institution (`financial_institution.json`)

**Perfect for:** Banks, credit unions, financial services

```json
{
  "KEM": { "standard": "9-13 digits" },
  "FIN": { "exact": "12 digits only" }
}
```

**Features:**
- ✅ Strict 12-digit validation for financial documents
- ✅ Extended 7-year retention (84 months)
- ✅ Conservative processing settings
- ✅ Enhanced error handling

### High Volume Processing (`high_volume_processing.json`)

**Perfect for:** Organizations processing thousands of documents daily

```json
{
  "HVL": {
    "processing": {
      "batch_size": 500,
      "timeout_seconds": 30,
      "parallel_processing": true
    }
  }
}
```

**Features:**
- ✅ Optimized for speed (500 documents per batch)
- ✅ FTP integration enabled
- ✅ Short retention periods
- ✅ Performance monitoring

### Legacy Migration (`legacy_migration.json`)

**Perfect for:** Migrating historical documents

```json
{
  "LEG": {
    "validation_rules": {
      "min_digits": 1,
      "max_digits": 50,
      "prefix_required": false
    }
  }
}
```

**Features:**
- ✅ Very flexible validation (1-50 digits)
- ✅ Prefix not required for old documents
- ✅ Extended 10-year retention
- ✅ Slower, careful processing

### Enterprise Multi-Site (`enterprise_multi_site.json`)

**Perfect for:** Large organizations with multiple locations

```json
{
  "KEM": { "site": "Primary" },
  "SEA": { "site": "Regional" },
  "TAC": { "site": "Satellite" },
  "ENT": { "site": "Central Processing" }
}
```

**Features:**
- ✅ Four courts with different roles
- ✅ Full FTP integration for all sites
- ✅ Different processing profiles per site
- ✅ Enterprise-level monitoring

---

## 🔧 Validation Rules Library

### Standard Patterns

Use `validation_rules_library.json` for pre-defined validation patterns:

#### Short Range (6-10 digits)
```json
{
  "validation_rules": {
    "min_digits": 6,
    "max_digits": 10,
    "prefix_required": true
  }
}
```
**Use cases:** Small organizations, simple tracking

#### Medium Range (8-14 digits)
```json
{
  "validation_rules": {
    "min_digits": 8,
    "max_digits": 14,
    "prefix_required": true
  }
}
```
**Use cases:** Standard organizations, regional courts

#### Long Range (10-20 digits)
```json
{
  "validation_rules": {
    "min_digits": 10,
    "max_digits": 20,
    "prefix_required": true
  }
}
```
**Use cases:** Large organizations, enterprise systems

### Industry-Specific Patterns

#### Banking (10-16 digits)
```json
{
  "validation_rules": {
    "min_digits": 10,
    "max_digits": 16,
    "prefix_required": true
  },
  "compliance": ["PCI DSS", "SOX"],
  "retention_months": 84
}
```

#### Healthcare (8-16 digits)
```json
{
  "validation_rules": {
    "min_digits": 8,
    "max_digits": 16,
    "prefix_required": true
  },
  "compliance": ["HIPAA"],
  "retention_months": 72
}
```

#### Legal (6-20 digits)
```json
{
  "validation_rules": {
    "min_digits": 6,
    "max_digits": 20,
    "prefix_required": true
  },
  "retention_months": 120
}
```

---

## ⚙️ Processing Templates

### High Speed
```json
{
  "processing": {
    "batch_size": 500,
    "timeout_seconds": 30,
    "retry_attempts": 1,
    "parallel_processing": true
  }
}
```
**Use cases:** High-volume, time-sensitive processing

### High Accuracy
```json
{
  "processing": {
    "batch_size": 25,
    "timeout_seconds": 600,
    "retry_attempts": 5,
    "parallel_processing": false
  }
}
```
**Use cases:** Financial, legal, compliance-critical

### Balanced
```json
{
  "processing": {
    "batch_size": 100,
    "timeout_seconds": 300,
    "retry_attempts": 3,
    "parallel_processing": true
  }
}
```
**Use cases:** General processing, most common

---

## 🌐 FTP Templates

### Basic FTP
```json
{
  "ftp": {
    "enabled": true,
    "input_path": "/ftp/courts/{court}/incoming",
    "output_path": "/ftp/courts/{court}/processed",
    "error_path": "/ftp/courts/{court}/errors"
  }
}
```

### Enterprise FTP
```json
{
  "ftp": {
    "enabled": true,
    "input_path": "/ftp/courts/{court}/incoming",
    "output_path": "/ftp/courts/{court}/processed",
    "error_path": "/ftp/courts/{court}/errors",
    "archive_path": "/ftp/courts/{court}/archive",
    "settings": {
      "polling_interval": 30,
      "batch_size": 50
    }
  }
}
```

---

## 🎯 Quick Start by Organization Size

### Small Office (1-50 users)
```bash
cp court_configs/basic_single_court.json courts_config.json
```
- **Courts:** KEM only
- **Retention:** 12 months
- **Processing:** Balanced

### Regional Office (50-500 users)
```bash
cp court_configs/dual_court_regional.json courts_config.json
```
- **Courts:** KEM + SEA
- **Retention:** 24 months
- **Processing:** Balanced with FTP

### Enterprise (500+ users)
```bash
cp court_configs/enterprise_multi_site.json courts_config.json
```
- **Courts:** KEM + SEA + TAC + ENT
- **Retention:** 36 months
- **Processing:** High speed with full FTP

---

## 🔄 Migration Scenarios

### From Single Court to Multi-Court

1. **Backup current setup:**
```bash
cp courts_config.json courts_config.json.backup
```

2. **Choose migration path:**
```bash
# Conservative: Add one court
cp court_configs/dual_court_regional.json courts_config.json

# Comprehensive: Full regional suite
cp court_configs/full_regional_suite.json courts_config.json
```

3. **Test with existing files:**
```bash
# Your existing KEM files should work unchanged
python kem_validator_local.py existing_kem_file.txt
```

### From Legacy System

1. **Start with legacy template:**
```bash
cp court_configs/legacy_migration.json courts_config.json
```

2. **Process historical documents:**
```bash
# Very flexible validation for old documents
python kem_validator_local.py historical_documents.txt
```

3. **Gradually add standard courts:**
```bash
# Edit courts_config.json to enable KEM court
# Migrate to dual-court configuration
```

---

## 🔧 Customization Guide

### Creating Custom Courts

1. **Use the template:**
```json
{
  "YOUR_COURT": {
    "enabled": true,
    "name": "Your Court Name",
    "validation_rules": {
      "min_digits": 8,
      "max_digits": 15,
      "prefix_required": true
    },
    "directories": {
      "input_dir": "your-inbox",
      "output_dir": "your-output",
      "invalid_dir": "your-invalid",
      "processed_dir": "your-processed"
    }
  }
}
```

2. **Create directories:**
```bash
mkdir -p your-inbox your-output your-invalid your-processed
```

3. **Test configuration:**
```bash
python -c "import json; json.load(open('courts_config.json'))"
```

### Combining Templates

Mix and match elements from different templates:

```json
{
  "KEM": {
    "validation_rules": "from basic_single_court.json",
    "processing": "from high_volume_processing.json",
    "ftp": "from enterprise_multi_site.json"
  }
}
```

---

## 📊 Performance Tuning

### For High Volume

```json
{
  "processing": {
    "batch_size": 500,
    "concurrent_courts": 5,
    "parallel_processing": true
  },
  "global_settings": {
    "max_file_size_mb": 100,
    "logging_level": "WARNING"
  }
}
```

### For High Accuracy

```json
{
  "processing": {
    "batch_size": 25,
    "retry_attempts": 5,
    "timeout_seconds": 900
  },
  "global_settings": {
    "logging_level": "DEBUG",
    "backup_enabled": true
  }
}
```

---

## 🆘 Troubleshooting Templates

### Template Won't Load
```bash
# Check JSON syntax
python -c "import json; json.load(open('courts_config.json'))"

# Common issues:
# - Missing commas
# - Extra commas
# - Unmatched brackets
# - Invalid characters
```

### Missing Directories
```bash
# Check required directories exist
python -c "
import json, os
config = json.load(open('courts_config.json'))
for court, data in config.items():
    if court != 'global_settings' and 'directories' in data:
        for name, path in data['directories'].items():
            print(f'{court} {name}: {path} - {'✅' if os.path.exists(path) else '❌'}')
"
```

### Court Not Appearing
```bash
# Check court is enabled
python -c "
import json
config = json.load(open('courts_config.json'))
for court, data in config.items():
    if court != 'global_settings':
        enabled = data.get('enabled', False)
        print(f'{court}: {'✅' if enabled else '❌'} ({\"enabled\" if enabled else \"disabled\"})')
"
```

---

## 📚 Additional Resources

- **Main Documentation:** README.md
- **Migration Guide:** MIGRATION_GUIDE.md
- **Admin Guide:** COURT_ADMIN_GUIDE.md
- **Template Library:** validation_rules_library.json
- **Sample Files:** sample-files/ directory

---

*Configuration Templates Guide: Ready-to-use configurations for every organization size and industry.*