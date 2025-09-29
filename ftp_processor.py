"""
FTP Processor for File Validator
Integrates with FTP server to download, process, and upload files
IMPROVED VERSION - Fixes archive move operation while preserving all existing functionality
"""

import ftplib
import os
import sys
import json
import csv
import re
import logging
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
import time

# Third-party utilities used by local processing functionalities
import sqlite3
import hashlib
import pandas as pd
import PyPDF2
from PIL import Image
import pytesseract
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Optional imports - wrapped in try-except
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    # Will log later if used

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ftp_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Optional schedule import
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    logger.warning("Schedule module not available. Continuous processing will be disabled.")


# ==================== Configuration (from kem_validator_local) ====================
@dataclass
class Config:
    """Application configuration with multi-court support"""
    # Directories
    input_dir: str = "kem-inbox"
    output_dir: str = "kem-results"
    processed_dir: str = "processed-archive"
    invalid_dir: str = "invalid-archive"

    # OCR Settings
    ocr_provider: str = "tesseract"  # Options: tesseract, openai, azure
    openai_api_key: str = ""
    azure_endpoint: str = ""
    azure_key: str = ""

    # Database
    db_path: str = "kem_validator.db"

    # Processing
    auto_watch: bool = True
    process_interval: int = 5  # seconds

    # Multi-court configuration
    court_config_path: str = "courts_config.json"
    default_court: str = "KEM"
    enable_court_detection: bool = True

    # Additional config sections
    validation_rules: dict = field(default_factory=dict)
    file_settings: dict = field(default_factory=dict)
    logging: dict = field(default_factory=dict)
    web_interface: dict = field(default_factory=dict)
    court_settings: dict = field(default_factory=dict)  # New section for court-specific overrides

    def __post_init__(self):
        """Initialize court configuration manager after dataclass initialization"""
        self._court_config_manager = None
        self._load_court_configuration()

    def _load_court_configuration(self):
        """Load court configuration manager"""
        try:
            from court_config_manager import CourtConfigManager
            self._court_config_manager = CourtConfigManager(self.court_config_path)
            logger.info(f"Court configuration loaded from: {self.court_config_path}")
        except ImportError:
            logger.warning("Court configuration manager not available, using single-court mode")
            self._court_config_manager = None
        except Exception as e:
            logger.warning(f"Failed to load court configuration: {e}, using single-court mode")
            self._court_config_manager = None

    def get_court_config_manager(self):
        """Get the court configuration manager instance"""
        if self._court_config_manager is None:
            self._load_court_configuration()
        return self._court_config_manager

    def get_court_directories(self, court_code: str = None):
        """Get directories for specific court or default"""
        if court_code is None:
            court_code = self.default_court

        # Try to get court-specific directories
        if self._court_config_manager:
            try:
                court_info = self._court_config_manager.get_court(court_code)
                if court_info and court_info.enabled:
                    return {
                        'input_dir': court_info.get_directory('input_dir'),
                        'output_dir': court_info.get_directory('output_dir'),
                        'processed_dir': court_info.get_directory('processed_dir'),
                        'invalid_dir': court_info.get_directory('invalid_dir')
                    }
            except Exception as e:
                logger.warning(f"Failed to get court-specific directories for {court_code}: {e}")

        # Fall back to default directories (backward compatibility)
        return {
            'input_dir': self.input_dir,
            'output_dir': self.output_dir,
            'processed_dir': self.processed_dir,
            'invalid_dir': self.invalid_dir
        }

    def get_court_validation_rules(self, court_code: str = None):
        """Get validation rules for specific court"""
        if court_code is None:
            court_code = self.default_court

        # Try to get court-specific validation rules
        if self._court_config_manager:
            try:
                court_info = self._court_config_manager.get_court(court_code)
                if court_info and court_info.enabled:
                    return court_info.validation_rules
            except Exception as e:
                logger.warning(f"Failed to get validation rules for {court_code}: {e}")

        # Fall back to legacy validation rules from config.json
        if self.validation_rules:
            return self.validation_rules

        # Ultimate fallback for KEM
        return {
            'min_digits': 9,
            'max_digits': 13,
            'prefix': 'KEM',
            'prefix_required': True,
            'allow_alphanumeric': True,
            'case_sensitive': False
        }

    def get_enabled_courts(self):
        """Get list of enabled courts"""
        if self._court_config_manager:
            try:
                return self._court_config_manager.get_enabled_court_codes()
            except Exception as e:
                logger.warning(f"Failed to get enabled courts: {e}")

        # Fall back to single court mode
        return [self.default_court]

    def is_court_enabled(self, court_code: str) -> bool:
        """Check if specific court is enabled"""
        if self._court_config_manager:
            try:
                return self._court_config_manager.is_court_enabled(court_code)
            except Exception as e:
                logger.warning(f"Failed to check if court {court_code} is enabled: {e}")

        # Fall back to KEM-only mode
        return court_code == self.default_court

    def reload_court_configuration(self):
        """Reload court configuration from file"""
        if self._court_config_manager:
            try:
                self._court_config_manager.reload_config()
                logger.info("Court configuration reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to reload court configuration: {e}")
        else:
            # Try to reinitialize if it wasn't available before
            self._load_court_configuration()

    @classmethod
    def from_json(cls, path: str) -> 'Config':
        """Load configuration from JSON file with enhanced court support"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                config_data = json.load(f)

                # Handle legacy config files that don't have court fields
                if 'court_config_path' not in config_data:
                    config_data['court_config_path'] = "courts_config.json"
                if 'default_court' not in config_data:
                    config_data['default_court'] = "KEM"
                if 'enable_court_detection' not in config_data:
                    config_data['enable_court_detection'] = True
                if 'court_settings' not in config_data:
                    config_data['court_settings'] = {}

                return cls(**config_data)

        # Return default configuration if file doesn't exist
        return cls()

    def save(self, path: str):
        """Save configuration to JSON file"""
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    def get_config_summary(self):
        """Get a summary of current configuration for debugging"""
        summary = {
            'config_file': 'loaded from JSON' if hasattr(self, '_loaded_from_file') else 'default',
            'court_config_path': self.court_config_path,
            'default_court': self.default_court,
            'court_detection_enabled': self.enable_court_detection,
            'court_config_available': self._court_config_manager is not None,
            'enabled_courts': self.get_enabled_courts(),
            'directories': self.get_court_directories()
        }

        if self._court_config_manager:
            try:
                court_summary = self._court_config_manager.get_config_summary()
                summary['court_config_summary'] = court_summary
            except Exception as e:
                summary['court_config_error'] = str(e)

        return summary


# ==================== Core Validator (from kem_validator_local) ====================
class LegacyKemValidator:
    """Legacy KEM validation logic - preserved for backward compatibility"""

    @staticmethod
    def parse_kem_line(line: str) -> Optional[str]:
        """Extract KEM ID from a line"""
        # First try tab-separated format
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2 and parts[0] == 'KEM':
                return parts[1]

        # Fall back to regex for space-separated format (anchor to start)
        match = re.search(r'^\s*KEM\s+(\S+)', line)
        if match:
            token = match.group(1).strip()
            digits_only = ''.join(c for c in token if c.isdigit())
            # Only treat as a KEM data line if token has enough digits
            if len(digits_only) >= 9:
                return token
            return None

        return None

    @staticmethod
    def validate_kem_id(kem_id: str) -> Tuple[bool, str, int, str]:
        """
        Validate a KEM ID based on digit count
        Returns: (is_valid, digits_only, digit_count, fail_reason)
        """
        digits_only = ''.join(c for c in kem_id if c.isdigit())
        digit_count = len(digits_only)

        if digit_count == 0:
            return (False, digits_only, digit_count, "no_digits_found")

        if 9 <= digit_count <= 13:
            return (True, digits_only, digit_count, "")
        else:
            return (False, digits_only, digit_count, "digit_count_out_of_range")

    @staticmethod
    def validate_text(text: str) -> List[Dict]:
        """Validate all lines in the text"""
        results = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip blank lines
            if not line.strip():
                continue

            # Try to parse as KEM line
            kem_id = LegacyKemValidator.parse_kem_line(line)

            if kem_id is None:
                # Not a KEM line - informational only
                results.append({
                    'line_number': line_num,
                    'kem_id_raw': '',
                    'kem_digits': '',
                    'digits_count': 0,
                    'is_valid': True,
                    'fail_reason': 'not_a_KEM_line',
                    'raw': line
                })
            else:
                # Validate the KEM ID
                is_valid, digits, count, reason = LegacyKemValidator.validate_kem_id(kem_id)
                results.append({
                    'line_number': line_num,
                    'kem_id_raw': kem_id,
                    'kem_digits': digits,
                    'digits_count': count,
                    'is_valid': is_valid,
                    'fail_reason': reason,
                    'raw': line
                })

        return results


class CourtValidator:
    """Multi-court validation logic using ValidatorFactory"""

    def __init__(self):
        # Import here to avoid circular imports
        try:
            from court_validator_base import ValidatorFactory
            from court_config_manager import get_court_config_manager
            self.factory = ValidatorFactory()
            self.config_manager = get_court_config_manager()
        except ImportError:
            logger.warning("Court validation modules not available, falling back to legacy KEM validation")
            self.factory = None
            self.config_manager = None

    def parse_court_line(self, line: str, court_code: str = 'KEM') -> Optional[str]:
        """Extract document ID from a line for specified court"""
        if self.factory is None:
            # Fall back to legacy KEM parsing
            return LegacyKemValidator.parse_kem_line(line)

        try:
            validator = self.factory.get_validator(court_code)
            return validator.parse_line(line)
        except Exception as e:
            logger.warning(f"Error in court validator for {court_code}: {e}, falling back to legacy")
            return LegacyKemValidator.parse_kem_line(line)

    def validate_court_id(self, document_id: str, court_code: str = 'KEM') -> Tuple[bool, str, int, str]:
        """
        Validate a document ID for specified court
        Returns: (is_valid, digits_only, digit_count, fail_reason)
        """
        if self.factory is None:
            # Fall back to legacy KEM validation
            return LegacyKemValidator.validate_kem_id(document_id)

        try:
            validator = self.factory.get_validator(court_code)
            result = validator.validate_id(document_id)
            return (result.is_valid, result.digits_only, result.digit_count, result.fail_reason)
        except Exception as e:
            logger.warning(f"Error in court validator for {court_code}: {e}, falling back to legacy")
            return LegacyKemValidator.validate_kem_id(document_id)

    def validate_text(self, text: str, court_code: str = 'KEM') -> List[Dict]:
        """Validate all lines in text for specified court"""
        if self.factory is None:
            # Fall back to legacy validation
            return LegacyKemValidator.validate_text(text)

        try:
            validator = self.factory.get_validator(court_code)
            return validator.validate_text(text)
        except Exception as e:
            logger.warning(f"Error in court validator for {court_code}: {e}, falling back to legacy")
            return LegacyKemValidator.validate_text(text)

    def detect_court_from_text(self, text: str) -> str:
        """Auto-detect court from text content"""
        if self.config_manager is None:
            return 'KEM'  # Default fallback

        try:
            return self.config_manager.detect_court_from_content(text)
        except Exception as e:
            logger.warning(f"Error detecting court from content: {e}")
            return 'KEM'

    def detect_court_from_path(self, file_path: str) -> str:
        """Auto-detect court from file path"""
        if self.config_manager is None:
            return 'KEM'  # Default fallback

        try:
            return self.config_manager.detect_court_from_path(file_path)
        except Exception as e:
            logger.warning(f"Error detecting court from path: {e}")
            return 'KEM'


# Backward compatibility wrapper - maintains exact same interface as original KemValidator
class KemValidator:
    """
    Backward compatibility wrapper for KemValidator
    Maintains exact same static method interface while using new multi-court system
    """
    _instance = None

    @classmethod
    def _get_instance(cls):
        """Get singleton instance of CourtValidator"""
        if cls._instance is None:
            cls._instance = CourtValidator()
        return cls._instance

    @staticmethod
    def parse_kem_line(line: str) -> Optional[str]:
        """Extract KEM ID from a line - backward compatibility method"""
        return KemValidator._get_instance().parse_court_line(line, 'KEM')

    @staticmethod
    def validate_kem_id(kem_id: str) -> Tuple[bool, str, int, str]:
        """
        Validate a KEM ID based on digit count - backward compatibility method
        Returns: (is_valid, digits_only, digit_count, fail_reason)
        """
        return KemValidator._get_instance().validate_court_id(kem_id, 'KEM')

    @staticmethod
    def validate_text(text: str) -> List[Dict]:
        """Validate all lines in the text - backward compatibility method"""
        return KemValidator._get_instance().validate_text(text, 'KEM')

    # New methods for multi-court support (optional usage)
    @staticmethod
    def parse_court_line(line: str, court_code: str = 'KEM') -> Optional[str]:
        """Extract document ID from a line for specified court"""
        return KemValidator._get_instance().parse_court_line(line, court_code)

    @staticmethod
    def validate_court_id(document_id: str, court_code: str = 'KEM') -> Tuple[bool, str, int, str]:
        """Validate a document ID for specified court"""
        return KemValidator._get_instance().validate_court_id(document_id, court_code)

    @staticmethod
    def validate_text_for_court(text: str, court_code: str = 'KEM') -> List[Dict]:
        """Validate all lines in text for specified court"""
        return KemValidator._get_instance().validate_text(text, court_code)

    @staticmethod
    def detect_court_from_text(text: str) -> str:
        """Auto-detect court from text content"""
        return KemValidator._get_instance().detect_court_from_text(text)

    @staticmethod
    def detect_court_from_path(file_path: str) -> str:
        """Auto-detect court from file path"""
        return KemValidator._get_instance().detect_court_from_path(file_path)


# ==================== OCR + PDF Processors (from kem_validator_local) ====================
class OcrProcessor:
    """Base class for OCR processing"""

    def extract_text(self, file_path: str) -> str:
        """Extract text from file"""
        raise NotImplementedError


class TesseractOcr(OcrProcessor):
    """OCR using Tesseract"""

    def extract_text(self, file_path: str) -> str:
        """Extract text from image using Tesseract"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return ""


