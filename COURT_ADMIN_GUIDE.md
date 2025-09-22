# Court Administration Guide 🏛️

A comprehensive guide for administrators managing multiple court systems in the document validation platform. This guide covers adding new courts, configuring validation rules, managing FTP structures, and troubleshooting common issues.

## 📋 Overview

The multi-court system allows administrators to:
- **Add unlimited courts** with unique validation rules
- **Configure court-specific processing** directories and settings
- **Manage FTP integration** for automated file routing
- **Monitor court performance** and processing statistics
- **Maintain backward compatibility** with existing KEM workflows

### Supported Court Types
- **Primary Courts**: KEM (always available), SEA, TAC
- **Custom Courts**: Any 3-letter court code with custom validation rules
- **Legacy Support**: Existing single-court systems continue unchanged

---

## 🏗️ Adding a New Court

### Quick Start: Add a Standard Court

#### Step 1: Edit Configuration File
```bash
# Open the courts configuration file
nano courts_config.json
```

#### Step 2: Add Court Entry
Add your new court to the configuration:

```json
{
  "KEM": {
    "enabled": true,
    "name": "Kirkland Court",
    "validation_rules": {
      "min_digits": 9,
      "max_digits": 13,
      "prefix_required": true
    }
  },
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
    },
    "archive": {
      "enabled": true,
      "retention_months": 12
    },
    "ftp": {
      "enabled": false,
      "input_path": "/ftp/courts/new/incoming",
      "output_path": "/ftp/courts/new/processed"
    }
  }
}
```

#### Step 3: Create Directories
```bash
# Create required directories for the new court
mkdir -p new-inbox new-output new-invalid new-processed

# Set appropriate permissions
chmod 755 new-*

echo "Directories created for NEW court"
```

#### Step 4: Test Configuration
```bash
# Validate JSON syntax
python -c "
import json
try:
    with open('courts_config.json') as f:
        config = json.load(f)
    print('✅ Configuration is valid')
    print(f'✅ NEW court enabled: {config[\"NEW\"][\"enabled\"]}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"

# Test with sample file
echo -e "NEW\t12345678\tTest Equipment 1" > new-inbox/test_file.txt
```

#### Step 5: Restart Application
```bash
# Restart the application to load new configuration
pkill -f streamlit
streamlit run streamlit_app.py

# The new court should appear in the court selector dropdown
```

### Advanced Court Setup

#### Custom Court with Full Configuration
```json
{
  "ABC": {
    "enabled": true,
    "name": "ABC District Court",
    "description": "District court handling ABC region documents",
    "validation_rules": {
      "min_digits": 6,
      "max_digits": 20,
      "prefix_required": true,
      "allow_alpha": false,
      "custom_pattern": null,
      "case_sensitive": false
    },
    "directories": {
      "input_dir": "abc-inbox",
      "output_dir": "abc-output",
      "invalid_dir": "abc-invalid",
      "processed_dir": "abc-processed"
    },
    "archive": {
      "enabled": true,
      "retention_months": 24,
      "compression": true,
      "cleanup_policy": "monthly"
    },
    "ftp": {
      "enabled": true,
      "input_path": "/ftp/courts/abc/incoming",
      "output_path": "/ftp/courts/abc/processed",
      "error_path": "/ftp/courts/abc/errors",
      "archive_path": "/ftp/courts/abc/archive"
    },
    "notifications": {
      "enabled": false,
      "email": "admin@abccourt.gov",
      "webhook": null
    },
    "processing": {
      "batch_size": 100,
      "timeout_seconds": 300,
      "retry_attempts": 3,
      "parallel_processing": true
    }
  }
}
```

---

## ⚙️ Court Configuration Options Explained

### Core Settings

#### Basic Information
```json
{
  "enabled": true,           // Whether court is active (true/false)
  "name": "Court Name",      // Human-readable court name
  "description": "...",      // Optional description for documentation
}
```

