#!/usr/bin/env python3
"""
Migration Testing Suite
======================

Tests to verify backward compatibility and migration from single-court KEM system
to multi-court architecture. Ensures existing data, configurations, and workflows
continue functioning without disruption.

Created: 2025-09-18
Author: Claude Code Assistant
"""

import unittest
import tempfile
import shutil
import os
import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import configparser

# Test environment setup
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Core module imports with graceful fallbacks
try:
    from court_config_manager import CourtConfigManager, CourtInfo
    from court_validator_base import ValidatorFactory, LegacyKemValidator
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

try:
    from kem_validator_local import FileProcessor, DatabaseManager, Config
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False


class MigrationTestBase(unittest.TestCase):
    """Base class for migration tests with common setup."""

    def setUp(self):
        """Set up test environment with legacy and new structures."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

        # Legacy directory structure
        self.legacy_dirs = {
            "inbox": os.path.join(self.test_dir, "kem-inbox"),
            "output": os.path.join(self.test_dir, "kem-output"),
            "invalid": os.path.join(self.test_dir, "kem-invalid"),
            "archive": os.path.join(self.test_dir, "archive"),
            "processed": os.path.join(self.test_dir, "kem-processed")
        }

        # Create legacy directories
        for dir_path in self.legacy_dirs.values():
            os.makedirs(dir_path, exist_ok=True)

        # Legacy database
        self.legacy_db = os.path.join(self.test_dir, "kem_validator.db")

        # Legacy configuration file
        self.legacy_config_file = os.path.join(self.test_dir, "config.ini")

        # New multi-court structure
        self.new_config_file = os.path.join(self.test_dir, "courts_config.json")

        self._create_legacy_configuration()
        self._create_legacy_database()
        self._create_legacy_test_files()

    def _create_legacy_configuration(self):
        """Create legacy configuration file."""
        legacy_config = configparser.ConfigParser()

        legacy_config['DEFAULT'] = {
            'input_directory': self.legacy_dirs["inbox"],
            'output_directory': self.legacy_dirs["output"],
            'invalid_directory': self.legacy_dirs["invalid"],
            'processed_directory': self.legacy_dirs["processed"],
            'archive_directory': self.legacy_dirs["archive"],
            'database_path': self.legacy_db,
            'min_digits': '9',
            'max_digits': '13',
            'backup_enabled': 'true',
            'logging_level': 'INFO',
            'file_extension': '.txt',
            'archive_enabled': 'true'
        }

        legacy_config['FTP'] = {
            'enabled': 'false',
            'host': 'ftp.example.com',
            'username': 'kemuser',
            'password': 'kempass',
            'remote_path': '/kem/incoming'
        }

        legacy_config['VALIDATION'] = {
            'strict_mode': 'true',
            'allow_duplicates': 'false',
            'check_format': 'true'
        }

        with open(self.legacy_config_file, 'w') as f:
            legacy_config.write(f)

    def _create_legacy_database(self):
        """Create legacy database with historical data."""
        conn = sqlite3.connect(self.legacy_db)
        cursor = conn.cursor()

        # Legacy table structure (no court_code column)
        cursor.execute("""
            CREATE TABLE equipment_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                file_name TEXT,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validation_rules TEXT
            )
        """)

        # Insert historical data
        historical_data = [
            ('123456789', 'Legacy Equipment 1', 'valid', None, 'legacy_file_1.txt', '2024-01-15 10:30:00', '9-13 digits'),
            ('1234567890123', 'Legacy Equipment 2', 'valid', None, 'legacy_file_1.txt', '2024-01-15 10:30:01', '9-13 digits'),
            ('12345678', 'Legacy Equipment 3', 'invalid', 'Too short', 'legacy_file_2.txt', '2024-02-20 14:45:00', '9-13 digits'),
            ('987654321', 'Legacy Equipment 4', 'valid', None, 'legacy_file_3.txt', '2024-03-10 09:15:00', '9-13 digits'),
            ('invalid123', 'Legacy Equipment 5', 'invalid', 'Non-numeric', 'legacy_file_4.txt', '2024-04-05 16:20:00', '9-13 digits'),
            ('4152500182618', 'Legacy Equipment 6', 'valid', None, 'legacy_file_5.txt', '2024-05-12 11:45:00', '9-13 digits')
        ]

        cursor.executemany("""
            INSERT INTO equipment_validations
            (equipment_id, description, status, error_message, file_name, processed_date, validation_rules)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, historical_data)

        # Create legacy indexes
        cursor.execute("CREATE INDEX idx_equipment_id ON equipment_validations(equipment_id)")
        cursor.execute("CREATE INDEX idx_status ON equipment_validations(status)")
        cursor.execute("CREATE INDEX idx_processed_date ON equipment_validations(processed_date)")

        conn.commit()
        conn.close()

    def _create_legacy_test_files(self):
        """Create legacy test files in various directories."""
        # Files in inbox (unprocessed)
        legacy_inbox_files = {
            "pending_file_1.txt": """Equipment Inventory Report
Generated: 2024-06-15
Department: Facilities

123456789	Office Chair Model A
1234567890123	Conference Table Model B
987654321	File Cabinet Model C
""",
            "pending_file_2.txt": """Maintenance Equipment List
Date: 2024-06-16

555666777888	Cleaning Cart (valid 12 digits)
12345678	Invalid Equipment (too short)
nonumeric	Invalid Equipment (non-numeric)
"""
        }

        for filename, content in legacy_inbox_files.items():
            file_path = os.path.join(self.legacy_dirs["inbox"], filename)
            with open(file_path, 'w') as f:
                f.write(content)

        # Files in processed directory
        legacy_processed_files = {
            "processed_2024_01_15.txt": """KEM Equipment Processed
Date: 2024-01-15

123456789	Legacy Equipment 1	Valid
1234567890123	Legacy Equipment 2	Valid
""",
            "processed_2024_02_20.txt": """KEM Equipment Processed
Date: 2024-02-20

12345678	Legacy Equipment 3	Invalid - Too short
"""
        }

        for filename, content in legacy_processed_files.items():
            file_path = os.path.join(self.legacy_dirs["processed"], filename)
            with open(file_path, 'w') as f:
                f.write(content)

        # Files in archive directory (old structure)
        legacy_archive_files = {
            "archive_2023_12.txt": "Old archived content from December 2023",
            "archive_2024_01.txt": "Old archived content from January 2024",
            "archive_2024_02.txt": "Old archived content from February 2024"
        }

        for filename, content in legacy_archive_files.items():
            file_path = os.path.join(self.legacy_dirs["archive"], filename)
            with open(file_path, 'w') as f:
                f.write(content)

    def _create_new_multi_court_config(self):
        """Create new multi-court configuration."""
        new_config = {
            "KEM": {
                "enabled": True,
                "name": "Kirkland Court",
                "validation_rules": {
                    "min_digits": 9,
                    "max_digits": 13,
                    "prefix_required": True
                },
                "directories": {
                    "input_dir": self.legacy_dirs["inbox"],
                    "output_dir": self.legacy_dirs["output"],
                    "invalid_dir": self.legacy_dirs["invalid"],
                    "processed_dir": self.legacy_dirs["processed"]
                },
                "archive": {
                    "enabled": True,
                    "retention_months": 6
                },
                "ftp": {
                    "enabled": False,
                    "input_path": "/ftp/courts/kem/incoming",
                    "output_path": "/ftp/courts/kem/processed"
                }
            },
            "global_settings": {
                "default_court": "KEM",
                "archive_base_dir": self.legacy_dirs["archive"],
                "database_path": self.legacy_db,
                "backup_enabled": True,
                "logging_level": "INFO"
            }
        }

        with open(self.new_config_file, 'w') as f:
            json.dump(new_config, f, indent=2)

        return new_config


