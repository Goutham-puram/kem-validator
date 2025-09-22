# Migration Guide: Single-Court to Multi-Court System 📈

A comprehensive guide for migrating from the legacy KEM-only system to the new multi-court architecture while ensuring zero downtime and complete backward compatibility.

## 🎯 Migration Overview

This migration is designed to be **completely safe and reversible**. Your existing KEM processing continues to work exactly as before, while optionally adding support for additional courts (SEA, TAC, or custom courts).

### Key Principles
- **Zero Breaking Changes**: Existing functionality preserved
- **Optional Upgrade**: Migrate only when ready
- **Reversible Process**: Complete rollback capability
- **Gradual Transition**: Add courts incrementally
- **No Downtime**: Continue processing during migration

---

## 🚀 Quick Migration Path

### Option 1: Keep Current Setup (Recommended)
**Do nothing!** Your existing KEM system continues working perfectly. The multi-court upgrade is backward compatible.

### Option 2: Enable Multi-Court (Optional)
Follow the step-by-step guide below to add multi-court capabilities when ready.

---

## 📋 Pre-Migration Checklist

Before starting migration, ensure you have:

- [ ] **Backup of current system** (database, configuration, directories)
- [ ] **Note current directory structure** and file locations
- [ ] **Identify all KEM processing scripts** and dependencies
- [ ] **Test environment** for validation before production migration
- [ ] **Rollback plan** prepared and understood
- [ ] **Scheduled maintenance window** (though downtime not required)

### Current System Inventory

Document your current setup:

```bash
# Note your current directories
ls -la kem-*

# Note your current database location
find . -name "*.db" -o -name "*.sqlite*"

# Note your configuration files
find . -name "config*" -o -name "*.ini" -o -name "*.json"

# Check for any custom scripts
ls -la *.py *.sh *.bat
```

---

## 🔄 Step-by-Step Migration Process

### Phase 1: System Backup and Preparation

#### 1.1 Create System Backup
```bash
# Create backup directory with timestamp
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir $BACKUP_DIR

# Backup database
cp kem_validator.db $BACKUP_DIR/kem_validator.db.backup

# Backup configuration files
cp config.ini $BACKUP_DIR/config.ini.backup 2>/dev/null || echo "No config.ini found"
cp config.json $BACKUP_DIR/config.json.backup 2>/dev/null || echo "No config.json found"

# Backup entire directory structure
tar -czf $BACKUP_DIR/directories_backup.tar.gz kem-*/ archive/ 2>/dev/null || echo "Backing up available directories"

# Backup custom scripts
cp *.py $BACKUP_DIR/ 2>/dev/null || echo "No custom Python scripts found"

echo "Backup completed in: $BACKUP_DIR"
```

#### 1.2 Verify Current System
```bash
# Test current KEM processing
python kem_validator_local.py --test

# Verify web interface (if used)
# streamlit run streamlit_app.py
# Test a few files to ensure everything works normally
```

### Phase 2: Multi-Court Configuration Setup

#### 2.1 Create Multi-Court Configuration

Create the new `courts_config.json` file. **This file's presence enables multi-court mode**.

```bash
# Create the multi-court configuration file
cat > courts_config.json << 'EOF'
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
    },
    "ftp": {
      "enabled": false,
      "input_path": "/ftp/courts/kem/incoming",
      "output_path": "/ftp/courts/kem/processed"
    }
  },
  "global_settings": {
    "default_court": "KEM",
    "archive_base_dir": "archive",
    "database_path": "kem_validator.db",
    "backup_enabled": true,
    "logging_level": "INFO"
  }
}
EOF

echo "Multi-court configuration created"
```

#### 2.2 Validate Configuration
```bash
# Test configuration loading
python -c "
import json
try:
    with open('courts_config.json') as f:
        config = json.load(f)
    print('✅ Configuration file is valid JSON')
    print(f'✅ KEM court enabled: {config[\"KEM\"][\"enabled\"]}')
    print(f'✅ Default court: {config[\"global_settings\"][\"default_court\"]}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

### Phase 3: Database Migration

#### 3.1 Database Backup and Migration
```bash
# Create database backup with timestamp
cp kem_validator.db "kem_validator_backup_$(date +%Y%m%d_%H%M%S).db"