#### Validation Rules
```json
{
  "validation_rules": {
    "min_digits": 8,          // Minimum number of digits required
    "max_digits": 15,         // Maximum number of digits allowed
    "prefix_required": true,  // Whether court prefix is required
    "allow_alpha": false,     // Allow alphabetic characters (future feature)
    "custom_pattern": null,   // Custom regex pattern (advanced)
    "case_sensitive": false   // Case sensitivity for validation
  }
}
```

#### Directory Configuration
```json
{
  "directories": {
    "input_dir": "court-inbox",     // Where files are placed for processing
    "output_dir": "court-output",   // Where valid results are saved
    "invalid_dir": "court-invalid", // Where invalid results are saved
    "processed_dir": "court-processed" // Where processed files are moved
  }
}
```

### Advanced Settings

#### Archive Configuration
```json
{
  "archive": {
    "enabled": true,           // Enable archiving for this court
    "retention_months": 12,    // How long to keep archived files
    "compression": true,       // Compress archived files (future feature)
    "cleanup_policy": "monthly" // When to run cleanup (monthly/weekly/daily)
  }
}
```

#### FTP Integration
```json
{
  "ftp": {
    "enabled": true,                        // Enable FTP for this court
    "input_path": "/ftp/courts/abc/incoming", // FTP input directory
    "output_path": "/ftp/courts/abc/processed", // FTP output directory
    "error_path": "/ftp/courts/abc/errors",   // FTP error directory
    "archive_path": "/ftp/courts/abc/archive" // FTP archive directory
  }
}
```

#### Processing Options
```json
{
  "processing": {
    "batch_size": 100,         // Number of records to process at once
    "timeout_seconds": 300,    // Processing timeout per file
    "retry_attempts": 3,       // Number of retry attempts for failed files
    "parallel_processing": true // Enable parallel processing (future feature)
  }
}
```

#### Notifications (Future Feature)
```json
{
  "notifications": {
    "enabled": false,                    // Enable notifications
    "email": "admin@court.gov",         // Email for notifications
    "webhook": "https://api.court.gov/webhook" // Webhook URL
  }
}
```

### Global Settings
```json
{
  "global_settings": {
    "default_court": "KEM",           // Default court for files without prefix
    "archive_base_dir": "archive",    // Base directory for all archives
    "database_path": "kem_validator.db", // Database file location
    "backup_enabled": true,           // Enable automatic backups
    "logging_level": "INFO",          // Logging verbosity (DEBUG/INFO/WARNING/ERROR)
    "max_file_size_mb": 50,          // Maximum file size for processing
    "allowed_extensions": [".txt", ".pdf", ".png", ".jpg"] // Allowed file types
  }
}
```

---

## 🔍 Validation Rule Types and Examples

### Standard Numeric Validation

#### Basic Digit Range
```json
{
  "validation_rules": {
    "min_digits": 9,
    "max_digits": 13,
    "prefix_required": true
  }
}
```

**Examples:**
- ✅ `KEM 123456789` (9 digits - valid)
- ✅ `KEM 1234567890123` (13 digits - valid)
- ❌ `KEM 12345678` (8 digits - too short)
- ❌ `KEM 12345678901234` (14 digits - too long)

#### Different Ranges by Court
```json
{
  "KEM": {
    "validation_rules": { "min_digits": 9, "max_digits": 13 }
  },
  "SEA": {
    "validation_rules": { "min_digits": 8, "max_digits": 12 }
  },
  "TAC": {
    "validation_rules": { "min_digits": 10, "max_digits": 14 }
  }
}
```

**Examples:**
- ✅ `SEA 12345678` (8 digits - valid for SEA, invalid for KEM)
- ✅ `TAC 1234567890` (10 digits - valid for TAC, invalid for SEA)
- ❌ `KEM 12345678` (8 digits - invalid for KEM)

### Advanced Validation Rules

#### Custom Pattern Validation (Future Feature)
```json
{
  "validation_rules": {
    "min_digits": 6,
    "max_digits": 20,
    "custom_pattern": "^[A-Z]{2}[0-9]{8,12}$",
    "description": "Two letters followed by 8-12 digits"
  }
}
```