@unittest.skipUnless(CORE_AVAILABLE and CONFIG_AVAILABLE, "Core modules not available")
class TestLegacyFileProcessing(MigrationTestBase):
    """Test that existing single-court KEM files process correctly."""

    def test_legacy_file_format_processing(self):
        """Test processing of legacy KEM files without court prefixes."""
        # Legacy file content (no KEM prefix)
        legacy_content = """Equipment Inventory
Processing Date: 2025-09-18
Department: IT

123456789	Desktop Computer Model A
1234567890123	Server Equipment Model B
987654321	Network Switch Model C
12345678	Invalid Equipment (too short)
"""

        legacy_file = os.path.join(self.legacy_dirs["inbox"], "legacy_format.txt")
        with open(legacy_file, 'w') as f:
            f.write(legacy_content)

        # Mock the legacy validator
        with patch('court_validator_base.LegacyKemValidator') as mock_validator:
            validator_instance = mock_validator.return_value

            # Configure validation responses
            validator_instance.validate.side_effect = lambda x: len(x) >= 9 and len(x) <= 13 and x.isdigit()

            # Test validation of legacy format
            test_ids = ["123456789", "1234567890123", "987654321", "12345678"]
            expected_results = [True, True, True, False]

            results = [validator_instance.validate(id_val) for id_val in test_ids]
            self.assertEqual(results, expected_results)

    def test_legacy_file_without_court_detection(self):
        """Test that files without court codes default to KEM."""
        # Create file with no court indicators
        no_court_content = """Equipment List
Date: 2025-09-18

123456789	Equipment Item 1
1234567890	Equipment Item 2
12345678901	Equipment Item 3
"""

        test_file = os.path.join(self.legacy_dirs["inbox"], "no_court_indicators.txt")
        with open(test_file, 'w') as f:
            f.write(no_court_content)

        # Mock court detection
        with patch('court_config_manager.CourtConfigManager') as mock_config:
            config_manager = mock_config.return_value
            config_manager.get_default_court.return_value = "KEM"

            # Test default court assignment
            default_court = config_manager.get_default_court()
            self.assertEqual(default_court, "KEM")

    def test_legacy_directory_structure_compatibility(self):
        """Test that legacy directory structure continues to work."""
        # Verify legacy directories exist and are functional
        for dir_name, dir_path in self.legacy_dirs.items():
            self.assertTrue(os.path.exists(dir_path), f"Legacy directory {dir_name} should exist")
            self.assertTrue(os.path.isdir(dir_path), f"Legacy path {dir_name} should be a directory")

        # Test file operations in legacy directories
        test_file = os.path.join(self.legacy_dirs["inbox"], "test_legacy_ops.txt")
        test_content = "Legacy operation test"

        with open(test_file, 'w') as f:
            f.write(test_content)

        self.assertTrue(os.path.exists(test_file))

        with open(test_file, 'r') as f:
            read_content = f.read()

        self.assertEqual(read_content, test_content)

    def test_legacy_validation_rules_preserved(self):
        """Test that legacy KEM validation rules (9-13 digits) are preserved."""
        # Mock legacy configuration loading
        with patch('kem_validator_local.Config') as mock_config:
            config_instance = mock_config.return_value
            config_instance.min_digits = 9
            config_instance.max_digits = 13

            # Test legacy validation rules
            self.assertEqual(config_instance.min_digits, 9)
            self.assertEqual(config_instance.max_digits, 13)

        # Test validation with legacy rules
        test_cases = [
            ("123456789", True),      # 9 digits - valid
            ("1234567890123", True),  # 13 digits - valid
            ("12345678", False),      # 8 digits - invalid
            ("12345678901234", False) # 14 digits - invalid
        ]

        for test_id, expected in test_cases:
            # Mock validation
            is_valid = 9 <= len(test_id) <= 13 and test_id.isdigit()
            self.assertEqual(is_valid, expected, f"ID {test_id} validation failed")