# The database migration happens automatically when the application starts
# with the new multi-court configuration. The migration:
# 1. Adds 'court_code' column with default value 'KEM'
# 2. Preserves all existing data
# 3. Maintains all indexes and performance
```

#### 3.2 Verify Database Migration

Run the application once to trigger automatic migration:

```bash
# Start the application briefly to trigger migration
python -c "
try:
    from kem_validator_local import DatabaseManager
    db = DatabaseManager('kem_validator.db')
    print('✅ Database migration completed successfully')
except Exception as e:
    print(f'❌ Database migration error: {e}')
"
```

#### 3.3 Verify Migration Results
```bash
# Check database structure
sqlite3 kem_validator.db "PRAGMA table_info(equipment_validations);"

# Verify data preservation
sqlite3 kem_validator.db "SELECT COUNT(*) as total_records FROM equipment_validations;"

# Check court_code values
sqlite3 kem_validator.db "SELECT court_code, COUNT(*) FROM equipment_validations GROUP BY court_code;"
```

Expected output:
- All original columns present
- New `court_code` column added
- All historical records have `court_code = 'KEM'`
- Record count unchanged

### Phase 4: System Testing

#### 4.1 Test Legacy KEM Processing
```bash
# Test with existing KEM files
python kem_validator_local.py

# Verify web interface
streamlit run streamlit_app.py
# Navigate to localhost:8501 and test file upload
```

#### 4.2 Test Multi-Court Features
```bash
# Generate test files for all courts
python create_samples.py

# Test KEM sample file
# Upload sample-files/KEM_sample.txt through web interface

# Verify court detection and validation
```

#### 4.3 Run Test Suite
```bash
# Run migration compatibility tests
python test_migration.py

# Run multi-court functionality tests
python test_multi_court_basic.py

# Expected: All tests pass or skip gracefully
```

### Phase 5: Optional Additional Courts

#### 5.1 Add SEA Court (Optional)
```bash
# Edit courts_config.json to add SEA court
python -c "
import json
with open('courts_config.json', 'r') as f:
    config = json.load(f)

config['SEA'] = {
    'enabled': True,
    'name': 'Seattle Court',
    'validation_rules': {
        'min_digits': 8,
        'max_digits': 12,
        'prefix_required': True
    },
    'directories': {
        'input_dir': 'sea-inbox',
        'output_dir': 'sea-output',
        'invalid_dir': 'sea-invalid',
        'processed_dir': 'sea-processed'
    },
    'archive': {
        'enabled': True,
        'retention_months': 12
    }
}

with open('courts_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print('✅ SEA court configuration added')
"

# Create SEA directories
mkdir -p sea-inbox sea-output sea-invalid sea-processed

echo "SEA court setup completed"
```

#### 5.2 Test Additional Courts
```bash
# Test SEA court processing
# Upload sample-files/SEA_sample.txt through web interface

# Verify court-specific validation rules
# SEA should accept 8-12 digits (different from KEM's 9-13)
```

---

## 💾 Database Migration Details

### Automatic Migration Process

The database migration happens automatically when you first run the application with multi-court configuration:

1. **Backup Creation**: Automatic backup before migration
2. **Schema Update**: Adds `court_code` column with default 'KEM'
3. **Data Preservation**: All existing records preserved
4. **Index Maintenance**: All indexes maintained for performance
5. **Validation**: Migration success verification

### Manual Database Migration (Alternative)

If you prefer manual control:

```sql
-- Connect to database
sqlite3 kem_validator.db

-- Create backup table
CREATE TABLE equipment_validations_backup AS SELECT * FROM equipment_validations;

-- Add court_code column
ALTER TABLE equipment_validations ADD COLUMN court_code TEXT DEFAULT 'KEM';

-- Verify migration
SELECT court_code, COUNT(*) FROM equipment_validations GROUP BY court_code;

-- Expected result: All records have court_code = 'KEM'
```

### Database Schema Changes

**Before Migration:**
```sql
CREATE TABLE equipment_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    file_name TEXT,
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_rules TEXT
);
```

**After Migration:**
```sql
CREATE TABLE equipment_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    file_name TEXT,
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_rules TEXT,
    court_code TEXT DEFAULT 'KEM'  -- NEW COLUMN
);
```

---

## ⚙️ Configuration File Updates

### Legacy Configuration (config.ini)

Your existing configuration continues to work. Example:

```ini
[DEFAULT]
input_directory = kem-inbox
output_directory = kem-output
invalid_directory = kem-invalid
processed_directory = kem-processed
archive_directory = archive
database_path = kem_validator.db
min_digits = 9
max_digits = 13
```

### New Multi-Court Configuration (courts_config.json)

The new configuration provides more flexibility:

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
  "global_settings": {
    "default_court": "KEM",
    "archive_base_dir": "archive",
    "database_path": "kem_validator.db"
  }
}
```