#### Alphanumeric Support (Future Feature)
```json
{
  "validation_rules": {
    "min_digits": 8,
    "max_digits": 15,
    "allow_alpha": true,
    "alpha_positions": [1, 2, 7],
    "description": "Letters allowed in positions 1, 2, and 7"
  }
}
```

### Validation Examples by Court Type

#### Court with Strict Rules (Financial)
```json
{
  "FIN": {
    "name": "Financial Court",
    "validation_rules": {
      "min_digits": 12,
      "max_digits": 12,
      "prefix_required": true,
      "description": "Exactly 12 digits required for financial documents"
    }
  }
}
```

#### Court with Flexible Rules (General)
```json
{
  "GEN": {
    "name": "General Court",
    "validation_rules": {
      "min_digits": 6,
      "max_digits": 20,
      "prefix_required": false,
      "description": "Flexible validation for general documents"
    }
  }
}
```

#### Court with Legacy Support
```json
{
  "LEG": {
    "name": "Legacy Document Court",
    "validation_rules": {
      "min_digits": 1,
      "max_digits": 50,
      "prefix_required": false,
      "allow_alpha": true,
      "description": "Accepts any format for legacy document processing"
    }
  }
}
```

---

## 🌐 FTP Structure for Multi-Court

### FTP Directory Organization

#### Standard Multi-Court FTP Structure
```
/ftp/
├── courts/
│   ├── kem/
│   │   ├── incoming/          # Files to be processed
│   │   ├── processed/         # Successfully processed files
│   │   ├── errors/           # Files with processing errors
│   │   └── archive/          # Archived files
│   ├── sea/
│   │   ├── incoming/
│   │   ├── processed/
│   │   ├── errors/
│   │   └── archive/
│   └── tac/
│       ├── incoming/
│       ├── processed/
│       ├── errors/
│       └── archive/
├── shared/
│   ├── templates/            # File format templates
│   ├── documentation/        # Court-specific documentation
│   └── reports/             # Cross-court reports
└── admin/
    ├── logs/                # System logs
    ├── backups/            # Configuration backups
    └── monitoring/         # Health check files
```

### FTP Configuration per Court

#### Basic FTP Setup
```json
{
  "ABC": {
    "ftp": {
      "enabled": true,
      "input_path": "/ftp/courts/abc/incoming",
      "output_path": "/ftp/courts/abc/processed",
      "error_path": "/ftp/courts/abc/errors",
      "archive_path": "/ftp/courts/abc/archive"
    }
  }
}
```

#### Advanced FTP Configuration
```json
{
  "ABC": {
    "ftp": {
      "enabled": true,
      "paths": {
        "input": "/ftp/courts/abc/incoming",
        "processed": "/ftp/courts/abc/processed",
        "errors": "/ftp/courts/abc/errors",
        "archive": "/ftp/courts/abc/archive",
        "temp": "/ftp/courts/abc/temp"
      },
      "settings": {
        "polling_interval": 30,      # Seconds between checks
        "max_file_age": 3600,       # Maximum age before timeout
        "batch_size": 10,           # Files to process per batch
        "retry_failed": true,       # Retry failed transfers
        "cleanup_processed": true   # Remove processed files after archiving
      },
      "filters": {
        "allowed_extensions": [".txt", ".pdf"],
        "max_size_mb": 50,
        "ignore_patterns": [".*temp.*", ".*backup.*"]
      }
    }
  }
}
```

### FTP Processing Workflow

#### 1. File Arrival and Detection
```bash
# Files arrive in court-specific incoming directory
/ftp/courts/abc/incoming/ABC_20250918_batch1.txt

# System detects court from path structure
# Court = "ABC" (extracted from path)
```

#### 2. Processing and Routing
```bash
# Valid files moved to processed directory
/ftp/courts/abc/processed/ABC_20250918_batch1_valid.csv

# Invalid files moved to errors directory
/ftp/courts/abc/errors/ABC_20250918_batch1_invalid.csv

# Original files archived
/ftp/courts/abc/archive/2025/09/ABC_20250918_batch1.txt
```