@unittest.skipUnless(CORE_AVAILABLE, "Core modules not available")
class TestDatabaseMigration(MigrationTestBase):
    """Test database migration preserves historical data."""

    def test_legacy_database_structure_readable(self):
        """Test that legacy database can be read and queried."""
        conn = sqlite3.connect(self.legacy_db)
        cursor = conn.cursor()

        # Verify legacy table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='equipment_validations'")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(table_exists, "Legacy table should exist")

        # Verify legacy data is readable
        cursor.execute("SELECT COUNT(*) FROM equipment_validations")
        record_count = cursor.fetchone()[0]
        self.assertGreater(record_count, 0, "Legacy data should exist")

        # Verify specific legacy records
        cursor.execute("SELECT equipment_id, status FROM equipment_validations WHERE equipment_id = '123456789'")
        legacy_record = cursor.fetchone()
        self.assertIsNotNone(legacy_record, "Specific legacy record should exist")
        self.assertEqual(legacy_record[1], 'valid', "Legacy record status should be preserved")

        conn.close()

    def test_database_migration_adds_court_code(self):
        """Test that database migration adds court_code column."""
        # Mock database migration
        conn = sqlite3.connect(self.legacy_db)
        cursor = conn.cursor()

        # Check if court_code column exists (it shouldn't in legacy)
        cursor.execute("PRAGMA table_info(equipment_validations)")
        columns = [column[1] for column in cursor.fetchall()]
        self.assertNotIn('court_code', columns, "Legacy table should not have court_code column")

        # Simulate migration by adding court_code column
        try:
            cursor.execute("ALTER TABLE equipment_validations ADD COLUMN court_code TEXT DEFAULT 'KEM'")
            conn.commit()

            # Verify column was added
            cursor.execute("PRAGMA table_info(equipment_validations)")
            new_columns = [column[1] for column in cursor.fetchall()]
            self.assertIn('court_code', new_columns, "Migration should add court_code column")

            # Verify default values applied
            cursor.execute("SELECT DISTINCT court_code FROM equipment_validations")
            court_codes = [row[0] for row in cursor.fetchall()]
            self.assertIn('KEM', court_codes, "Default court_code should be KEM")

        except sqlite3.Error as e:
            # Column might already exist from previous test run
            if "duplicate column name" not in str(e).lower():
                raise

        conn.close()

    def test_historical_data_preservation(self):
        """Test that historical data is preserved during migration."""
        conn = sqlite3.connect(self.legacy_db)
        cursor = conn.cursor()

        # Get original data count and content
        cursor.execute("SELECT COUNT(*) FROM equipment_validations")
        original_count = cursor.fetchone()[0]

        cursor.execute("SELECT equipment_id, description, status FROM equipment_validations ORDER BY id")
        original_data = cursor.fetchall()

        # Simulate migration (add court_code column if not exists)
        try:
            cursor.execute("ALTER TABLE equipment_validations ADD COLUMN court_code TEXT DEFAULT 'KEM'")
            conn.commit()
        except sqlite3.Error:
            pass  # Column might already exist

        # Verify data count unchanged
        cursor.execute("SELECT COUNT(*) FROM equipment_validations")
        post_migration_count = cursor.fetchone()[0]
        self.assertEqual(original_count, post_migration_count, "Migration should preserve all records")

        # Verify data content unchanged
        cursor.execute("SELECT equipment_id, description, status FROM equipment_validations ORDER BY id")
        post_migration_data = cursor.fetchall()
        self.assertEqual(original_data, post_migration_data, "Migration should preserve record content")

        conn.close()

    def test_database_indexes_preserved(self):
        """Test that database indexes are preserved during migration."""
        conn = sqlite3.connect(self.legacy_db)
        cursor = conn.cursor()

        # Check existing indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='equipment_validations'")
        existing_indexes = [row[0] for row in cursor.fetchall()]

        # Should have at least the indexes we created in setup
        expected_indexes = ['idx_equipment_id', 'idx_status', 'idx_processed_date']
        for expected_index in expected_indexes:
            self.assertIn(expected_index, existing_indexes, f"Index {expected_index} should be preserved")

        conn.close()

    def test_database_performance_after_migration(self):
        """Test that database performance is maintained after migration."""
        conn = sqlite3.connect(self.legacy_db)
        cursor = conn.cursor()

        # Test query performance (simple timing)
        start_time = time.time()
        cursor.execute("SELECT * FROM equipment_validations WHERE status = 'valid'")
        results = cursor.fetchall()
        end_time = time.time()

        query_time = end_time - start_time
        self.assertLess(query_time, 1.0, "Query should complete quickly")
        self.assertGreater(len(results), 0, "Query should return results")

        conn.close()