### Configuration Migration Mapping

| Legacy (config.ini) | New (courts_config.json) | Notes |
|---------------------|--------------------------|-------|
| `min_digits = 9` | `"min_digits": 9` | Under KEM validation_rules |
| `max_digits = 13` | `"max_digits": 13` | Under KEM validation_rules |
| `input_directory` | `"input_dir"` | Under KEM directories |
| `output_directory` | `"output_dir"` | Under KEM directories |
| `database_path` | `"database_path"` | Under global_settings |
| `archive_directory` | `"archive_base_dir"` | Under global_settings |

---

## 🔒 Backward Compatibility Notes

### What Remains Unchanged

✅ **File Formats**: All existing file formats continue to work
✅ **Validation Rules**: KEM validation (9-13 digits) unchanged
✅ **Directory Structure**: Existing directories continue to work
✅ **Database**: All historical data preserved and accessible
✅ **Web Interface**: Same URLs and basic functionality
✅ **Command Line**: Original commands continue to work
✅ **Scripts**: Custom scripts using the API continue to work
✅ **Performance**: No performance degradation

### What's Enhanced (Optional)

🔧 **Court Selection**: New dropdown in web interface (defaults to KEM)
🔧 **Multi-Court Analytics**: New analytics views (KEM data still primary)
🔧 **Configuration**: New JSON format (legacy .ini still works)
🔧 **Database Schema**: New court_code column (existing data unaffected)
🔧 **Archive Organization**: New court-based structure (existing archives preserved)

### Compatibility Guarantees

1. **API Compatibility**: All existing function calls work unchanged
2. **File Processing**: Legacy files process exactly as before
3. **Output Format**: CSV and report formats unchanged for KEM
4. **Error Handling**: Same error messages and validation logic
5. **Performance**: Same or better processing speed

### Fallback Behavior

If multi-court configuration is missing or invalid:
- System automatically falls back to KEM-only mode
- All functionality continues as before migration
- No multi-court features available, but no errors occur

---

## 🔄 Rollback Procedures

### Emergency Rollback (Immediate)

If you encounter issues and need immediate rollback:

```bash
# Method 1: Disable multi-court by removing configuration
mv courts_config.json courts_config.json.disabled

# Restart application - it will revert to KEM-only mode
# Your system now works exactly as before migration
```

### Complete Rollback (Full Restoration)

To completely restore to pre-migration state:

#### Step 1: Stop Application
```bash
# Stop any running processes
pkill -f streamlit
pkill -f kem_validator
```

#### Step 2: Restore Database
```bash
# Find your backup
ls -la *backup*.db

# Restore database (replace with your backup filename)
cp kem_validator_backup_YYYYMMDD_HHMMSS.db kem_validator.db
```

#### Step 3: Restore Configuration
```bash
# Remove multi-court configuration
rm courts_config.json

# Restore legacy configuration if you had one
cp backup_*/config.ini.backup config.ini 2>/dev/null || echo "No legacy config to restore"
```

#### Step 4: Restore Directories (if modified)
```bash
# If you created new court directories and want to remove them
rm -rf sea-* tac-* 2>/dev/null || echo "No additional court directories found"

# Restore from backup if needed
tar -xzf backup_*/directories_backup.tar.gz 2>/dev/null || echo "No directory backup to restore"
```

#### Step 5: Verify Rollback
```bash
# Test that everything works as before
python kem_validator_local.py --test

# Check web interface
streamlit run streamlit_app.py
# Verify it shows KEM-only interface
```

### Partial Rollback (Keep Multi-Court, Disable Specific Courts)

To disable specific courts while keeping multi-court system:

```bash
# Edit configuration to disable unwanted courts
python -c "
import json
with open('courts_config.json', 'r') as f:
    config = json.load(f)

# Disable SEA court (example)
if 'SEA' in config:
    config['SEA']['enabled'] = False

# Disable TAC court (example)
if 'TAC' in config:
    config['TAC']['enabled'] = False

with open('courts_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print('✅ Courts disabled - only KEM remains active')
"
```