class OpenAiOcr(OcrProcessor):
    """OCR using OpenAI Vision API"""

    def __init__(self, api_key: str):
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not installed. Run: pip install openai")
        self.client = OpenAI(api_key=api_key) if OPENAI_AVAILABLE else None

    def extract_text(self, file_path: str) -> str:
        """Extract text using OpenAI Vision"""
        try:
            if not self.client:
                return ""
            with open(file_path, "rb") as image_file:
                import base64 as _b64
                base64_image = _b64.b64encode(image_file.read()).decode('utf-8')

            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text from this image, maintaining the original format and line breaks."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=4096
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI OCR failed: {e}")
            return ""


class AzureDocIntelligence(OcrProcessor):
    """OCR using Azure Document Intelligence"""

    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key

    def extract_text(self, file_path: str) -> str:
        """Extract text using Azure Document Intelligence"""
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential

            client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )

            with open(file_path, "rb") as f:
                poller = client.begin_analyze_document("prebuilt-read", f)
                result = poller.result()

            text_content = []
            for page in result.pages:
                for line in page.lines:
                    text_content.append(line.content)

            return '\n'.join(text_content)
        except Exception as e:
            logger.error(f"Azure Document Intelligence failed: {e}")
            return ""


class PdfProcessor:
    """PDF text extraction"""

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from PDF"""
        try:
            text_content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
            return '\n'.join(text_content)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""


# ==================== File Processor (from kem_validator_local) ====================
class FileProcessor:
    """Main file processing engine"""

    def __init__(self, config: Config):
        self.config = config
        self.validator = KemValidator()
        self.db = DatabaseManager(config.db_path)
        self._setup_directories()
        self._setup_ocr()

    def _setup_directories(self):
        """Create necessary directories"""
        for dir_path in [self.config.input_dir, self.config.output_dir,
                         self.config.processed_dir, self.config.invalid_dir]:
            Path(dir_path).mkdir(exist_ok=True)

    def _setup_ocr(self):
        """Initialize OCR processor based on config"""
        if self.config.ocr_provider == "openai" and self.config.openai_api_key:
            self.ocr = OpenAiOcr(self.config.openai_api_key)
        elif self.config.ocr_provider == "azure" and self.config.azure_endpoint:
            self.ocr = AzureDocIntelligence(self.config.azure_endpoint, self.config.azure_key)
        else:
            self.ocr = TesseractOcr()

    def detect_court_from_file(self, file_path: str, content: str = None) -> Dict[str, Any]:
        """High-level detection wrapper. See kem_validator_local for details."""
        audit_trail: List[str] = []
        alternatives: List[str] = []
        detected_court: Optional[str] = None
        detection_method: Optional[str] = None
        confidence: float = 0.0

        try:
            config_manager = self._get_court_config_manager()
            if config_manager:
                detection_config = config_manager.get_court_detection_config()
                audit_logging = detection_config.get('audit_logging', {})
                should_log = audit_logging.get('enabled', True)
            else:
                detection_config = {}
                should_log = True

            file_name = os.path.basename(file_path)
            file_name_lower = file_name.lower()
            file_path_lower = file_path.lower()

            audit_trail.append(f"Starting court detection for: {file_path}")

            # Method 1: Explicit filename prefix detection
            for prefix in ['KEM_', 'SEA_', 'TAC_']:
                if file_name.upper().startswith(prefix):
                    detected_court = prefix.rstrip('_')
                    detection_method = "filename_prefix"
                    confidence = 0.95
                    audit_trail.append(f"SUCCESS: Filename prefix match: '{prefix}' -> {detected_court}")
                    if should_log:
                        logger.info(f"Court detection: {detected_court} via filename prefix for {file_name}")
                    break

            # Method 2: Directory mapping (from config)
            if not detected_court:
                dir_mapping = detection_config.get('path_mapping', {})
                for dir_pattern, court_code in dir_mapping.items():
                    if dir_pattern.lower() in file_path_lower:
                        detected_court = court_code
                        detection_method = "directory_mapping"
                        confidence = 0.8
                        audit_trail.append(f"SUCCESS: Directory mapping match: '{dir_pattern}' -> {court_code}")
                        if should_log:
                            logger.info(f"Court detection: {court_code} via directory mapping '{dir_pattern}' in {file_path}")

            # Method 3: File pattern mapping
            if not detected_court or confidence < 0.7:
                file_pattern_mapping = detection_config.get('file_pattern_mapping', {})
                for court_code, patterns in file_pattern_mapping.items():
                    for pattern in patterns:
                        import fnmatch
                        if fnmatch.fnmatch(file_path_lower, pattern.lower()) or fnmatch.fnmatch(file_name_lower, pattern.lower()):
                            if not detected_court or confidence < 0.7:
                                if detected_court and detected_court != court_code:
                                    alternatives.append(detected_court)
                                detected_court = court_code
                                detection_method = "file_pattern"
                                confidence = 0.7
                                audit_trail.append(f"SUCCESS: File pattern match: '{pattern}' -> {court_code}")
                                if should_log:
                                    logger.info(f"Court detection: {court_code} via file pattern '{pattern}' for {file_name}")
                            break

            # Method 4: Content-based detection (optional)
            if content and (not detected_court or confidence < 0.85):
                fallback_config = detection_config.get('fallback_behavior', {})
                if fallback_config.get('use_content_detection', True):
                    scan_lines = fallback_config.get('content_scan_lines', 20)
                    content_lines = content.split('\n')[:scan_lines]
                    content_sample = '\n'.join(content_lines)

                    content_detected = self._detect_court_from_content(content_sample, detection_config)
                    if content_detected:
                        content_court, content_confidence = content_detected
                        if not detected_court or content_confidence > confidence:
                            if detected_court and detected_court != content_court:
                                alternatives.append(detected_court)
                            detected_court = content_court
                            detection_method = "content_analysis"
                            confidence = content_confidence
                            audit_trail.append(f"SUCCESS: Content analysis match: {content_court} (confidence: {content_confidence:.2f})")
                            if should_log:
                                logger.info(f"Court detection: {content_court} via content analysis (confidence: {content_confidence:.2f})")

            # Fallback to default
            if not detected_court:
                default_court = detection_config.get('fallback_behavior', {}).get('default_on_no_match', 'KEM')
                detected_court = default_court
                detection_method = "default_fallback"
                confidence = 0.1
                audit_trail.append(f"FALLBACK: Using default fallback: {default_court}")
                if should_log:
                    logger.info(f"Court detection: Using default fallback {default_court} for {file_name}")

            # Log conflicts
            if alternatives and should_log and detection_config.get('audit_logging', {}).get('log_conflicts', True):
                logger.warning(f"Court detection conflict for {file_name}: detected={detected_court}, alternatives={alternatives}")
                audit_trail.append(f"WARNING: Conflict detected: chose {detected_court} over {alternatives}")

            return {
                'court_code': detected_court,
                'method': detection_method,
                'confidence': confidence,
                'alternatives': alternatives,
                'audit_trail': audit_trail
            }

        except Exception as e:
            logger.error(f"Error in court detection for {file_path}: {e}")
            audit_trail.append(f"ERROR: Detection error: {e}")
            return {
                'court_code': 'KEM',
                'method': 'error_fallback',
                'confidence': 0.0,
                'alternatives': [],
                'audit_trail': audit_trail
            }

    def _get_court_config_manager(self):
        try:
            if hasattr(self.config, '_court_config_manager') and self.config._court_config_manager:
                return self.config._court_config_manager
            else:
                from court_config_manager import CourtConfigManager
                return CourtConfigManager()
        except:
            return None

    def _detect_court_from_content(self, content: str, detection_config: Dict) -> Tuple[str, float]:
        content_prefixes = detection_config.get('content_prefixes', {})
        court_scores: Dict[str, int] = {}
        for court_code, patterns in content_prefixes.items():
            score = 0
            for pattern in patterns:
                import re as _re
                matches = len(_re.findall(pattern, content, _re.MULTILINE | _re.IGNORECASE))
                score += matches
            if score > 0:
                court_scores[court_code] = score
        if not court_scores:
            return None
        best_court = max(court_scores.items(), key=lambda x: x[1])
        court_code, score = best_court
        lines = len(content.split('\n'))
        confidence = min(0.9, (score / max(1, lines)) * 5)
        return court_code, confidence

    def _setup_court_directories(self, court_code: str):
        try:
            from court_config_manager import get_court_config_manager
            config_manager = get_court_config_manager()
            court_info = config_manager.get_court(court_code)
            if court_info:
                court_dirs = [
                    court_info.get_directory('input_dir'),
                    court_info.get_directory('output_dir'),
                    court_info.get_directory('processed_dir'),
                    court_info.get_directory('invalid_dir')
                ]
            else:
                court_dirs = [
                    os.path.join(self.config.input_dir, court_code.lower()),
                    os.path.join(self.config.output_dir, court_code.lower()),
                    os.path.join(self.config.processed_dir, court_code.lower()),
                    os.path.join(self.config.invalid_dir, court_code.lower())
                ]
            for dir_path in court_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        except ImportError:
            court_dirs = [
                os.path.join(self.config.processed_dir, court_code.upper()),
                os.path.join(self.config.invalid_dir, court_code.upper())
            ]
            for dir_path in court_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not setup court-specific directories for {court_code}: {e}")

    def process_file(self, file_path: str, court_code: str = None) -> Dict[str, Any]:
        logger.info(f"Processing file: {file_path}")
        file_name = os.path.basename(file_path)
        file_ext = Path(file_path).suffix.lower()
        detection_result = None
        try:
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    text_content = f.read()
            elif file_ext == '.pdf':
                text_content = PdfProcessor.extract_text(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg']:
                text_content = self.ocr.extract_text(file_path)
            else:
                text_content = ''
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {e}")
            text_content = ''

        if court_code is None:
            detection_result = self.detect_court_from_file(file_path, content=text_content)
            court_code = detection_result['court_code']
        else:
            detection_result = {
                'court_code': court_code,
                'method': 'explicit_parameter',
                'confidence': 1.0,
                'alternatives': [],
                'audit_trail': [f"Court code explicitly provided: {court_code}"]
            }

        self._setup_court_directories(court_code)

        try:
            if hasattr(self.validator, 'validate_text_for_court'):
                validation_results = self.validator.validate_text_for_court(text_content, court_code)
            else:
                validation_results = self.validator.validate_text(text_content)

            stats = self._calculate_stats(validation_results, court_code)
            csv_path = self._save_csv(file_name, validation_results, stats, court_code)
            self.db.save_processing_result(file_name, stats, csv_path, court_code)

            logger.info(f"File processed successfully: {file_name} - {stats['validation_status']} (Court: {court_code})")
            return {
                "status": "success",
                "file": file_name,
                "court_code": court_code,
                "validation_status": stats['validation_status'],
                "stats": stats,
                "csv_path": csv_path,
                "detection": detection_result
            }
        except Exception as e:
            logger.error(f"Error processing file {file_name}: {e}")
            return {"status": "failed", "reason": str(e), "court_code": court_code, "detection": detection_result}

    def _calculate_stats(self, results: List[Dict], court_code: str = 'KEM') -> Dict:
        import re as _re
        total_lines = len(results)
        prefix = court_code.upper()

        def is_court_row(r: Dict) -> bool:
            raw = r.get('raw', '') or ''
            if not raw:
                return False
            starts_with_prefix = raw.startswith(f"{prefix}\t") or _re.match(rf"^\s*{_re.escape(prefix)}\s+", raw)
            if not starts_with_prefix:
                return False
            if int(r.get('digits_count', 0) or 0) <= 0:
                return False
            if not (r.get('kem_id_raw') or '').strip():
                return False
            return True

        court_rows = [r for r in results if is_court_row(r)]
        kem_lines = len(court_rows)
        valid_lines = sum(1 for r in court_rows if r.get('is_valid'))
        failed_lines = sum(1 for r in court_rows if not r.get('is_valid'))
        validation_status = 'passed' if failed_lines == 0 and kem_lines > 0 else 'failed'
        return {
            'total_lines': total_lines,
            'kem_lines': kem_lines,
            'valid_lines': valid_lines,
            'failed_lines': failed_lines,
            'info_lines': total_lines - kem_lines,
            'validation_status': validation_status,
            'success_rate': (valid_lines / kem_lines * 100) if kem_lines > 0 else 0,
            'court_code': court_code
        }

    def _save_csv(self, original_name: str, results: List[Dict], stats: Dict, court_code: str = 'KEM') -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%SZ')
        base_name = Path(original_name).stem
        status = 'passed' if stats['validation_status'] == 'passed' else 'failed'
        csv_name = f"{court_code}_{base_name}_{status}_{timestamp}.csv"
        court_name = court_code
        court_full_name = court_code
        try:
            from court_config_manager import get_court_config_manager
            config_manager = get_court_config_manager()
            court_info = config_manager.get_court(court_code)
            if court_info and court_info.enabled:
                court_name = court_info.name
                court_full_name = court_info.full_name
                output_dir = court_info.get_directory('output_dir')
            else:
                output_dir = os.path.join(self.config.output_dir, court_code.upper())
                Path(output_dir).mkdir(parents=True, exist_ok=True)
        except (ImportError, Exception):
            output_dir = self.config.output_dir
        csv_path = os.path.join(output_dir, csv_name)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([f"# File Validation Report"])
            writer.writerow([f"# Court: {court_code} - {court_full_name}"])
            writer.writerow([f"# Source File: {original_name}"])
            writer.writerow([f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([f"# Status: {stats['validation_status'].upper()}"])
            writer.writerow([])
            writer.writerow(["# COURT SUMMARY STATISTICS"])
            writer.writerow([f"# Court Code: {court_code}"])
            writer.writerow([f"# Court Name: {court_name}"])
            writer.writerow([f"# Total Lines Processed: {stats['total_lines']}"])
            writer.writerow([f"# {court_code} Lines Found: {stats['kem_lines']}"])
            writer.writerow([f"# Valid {court_code} IDs: {stats['valid_lines']}"])
            writer.writerow([f"# Failed {court_code} IDs: {stats['failed_lines']}"])
            writer.writerow([f"# Success Rate: {stats['success_rate']:.1f}%"])
            writer.writerow([])
            writer.writerow(["# DETAILED VALIDATION RESULTS"])
            fieldnames = [
                'court_code', 'court_name', 'line_number', f'{court_code.lower()}_id_raw',
                f'{court_code.lower()}_digits', 'digits_count', 'is_valid', 'fail_reason',
                'validation_details', 'raw_line'
            ]
            writer.writerow(fieldnames)
            for result in results:
                validation_details = ""
                if not result['is_valid'] and result['fail_reason']:
                    if result['fail_reason'] == 'digit_count_out_of_range':
                        try:
                            from court_config_manager import get_court_config_manager
                            config_manager = get_court_config_manager()
                            court_info = config_manager.get_court(court_code)
                            if court_info:
                                min_digits = court_info.validation_rules.get('min_digits', 9)
                                max_digits = court_info.validation_rules.get('max_digits', 13)
                            else:
                                min_digits, max_digits = 9, 13
                        except Exception:
                            min_digits, max_digits = 9, 13
                        validation_details = f"Expected {min_digits}-{max_digits} digits"
                    else:
                        validation_details = result['fail_reason']
                row = [
                    court_code, court_name, result.get('line_number', ''),
                    result.get('kem_id_raw', ''), result.get('kem_digits', ''),
                    result.get('digits_count', ''), result.get('is_valid', ''),
                    result.get('fail_reason', ''), validation_details, result.get('raw', '')
                ]
                writer.writerow(row)
        return csv_path

    def _get_court_archive_dir(self, court_code: str, archive_type: str) -> str:
        """Get court-specific archive directory path with enhanced structure"""
        try:
            from court_config_manager import get_court_config_manager
            config_manager = get_court_config_manager()
            court_info = config_manager.get_court(court_code)

            if court_info and court_info.enabled:
                if archive_type == 'processed':
                    base_dir = court_info.get_directory('processed_dir')
                elif archive_type == 'invalid':
                    base_dir = court_info.get_directory('invalid_dir')
                else:
                    base_dir = court_info.get_directory('processed_dir')

                # Always create court subdirectory for organization
                court_archive_dir = os.path.join(base_dir, court_code.upper())
            else:
                # Fall back to court subdirectories in default archive locations
                base_dir = self.config.processed_dir if archive_type == 'processed' else self.config.invalid_dir
                court_archive_dir = os.path.join(base_dir, court_code.upper())

        except (ImportError, Exception):
            # Ultimate fallback
            base_dir = self.config.processed_dir if archive_type == 'processed' else self.config.invalid_dir
            court_archive_dir = os.path.join(base_dir, court_code.upper())

        # Ensure directory structure exists
        Path(court_archive_dir).mkdir(parents=True, exist_ok=True)

        # Create monthly subdirectories for better organization
        current_month = datetime.now().strftime('%Y-%m')
        monthly_dir = os.path.join(court_archive_dir, current_month)
        Path(monthly_dir).mkdir(parents=True, exist_ok=True)

        return monthly_dir

    def _archive_file(self, source_path: str, dest_dir: str, status: str, court_code: str = 'KEM'):
        """Archive processed file to court-specific directory with enhanced organization"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = os.path.basename(source_path)

        dest_name = f"{court_code}_{timestamp}_{status}_{file_name}"
        dest_path = os.path.join(dest_dir, dest_name)

        Path(dest_dir).mkdir(parents=True, exist_ok=True)

        try:
            os.rename(source_path, dest_path)
            logger.info(f"File archived to {court_code} court directory: {dest_path}")
            self._track_archived_file(dest_path, court_code, status, file_name)
        except Exception as e:
            logger.error(f"Failed to archive file {source_path}: {e}")
            try:
                import shutil as _shutil
                _shutil.copy2(source_path, dest_path)
                os.remove(source_path)
                logger.info(f"File copied and original removed: {dest_path}")
                self._track_archived_file(dest_path, court_code, status, file_name)
            except Exception as e2:
                logger.error(f"Failed to copy file {source_path}: {e2}")

    def _track_archived_file(self, archive_path: str, court_code: str, status: str, original_name: str):
        """Track archived files in database for statistics and cleanup"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS archived_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    court_code TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    archive_path TEXT NOT NULL,
                    archive_status TEXT NOT NULL,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    retention_date DATE
                )
            ''')
            file_size = os.path.getsize(archive_path) if os.path.exists(archive_path) else 0
            retention_date = self._calculate_retention_date(court_code)
            cursor.execute('''
                INSERT INTO archived_files
                (court_code, original_filename, archive_path, archive_status, file_size, retention_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (court_code, original_name, archive_path, status, file_size, retention_date))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to track archived file: {e}")

    def _calculate_retention_date(self, court_code: str) -> str:
        """Calculate retention date based on court-specific policies"""
        try:
            from court_config_manager import get_court_config_manager
            config_manager = get_court_config_manager()
            court_info = config_manager.get_court(court_code)
            if court_info:
                retention_days = court_info.database.get('retention_days', 365)
            else:
                retention_days = 365
            retention_date = datetime.now() + timedelta(days=retention_days)
            return retention_date.strftime('%Y-%m-%d')
        except Exception:
            retention_date = datetime.now() + timedelta(days=365)
            return retention_date.strftime('%Y-%m-%d')

    def migrate_legacy_archives_to_court_structure(self):
        """Migrate existing archived files to court-specific subdirectories"""
        logger.info("Starting migration of legacy archives to court structure...")
        migration_stats = {
            'processed_files': 0,
            'invalid_files': 0,
            'errors': 0,
            'migrated_to_kem': 0
        }
        try:
            processed_dir = Path(self.config.processed_dir)
            if processed_dir.exists():
                migration_stats['processed_files'] = self._migrate_directory_files(
                    processed_dir, 'processed', migration_stats
                )
            invalid_dir = Path(self.config.invalid_dir)
            if invalid_dir.exists():
                migration_stats['invalid_files'] = self._migrate_directory_files(
                    invalid_dir, 'invalid', migration_stats
                )
            logger.info(f"Archive migration completed: {migration_stats}")
            return migration_stats
        except Exception as e:
            logger.error(f"Archive migration failed: {e}")
            migration_stats['errors'] += 1
            return migration_stats

    def _migrate_directory_files(self, directory: Path, archive_type: str, stats: dict) -> int:
        """Migrate files in a specific directory to court structure"""
        migrated_count = 0
        try:
            files_to_migrate = [f for f in directory.iterdir() if f.is_file()]
            for file_path in files_to_migrate:
                try:
                    court_code = self._detect_court_from_filename(file_path.name)
                    dest_dir = self._get_court_archive_dir(court_code, archive_type)
                    new_name = file_path.name
                    if not new_name.startswith(f"{court_code}_"):
                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        new_name = f"{court_code}_{timestamp}_migrated_{file_path.name}"
                    dest_path = os.path.join(dest_dir, new_name)
                    os.rename(str(file_path), dest_path)
                    migrated_count += 1
                    self._track_archived_file(dest_path, court_code, 'migrated', file_path.name)
                    if court_code == 'KEM':
                        stats['migrated_to_kem'] += 1
                    logger.debug(f"Migrated {file_path.name} to {court_code} archive")
                except Exception as e:
                    logger.warning(f"Failed to migrate file {file_path}: {e}")
                    stats['errors'] += 1
        except Exception as e:
            logger.error(f"Failed to migrate directory {directory}: {e}")
            stats['errors'] += 1
        return migrated_count

    def _detect_court_from_filename(self, filename: str) -> str:
        filename_upper = filename.upper()
        for prefix in ['KEM_', 'SEA_', 'TAC_']:
            if filename_upper.startswith(prefix):
                return prefix.rstrip('_')
        return 'KEM'

    def cleanup_expired_archives(self, court_code: str = None, dry_run: bool = True):
        """Clean up expired archived files based on retention policies"""
        logger.info(f"Starting archive cleanup for {'all courts' if not court_code else court_code} (dry_run={dry_run})")
        cleanup_stats = {
            'files_checked': 0,
            'files_expired': 0,
            'files_deleted': 0,
            'space_freed_mb': 0,
            'errors': 0
        }
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            base_query = '''
                SELECT id, court_code, archive_path, file_size, retention_date
                FROM archived_files
                WHERE retention_date <= date('now')
            '''
            if court_code:
                cursor.execute(base_query + ' AND court_code = ?', (court_code,))
            else:
                cursor.execute(base_query)
            expired_files = cursor.fetchall()
            cleanup_stats['files_checked'] = len(expired_files)
            for file_id, file_court, archive_path, file_size, retention_date in expired_files:
                cleanup_stats['files_expired'] += 1
                try:
                    if os.path.exists(archive_path):
                        if not dry_run:
                            os.remove(archive_path)
                            cleanup_stats['files_deleted'] += 1
                            cleanup_stats['space_freed_mb'] += (file_size or 0) / (1024 * 1024)
                            cursor.execute('DELETE FROM archived_files WHERE id = ?', (file_id,))
                        logger.debug(f"{'Would delete' if dry_run else 'Deleted'} expired file: {archive_path}")
                    else:
                        if not dry_run:
                            cursor.execute('DELETE FROM archived_files WHERE id = ?', (file_id,))
                        logger.debug(f"Cleaned up missing file record: {archive_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up file {archive_path}: {e}")
                    cleanup_stats['errors'] += 1
            if not dry_run:
                conn.commit()
            conn.close()
            logger.info(f"Archive cleanup completed: {cleanup_stats}")
            return cleanup_stats
        except Exception as e:
            logger.error(f"Archive cleanup failed: {e}")
            cleanup_stats['errors'] += 1
            return cleanup_stats

    def get_archive_statistics(self, court_code: str = None) -> dict:
        """Get comprehensive archive statistics per court"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            base_query = '''
                SELECT
                    court_code,
                    COUNT(*) as total_files,
                    SUM(file_size) as total_size_bytes,
                    MIN(archived_at) as oldest_file,
                    MAX(archived_at) as newest_file,
                    COUNT(CASE WHEN archive_status = 'passed' THEN 1 END) as processed_files,
                    COUNT(CASE WHEN archive_status = 'failed' THEN 1 END) as invalid_files,
                    COUNT(CASE WHEN retention_date <= date('now') THEN 1 END) as expired_files
                FROM archived_files
            '''
            if court_code:
                cursor.execute(base_query + ' WHERE court_code = ? GROUP BY court_code', (court_code,))
                results = cursor.fetchall()
            else:
                cursor.execute(base_query + ' GROUP BY court_code')
                results = cursor.fetchall()
            archive_stats = {}
            for row in results:
                court, total_files, total_size, oldest, newest, processed, invalid, expired = row
                dir_stats = self._get_directory_statistics(court)
                archive_stats[court] = {
                    'database_tracking': {
                        'total_files': total_files,
                        'total_size_mb': round((total_size or 0) / (1024 * 1024), 2),
                        'oldest_file': oldest,
                        'newest_file': newest,
                        'processed_files': processed,
                        'invalid_files': invalid,
                        'expired_files': expired
                    },
                    'directory_analysis': dir_stats,
                    'retention_policy': self._get_court_retention_info(court)
                }
            conn.close()
            if court_code and court_code in archive_stats:
                return archive_stats[court_code]
            else:
                return archive_stats
        except Exception as e:
            logger.error(f"Failed to get archive statistics: {e}")
            return {'error': str(e)}

    def _get_directory_statistics(self, court_code: str) -> dict:
        """Get filesystem-based archive statistics for a court"""
        dir_stats = {
            'processed_dir': {'files': 0, 'size_mb': 0},
            'invalid_dir': {'files': 0, 'size_mb': 0},
            'monthly_breakdown': {}
        }
        try:
            for archive_type in ['processed', 'invalid']:
                try:
                    from court_config_manager import get_court_config_manager
                    config_manager = get_court_config_manager()
                    court_info = config_manager.get_court(court_code)
                    if court_info and court_info.enabled:
                        base_dir = court_info.get_directory(f'{archive_type}_dir')
                    else:
                        base_dir = getattr(self.config, f'{archive_type}_dir')
                    court_dir = os.path.join(base_dir, court_code.upper())
                except Exception:
                    base_dir = getattr(self.config, f'{archive_type}_dir')
                    court_dir = os.path.join(base_dir, court_code.upper())
                if os.path.exists(court_dir):
                    files, size_mb, monthly = self._analyze_directory(court_dir)
                    dir_stats[f'{archive_type}_dir'] = {'files': files, 'size_mb': size_mb}
                    for month, month_stats in monthly.items():
                        if month not in dir_stats['monthly_breakdown']:
                            dir_stats['monthly_breakdown'][month] = {'files': 0, 'size_mb': 0}
                        dir_stats['monthly_breakdown'][month]['files'] += month_stats['files']
                        dir_stats['monthly_breakdown'][month]['size_mb'] += month_stats['size_mb']
        except Exception as e:
            logger.warning(f"Failed to analyze directories for {court_code}: {e}")
        return dir_stats

    def _analyze_directory(self, directory: str) -> tuple:
        """Analyze a directory and return file count, size, and monthly breakdown"""
        total_files = 0
        total_size = 0
        monthly_breakdown = {}
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        total_files += 1
                        total_size += os.path.getsize(file_path)
                        month = self._extract_month_from_path(root, file_path)
                        if month not in monthly_breakdown:
                            monthly_breakdown[month] = {'files': 0, 'size_mb': 0}
                        monthly_breakdown[month]['files'] += 1
                        monthly_breakdown[month]['size_mb'] += os.path.getsize(file_path) / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Failed to analyze directory {directory}: {e}")
        return total_files, total_size / (1024 * 1024), monthly_breakdown

    def _extract_month_from_path(self, root: str, file_path: str) -> str:
        """Extract month identifier from path or file modification time"""
        try:
            path_parts = root.split(os.sep)
            for part in path_parts:
                if len(part) == 7 and part[4] == '-' and part[:4].isdigit() and part[5:].isdigit():
                    return part
            mtime = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mtime).strftime('%Y-%m')
        except Exception:
            return datetime.now().strftime('%Y-%m')

    def _get_court_retention_info(self, court_code: str) -> dict:
        """Get retention policy information for a court"""
        try:
            from court_config_manager import get_court_config_manager
            config_manager = get_court_config_manager()
            court_info = config_manager.get_court(court_code)
            if court_info:
                retention_days = court_info.database.get('retention_days', 365)
                return {
                    'retention_days': retention_days,
                    'retention_years': round(retention_days / 365, 1),
                    'policy_source': 'court_configuration'
                }
            else:
                return {
                    'retention_days': 365,
                    'retention_years': 1.0,
                    'policy_source': 'default_fallback'
                }
        except Exception:
            return {
                'retention_days': 365,
                'retention_years': 1.0,
                'policy_source': 'error_fallback'
            }


# ==================== Database Manager (from kem_validator_local) ====================
class DatabaseManager:
    """SQLite database for tracking processing history"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema with multi-court support"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validation_status TEXT,
                total_lines INTEGER,
                kem_lines INTEGER,
                valid_lines INTEGER,
                failed_lines INTEGER,
                success_rate REAL,
                csv_path TEXT,
                file_hash TEXT,
                court_code TEXT DEFAULT 'KEM'
            )
        ''')

        cursor.execute("PRAGMA table_info(processing_history)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'court_code' not in columns:
            logger.info("Migrating database: Adding court_code column")
            cursor.execute('ALTER TABLE processing_history ADD COLUMN court_code TEXT DEFAULT "KEM"')
            cursor.execute('UPDATE processing_history SET court_code = "KEM" WHERE court_code IS NULL')
            logger.info("Database migration completed: All existing records assigned to KEM court")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')

        cursor.execute('''
            INSERT OR IGNORE INTO schema_version (version, description)
            VALUES ('1.1', 'Added multi-court support with court_code column')
        ''')

        conn.commit()
        conn.close()

    def save_processing_result(self, file_name: str, stats: Dict, csv_path: str, court_code: str = 'KEM'):
        """Save processing result to database with court code support"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO processing_history
            (file_name, validation_status, total_lines, kem_lines, valid_lines,
             failed_lines, success_rate, csv_path, court_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (file_name, stats['validation_status'], stats['total_lines'],
              stats['kem_lines'], stats['valid_lines'], stats['failed_lines'],
              stats['success_rate'], csv_path, court_code))

        conn.commit()
        conn.close()

    def get_history(self, limit: int = 100, court_code: Optional[str] = None) -> pd.DataFrame:
        """Get processing history, optionally filtered by court"""
        conn = sqlite3.connect(self.db_path)
        if court_code:
            df = pd.read_sql_query(
                "SELECT * FROM processing_history WHERE court_code = ? ORDER BY processed_at DESC LIMIT ?",
                conn, params=(court_code, limit)
            )
        else:
            df = pd.read_sql_query(
                "SELECT * FROM processing_history ORDER BY processed_at DESC LIMIT ?",
                conn, params=(limit,)
            )
        conn.close()
        return df

    def get_statistics(self, court_code: Optional[str] = None) -> Dict:
        """Get statistics, optionally filtered by court"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if court_code:
            cursor.execute('''
                SELECT
                    COUNT(*) as total_files,
                    SUM(CASE WHEN validation_status = 'passed' THEN 1 ELSE 0 END) as passed_files,
                    SUM(CASE WHEN validation_status = 'failed' THEN 1 ELSE 0 END) as failed_files,
                    AVG(success_rate) as avg_success_rate,
                    SUM(total_lines) as total_lines_processed,
                    SUM(kem_lines) as total_kem_lines,
                    SUM(valid_lines) as total_valid_lines,
                    SUM(failed_lines) as total_failed_lines
                FROM processing_history
                WHERE court_code = ?
            ''', (court_code,))
        else:
            cursor.execute('''
                SELECT
                    COUNT(*) as total_files,
                    SUM(CASE WHEN validation_status = 'passed' THEN 1 ELSE 0 END) as passed_files,
                    SUM(CASE WHEN validation_status = 'failed' THEN 1 ELSE 0 END) as failed_files,
                    AVG(success_rate) as avg_success_rate,
                    SUM(total_lines) as total_lines_processed,
                    SUM(kem_lines) as total_kem_lines,
                    SUM(valid_lines) as total_valid_lines,
                    SUM(failed_lines) as total_failed_lines
                FROM processing_history
            ''')
        result = cursor.fetchone()
        conn.close()
        return {
            'total_files': result[0] or 0,
            'passed_files': result[1] or 0,
            'failed_files': result[2] or 0,
            'avg_success_rate': result[3] or 0,
            'total_lines_processed': result[4] or 0,
            'total_kem_lines': result[5] or 0,
            'total_valid_lines': result[6] or 0,
            'total_failed_lines': result[7] or 0
        }

    def get_court_summary(self) -> Dict:
        """Get summary statistics broken down by court"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                court_code,
                COUNT(*) as total_files,
                SUM(CASE WHEN validation_status = 'passed' THEN 1 ELSE 0 END) as passed_files,
                SUM(CASE WHEN validation_status = 'failed' THEN 1 ELSE 0 END) as failed_files,
                AVG(success_rate) as avg_success_rate,
                MAX(processed_at) as last_processed
            FROM processing_history
            GROUP BY court_code
            ORDER BY total_files DESC
        ''')
        courts = {}
        for row in cursor.fetchall():
            courts[row[0]] = {
                'total_files': row[1],
                'passed_files': row[2],
                'failed_files': row[3],
                'avg_success_rate': row[4] or 0,
                'last_processed': row[5]
            }
        conn.close()
        return courts


# ==================== File Watcher (from kem_validator_local) ====================
class FileWatcher(FileSystemEventHandler):
    """Watch directory for new files"""

    def __init__(self, processor: FileProcessor):
        self.processor = processor
        self.processing_queue = []
        self.is_processing = False

    def on_created(self, event):
        """Handle file creation event"""
        if not event.is_directory:
            logger.info(f"New file detected: {event.src_path}")
            self.processing_queue.append(event.src_path)
            self.process_queue()

    def process_queue(self):
        """Process files in queue"""
        if self.is_processing or not self.processing_queue:
            return

        self.is_processing = True
        while self.processing_queue:
            file_path = self.processing_queue.pop(0)
            # Wait a bit to ensure file is fully written
            time.sleep(2)
            self.processor.process_file(file_path)
        self.is_processing = False


# ==================== CLI Interface (from kem_validator_local) ====================
class KemValidatorCLI:
    """Command-line interface"""

    def __init__(self):
        self.config = Config.from_json("config.json")
        self.processor = FileProcessor(self.config)

    def run(self):
        """Run the CLI"""
        print("=" * 50)
        print("  File Validator - Local Edition")
        print("=" * 50)

        while True:
            print("\nOptions:")
            print("1. Process single file")
            print("2. Process all files in inbox")
            print("3. Start file watcher")
            print("4. View statistics")
            print("5. View history")
            print("6. Configure settings")
            print("7. Exit")

            choice = input("\nSelect option: ").strip()

            if choice == "1":
                self.process_single_file()
            elif choice == "2":
                self.process_all_files()
            elif choice == "3":
                self.start_watcher()
            elif choice == "4":
                self.show_statistics()
            elif choice == "5":
                self.show_history()
            elif choice == "6":
                self.configure_settings()
            elif choice == "7":
                print("Goodbye!")
                break
            else:
                print("Invalid option")

    def process_single_file(self):
        """Process a single file"""
        file_path = input("Enter file path: ").strip()
        if os.path.exists(file_path):
            result = self.processor.process_file(file_path)
            print(f"\nResult: {result}")
        else:
            print("File not found")

    def process_all_files(self):
        """Process all files in inbox"""
        files = list(Path(self.config.input_dir).glob("*"))
        print(f"Found {len(files)} files to process")

        for file_path in files:
            if file_path.is_file():
                result = self.processor.process_file(str(file_path))
                print(f"Processed: {file_path.name} - {result['status']}")

    def start_watcher(self):
        """Start file watcher"""
        print(f"Watching directory: {self.config.input_dir}")
        print("Press Ctrl+C to stop")

        event_handler = FileWatcher(self.processor)
        observer = Observer()
        observer.schedule(event_handler, self.config.input_dir, recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        print("\nWatcher stopped")

    def show_statistics(self):
        """Show processing statistics"""
        stats = self.processor.db.get_statistics()
        print("\n" + "=" * 40)
        print("  Overall Statistics")
        print("=" * 40)
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")

    def show_history(self):
        """Show processing history"""
        history = self.processor.db.get_history(10)
        if not history.empty:
            print("\nRecent Processing History:")
            print(history[['file_name', 'processed_at', 'validation_status', 'success_rate']].to_string())
        else:
            print("No processing history")

    def configure_settings(self):
        """Configure application settings"""
        print("\nCurrent Settings:")
        print(f"OCR Provider: {self.config.ocr_provider}")
        print(f"Input Directory: {self.config.input_dir}")
        print(f"Output Directory: {self.config.output_dir}")

        change = input("\nChange settings? (y/n): ").strip().lower()
        if change == 'y':
            self.config.ocr_provider = input(f"OCR Provider [{self.config.ocr_provider}]: ").strip() or self.config.ocr_provider

            if self.config.ocr_provider == "openai":
                self.config.openai_api_key = input("OpenAI API Key: ").strip()
            elif self.config.ocr_provider == "azure":
                self.config.azure_endpoint = input("Azure Endpoint: ").strip()
                self.config.azure_key = input("Azure Key: ").strip()

            self.config.save("config.json")
            print("Settings saved!")


# ==================== Compatibility helpers & constants ====================
def get_validator():
    """Factory function for getting a validator instance"""
    return KemValidator()


def validate_kem_text(text: str):
    """Standalone function for text validation (delegates to KemValidator)"""
    return KemValidator.validate_text(text)


def parse_kem_id(line: str):
    """Standalone function for ID parsing (delegates to KemValidator)"""
    return KemValidator.parse_kem_line(line)


# Module-level constants for backward compatibility
KEM_MIN_DIGITS = 9
KEM_MAX_DIGITS = 13
DEFAULT_COURT = 'KEM'


class FTPConfig:
    """Enhanced FTP Configuration with multi-court support"""
    def __init__(self, config_path: str = "ftp_config.json"):
        self.load_config(config_path)
        self.court_paths = {}  # Initialize court paths dictionary

    def load_config(self, config_path: str):
        """Load enhanced FTP configuration from JSON file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            # Enhanced default configuration with multi-court support
            config = {
                "ftp_server": "40.65.119.170",
                "ftp_port": 21,
                "ftp_username": "Ocourt",
                "ftp_password": "ptg_123",
                "ftp_base_path": "/PAMarchive/",

                # Multi-court FTP path structure
                "court_paths": {
                    "KEM": {
                        "base_path": "/PAMarchive/SeaTac/",
                        "inbox": "/PAMarchive/SeaTac/kem-inbox/",
                        "results": "/PAMarchive/SeaTac/kem-results/",
                        "processed": "/PAMarchive/SeaTac/processed-archive/KEM/",
                        "invalid": "/PAMarchive/SeaTac/invalid-archive/KEM/",
                        "enabled": True
                    },
                    "SEA": {
                        "base_path": "/PAMarchive/Seattle/",
                        "inbox": "/PAMarchive/Seattle/sea-inbox/",
                        "results": "/PAMarchive/Seattle/sea-results/",
                        "processed": "/PAMarchive/Seattle/processed-archive/SEA/",
                        "invalid": "/PAMarchive/Seattle/invalid-archive/SEA/",
                        "enabled": False
                    },
                    "TAC": {
                        "base_path": "/PAMarchive/Tacoma/",
                        "inbox": "/PAMarchive/Tacoma/tac-inbox/",
                        "results": "/PAMarchive/Tacoma/tac-results/",
                        "processed": "/PAMarchive/Tacoma/processed-archive/TAC/",
                        "invalid": "/PAMarchive/Tacoma/invalid-archive/TAC/",
                        "enabled": False
                    }
                },

                # Legacy single-court paths (for backward compatibility)
                "ftp_inbox": "/PAMarchive/SeaTac/kem-inbox/",
                "ftp_results": "/PAMarchive/SeaTac/kem-results/",
                "ftp_processed": "/PAMarchive/SeaTac/processed-archive/KEM/",
                "ftp_invalid": "/PAMarchive/SeaTac/invalid-archive/KEM/",

                # Court detection configuration
                "court_detection": {
                    "methods": ["path_structure", "filename_prefix", "directory_mapping"],
                    "path_mapping": {
                        "/PAMarchive/SeaTac/": "KEM",
                        "/PAMarchive/Seattle/": "SEA",
                        "/PAMarchive/Tacoma/": "TAC"
                    },
                    "default_court": "KEM",
                    "auto_enable_detection": True
                },

                # Processing configuration
                "local_temp_dir": "ftp_temp",
                "process_interval_minutes": 5,
                "batch_size": 10,
                "delete_after_download": False,
                "upload_results": True,
                "archive_on_ftp": True,
                "process_all_courts": True,
                "court_priority": ["KEM", "SEA", "TAC"]
            }
            # Save default config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

        # Set attributes
        for key, value in config.items():
            setattr(self, key, value)

    def get_court_paths(self, court_code: str) -> Dict[str, str]:
        """Get FTP paths for a specific court"""
        if hasattr(self, 'court_paths') and court_code in self.court_paths:
            return self.court_paths[court_code]

        # Fallback to legacy paths for KEM
        if court_code == 'KEM':
            return {
                "base_path": getattr(self, 'ftp_base_path', '/PAMarchive/SeaTac/'),
                "inbox": getattr(self, 'ftp_inbox', '/PAMarchive/SeaTac/kem-inbox/'),
                "results": getattr(self, 'ftp_results', '/PAMarchive/SeaTac/kem-results/'),
                "processed": getattr(self, 'ftp_processed', '/PAMarchive/SeaTac/processed-archive/KEM/'),
                "invalid": getattr(self, 'ftp_invalid', '/PAMarchive/SeaTac/invalid-archive/KEM/'),
                "enabled": True
            }

        return None

    def get_enabled_courts(self) -> List[str]:
        """Get list of enabled courts for FTP processing"""
        enabled_courts = []

        if hasattr(self, 'court_paths'):
            for court_code, paths in self.court_paths.items():
                if paths.get('enabled', False):
                    enabled_courts.append(court_code)

        # Fallback to KEM if no courts configured
        if not enabled_courts:
            enabled_courts = ['KEM']

        return enabled_courts

    def detect_court_from_path(self, file_path: str) -> str:
        """Detect court from FTP file path"""
        if hasattr(self, 'court_detection'):
            path_mapping = self.court_detection.get('path_mapping', {})

            for path_pattern, court_code in path_mapping.items():
                if path_pattern in file_path:
                    return court_code

        # Fallback to default court
        return getattr(self.court_detection, 'default_court', 'KEM') if hasattr(self, 'court_detection') else 'KEM'


class FTPProcessor:
    """Main FTP Processor class"""
    
    def __init__(self, ftp_config: FTPConfig = None, kem_config: Config = None):
        """Initialize FTP Processor"""
        self.ftp_config = ftp_config or FTPConfig()
        self.kem_config = kem_config or Config.from_json("config.json")
        self.file_processor = FileProcessor(self.kem_config)
        self.ftp = None
        self._setup_local_dirs()
        
    def _setup_local_dirs(self):
        """Create local temporary directories"""
        dirs = [
            self.ftp_config.local_temp_dir,
            os.path.join(self.ftp_config.local_temp_dir, "downloads"),
            os.path.join(self.ftp_config.local_temp_dir, "results"),
            os.path.join(self.ftp_config.local_temp_dir, "processed")
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def _chdir_strict(self, ftp: ftplib.FTP, path: str):
        """cd to path; fail fast if it doesn't exist (avoids phantom empty folders)."""
        try:
            ftp.cwd(path)
        except ftplib.error_perm as e:
            raise RuntimeError(
                f"FTP chdir failed for '{path}'. Check exact spelling/case in WinSCP. ({e})"
            )

    def connect_ftp(self) -> ftplib.FTP:
        """Establish FTP connection"""
        try:
            logger.info(f"Connecting to FTP server: {self.ftp_config.ftp_server}")
            
            # Create FTP connection
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_config.ftp_server, self.ftp_config.ftp_port)
            ftp.login(self.ftp_config.ftp_username, self.ftp_config.ftp_password)
            
            logger.info(f"Successfully connected to FTP server")
            logger.info(f"Current directory: {ftp.pwd()}")
            
            # Ensure required directories exist on FTP
            self._ensure_ftp_directories(ftp)
            
            self.ftp = ftp
            return ftp
            
        except Exception as e:
            logger.error(f"Failed to connect to FTP: {e}")
            raise
    
    def _ensure_ftp_directories(self, ftp: ftplib.FTP):
        """Verify and create FTP directories for all enabled courts"""
        enabled_courts = self.ftp_config.get_enabled_courts()

        for court_code in enabled_courts:
            court_paths = self.ftp_config.get_court_paths(court_code)
            if not court_paths:
                continue

            logger.info(f"Ensuring FTP directories for {court_code} court...")

            # 1) Inbox must already exist (exact path & case)
            inbox = court_paths['inbox'].rstrip("/")
            try:
                ftp.cwd(inbox)
                logger.info(f"{court_code} inbox OK: {inbox}")
            except ftplib.error_perm as e:
                logger.warning(f"{court_code} inbox does not exist: '{inbox}' ({e})")
                continue  # Skip this court if inbox doesn't exist

            # 2) Auto-create output and archive directories if missing
            for dir_type in ['results', 'processed', 'invalid']:
                path = court_paths[dir_type].rstrip("/")
                try:
                    ftp.cwd(path)  # Check if exists
                    logger.debug(f"{court_code} {dir_type} directory exists: {path}")
                except ftplib.error_perm:
                    try:
                        # Create directory (and parent directories if needed)
                        self._create_ftp_directory_recursive(ftp, path)
                        logger.info(f"Created {court_code} {dir_type} directory: {path}")
                    except Exception as e:
                        logger.warning(f"Could not create {court_code} {dir_type} directory '{path}': {e}")

        # Also ensure legacy directories for backward compatibility
        if hasattr(self.ftp_config, 'ftp_inbox'):
            legacy_paths = [
                self.ftp_config.ftp_results,
                self.ftp_config.ftp_processed,
                self.ftp_config.ftp_invalid,
            ]

            for raw_path in legacy_paths:
                path = raw_path.rstrip("/")
                try:
                    ftp.cwd(path)
                except ftplib.error_perm:
                    try:
                        self._create_ftp_directory_recursive(ftp, path)
                        logger.info(f"Created legacy directory: {path}")
                    except Exception as e:
                        logger.warning(f"Could not create legacy directory '{path}': {e}")

    def _create_ftp_directory_recursive(self, ftp: ftplib.FTP, path: str):
        """Create FTP directory and parent directories recursively"""
        path = path.strip('/')
        path_parts = path.split('/')

        current_path = ""
        for part in path_parts:
            if not part:
                continue

            current_path += "/" + part

            try:
                ftp.cwd(current_path)
            except ftplib.error_perm:
                try:
                    ftp.mkd(current_path)
                    logger.debug(f"Created directory: {current_path}")
                except Exception as e:
                    logger.debug(f"Could not create directory '{current_path}': {e}")
                    raise

    def disconnect_ftp(self):
        """Close FTP connection"""
        if self.ftp:
            try:
                self.ftp.quit()
                logger.info("FTP connection closed")
            except:
                pass
            self.ftp = None
    
    def list_ftp_files(self, directory: str = None) -> List[str]:
        """Return filenames (files only) in the given FTP directory.

        Order of strategies:
          1) MLSD -> filter type=='file'
          2) NLST -> keep entries that respond to SIZE (dirs typically don't)
          3) LIST -> parse Unix/Windows formats (last resort)
        """
        if not self.ftp:
            self.connect_ftp()

        dir_path = (directory or self.ftp_config.ftp_inbox).rstrip("/")

        # Use _chdir_strict if available
        try:
            self._chdir_strict(self.ftp, dir_path)
        except AttributeError:
            # Fallback if _chdir_strict doesn't exist in your class
            self.ftp.cwd(dir_path)

        # --- 1) MLSD (structured, preferred) ---
        try:
            files = []
            for name, facts in self.ftp.mlsd():
                # 'type' is 'file' or 'dir' (when server supports MLSD)
                if facts.get("type") == "file":
                    files.append(name)
            if files:
                logger.info(f"[LIST] PWD={self.ftp.pwd()}  MLSD -> {len(files)} file(s): {files}")
                return files
        except Exception as e:
            logger.debug(f"[LIST] MLSD not supported or failed: {e}")

        # --- 2) NLST + SIZE (portable, filenames only) ---
        try:
            names = [n for n in self.ftp.nlst() if n not in (".", "..")]
            files = []
            for n in names:
                try:
                    # SIZE usually works for files; dirs often raise
                    self.ftp.size(n)
                    files.append(n)
                except Exception:
                    # likely a directory or server doesn't support SIZE for it
                    pass
            if files:
                logger.info(f"[LIST] PWD={self.ftp.pwd()}  NLST/SIZE -> {len(files)} file(s): {files}")
                return files
        except Exception as e:
            logger.debug(f"[LIST] NLST failed: {e}")

        # --- 3) LIST parse (your original approach, plus Windows format support) ---
        try:
            lines: List[str] = []
            self.ftp.retrlines("LIST", lines.append)
            files = []
            for line in lines:
                parts = line.split()
                if not parts:
                    continue

                # Unix-like: starts with perms e.g. '-rw-r--r--' or 'drwxr-xr-x'
                token = parts[0]

                if token and token[0] in ("d", "l"):
                    # directory or symlink -> skip
                    continue

                if len(parts) >= 9 and token.startswith("-"):
                    # Unix file line: perms links owner group size month day time/name name...
                    name = " ".join(parts[8:])
                    files.append(name)
                    continue

                # Windows/IIS style LIST: "09-15-25  02:12PM       <DIR>  FolderName"
                # or                      "09-15-25  02:12PM         123  File.txt"
                if len(parts) >= 4:
                    # parts[2] is <DIR> for directories
                    if parts[2].upper() != "<DIR>":
                        name = " ".join(parts[3:])
                        files.append(name)

            logger.info(f"[LIST] PWD={self.ftp.pwd()}  LIST-parse -> {len(files)} file(s): {files}")
            return files
        except Exception as e:
            logger.error(f"Error listing FTP files in {dir_path}: {e}")
            return []
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from FTP"""
        if not self.ftp:
            self.connect_ftp()
        
        try:
            logger.info(f"Downloading: {remote_path} -> {local_path}")
            
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {remote_path}', f.write)
            
            logger.info(f"Successfully downloaded: {os.path.basename(remote_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {remote_path}: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file to FTP"""
        if not self.ftp:
            self.connect_ftp()
        
        try:
            logger.info(f"Uploading: {local_path} -> {remote_path}")
            
            with open(local_path, 'rb') as f:
                self.ftp.storbinary(f'STOR {remote_path}', f)
            
            logger.info(f"Successfully uploaded: {os.path.basename(local_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return False
    
    def delete_ftp_file(self, remote_path: str) -> bool:
        """Delete file from FTP"""
        if not self.ftp:
            self.connect_ftp()
        
        try:
            self.ftp.delete(remote_path)
            logger.info(f"Deleted from FTP: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {remote_path}: {e}")
            return False
    
    def move_ftp_file(self, source: str, destination: str) -> bool:
        """Move file on FTP server - IMPROVED VERSION
        Tries rename first, falls back to copy+delete if rename fails
        """
        if not self.ftp:
            self.connect_ftp()
        
        # First try simple rename (works if on same filesystem)
        try:
            self.ftp.rename(source, destination)
            logger.info(f"Moved on FTP (rename): {source} -> {destination}")
            return True
        except Exception as e:
            logger.warning(f"Rename failed, trying copy+delete: {e}")
        
        # Fallback: Download + Upload + Delete
        try:
            # Create temp file
            temp_file = os.path.join(self.ftp_config.local_temp_dir, "temp_move.tmp")
            
            # Parse source and destination paths
            source_file = os.path.basename(source.rstrip('/'))
            dest_dir = os.path.dirname(destination.rstrip('/'))
            dest_file = os.path.basename(destination.rstrip('/'))
            
            # Navigate to source directory and download
            source_dir = os.path.dirname(source.rstrip('/'))
            if source_dir:
                self.ftp.cwd(source_dir)
            
            logger.info(f"Downloading {source_file} for move operation")
            with open(temp_file, 'wb') as f:
                self.ftp.retrbinary(f'RETR {source_file}', f.write)
            
            # Navigate to destination directory and upload
            if dest_dir:
                self.ftp.cwd(dest_dir)
            
            logger.info(f"Uploading to {dest_dir}/{dest_file}")
            with open(temp_file, 'rb') as f:
                self.ftp.storbinary(f'STOR {dest_file}', f)
            
            # Delete original file
            if source_dir:
                self.ftp.cwd(source_dir)
            self.ftp.delete(source_file)
            
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            logger.info(f"Moved on FTP (copy+delete): {source} -> {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move {source} to {destination}: {e}")
            # Clean up temp file on failure
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.remove(temp_file)
            return False
    
    def process_ftp_file(self, filename: str, court_code: str = None, source_path: str = None) -> Dict:
        """Download, process, and upload results for a single file with multi-court support"""

        # Step 1: Detect court if not provided
        if not court_code:
            if source_path:
                court_code = self.ftp_config.detect_court_from_path(source_path)
            else:
                # Try to detect from filename
                court_code = self._detect_court_from_filename(filename)

        logger.info(f"Processing file: {filename} for court: {court_code}")

        # Step 2: Get court-specific paths
        court_paths = self.ftp_config.get_court_paths(court_code)
        if not court_paths:
            logger.error(f"No FTP configuration found for court: {court_code}")
            return {"status": "failed", "reason": f"no_ftp_config_for_court_{court_code}"}

        # Step 3: Setup file paths
        if source_path:
            remote_inbox_path = source_path
        else:
            remote_inbox_path = f"{court_paths['inbox'].rstrip('/')}/{filename}"

        local_download_path = os.path.join(
            self.ftp_config.local_temp_dir, "downloads", f"{court_code}_{filename}"
        )

        try:
            # Step 4: Download file
            if not self.download_file(remote_inbox_path, local_download_path):
                return {"status": "failed", "reason": "download_failed", "court_code": court_code}

            # Step 5: Process with multi-court validator
            logger.info(f"Processing {court_code} file: {filename}")
            result = self.file_processor.process_file(local_download_path, court_code=court_code)

            # Add court information to result
            result['court_code'] = court_code
            result['source_path'] = remote_inbox_path

            # Step 6: Upload results to court-specific directories
            if result['status'] == 'success' and self.ftp_config.upload_results:
                # Upload CSV result to court-specific results directory
                if 'csv_path' in result:
                    csv_filename = os.path.basename(result['csv_path'])
                    remote_csv_path = f"{court_paths['results'].rstrip('/')}/{csv_filename}"

                    if self.upload_file(result['csv_path'], remote_csv_path):
                        result['ftp_csv_path'] = remote_csv_path
                        logger.info(f"Uploaded {court_code} results: {remote_csv_path}")
                    else:
                        logger.warning(f"Failed to upload {court_code} results")

                # Archive original file in court-specific archive directory
                if self.ftp_config.archive_on_ftp:
                    archive_success = self._archive_ftp_file(
                        remote_inbox_path, filename, result, court_paths, court_code
                    )

                    if not archive_success:
                        result['archive_warning'] = f"File processed but not archived for {court_code}"

                elif self.ftp_config.delete_after_download:
                    # Delete from FTP inbox
                    if self.delete_ftp_file(remote_inbox_path):
                        logger.info(f"Deleted processed file from {court_code} inbox: {filename}")

            # Step 7: Cleanup local temp file
            if os.path.exists(local_download_path):
                os.remove(local_download_path)

            logger.info(f"Successfully processed {court_code} file: {filename}")
            return result

        except Exception as e:
            logger.error(f"Error processing {court_code} file {filename}: {e}")
            # Cleanup on error
            if os.path.exists(local_download_path):
                os.remove(local_download_path)
            return {"status": "failed", "reason": str(e), "court_code": court_code}

    def _detect_court_from_filename(self, filename: str) -> str:
        """Detect court from filename patterns"""
        filename_upper = filename.upper()

        # Check for court prefixes in filename
        court_prefixes = ['KEM_', 'SEA_', 'TAC_']
        for prefix in court_prefixes:
            if filename_upper.startswith(prefix):
                return prefix.rstrip('_')

        # Fallback to default court
        return getattr(self.ftp_config.court_detection, 'default_court', 'KEM') if hasattr(self.ftp_config, 'court_detection') else 'KEM'

    def _archive_ftp_file(self, remote_inbox_path: str, filename: str, result: Dict, court_paths: Dict, court_code: str) -> bool:
        """Archive file to court-specific FTP directory"""
        try:
            # Determine archive directory based on validation result
            if result.get('validation_status') == 'passed':
                archive_dir = court_paths['processed'].rstrip('/')
                status = 'passed'
            else:
                archive_dir = court_paths['invalid'].rstrip('/')
                status = 'failed'

            # Create archive filename with court code and timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            archive_name = f"{court_code}_{timestamp}_{status}_{filename}"
            archive_path = f"{archive_dir}/{archive_name}"

            # Move file on FTP to court-specific archive
            if self.move_ftp_file(remote_inbox_path, archive_path):
                result['ftp_archive_path'] = archive_path
                logger.info(f"Archived {court_code} file to: {archive_path}")
                return True
            else:
                logger.error(f"Failed to archive {court_code} file on FTP")
                return False

        except Exception as e:
            logger.error(f"Error archiving {court_code} file {filename}: {e}")
            return False
    
    def process_batch(self, max_files: int = None, court_code: str = None) -> List[Dict]:
        """Process a batch of files from FTP with multi-court support"""
        max_files = max_files or self.ftp_config.batch_size

        try:
            # Connect to FTP
            self.connect_ftp()

            results = []

            if court_code:
                # Process files for a specific court
                results.extend(self._process_court_batch(court_code, max_files))
            else:
                # Process files for all enabled courts
                if getattr(self.ftp_config, 'process_all_courts', True):
                    enabled_courts = self.ftp_config.get_enabled_courts()

                    # Respect court priority if configured
                    if hasattr(self.ftp_config, 'court_priority'):
                        court_order = [c for c in self.ftp_config.court_priority if c in enabled_courts]
                        court_order.extend([c for c in enabled_courts if c not in court_order])
                    else:
                        court_order = enabled_courts

                    files_per_court = max_files // len(court_order) if len(court_order) > 1 else max_files

                    for court in court_order:
                        logger.info(f"Processing batch for {court} court...")
                        court_results = self._process_court_batch(court, files_per_court)
                        results.extend(court_results)

                        # Stop if we've reached the total file limit
                        if len(results) >= max_files:
                            break
                else:
                    # Legacy mode: process default court only
                    default_court = getattr(self.ftp_config.court_detection, 'default_court', 'KEM') if hasattr(self.ftp_config, 'court_detection') else 'KEM'
                    results.extend(self._process_court_batch(default_court, max_files))

            # Disconnect
            self.disconnect_ftp()

            # Summary
            success_count = sum(1 for r in results if r['status'] == 'success')
            court_summary = {}
            for r in results:
                court = r.get('court_code', 'Unknown')
                if court not in court_summary:
                    court_summary[court] = {'total': 0, 'success': 0}
                court_summary[court]['total'] += 1
                if r['status'] == 'success':
                    court_summary[court]['success'] += 1

            logger.info(f"Multi-court batch complete: {success_count}/{len(results)} total succeeded")
            for court, stats in court_summary.items():
                logger.info(f"  {court}: {stats['success']}/{stats['total']} succeeded")

            return results

        except Exception as e:
            logger.error(f"Multi-court batch processing error: {e}")
            self.disconnect_ftp()
            return []

    def _process_court_batch(self, court_code: str, max_files: int) -> List[Dict]:
        """Process files for a specific court"""
        results = []

        try:
            # Get court-specific paths
            court_paths = self.ftp_config.get_court_paths(court_code)
            if not court_paths:
                logger.warning(f"No FTP configuration for court: {court_code}")
                return results

            if not court_paths.get('enabled', True):
                logger.info(f"Court {court_code} is disabled, skipping")
                return results

            # List files in court's inbox
            files = self.list_ftp_files(court_paths['inbox'])

            if not files:
                logger.debug(f"No files to process for {court_code}")
                return results

            # Process files (up to max_files)
            files_to_process = files[:max_files]

            logger.info(f"Processing {len(files_to_process)} files for {court_code} court")

            for filename in files_to_process:
                # Skip directories and hidden files
                if filename.startswith('.'):
                    continue

                # Build full source path for court detection
                source_path = f"{court_paths['inbox'].rstrip('/')}/{filename}"

                result = self.process_ftp_file(filename, court_code=court_code, source_path=source_path)
                result['filename'] = filename
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error processing {court_code} court batch: {e}")
            return results
    
    def run_continuous(self, interval_minutes: int = None):
        """Run continuous processing at specified interval"""
        if not SCHEDULE_AVAILABLE:
            logger.error("Schedule module not available. Cannot run continuous processing.")
            logger.info("Install with: pip install schedule")
            return

        interval = interval_minutes or self.ftp_config.process_interval_minutes

        logger.info(f"Starting continuous processing (every {interval} minutes)")

        # Schedule the job
        schedule.every(interval).minutes.do(self.process_batch)

        # Run immediately
        self.process_batch()

        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Continuous processing stopped by user")
            self.disconnect_ftp()
    
    def test_connection(self) -> bool:
        """Test FTP connection and permissions"""
        try:
            logger.info("Testing FTP connection...")
            
            # Connect
            self.connect_ftp()
            
            # Test directory access
            logger.info("Testing directory access...")
            self.ftp.cwd(self.ftp_config.ftp_base_path)
            logger.info(f"[SUCCESS] Can access base path: {self.ftp_config.ftp_base_path}")
            
            # Test file listing
            files = self.list_ftp_files(self.ftp_config.ftp_inbox)
            logger.info(f"[SUCCESS] Can list files in inbox: {len(files)} files found")
            
            # Test write permission (create and delete a test file)
            test_file = "test_permission.txt"
            test_path = f"{self.ftp_config.ftp_results.rstrip('/')}/{test_file}"
            local_test = os.path.join(self.ftp_config.local_temp_dir, test_file)
            
            with open(local_test, 'w') as f:
                f.write("File Validator FTP Test")
            
            if self.upload_file(local_test, test_path):
                logger.info("[SUCCESS] Can upload files")
                if self.delete_ftp_file(test_path):
                    logger.info("[SUCCESS] Can delete files")
            
            os.remove(local_test)
            
            # Test move operation
            logger.info("Testing move operation...")
            test_src = f"{self.ftp_config.ftp_results.rstrip('/')}/test_move_src.txt"
            test_dst = f"{self.ftp_config.ftp_processed.rstrip('/')}/test_move_dst.txt"
            
            # Create test file
            with open(local_test, 'w') as f:
                f.write("Test move operation")
            
            if self.upload_file(local_test, test_src):
                if self.move_ftp_file(test_src, test_dst):
                    logger.info("[SUCCESS] Can move files between directories")
                    # Clean up
                    self.delete_ftp_file(test_dst)
                else:
                    logger.warning("✗ Move operation failed")
                    # Clean up source if still exists
                    try:
                        self.delete_ftp_file(test_src)
                    except:
                        pass
            
            if os.path.exists(local_test):
                os.remove(local_test)
            
            # Disconnect
            self.disconnect_ftp()
            
            logger.info("[SUCCESS] FTP connection test successful!")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] FTP connection test failed: {e}")
            self.disconnect_ftp()
            return False


# ==================== CLI Interface ====================
def main():
    """Main CLI for FTP Processor"""
    print("=" * 60)
    print("  File Validator - FTP Processor")
    print("=" * 60)
    
    # Initialize
    ftp_processor = FTPProcessor()
    
    while True:
        print("\nOptions:")
        print("1. Test FTP Connection")
        print("2. List Files in FTP Inbox")
        print("3. Process Single File")
        print("4. Process All Files (Batch)")
        print("5. Start Continuous Processing")
        print("6. View/Edit FTP Configuration")
        print("7. Check Archive Folders")
        print("8. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            ftp_processor.test_connection()
        
        elif choice == "2":
            ftp_processor.connect_ftp()
            files = ftp_processor.list_ftp_files()
            if files:
                print(f"\nFiles in {ftp_processor.ftp_config.ftp_inbox}:")
                for i, file in enumerate(files, 1):
                    print(f"  {i}. {file}")
            else:
                print("No files found in inbox")
            ftp_processor.disconnect_ftp()
        
        elif choice == "3":
            filename = input("Enter filename to process: ").strip()
            if filename:
                ftp_processor.connect_ftp()
                result = ftp_processor.process_ftp_file(filename)
                print(f"\nResult: {result}")
                ftp_processor.disconnect_ftp()
        
        elif choice == "4":
            batch_size = input(f"Enter batch size (default {ftp_processor.ftp_config.batch_size}): ").strip()
            batch_size = int(batch_size) if batch_size else None
            results = ftp_processor.process_batch(batch_size)
            
            print(f"\nProcessed {len(results)} files:")
            for r in results:
                status = "[OK]" if r['status'] == 'success' else "[FAIL]"
                print(f"  {status} {r.get('filename', 'Unknown')}: {r.get('validation_status', r.get('reason', 'N/A'))}")
        
        elif choice == "5":
            interval = input(f"Enter interval in minutes (default {ftp_processor.ftp_config.process_interval_minutes}): ").strip()
            interval = int(interval) if interval else None
            print("\nStarting continuous processing. Press Ctrl+C to stop.")
            ftp_processor.run_continuous(interval)
        
        elif choice == "6":
            print("\nCurrent FTP Configuration:")
            print(f"  Server: {ftp_processor.ftp_config.ftp_server}")
            print(f"  Username: {ftp_processor.ftp_config.ftp_username}")
            print(f"  Base Path: {ftp_processor.ftp_config.ftp_base_path}")
            print(f"  Inbox: {ftp_processor.ftp_config.ftp_inbox}")
            print(f"  Results: {ftp_processor.ftp_config.ftp_results}")
            print(f"  Processed: {ftp_processor.ftp_config.ftp_processed}")
            print(f"  Invalid: {ftp_processor.ftp_config.ftp_invalid}")
            print("\nEdit ftp_config.json to change settings")
        
        elif choice == "7":
            print("\nChecking archive folders...")
            ftp_processor.connect_ftp()
            
            # Check processed archive
            processed_files = ftp_processor.list_ftp_files(ftp_processor.ftp_config.ftp_processed)
            print(f"\nProcessed Archive ({ftp_processor.ftp_config.ftp_processed}):")
            print(f"  {len(processed_files)} files")
            for f in processed_files[:5]:
                print(f"  - {f}")
            if len(processed_files) > 5:
                print(f"  ... and {len(processed_files) - 5} more")
            
            # Check invalid archive
            invalid_files = ftp_processor.list_ftp_files(ftp_processor.ftp_config.ftp_invalid)
            print(f"\nInvalid Archive ({ftp_processor.ftp_config.ftp_invalid}):")
            print(f"  {len(invalid_files)} files")
            for f in invalid_files[:5]:
                print(f"  - {f}")
            if len(invalid_files) > 5:
                print(f"  ... and {len(invalid_files) - 5} more")
            
            ftp_processor.disconnect_ftp()
        
        elif choice == "8":
            print("Goodbye!")
            break
        
        else:
            print("Invalid option")


if __name__ == "__main__":
    main()