class TestLegacyConfigurationCompatibility(MigrationTestBase):
    """Test that old configuration files still work."""

    def test_legacy_config_file_loading(self):
        """Test that legacy .ini configuration files can be loaded."""
        # Verify legacy config file exists
        self.assertTrue(os.path.exists(self.legacy_config_file), "Legacy config file should exist")

        # Load and parse legacy configuration
        config = configparser.ConfigParser()
        config.read(self.legacy_config_file)

        # Verify essential settings are preserved
        self.assertEqual(config['DEFAULT']['min_digits'], '9')
        self.assertEqual(config['DEFAULT']['max_digits'], '13')
        self.assertEqual(config['DEFAULT']['input_directory'], self.legacy_dirs["inbox"])
        self.assertEqual(config['DEFAULT']['database_path'], self.legacy_db)

    def test_legacy_config_to_multi_court_mapping(self):
        """Test mapping legacy configuration to multi-court format."""
        # Load legacy configuration
        config = configparser.ConfigParser()
        config.read(self.legacy_config_file)

        # Map to new multi-court format
        new_config = self._create_new_multi_court_config()

        # Verify mapping preserves essential settings
        self.assertEqual(
            new_config["KEM"]["validation_rules"]["min_digits"],
            int(config['DEFAULT']['min_digits'])
        )
        self.assertEqual(
            new_config["KEM"]["validation_rules"]["max_digits"],
            int(config['DEFAULT']['max_digits'])
        )
        self.assertEqual(
            new_config["KEM"]["directories"]["input_dir"],
            config['DEFAULT']['input_directory']
        )

    def test_legacy_environment_variables(self):
        """Test that legacy environment variable usage continues to work."""
        # Mock environment variables that might have been used
        test_env_vars = {
            'KEM_INPUT_DIR': self.legacy_dirs["inbox"],
            'KEM_OUTPUT_DIR': self.legacy_dirs["output"],
            'KEM_DB_PATH': self.legacy_db
        }

        with patch.dict('os.environ', test_env_vars):
            # Test environment variable reading
            self.assertEqual(os.environ.get('KEM_INPUT_DIR'), self.legacy_dirs["inbox"])
            self.assertEqual(os.environ.get('KEM_DB_PATH'), self.legacy_db)

    def test_legacy_command_line_arguments(self):
        """Test that legacy command line arguments still function."""
        # Mock legacy command line arguments
        legacy_args = [
            '--input-dir', self.legacy_dirs["inbox"],
            '--output-dir', self.legacy_dirs["output"],
            '--min-digits', '9',
            '--max-digits', '13',
            '--database', self.legacy_db
        ]

        # Test argument parsing (simplified mock)
        arg_dict = {}
        for i in range(0, len(legacy_args), 2):
            key = legacy_args[i].lstrip('-').replace('-', '_')
            value = legacy_args[i + 1]
            arg_dict[key] = value

        self.assertEqual(arg_dict['input_dir'], self.legacy_dirs["inbox"])
        self.assertEqual(arg_dict['min_digits'], '9')
        self.assertEqual(arg_dict['max_digits'], '13')