#### 3. Cross-Court Processing
```bash
# Mixed court files automatically routed
/ftp/courts/kem/incoming/mixed_court_file.txt
# -> KEM entries -> /ftp/courts/kem/processed/
# -> SEA entries -> /ftp/courts/sea/processed/
# -> TAC entries -> /ftp/courts/tac/processed/
```

### FTP Security and Permissions

#### Directory Permissions
```bash
# Set up FTP directories with proper permissions
mkdir -p /ftp/courts/{kem,sea,tac}/{incoming,processed,errors,archive}

# Set permissions
chmod 755 /ftp/courts/
chmod 750 /ftp/courts/*/
chmod 770 /ftp/courts/*/incoming/
chmod 755 /ftp/courts/*/processed/
chmod 755 /ftp/courts/*/errors/
chmod 750 /ftp/courts/*/archive/

# Set ownership (adjust user/group as needed)
chown -R ftpuser:courtadmin /ftp/courts/
```

#### Access Control Configuration
```json
{
  "ftp_security": {
    "user_permissions": {
      "kem_user": {
        "courts": ["KEM"],
        "access": ["read", "write"],
        "paths": ["/ftp/courts/kem/incoming", "/ftp/courts/kem/processed"]
      },
      "admin_user": {
        "courts": ["KEM", "SEA", "TAC"],
        "access": ["read", "write", "admin"],
        "paths": ["/ftp/courts/*"]
      }
    }
  }
}
```

---

## 🔧 Troubleshooting Common Court Configuration Issues

### Configuration File Issues

#### Issue: Invalid JSON Syntax
**Symptoms:**
- Application fails to start
- Error: "JSON decode error"
- Court selector not appearing

**Solution:**
```bash
# Validate JSON syntax
python -c "
import json
try:
    with open('courts_config.json') as f:
        json.load(f)
    print('✅ JSON is valid')
except json.JSONDecodeError as e:
    print(f'❌ JSON Error: {e}')
    print('Line:', e.lineno, 'Column:', e.colno)
"

# Common fixes:
# - Remove trailing commas
# - Check matching brackets and quotes
# - Escape backslashes in paths
```

#### Issue: Missing Required Fields
**Symptoms:**
- Court not appearing in dropdown
- Validation errors in logs

**Solution:**
```json
{
  "ABC": {
    "enabled": true,                    // Required
    "name": "ABC Court",               // Required
    "validation_rules": {              // Required
      "min_digits": 8,                 // Required
      "max_digits": 15,                // Required
      "prefix_required": true          // Required
    }
  }
}
```

#### Issue: Directory Path Problems
**Symptoms:**
- Files not processing
- Permission errors
- Directory not found errors

**Solution:**
```bash
# Check directory existence
ls -la abc-inbox abc-output abc-invalid abc-processed

# Create missing directories
mkdir -p abc-inbox abc-output abc-invalid abc-processed

# Check permissions
chmod 755 abc-*

# Verify in configuration
python -c "
import json, os
config = json.load(open('courts_config.json'))
court = config['ABC']['directories']
for name, path in court.items():
    exists = os.path.exists(path)
    print(f'{name}: {path} - {'✅' if exists else '❌'}')
"
```

### Validation Rule Issues

#### Issue: Conflicting Validation Rules
**Symptoms:**
- Unexpected validation results
- Files marked invalid incorrectly

**Solution:**
```bash
# Check validation ranges
python -c "
import json
config = json.load(open('courts_config.json'))
for court, data in config.items():
    if court != 'global_settings':
        rules = data['validation_rules']
        min_d = rules['min_digits']
        max_d = rules['max_digits']
        print(f'{court}: {min_d}-{max_d} digits')
        if min_d >= max_d:
            print(f'❌ {court}: min_digits >= max_digits')
"
```

#### Issue: Court Prefix Not Working
**Symptoms:**
- Files default to wrong court
- Court detection fails

