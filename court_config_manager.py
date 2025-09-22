"""
Court Configuration Manager
Provides centralized access to court configurations with validation and caching
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CourtInfo:
    """Structured court information"""
    code: str
    name: str
    full_name: str
    enabled: bool
    validation_rules: Dict[str, Any]
    directories: Dict[str, str]
    ftp_config: Dict[str, Any]
    database: Dict[str, Any]
    file_naming: Dict[str, str]

    def __post_init__(self):
        """Validate court configuration after initialization"""
        self._validate_config()

    def _validate_config(self):
        """Validate that court configuration is complete and valid"""
        # Required validation rule fields
        required_validation_fields = {'min_digits', 'max_digits', 'prefix', 'prefix_required'}
        missing_validation = required_validation_fields - set(self.validation_rules.keys())
        if missing_validation:
            raise ValueError(f"Court {self.code} missing validation rules: {missing_validation}")

        # Validate digit ranges
        min_digits = self.validation_rules.get('min_digits')
        max_digits = self.validation_rules.get('max_digits')
        if not isinstance(min_digits, int) or not isinstance(max_digits, int):
            raise ValueError(f"Court {self.code} digit ranges must be integers")
        if min_digits < 1 or max_digits < min_digits:
            raise ValueError(f"Court {self.code} invalid digit range: {min_digits}-{max_digits}")

        # Required directory fields
        required_dir_fields = {'input_dir', 'output_dir', 'processed_dir', 'invalid_dir'}
        missing_dirs = required_dir_fields - set(self.directories.keys())
        if missing_dirs:
            raise ValueError(f"Court {self.code} missing directories: {missing_dirs}")

        # Required FTP config fields (if FTP is enabled)
        if self.ftp_config.get('enabled', False):
            required_ftp_fields = {'base_path', 'inbox_path', 'results_path'}
            missing_ftp = required_ftp_fields - set(self.ftp_config.keys())
            if missing_ftp:
                raise ValueError(f"Court {self.code} missing FTP config: {missing_ftp}")

    def get_validation_rule(self, rule_name: str, default: Any = None) -> Any:
        """Get specific validation rule with default fallback"""
        return self.validation_rules.get(rule_name, default)

    def get_directory(self, dir_type: str) -> str:
        """Get directory path for specified type"""
        if dir_type not in self.directories:
            raise ValueError(f"Directory type '{dir_type}' not configured for court {self.code}")
        return self.directories[dir_type]

    def get_ftp_path(self, path_type: str) -> str:
        """Get FTP path for specified type"""
        key = f"{path_type}_path"
        if key not in self.ftp_config:
            raise ValueError(f"FTP path type '{path_type}' not configured for court {self.code}")
        return self.ftp_config[key]

    def is_ftp_enabled(self) -> bool:
        """Check if FTP is enabled for this court"""
        return self.ftp_config.get('enabled', False)


class CourtConfigManager:
    """Centralized manager for court configurations"""

    def __init__(self, config_path: str = "courts_config.json"):
        self.config_path = config_path
        self.config_data: Dict = {}
        self.courts_cache: Dict[str, CourtInfo] = {}
        self.last_modified: Optional[float] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from JSON file with validation"""
        try:
            config_file = Path(self.config_path)

            if not config_file.exists():
                logger.warning(f"Courts config file not found: {self.config_path}")
                self._create_default_config()
                return

            # Check if file has been modified since last load
            current_mtime = config_file.stat().st_mtime
            if self.last_modified and current_mtime <= self.last_modified:
                return  # No need to reload

            with open(config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)

            self.last_modified = current_mtime
            self.courts_cache.clear()  # Clear cache after reload

            # Validate the configuration structure
            self._validate_config_structure()

            logger.info(f"Loaded courts configuration from {self.config_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in courts config: {e}")
            raise ValueError(f"Invalid JSON in courts configuration: {e}")
        except Exception as e:
            logger.error(f"Error loading courts config: {e}")
            raise

    def _create_default_config(self) -> None:
        """Create minimal default configuration for backward compatibility"""
        logger.info("Creating default courts configuration")

        default_config = {
            "version": "1.0",
            "default_court": "KEM",
            "courts": {
                "KEM": {
                    "name": "Kirkland Court",
                    "full_name": "Kirkland Equipment Management",
                    "enabled": True,
                    "validation_rules": {
                        "min_digits": 9,
                        "max_digits": 13,
                        "prefix_required": True,
                        "prefix": "KEM",
                        "allow_alphanumeric": True,
                        "case_sensitive": False
                    },
                    "directories": {
                        "input_dir": "kem-inbox",
                        "output_dir": "kem-results",
                        "processed_dir": "processed-archive",
                        "invalid_dir": "invalid-archive"
                    },
                    "ftp_config": {
                        "enabled": False,
                        "base_path": "/PAMarchive/SeaTac/",
                        "inbox_path": "/PAMarchive/SeaTac/kem-inbox/",
                        "results_path": "/PAMarchive/SeaTac/kem-results/",
                        "processed_path": "/PAMarchive/SeaTac/processed-archive/",
                        "invalid_path": "/PAMarchive/SeaTac/invalid-archive/"
                    },
                    "database": {
                        "table_suffix": "kem",
                        "retention_days": 365
                    },
                    "file_naming": {
                        "csv_prefix": "kem_validation",
                        "archive_prefix": "kem_archive"
                    }
                }
            },
            "global_settings": {
                "auto_detect_court": True,
                "fallback_to_default": True,
                "create_directories": True
            }
        }

        self.config_data = default_config

        # Save default config to file
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default courts configuration at {self.config_path}")
        except Exception as e:
            logger.warning(f"Could not save default config: {e}")

    def _validate_config_structure(self) -> None:
        """Validate the overall configuration structure"""
        required_top_level = {'courts', 'default_court'}
        missing_top_level = required_top_level - set(self.config_data.keys())
        if missing_top_level:
            raise ValueError(f"Missing required configuration sections: {missing_top_level}")

        # Validate default court exists
        default_court = self.config_data.get('default_court')
        if default_court not in self.config_data.get('courts', {}):
            raise ValueError(f"Default court '{default_court}' not found in courts configuration")

        # Validate each court configuration by attempting to create CourtInfo objects
        courts = self.config_data.get('courts', {})
        if not courts:
            raise ValueError("No courts configured")

        for court_code, court_config in courts.items():
            try:
                self._create_court_info(court_code, court_config)
            except Exception as e:
                logger.error(f"Invalid configuration for court {court_code}: {e}")
                raise ValueError(f"Invalid configuration for court {court_code}: {e}")

        logger.info(f"Configuration validation passed for {len(courts)} courts")

    def _create_court_info(self, court_code: str, court_config: Dict) -> CourtInfo:
        """Create CourtInfo object with validation"""
        try:
            return CourtInfo(
                code=court_code,
                name=court_config.get('name', court_code),
                full_name=court_config.get('full_name', court_config.get('name', court_code)),
                enabled=court_config.get('enabled', False),
                validation_rules=court_config.get('validation_rules', {}),
                directories=court_config.get('directories', {}),
                ftp_config=court_config.get('ftp_config', {}),
                database=court_config.get('database', {}),
                file_naming=court_config.get('file_naming', {})
            )
        except Exception as e:
            raise ValueError(f"Failed to create court info for {court_code}: {e}")

    def reload_config(self) -> None:
        """Force reload configuration from file"""
        self.last_modified = None
        self._load_config()

    def get_court(self, court_code: str) -> Optional[CourtInfo]:
        """Get court configuration by code with caching"""
        # Ensure config is up to date
        self._load_config()

        if court_code in self.courts_cache:
            return self.courts_cache[court_code]

        courts = self.config_data.get('courts', {})
        if court_code not in courts:
            return None

        try:
            court_info = self._create_court_info(court_code, courts[court_code])
            self.courts_cache[court_code] = court_info
            return court_info
        except Exception as e:
            logger.error(f"Error creating court info for {court_code}: {e}")
            return None

    def get_court_or_default(self, court_code: Optional[str] = None) -> CourtInfo:
        """Get court configuration, falling back to default if not found or not specified"""
        if court_code:
            court = self.get_court(court_code)
            if court and court.enabled:
                return court
            else:
                logger.warning(f"Court '{court_code}' not found or disabled, using default")

        default_court_code = self.get_default_court()
        default_court = self.get_court(default_court_code)

        if not default_court:
            raise ValueError(f"Default court '{default_court_code}' not found")

        return default_court

    def get_enabled_courts(self) -> List[CourtInfo]:
        """Get list of all enabled courts"""
        self._load_config()

        enabled_courts = []
        courts = self.config_data.get('courts', {})

        for court_code, court_config in courts.items():
            if court_config.get('enabled', False):
                court_info = self.get_court(court_code)
                if court_info:
                    enabled_courts.append(court_info)

        return enabled_courts

    def get_enabled_court_codes(self) -> List[str]:
        """Get list of enabled court codes"""
        return [court.code for court in self.get_enabled_courts()]

    def get_all_courts(self) -> dict:
        """Get dict of all courts (enabled and disabled)"""
        self._load_config()
        courts = self.config_data.get('courts', {})
        return {court_code: self.get_court(court_code) for court_code in courts.keys() if self.get_court(court_code)}

    def get_default_court(self) -> str:
        """Get the default court code"""
        return self.config_data.get('default_court', 'KEM')

    def is_court_enabled(self, court_code: str) -> bool:
        """Check if specific court is enabled"""
        court = self.get_court(court_code)
        return court is not None and court.enabled

    def get_global_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get global configuration setting"""
        return self.config_data.get('global_settings', {}).get(setting_name, default)

    def get_court_detection_config(self) -> Dict[str, Any]:
        """Get court detection configuration"""
        return self.config_data.get('court_detection', {})

    def detect_court_from_path(self, file_path: str) -> str:
        """Detect court code from file path using configured patterns"""
        detection_config = self.get_court_detection_config()
        path_patterns = detection_config.get('path_patterns', {})

        file_path_lower = file_path.lower()

        # Check each court's path patterns
        for court_code, patterns in path_patterns.items():
            if self.is_court_enabled(court_code):
                for pattern in patterns:
                    if pattern.lower() in file_path_lower:
                        return court_code

        # Return default court if no match
        return self.get_default_court()

    def detect_court_from_content(self, content: str) -> str:
        """Detect court code from file content using configured patterns"""
        import re

        detection_config = self.get_court_detection_config()
        content_prefixes = detection_config.get('content_prefixes', {})

        # Check each court's content patterns
        for court_code, patterns in content_prefixes.items():
            if self.is_court_enabled(court_code):
                for pattern in patterns:
                    if re.search(pattern, content, re.MULTILINE):
                        return court_code

        # Return default court if no match
        return self.get_default_court()

    def validate_configuration(self) -> Dict[str, List[str]]:
        """Validate entire configuration and return validation results"""
        validation_results = {
            'errors': [],
            'warnings': [],
            'info': []
        }

        try:
            self._load_config()

            # Check if at least one court is enabled
            enabled_courts = self.get_enabled_courts()
            if not enabled_courts:
                validation_results['errors'].append("No courts are enabled")
            else:
                validation_results['info'].append(f"Found {len(enabled_courts)} enabled courts")

            # Validate default court
            default_court = self.get_default_court()
            if not self.is_court_enabled(default_court):
                validation_results['warnings'].append(f"Default court '{default_court}' is not enabled")

            # Check for configuration completeness
            courts = self.config_data.get('courts', {})
            for court_code, court_config in courts.items():
                try:
                    court_info = self._create_court_info(court_code, court_config)
                    if court_info.enabled:
                        validation_results['info'].append(f"Court {court_code} configuration is valid")
                except Exception as e:
                    validation_results['errors'].append(f"Court {court_code}: {e}")

            # Check for required global settings
            global_settings = self.config_data.get('global_settings', {})
            if not global_settings:
                validation_results['warnings'].append("No global settings configured")

        except Exception as e:
            validation_results['errors'].append(f"Configuration validation failed: {e}")

        return validation_results

    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        try:
            enabled_courts = self.get_enabled_courts()
            all_courts = self.get_all_courts()

            return {
                'config_file': self.config_path,
                'config_exists': Path(self.config_path).exists(),
                'last_modified': datetime.fromtimestamp(self.last_modified) if self.last_modified else None,
                'default_court': self.get_default_court(),
                'total_courts': len(all_courts),
                'enabled_courts': len(enabled_courts),
                'enabled_court_codes': [court.code for court in enabled_courts],
                'disabled_courts': [court.code for court in all_courts if not court.enabled],
                'auto_detect_enabled': self.get_global_setting('auto_detect_court', False),
                'fallback_to_default': self.get_global_setting('fallback_to_default', True)
            }
        except Exception as e:
            return {
                'error': str(e),
                'config_file': self.config_path,
                'config_exists': Path(self.config_path).exists()
            }


# Singleton instance for global access
_config_manager: Optional[CourtConfigManager] = None


def get_court_config_manager(config_path: str = "courts_config.json") -> CourtConfigManager:
    """Get singleton instance of CourtConfigManager"""
    global _config_manager

    if _config_manager is None or _config_manager.config_path != config_path:
        _config_manager = CourtConfigManager(config_path)

    return _config_manager


# Convenience functions for easy access
def get_court(court_code: str) -> Optional[CourtInfo]:
    """Get court configuration by code"""
    return get_court_config_manager().get_court(court_code)


def get_enabled_courts() -> List[CourtInfo]:
    """Get list of enabled courts"""
    return get_court_config_manager().get_enabled_courts()


def get_default_court() -> str:
    """Get default court code"""
    return get_court_config_manager().get_default_court()


def detect_court_from_path(file_path: str) -> str:
    """Detect court from file path"""
    return get_court_config_manager().detect_court_from_path(file_path)


def detect_court_from_content(content: str) -> str:
    """Detect court from content"""
    return get_court_config_manager().detect_court_from_content(content)