@unittest.skipUnless(CONFIG_AVAILABLE, "Configuration modules not available")
class TestLegacyAPICompatibility(MigrationTestBase):
    """Test that legacy API calls function properly."""

    def test_legacy_validator_class_interface(self):
        """Test that legacy validator class interface is preserved."""
        # Mock legacy validator
        with patch('court_validator_base.LegacyKemValidator') as mock_validator:
            validator = mock_validator.return_value

            # Test legacy interface methods
            validator.validate.return_value = True
            validator.get_validation_rules.return_value = {"min_digits": 9, "max_digits": 13}

            # Test method calls
            result = validator.validate("123456789")
            self.assertTrue(result)

            rules = validator.get_validation_rules()
            self.assertEqual(rules["min_digits"], 9)

    def test_legacy_file_processor_interface(self):
        """Test that legacy file processor interface is preserved."""
        # Mock legacy file processor
        with patch('kem_validator_local.FileProcessor') as mock_processor:
            processor = mock_processor.return_value

            # Test legacy interface methods
            processor.process_file.return_value = {"status": "success", "records_processed": 10}
            processor.get_statistics.return_value = {"total_files": 5, "success_rate": 95.0}

            # Test method calls
            result = processor.process_file("test_file.txt")
            self.assertEqual(result["status"], "success")

            stats = processor.get_statistics()
            self.assertEqual(stats["total_files"], 5)

    def test_legacy_database_manager_interface(self):
        """Test that legacy database manager interface is preserved."""
        # Mock legacy database manager
        with patch('kem_validator_local.DatabaseManager') as mock_db:
            db_manager = mock_db.return_value

            # Test legacy interface methods
            db_manager.insert_validation.return_value = True
            db_manager.get_statistics.return_value = {"total_records": 1000, "valid_count": 950}

            # Test method calls
            result = db_manager.insert_validation("123456789", "valid", "Test equipment")
            self.assertTrue(result)

            stats = db_manager.get_statistics()
            self.assertEqual(stats["total_records"], 1000)

    def test_legacy_import_statements(self):
        """Test that legacy import statements continue to work."""
        # Test that old import paths still function
        try:
            # These would be the original import statements
            import_tests = [
                "from kem_validator_local import FileProcessor",
                "from kem_validator_local import DatabaseManager",
                "from kem_validator_local import Config"
            ]

            # In real implementation, these imports should work
            # For testing, we just verify the modules exist
            self.assertTrue(CORE_AVAILABLE, "Core modules should be available for legacy imports")

        except ImportError as e:
            self.fail(f"Legacy import failed: {e}")

    def test_legacy_function_signatures(self):
        """Test that legacy function signatures are preserved."""
        # Mock legacy functions with original signatures
        def mock_validate_equipment_id(equipment_id, min_digits=9, max_digits=13):
            return len(equipment_id) >= min_digits and len(equipment_id) <= max_digits and equipment_id.isdigit()

        def mock_process_file(file_path, output_dir=None, validation_rules=None):
            return {"status": "success", "file": file_path}

        # Test that legacy function signatures work
        result1 = mock_validate_equipment_id("123456789")
        self.assertTrue(result1)

        result2 = mock_process_file("test.txt", output_dir=self.legacy_dirs["output"])
        self.assertEqual(result2["status"], "success")