**Solution:**
```bash
# Test court detection
echo -e "ABC\t12345678\tTest Equipment" > test_file.txt

# Check prefix_required setting
python -c "
import json
config = json.load(open('courts_config.json'))
court = config['ABC']['validation_rules']
print('Prefix required:', court['prefix_required'])
"

# Verify file format:
# Correct: ABC\t12345678\tDescription
# Incorrect: ABC 12345678 Description
```

### Database Issues

#### Issue: Database Migration Failed
**Symptoms:**
- Database errors on startup
- Missing court_code column

**Solution:**
```bash
# Check database schema
sqlite3 kem_validator.db "PRAGMA table_info(equipment_validations);"

# Manual migration if needed
sqlite3 kem_validator.db "
ALTER TABLE equipment_validations
ADD COLUMN court_code TEXT DEFAULT 'KEM';
"

# Verify migration
sqlite3 kem_validator.db "
SELECT DISTINCT court_code, COUNT(*)
FROM equipment_validations
GROUP BY court_code;
"
```

#### Issue: Database Performance Problems
**Symptoms:**
- Slow queries
- High memory usage

**Solution:**
```bash
# Check database size
ls -lh kem_validator.db

# Analyze database
sqlite3 kem_validator.db "ANALYZE; .schema"

# Create missing indexes
sqlite3 kem_validator.db "
CREATE INDEX IF NOT EXISTS idx_court_code ON equipment_validations(court_code);
CREATE INDEX IF NOT EXISTS idx_processed_date ON equipment_validations(processed_date);
CREATE INDEX IF NOT EXISTS idx_status ON equipment_validations(status);
"
```

### FTP Configuration Issues

#### Issue: FTP Paths Not Working
**Symptoms:**
- Files not detected from FTP
- Court routing fails

**Solution:**
```bash
# Check FTP directory structure
ls -la /ftp/courts/

# Verify paths in configuration
python -c "
import json
config = json.load(open('courts_config.json'))
for court, data in config.items():
    if court != 'global_settings' and 'ftp' in data:
        ftp = data['ftp']
        if ftp['enabled']:
            print(f'{court} FTP paths:')
            print(f'  Input: {ftp[\"input_path\"]}')
            print(f'  Output: {ftp[\"output_path\"]}')
"

# Create missing FTP directories
mkdir -p /ftp/courts/{kem,sea,tac}/{incoming,processed,errors,archive}
```

#### Issue: FTP Permission Errors
**Symptoms:**
- Permission denied errors
- Files not accessible

**Solution:**
```bash
# Check current permissions
ls -la /ftp/courts/

# Fix permissions
chmod 755 /ftp/courts/
chmod 750 /ftp/courts/*/
chmod 770 /ftp/courts/*/incoming/

# Check ownership
chown -R ftpuser:courtadmin /ftp/courts/
```

### Performance Issues

#### Issue: Slow Processing with Multiple Courts
**Symptoms:**
- Long processing times
- High CPU usage

**Solution:**
```bash
# Check number of enabled courts
python -c "
import json
config = json.load(open('courts_config.json'))
enabled = [c for c, d in config.items()
           if c != 'global_settings' and d.get('enabled', False)]
print(f'Enabled courts: {len(enabled)} - {enabled}')
"

# Disable unused courts
# Edit courts_config.json and set "enabled": false

# Monitor processing
tail -f application.log | grep "Processing time"
```

#### Issue: Memory Usage Problems
**Symptoms:**
- High memory consumption
- Application crashes

**Solution:**
```bash
# Check file sizes being processed
find . -name "*.txt" -size +10M

# Adjust batch processing size
# Edit global_settings in courts_config.json:
{
  "global_settings": {
    "max_file_size_mb": 25,
    "batch_processing_enabled": true,
    "batch_size": 50
  }
}
```

### Web Interface Issues

#### Issue: Court Dropdown Empty
**Symptoms:**
- No courts in dropdown
- Default court not working