### Database Rollback

If database migration caused issues:

```bash
# Restore database from backup
cp kem_validator_backup_YYYYMMDD_HHMMSS.db kem_validator.db

# Or remove court_code column manually (advanced)
sqlite3 kem_validator.db "
CREATE TABLE equipment_validations_new AS
SELECT id, equipment_id, description, status, error_message, file_name, processed_date, validation_rules
FROM equipment_validations;

DROP TABLE equipment_validations;
ALTER TABLE equipment_validations_new RENAME TO equipment_validations;
"
```

---

## ✅ Migration Verification Checklist

After migration, verify these items:

### Basic Functionality
- [ ] **KEM file processing** works exactly as before
- [ ] **Web interface** loads and shows familiar interface
- [ ] **Database queries** return expected historical data
- [ ] **File uploads** process successfully
- [ ] **CSV exports** generate correct reports
- [ ] **Batch processing** handles multiple files

### Multi-Court Features (if enabled)
- [ ] **Court selector** appears in web interface
- [ ] **Court-specific validation** works correctly
- [ ] **Multi-court analytics** display appropriate data
- [ ] **Database** shows court_code values correctly
- [ ] **Sample files** process according to court rules

### Performance and Stability
- [ ] **Processing speed** same or better than before
- [ ] **Memory usage** remains reasonable
- [ ] **Error handling** graceful and informative
- [ ] **Log files** show normal operation
- [ ] **No unexpected errors** in application

### Data Integrity
- [ ] **Historical data** accessible and correct
- [ ] **Record counts** match pre-migration counts
- [ ] **File timestamps** preserved
- [ ] **Archive structure** intact
- [ ] **Backup files** created successfully

---

## 🆘 Troubleshooting Common Issues

### Issue: "Court configuration not found"
**Solution:** Ensure `courts_config.json` exists and is valid JSON
```bash
# Validate JSON syntax
python -c "import json; json.load(open('courts_config.json'))"
```

### Issue: "Database migration failed"
**Solution:** Restore from backup and retry
```bash
cp kem_validator_backup_*.db kem_validator.db
python kem_validator_local.py  # Retry migration
```

### Issue: "KEM files not processing"
**Solution:** Check KEM configuration is enabled
```bash
# Verify KEM is enabled in configuration
python -c "
import json
config = json.load(open('courts_config.json'))
print('KEM enabled:', config['KEM']['enabled'])
print('Default court:', config['global_settings']['default_court'])
"
```

### Issue: "Web interface shows errors"
**Solution:** Clear browser cache and restart application
```bash
# Restart Streamlit
pkill -f streamlit
streamlit run streamlit_app.py
```

### Issue: "Performance degraded"
**Solution:** Check database indexes
```bash
sqlite3 kem_validator.db "
.schema equipment_validations
PRAGMA index_list(equipment_validations);
"
```

---

## 📞 Support and Resources

### Getting Help
- **Test with sample files**: Use files in `sample-files/` directory
- **Check logs**: Enable debug logging for detailed information
- **Run test suite**: Execute migration tests to verify functionality
- **Use rollback**: If issues persist, use rollback procedures above

### Additional Resources
- **README.md**: Complete system documentation
- **test_migration.py**: Migration compatibility tests
- **sample-files/**: Test files for validation
- **courts_config.json.example**: Configuration template

### Best Practices
- **Test in development first**: Always test migration in non-production environment
- **Monitor after migration**: Watch for any unusual behavior
- **Keep backups**: Maintain backups until confident in migration
- **Gradual enablement**: Enable additional courts one at a time

---

## 🎉 Migration Complete!

Congratulations! You've successfully migrated to the multi-court system while preserving all existing functionality. Your KEM processing continues exactly as before, with optional multi-court capabilities available when needed.

### Next Steps
1. **Monitor system operation** for a few days
2. **Test additional courts** when ready (SEA, TAC, or custom)
3. **Explore new analytics** features in the web interface
4. **Consider FTP integration** for automated multi-court processing
5. **Remove old backups** after confirming system stability

---

*Migration Guide: Ensuring zero-disruption upgrade from single-court to multi-court document validation system.*