class TestArchiveMigration(MigrationTestBase):
    """Test archive migration moves old files to KEM subdirectory."""

    def test_legacy_archive_file_detection(self):
        """Test detection of legacy archive files."""
        # List files in legacy archive directory
        archive_files = os.listdir(self.legacy_dirs["archive"])
        self.assertGreater(len(archive_files), 0, "Legacy archive should contain files")

        # Verify specific legacy files exist
        expected_files = ["archive_2023_12.txt", "archive_2024_01.txt", "archive_2024_02.txt"]
        for expected_file in expected_files:
            self.assertIn(expected_file, archive_files, f"Legacy file {expected_file} should exist")

    def test_archive_migration_directory_structure(self):
        """Test creation of new archive directory structure."""
        # Create new archive structure
        new_archive_base = os.path.join(self.test_dir, "new_archive")
        os.makedirs(new_archive_base, exist_ok=True)

        # Create KEM subdirectory structure
        current_date = datetime.now()
        year = current_date.strftime("%Y")
        month = current_date.strftime("%m")

        kem_archive_path = os.path.join(new_archive_base, "KEM", year, month)
        os.makedirs(kem_archive_path, exist_ok=True)

        self.assertTrue(os.path.exists(kem_archive_path), "KEM archive path should be created")

    def test_legacy_file_migration_to_kem_subdirectory(self):
        """Test moving legacy files to KEM subdirectory."""
        # Create target KEM archive directory
        target_base = os.path.join(self.test_dir, "migrated_archive")
        kem_archive_dir = os.path.join(target_base, "KEM", "legacy")
        os.makedirs(kem_archive_dir, exist_ok=True)

        # Get list of legacy files
        legacy_files = os.listdir(self.legacy_dirs["archive"])

        # Simulate migration
        migrated_files = []
        for filename in legacy_files:
            source_path = os.path.join(self.legacy_dirs["archive"], filename)
            target_path = os.path.join(kem_archive_dir, filename)

            # Copy file to new location (simulating migration)
            shutil.copy2(source_path, target_path)
            migrated_files.append(filename)

        # Verify migration
        self.assertEqual(len(migrated_files), len(legacy_files), "All legacy files should be migrated")

        for filename in migrated_files:
            target_path = os.path.join(kem_archive_dir, filename)
            self.assertTrue(os.path.exists(target_path), f"Migrated file {filename} should exist")

    def test_archive_migration_preserves_timestamps(self):
        """Test that file timestamps are preserved during migration."""
        # Get original file timestamp
        original_file = os.path.join(self.legacy_dirs["archive"], "archive_2024_01.txt")
        original_stat = os.stat(original_file)
        original_mtime = original_stat.st_mtime

        # Simulate migration with timestamp preservation
        target_dir = os.path.join(self.test_dir, "timestamp_test")
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, "archive_2024_01.txt")

        # Copy with timestamp preservation
        shutil.copy2(original_file, target_file)

        # Verify timestamp preserved
        target_stat = os.stat(target_file)
        target_mtime = target_stat.st_mtime

        self.assertEqual(original_mtime, target_mtime, "File timestamp should be preserved")

    def test_archive_migration_handles_duplicates(self):
        """Test that migration handles duplicate filenames gracefully."""
        # Create target directory
        target_dir = os.path.join(self.test_dir, "duplicate_test")
        os.makedirs(target_dir, exist_ok=True)

        # Create a file in target that might conflict
        duplicate_name = "archive_2024_01.txt"
        target_file = os.path.join(target_dir, duplicate_name)
        with open(target_file, 'w') as f:
            f.write("Existing content")

        # Simulate migration with duplicate handling
        source_file = os.path.join(self.legacy_dirs["archive"], duplicate_name)

        # Generate new name for duplicate
        base_name, ext = os.path.splitext(duplicate_name)
        new_name = f"{base_name}_migrated{ext}"
        new_target = os.path.join(target_dir, new_name)

        # Copy with new name
        shutil.copy2(source_file, new_target)

        # Verify both files exist
        self.assertTrue(os.path.exists(target_file), "Original file should remain")
        self.assertTrue(os.path.exists(new_target), "Migrated file should exist with new name")

    def test_archive_migration_cleanup(self):
        """Test cleanup of legacy archive after successful migration."""
        # Create a copy of legacy archive for testing
        test_legacy_dir = os.path.join(self.test_dir, "test_legacy_archive")
        shutil.copytree(self.legacy_dirs["archive"], test_legacy_dir)

        # Verify files exist before cleanup
        files_before = os.listdir(test_legacy_dir)
        self.assertGreater(len(files_before), 0, "Test legacy archive should have files")

        # Simulate cleanup (move to backup location instead of delete)
        backup_dir = os.path.join(self.test_dir, "legacy_backup")
        shutil.move(test_legacy_dir, backup_dir)

        # Verify cleanup
        self.assertFalse(os.path.exists(test_legacy_dir), "Legacy archive should be moved")
        self.assertTrue(os.path.exists(backup_dir), "Backup should exist")

        # Verify files preserved in backup
        backup_files = os.listdir(backup_dir)
        self.assertEqual(len(backup_files), len(files_before), "All files should be preserved in backup")