**Solution:**
```bash
# Check enabled courts
python -c "
import json
config = json.load(open('courts_config.json'))
enabled = []
for court, data in config.items():
    if court != 'global_settings' and data.get('enabled', False):
        enabled.append(court)
print('Enabled courts:', enabled)
if not enabled:
    print('❌ No courts enabled!')
"

# Enable at least one court
# Edit courts_config.json:
{
  "KEM": {
    "enabled": true,
    ...
  }
}
```

#### Issue: Court-Specific Analytics Not Showing
**Symptoms:**
- Missing court data in analytics
- Empty charts

**Solution:**
```bash
# Check database data
sqlite3 kem_validator.db "
SELECT court_code, COUNT(*) as records
FROM equipment_validations
GROUP BY court_code;
"

# Verify court_code values
sqlite3 kem_validator.db "
SELECT DISTINCT court_code FROM equipment_validations;
"

# If empty, re-run database migration
python kem_validator_local.py --migrate-database
```

---

## 📊 Monitoring and Maintenance

### Regular Maintenance Tasks

#### Weekly Tasks
```bash
# Check configuration validity
python -c "import json; json.load(open('courts_config.json')); print('✅ Config valid')"

# Review processing statistics
sqlite3 kem_validator.db "
SELECT court_code,
       COUNT(*) as total_files,
       SUM(CASE WHEN status='valid' THEN 1 ELSE 0 END) as valid_files,
       ROUND(100.0 * SUM(CASE WHEN status='valid' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM equipment_validations
WHERE processed_date >= date('now', '-7 days')
GROUP BY court_code;
"

# Clean up old log files
find . -name "*.log" -mtime +30 -delete
```

#### Monthly Tasks
```bash
# Archive old processed files
python -c "
import json, os, shutil
from datetime import datetime, timedelta

config = json.load(open('courts_config.json'))
cutoff = datetime.now() - timedelta(days=30)

for court, data in config.items():
    if court != 'global_settings' and data.get('enabled', False):
        processed_dir = data['directories']['processed_dir']
        if os.path.exists(processed_dir):
            # Archive files older than 30 days
            # Implementation depends on your archival strategy
            print(f'Checking {processed_dir} for old files...')
"

# Update court statistics
# Run comprehensive analytics report
python analytics_report.py --all-courts --output monthly_report.pdf
```

### Performance Monitoring

#### Key Metrics to Monitor
- **Processing Speed**: Files processed per hour by court
- **Success Rate**: Percentage of valid files by court
- **Error Rate**: Types and frequency of validation errors
- **Storage Usage**: Directory sizes and growth trends
- **Database Performance**: Query times and database size

#### Monitoring Script Example
```bash
#!/bin/bash
# court_monitor.sh

# Check disk usage
echo "=== Disk Usage ==="
du -sh *-inbox *-output *-invalid *-processed archive/

# Check processing queue
echo "=== Processing Queue ==="
find *-inbox -name "*.txt" | wc -l

# Check recent errors
echo "=== Recent Errors ==="
tail -20 application.log | grep ERROR

# Check database size
echo "=== Database Size ==="
ls -lh kem_validator.db

# Generate summary
echo "=== Court Status ==="
python -c "
import json
config = json.load(open('courts_config.json'))
for court, data in config.items():
    if court != 'global_settings':
        status = '✅' if data.get('enabled', False) else '❌'
        print(f'{court}: {status} {data.get(\"name\", \"Unknown\")}')
"
```

---

## 📚 Advanced Configuration Examples

### Example 1: Financial Institution Court
```json
{
  "FIN": {
    "enabled": true,
    "name": "Financial Services Court",
    "description": "Handles financial document validation with strict requirements",
    "validation_rules": {
      "min_digits": 12,
      "max_digits": 12,
      "prefix_required": true,
      "description": "Exactly 12 digits for financial account numbers"
    },
    "directories": {
      "input_dir": "fin-inbox",
      "output_dir": "fin-output",
      "invalid_dir": "fin-invalid",
      "processed_dir": "fin-processed"
    },
    "archive": {
      "enabled": true,
      "retention_months": 84,
      "compliance_required": true
    },
    "processing": {
      "batch_size": 50,
      "timeout_seconds": 600,
      "retry_attempts": 5
    }
  }
}
```