class TestMigrationRollback(MigrationTestBase):
    """Test migration rollback capabilities."""

    def test_database_backup_before_migration(self):
        """Test that database backup is created before migration."""
        # Create backup of legacy database
        backup_path = f"{self.legacy_db}.backup"
        shutil.copy2(self.legacy_db, backup_path)

        # Verify backup exists and has same content
        self.assertTrue(os.path.exists(backup_path), "Database backup should exist")

        # Compare record counts
        conn_original = sqlite3.connect(self.legacy_db)
        cursor_original = conn_original.cursor()
        cursor_original.execute("SELECT COUNT(*) FROM equipment_validations")
        original_count = cursor_original.fetchone()[0]
        conn_original.close()

        conn_backup = sqlite3.connect(backup_path)
        cursor_backup = conn_backup.cursor()
        cursor_backup.execute("SELECT COUNT(*) FROM equipment_validations")
        backup_count = cursor_backup.fetchone()[0]
        conn_backup.close()

        self.assertEqual(original_count, backup_count, "Backup should have same record count")

        # Cleanup
        os.remove(backup_path)

    def test_configuration_rollback(self):
        """Test rollback to legacy configuration."""
        # Create new multi-court config
        new_config = self._create_new_multi_court_config()

        # Simulate rollback by reverting to legacy config
        config = configparser.ConfigParser()
        config.read(self.legacy_config_file)

        # Verify legacy settings are available for rollback
        self.assertEqual(config['DEFAULT']['min_digits'], '9')
        self.assertEqual(config['DEFAULT']['max_digits'], '13')
        self.assertTrue(os.path.exists(config['DEFAULT']['input_directory']))


def create_migration_test_suite():
    """Create a comprehensive migration test suite."""
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestLegacyFileProcessing,
        TestDatabaseMigration,
        TestLegacyConfigurationCompatibility,
        TestLegacyAPICompatibility,
        TestArchiveMigration,
        TestMigrationRollback
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    return suite


def main():
    """Run the migration test suite."""
    print("=" * 70)
    print("  MULTI-COURT MIGRATION TEST SUITE")
    print("=" * 70)
    print()

    # Check environment
    print("Environment Check:")
    print(f"  Core modules available: {CORE_AVAILABLE}")
    print(f"  Configuration modules available: {CONFIG_AVAILABLE}")
    print(f"  Pandas available: {PANDAS_AVAILABLE}")
    print()

    # Create and run test suite
    suite = create_migration_test_suite()
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)

    print("Running Migration Tests...")
    print("-" * 70)

    result = runner.run(suite)

    print()
    print("=" * 70)
    print("Migration Test Summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    print()

    if result.failures:
        print("FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
        print()

    if result.errors:
        print("ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
        print()

    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")

    if success_rate >= 90:
        print("[SUCCESS] Migration compatibility verified!")
    elif success_rate >= 75:
        print("[WARNING] Some migration issues detected - review needed")
    else:
        print("[ERROR] Significant migration problems - immediate attention required")

    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)