### Example 2: Legacy Document Court
```json
{
  "LEG": {
    "enabled": true,
    "name": "Legacy Document Court",
    "description": "Processes historical documents with flexible validation",
    "validation_rules": {
      "min_digits": 1,
      "max_digits": 50,
      "prefix_required": false,
      "description": "Accepts any format for legacy documents"
    },
    "directories": {
      "input_dir": "legacy-inbox",
      "output_dir": "legacy-output",
      "invalid_dir": "legacy-invalid",
      "processed_dir": "legacy-processed"
    },
    "archive": {
      "enabled": true,
      "retention_months": 120,
      "special_handling": true
    }
  }
}
```

### Example 3: High-Volume Processing Court
```json
{
  "HVL": {
    "enabled": true,
    "name": "High Volume Court",
    "description": "Optimized for processing large batches quickly",
    "validation_rules": {
      "min_digits": 8,
      "max_digits": 16,
      "prefix_required": true
    },
    "directories": {
      "input_dir": "hvl-inbox",
      "output_dir": "hvl-output",
      "invalid_dir": "hvl-invalid",
      "processed_dir": "hvl-processed"
    },
    "processing": {
      "batch_size": 500,
      "parallel_processing": true,
      "timeout_seconds": 60,
      "retry_attempts": 1
    },
    "ftp": {
      "enabled": true,
      "input_path": "/ftp/courts/hvl/incoming",
      "output_path": "/ftp/courts/hvl/processed",
      "settings": {
        "polling_interval": 10,
        "batch_size": 50
      }
    }
  }
}
```

---

## 🆘 Emergency Procedures

### Emergency Court Disable
```bash
# Quickly disable a problematic court
python -c "
import json
config = json.load(open('courts_config.json'))
config['PROBLEM_COURT']['enabled'] = False
with open('courts_config.json', 'w') as f:
    json.dump(config, f, indent=2)
print('Court disabled')
"

# Restart application
pkill -f streamlit && streamlit run streamlit_app.py
```

### Emergency Rollback to Single Court
```bash
# Backup current configuration
cp courts_config.json courts_config.json.backup

# Remove multi-court configuration
rm courts_config.json

# System will revert to KEM-only mode
# Restart application
pkill -f streamlit && streamlit run streamlit_app.py
```

### Emergency Database Recovery
```bash
# Stop application
pkill -f streamlit -f kem_validator

# Restore database from backup
cp kem_validator_backup_*.db kem_validator.db

# Restart with basic configuration
rm courts_config.json
streamlit run streamlit_app.py
```

---

## 📞 Support and Resources

### Configuration Validation Tools
```bash
# Validate complete configuration
python -c "
import json
import os
config = json.load(open('courts_config.json'))
print('Configuration Validation:')
for court, data in config.items():
    if court != 'global_settings':
        print(f'\\n{court}:')
        print(f'  Enabled: {data.get(\"enabled\", False)}')
        if 'validation_rules' in data:
            rules = data['validation_rules']
            print(f'  Range: {rules[\"min_digits\"]}-{rules[\"max_digits\"]} digits')
        if 'directories' in data:
            dirs = data['directories']
            for name, path in dirs.items():
                exists = '✅' if os.path.exists(path) else '❌'
                print(f'  {name}: {path} {exists}')
"
```

### Testing New Court Setup
```bash
# Create test file for new court
COURT_CODE="ABC"
echo -e "${COURT_CODE}\\t12345678\\tTest Equipment 1" > test_${COURT_CODE}.txt

# Process test file
python kem_validator_local.py test_${COURT_CODE}.txt

# Check results
ls -la ${COURT_CODE,,}-output/ ${COURT_CODE,,}-invalid/
```

### Documentation Resources
- **README.md**: Complete system overview
- **MIGRATION_GUIDE.md**: Upgrading from single-court
- **test_*.py**: Test suites for validation
- **sample-files/**: Example files for each court type

---

*Court Administration Guide: Complete reference for managing multi-court document validation systems.*