"""
KEM Validator - Local Python Application
Complete solution with file watching, OCR support, and web interface
"""

import os
import sys
import json
import csv
import re
import logging
import sqlite3
import hashlib
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import time
from io import StringIO
from dataclasses import dataclass, field, fields
from typing import Any, Dict

# Third-party imports (will be installed via requirements.txt)
import pandas as pd
import streamlit as st
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import PyPDF2
from PIL import Image
import pytesseract
import requests
from openai import OpenAI

# Optional imports - wrapped in try-except
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI not installed. Run: pip install openai")

try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("Azure Document Intelligence not installed. Run: pip install azure-ai-formrecognizer")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
# ==================== Configuration ====================
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


# ==================== Core Validator ====================
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


# ==================== OCR Processors ====================
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
        self.client = OpenAI(api_key=api_key)
    
    def extract_text(self, file_path: str) -> str:
        """Extract text using OpenAI Vision"""
        try:
            with open(file_path, "rb") as image_file:
                import base64
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
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


# ==================== File Processor ====================
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
        """
        Comprehensive court detection with audit trail

        Returns:
            Dict containing:
            - court_code: Detected court code
            - method: Detection method used
            - confidence: Confidence level
            - alternatives: Other possible courts found
            - audit_trail: Step-by-step detection log
        """
        audit_trail = []
        alternatives = []
        detected_court = None
        detection_method = None
        confidence = 0.0

        try:
            # Load court detection configuration
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
            filename_patterns = detection_config.get('filename_patterns', {
                'KEM': ['KEM_', 'KEM-', 'kem_', 'kem-'],
                'SEA': ['SEA_', 'SEA-', 'sea_', 'sea-'],
                'TAC': ['TAC_', 'TAC-', 'tac_', 'tac-']
            })

            for court_code, patterns in filename_patterns.items():
                for pattern in patterns:
                    if file_name.startswith(pattern):
                        detected_court = court_code
                        detection_method = "filename_prefix"
                        confidence = 0.95
                        audit_trail.append(f"SUCCESS: Filename prefix match: '{pattern}' -> {court_code}")
                        if should_log:
                            logger.info(f"Court detection: {court_code} via filename prefix '{pattern}' in {file_name}")
                        break
                if detected_court:
                    break

            # Method 2: Directory mapping detection
            if not detected_court:
                directory_mapping = detection_config.get('directory_mapping', {})
                for dir_pattern, court_code in directory_mapping.items():
                    if dir_pattern in file_path_lower:
                        if not detected_court or confidence < 0.8:
                            if detected_court and detected_court != court_code:
                                alternatives.append(detected_court)
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

            # Method 4: Path-based detection (legacy)
            if not detected_court or confidence < 0.6:
                try:
                    path_patterns = detection_config.get('path_patterns', {})
                    for court_code, patterns in path_patterns.items():
                        for pattern in patterns:
                            if pattern.lower() in file_path_lower:
                                if not detected_court or confidence < 0.6:
                                    if detected_court and detected_court != court_code:
                                        alternatives.append(detected_court)
                                    detected_court = court_code
                                    detection_method = "path_pattern"
                                    confidence = 0.6
                                    audit_trail.append(f"SUCCESS: Path pattern match: '{pattern}' -> {court_code}")
                                    if should_log:
                                        logger.info(f"Court detection: {court_code} via path pattern '{pattern}' in {file_path}")
                                break
                except Exception as e:
                    audit_trail.append(f"ERROR: Path detection error: {e}")

            # Method 5: Content-based detection (if content provided)
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

            # Log conflicts if multiple courts detected
            if alternatives and should_log and detection_config.get('audit_logging', {}).get('log_conflicts', True):
                logger.warning(f"Court detection conflict for {file_name}: detected={detected_court}, alternatives={alternatives}")
                audit_trail.append(f"WARNING: Conflict detected: chose {detected_court} over {alternatives}")

            result = {
                'court_code': detected_court,
                'method': detection_method,
                'confidence': confidence,
                'alternatives': alternatives,
                'audit_trail': audit_trail
            }

            # Log final decision
            if should_log and detection_config.get('audit_logging', {}).get('log_all_decisions', True):
                logger.info(f"Final court detection: {detected_court} via {detection_method} (confidence: {confidence:.2f}) for {file_name}")

            return result

        except Exception as e:
            logger.error(f"Error in court detection for {file_path}: {e}")
            audit_trail.append(f"ERROR: Detection error: {e}")
            return {
                'court_code': 'KEM',  # Safe fallback
                'method': 'error_fallback',
                'confidence': 0.0,
                'alternatives': [],
                'audit_trail': audit_trail
            }

    def _get_court_config_manager(self):
        """Get court configuration manager with error handling"""
        try:
            if hasattr(self.config, '_court_config_manager') and self.config._court_config_manager:
                return self.config._court_config_manager
            else:
                from court_config_manager import CourtConfigManager
                return CourtConfigManager()
        except:
            return None

    def _detect_court_from_content(self, content: str, detection_config: Dict) -> Tuple[str, float]:
        """
        Analyze file content to detect court code

        Returns:
            Tuple of (court_code, confidence) or None if no match
        """
        content_prefixes = detection_config.get('content_prefixes', {})

        # Count occurrences of each court's patterns
        court_scores = {}

        for court_code, patterns in content_prefixes.items():
            score = 0
            for pattern in patterns:
                import re
                matches = len(re.findall(pattern, content, re.MULTILINE | re.IGNORECASE))
                score += matches

            if score > 0:
                court_scores[court_code] = score

        if not court_scores:
            return None

        # Find court with highest score
        best_court = max(court_scores.items(), key=lambda x: x[1])
        court_code, score = best_court

        # Calculate confidence based on score and total lines
        lines = len(content.split('\n'))
        confidence = min(0.9, (score / max(1, lines)) * 5)  # Scale to reasonable confidence

        return court_code, confidence

    def _setup_court_directories(self, court_code: str):
        """Create court-specific directories if they don't exist"""
        try:
            # Get court-specific configuration if available
            from court_config_manager import get_court_config_manager
            config_manager = get_court_config_manager()
            court_info = config_manager.get_court(court_code)

            if court_info:
                # Use court-specific directories
                court_dirs = [
                    court_info.get_directory('input_dir'),
                    court_info.get_directory('output_dir'),
                    court_info.get_directory('processed_dir'),
                    court_info.get_directory('invalid_dir')
                ]
            else:
                # Fall back to creating court subdirectories
                court_dirs = [
                    os.path.join(self.config.input_dir, court_code.lower()),
                    os.path.join(self.config.output_dir, court_code.lower()),
                    os.path.join(self.config.processed_dir, court_code.lower()),
                    os.path.join(self.config.invalid_dir, court_code.lower())
                ]

            for dir_path in court_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)

        except ImportError:
            # Court configuration not available, create simple subdirectories
            court_dirs = [
                os.path.join(self.config.processed_dir, court_code.upper()),
                os.path.join(self.config.invalid_dir, court_code.upper())
            ]
            for dir_path in court_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not setup court-specific directories for {court_code}: {e}")
            # Continue with default directories
    
    def process_file(self, file_path: str, court_code: str = None) -> Dict[str, Any]:
        """Process a single file with enhanced multi-court support and audit trail"""
        logger.info(f"Processing file: {file_path}")

        file_name = os.path.basename(file_path)
        file_ext = Path(file_path).suffix.lower()

        # Initialize detection result
        detection_result = None

        # Extract text content first for detection and validation
        try:
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    text_content = f.read()
            elif file_ext == '.pdf':
                text_content = PdfProcessor.extract_text(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                text_content = self.ocr.extract_text(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_ext}")
                # Use provided court_code or detect from path only
                if court_code is None:
                    detection_result = self.detect_court_from_file(file_path, content=None)
                    court_code = detection_result['court_code']

                self._setup_court_directories(court_code)
                self._archive_file(file_path, self._get_court_archive_dir(court_code, 'invalid'), "unsupported_type", court_code)
                return {
                    "status": "failed",
                    "reason": "unsupported_file_type",
                    "court_code": court_code,
                    "detection": detection_result
                }

        except Exception as e:
            logger.error(f"Error extracting text from {file_name}: {e}")
            # Fallback court detection without content
            if court_code is None:
                detection_result = self.detect_court_from_file(file_path, content=None)
                court_code = detection_result['court_code']

            self._setup_court_directories(court_code)
            self._archive_file(file_path, self._get_court_archive_dir(court_code, 'invalid'), "text_extraction_error", court_code)
            return {
                "status": "failed",
                "reason": f"text_extraction_error: {e}",
                "court_code": court_code,
                "detection": detection_result
            }

        # Perform comprehensive court detection if not explicitly provided
        if court_code is None:
            detection_result = self.detect_court_from_file(file_path, content=text_content)
            court_code = detection_result['court_code']

            # Log detection audit trail if enabled
            config_manager = self._get_court_config_manager()
            if config_manager:
                detection_config = config_manager.get_court_detection_config()
                audit_logging = detection_config.get('audit_logging', {})

                if audit_logging.get('enabled', True) and detection_result:
                    logger.info(f"Court detection audit for {file_name}:")
                    for step in detection_result['audit_trail']:
                        logger.info(f"  {step}")

                    if detection_result['alternatives']:
                        logger.info(f"  Alternative courts considered: {detection_result['alternatives']}")
        else:
            # Court code was explicitly provided
            detection_result = {
                'court_code': court_code,
                'method': 'explicit_parameter',
                'confidence': 1.0,
                'alternatives': [],
                'audit_trail': [f"Court code explicitly provided: {court_code}"]
            }

        # Setup court-specific directories
        self._setup_court_directories(court_code)

        # Validate content detection against legacy method if available
        try:
            if hasattr(self.validator, 'detect_court_from_text'):
                legacy_content_court = self.validator.detect_court_from_text(text_content)
                if legacy_content_court != court_code and detection_result:
                    logger.info(f"Legacy content detection suggests '{legacy_content_court}' vs enhanced detection '{court_code}' - using enhanced result")
                    detection_result['audit_trail'].append(f"Legacy detection would suggest: {legacy_content_court}")
        except Exception as e:
            logger.debug(f"Legacy content detection not available: {e}")

        try:
            # Validate content using court-specific validator
            if hasattr(self.validator, 'validate_text_for_court'):
                validation_results = self.validator.validate_text_for_court(text_content, court_code)
            else:
                # Fallback for backward compatibility
                validation_results = self.validator.validate_text(text_content)

            # Calculate statistics
            stats = self._calculate_stats(validation_results, court_code)

            # Generate and save CSV with court code
            csv_path = self._save_csv(file_name, validation_results, stats, court_code)

            # Save to database with court code
            self.db.save_processing_result(file_name, stats, csv_path, court_code)

            # Archive original file to court-specific directory
            archive_status = stats['validation_status']
            archive_type = 'processed' if archive_status == 'passed' else 'invalid'
            archive_dir = self._get_court_archive_dir(court_code, archive_type)
            self._archive_file(file_path, archive_dir, archive_status, court_code)

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
            self._archive_file(file_path, self._get_court_archive_dir(court_code, 'invalid'), "processing_error", court_code)
            return {"status": "failed", "reason": str(e), "court_code": court_code, "detection": detection_result}
    
    def _calculate_stats(self, results: List[Dict], court_code: str = 'KEM') -> Dict:
        """Calculate validation statistics with court support and header safeguards"""
        import re
        total_lines = len(results)

        # Only count lines that are true court data rows:
        # - start with the court prefix at the beginning of the line (tab or space form)
        # - have a non-empty parsed ID and at least one digit present
        prefix = court_code.upper()

        def is_court_row(r: Dict) -> bool:
            raw = r.get('raw', '') or ''
            if not raw:
                return False
            starts_with_prefix = raw.startswith(f"{prefix}\t") or re.match(rf"^\s*{re.escape(prefix)}\s+", raw)
            if not starts_with_prefix:
                return False
            # Require that some digits were actually found to avoid counting headers
            if int(r.get('digits_count', 0) or 0) <= 0:
                return False
            # Must have a parsed ID token
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
            'kem_lines': kem_lines,  # Keep field name for backward compatibility
            'valid_lines': valid_lines,
            'failed_lines': failed_lines,
            'info_lines': total_lines - kem_lines,
            'validation_status': validation_status,
            'success_rate': (valid_lines / kem_lines * 100) if kem_lines > 0 else 0,
            'court_code': court_code  # Add court information
        }
    
    def _save_csv(self, original_name: str, results: List[Dict], stats: Dict, court_code: str = 'KEM') -> str:
        """Save validation results to CSV with enhanced court information and summary"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%SZ')
        base_name = Path(original_name).stem
        status = 'passed' if stats['validation_status'] == 'passed' else 'failed'

        # Enhanced CSV filename pattern: {court}_{filename}_{status}_{timestamp}.csv
        csv_name = f"{court_code}_{base_name}_{status}_{timestamp}.csv"

        # Get court information for headers
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
                # Fall back to court subdirectory
                output_dir = os.path.join(self.config.output_dir, court_code.upper())
                Path(output_dir).mkdir(parents=True, exist_ok=True)
        except (ImportError, Exception):
            # Fall back to default directory with court prefix in filename
            output_dir = self.config.output_dir

        csv_path = os.path.join(output_dir, csv_name)

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write enhanced header with court information
            writer.writerow([f"# Court Validation Report"])
            writer.writerow([f"# Court: {court_code} - {court_full_name}"])
            writer.writerow([f"# Source File: {original_name}"])
            writer.writerow([f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([f"# Status: {stats['validation_status'].upper()}"])
            writer.writerow([])  # Empty row for separation

            # Write court-specific summary statistics
            writer.writerow(["# COURT SUMMARY STATISTICS"])
            writer.writerow([f"# Court Code: {court_code}"])
            writer.writerow([f"# Court Name: {court_name}"])
            writer.writerow([f"# Total Lines Processed: {stats['total_lines']}"])
            writer.writerow([f"# {court_code} Lines Found: {stats['kem_lines']}"])  # Note: 'kem_lines' is generic for all courts
            writer.writerow([f"# Valid {court_code} IDs: {stats['valid_lines']}"])
            writer.writerow([f"# Failed {court_code} IDs: {stats['failed_lines']}"])
            writer.writerow([f"# Success Rate: {stats['success_rate']:.1f}%"])
            writer.writerow([])  # Empty row for separation

            # Write detailed validation results header
            writer.writerow(["# DETAILED VALIDATION RESULTS"])

            # Enhanced column headers with court context
            fieldnames = [
                'court_code',           # Prominently place court_code first
                'court_name',          # Add court name for clarity
                'line_number',
                f'{court_code.lower()}_id_raw',    # Court-specific ID field name
                f'{court_code.lower()}_digits',   # Court-specific digits field name
                'digits_count',
                'is_valid',
                'fail_reason',
                'validation_details',   # Enhanced failure details
                'raw_line'             # Clearer name for raw data
            ]

            writer.writerow(fieldnames)

            # Write enhanced result rows with court information
            for result in results:
                # Determine validation details based on court-specific rules
                validation_details = ""
                if not result['is_valid'] and result['fail_reason']:
                    if result['fail_reason'] == 'digit_count_out_of_range':
                        # Get court-specific digit requirements
                        try:
                            if court_info:
                                min_digits = court_info.validation_rules.get('min_digits', 'N/A')
                                max_digits = court_info.validation_rules.get('max_digits', 'N/A')
                                validation_details = f"Required: {min_digits}-{max_digits} digits"
                            else:
                                validation_details = "Digit count requirements not met"
                        except:
                            validation_details = "Digit count requirements not met"
                    elif 'not_a_' in result['fail_reason']:
                        validation_details = f"Not a {court_code} document line"
                    else:
                        validation_details = result['fail_reason'].replace('_', ' ').title()

                enhanced_row = [
                    court_code,                           # court_code (prominent first column)
                    court_name,                          # court_name (for clarity)
                    result['line_number'],               # line_number
                    result['kem_id_raw'],               # court_id_raw (keeping legacy field name for compatibility)
                    result['kem_digits'],               # court_digits (keeping legacy field name for compatibility)
                    result['digits_count'],             # digits_count
                    'VALID' if result['is_valid'] else 'INVALID',  # is_valid (clearer formatting)
                    result['fail_reason'],              # fail_reason (original code)
                    validation_details,                 # validation_details (human-readable)
                    result['raw']                       # raw_line (original line text)
                ]

                writer.writerow(enhanced_row)

            # Write summary footer
            writer.writerow([])  # Empty row for separation
            writer.writerow(["# END OF REPORT"])
            writer.writerow([f"# Report Generated by Court Validator v2.0 for {court_full_name}"])

        logger.info(f"Enhanced CSV saved for {court_code} ({court_name}): {csv_path}")
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

        # Include court code in archived filename for easy identification
        dest_name = f"{court_code}_{timestamp}_{status}_{file_name}"
        dest_path = os.path.join(dest_dir, dest_name)

        # Ensure destination directory exists
        Path(dest_dir).mkdir(parents=True, exist_ok=True)

        try:
            os.rename(source_path, dest_path)
            logger.info(f"File archived to {court_code} court directory: {dest_path}")

            # Update archive tracking database
            self._track_archived_file(dest_path, court_code, status, file_name)

        except Exception as e:
            logger.error(f"Failed to archive file {source_path}: {e}")
            # Try copy as fallback
            try:
                import shutil
                shutil.copy2(source_path, dest_path)
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

            # Create archive tracking table if it doesn't exist
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

            # Get file size
            file_size = os.path.getsize(archive_path) if os.path.exists(archive_path) else 0

            # Calculate retention date based on court configuration
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
                retention_days = 365  # Default 1 year

            retention_date = datetime.now() + timedelta(days=retention_days)
            return retention_date.strftime('%Y-%m-%d')

        except Exception:
            # Default to 1 year retention
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
            # Migrate processed archive files
            processed_dir = Path(self.config.processed_dir)
            if processed_dir.exists():
                migration_stats['processed_files'] = self._migrate_directory_files(
                    processed_dir, 'processed', migration_stats
                )

            # Migrate invalid archive files
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
            # Get all files in the directory (not in subdirectories)
            files_to_migrate = [f for f in directory.iterdir() if f.is_file()]

            for file_path in files_to_migrate:
                try:
                    # Detect court from filename or default to KEM
                    court_code = self._detect_court_from_filename(file_path.name)

                    # Get court-specific archive directory
                    dest_dir = self._get_court_archive_dir(court_code, archive_type)

                    # Generate new filename with court prefix if not already present
                    new_name = file_path.name
                    if not new_name.startswith(f"{court_code}_"):
                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        new_name = f"{court_code}_{timestamp}_migrated_{file_path.name}"

                    dest_path = os.path.join(dest_dir, new_name)

                    # Move file to court-specific directory
                    os.rename(str(file_path), dest_path)
                    migrated_count += 1

                    # Track the migrated file
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
        """Simple court detection from filename for migration"""
        filename_upper = filename.upper()

        # Check for court prefixes
        court_prefixes = ['KEM_', 'SEA_', 'TAC_']
        for prefix in court_prefixes:
            if filename_upper.startswith(prefix):
                return prefix.rstrip('_')

        # Default to KEM for legacy files
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

            # Build query based on court filter
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

                            # Remove from tracking database
                            cursor.execute('DELETE FROM archived_files WHERE id = ?', (file_id,))

                        logger.debug(f"{'Would delete' if dry_run else 'Deleted'} expired file: {archive_path}")
                    else:
                        # File doesn't exist, remove from database
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

            # Base statistics query
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

            # Also get directory-based statistics
            archive_stats = {}

            for row in results:
                court, total_files, total_size, oldest, newest, processed, invalid, expired = row

                # Calculate directory statistics
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
                # Get the base court directory (without monthly subdirectory)
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

                    # Merge monthly breakdown
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

                        # Extract month from directory structure or file date
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
            # Try to extract from directory structure (YYYY-MM format)
            path_parts = root.split(os.sep)
            for part in path_parts:
                if len(part) == 7 and part[4] == '-' and part[:4].isdigit() and part[5:].isdigit():
                    return part

            # Fall back to file modification time
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


# ==================== Database Manager ====================
class DatabaseManager:
    """SQLite database for tracking processing history"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema with multi-court support"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create main table with court_code support
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

        # Check if court_code column exists (for backward compatibility)
        cursor.execute("PRAGMA table_info(processing_history)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'court_code' not in columns:
            logger.info("Migrating database: Adding court_code column")
            cursor.execute('ALTER TABLE processing_history ADD COLUMN court_code TEXT DEFAULT "KEM"')

            # Update existing records to have KEM court code
            cursor.execute('UPDATE processing_history SET court_code = "KEM" WHERE court_code IS NULL')
            logger.info("Database migration completed: All existing records assigned to KEM court")

        # Create database schema version tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')

        # Record current schema version
        cursor.execute('''
            INSERT OR IGNORE INTO schema_version (version, description)
            VALUES ('1.1', 'Added multi-court support with court_code column')
        ''')

        conn.commit()
        conn.close()

        # Run router-related migrations (idempotent)
        try:
            self._run_router_migration()
        except Exception as e:
            logger.warning(f"Router migration skipped/failed: {e}")

    def _run_router_migration(self):
        """Run external router migration if available; fallback to internal steps."""
        try:
            from migrations.router_migration import RouterDatabaseMigration
            RouterDatabaseMigration(self.db_path).migrate()
            return
        except Exception as e:
            logger.debug(f"External router migration not used: {e}")

        # Fallback: minimal internal migration
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(processing_history)")
            cols = {row[1] for row in cursor.fetchall()}
            for name, coltype in [
                ("routed_court_code", "TEXT"),
                ("routing_confidence", "INTEGER"),
                ("routing_explanation", "TEXT"),
                ("router_scores_json", "TEXT"),
                ("idempotency_key", "TEXT"),
                ("router_mode", "TEXT"),
                ("quarantined", "INTEGER DEFAULT 0"),
            ]:
                if name not in cols:
                    try:
                        cursor.execute(f"ALTER TABLE processing_history ADD COLUMN {name} {coltype}")
                    except sqlite3.OperationalError:
                        pass
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_ledger (
                    idempotency_key TEXT PRIMARY KEY,
                    remote_path TEXT NOT NULL,
                    file_size INTEGER,
                    file_mtime TEXT,
                    court_code TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_status TEXT,
                    processing_id INTEGER,
                    FOREIGN KEY (processing_id) REFERENCES processing_history(id)
                )
                """
            )
            for idx, table, column in [
                ("idx_processing_history_court", "processing_history", "court_code"),
                ("idx_processing_history_routed", "processing_history", "routed_court_code"),
                ("idx_processing_history_processed_at", "processing_history", "processed_at"),
                ("idx_processing_history_idempotency", "processing_history", "idempotency_key"),
                ("idx_processed_ledger_processed_at", "processed_ledger", "processed_at"),
                ("idx_processed_ledger_path", "processed_ledger", "remote_path"),
            ]:
                try:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {table}({column})")
                except sqlite3.OperationalError:
                    pass
            conn.commit()
    
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


# ==================== File Watcher ====================
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


# ==================== CLI Interface ====================
class KemValidatorCLI:
    """Command-line interface"""
    
    def __init__(self):
        self.config = Config.from_json("config.json")
        self.processor = FileProcessor(self.config)
    
    def run(self):
        """Run the CLI"""
        print("=" * 50)
        print("  KEM Validator - Local Edition")
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


# ==================== Backward Compatibility Wrapper ====================
"""
Comprehensive backward compatibility layer for existing code
Ensures all existing imports, classes, and methods continue to work unchanged
"""

# Deprecation warning framework (commented out for now, can be enabled for migration)
def _deprecation_warning(old_name: str, new_name: str = None, version: str = "2.0"):
    """
    Framework for deprecation warnings - currently commented out
    Uncomment and customize when ready to guide users toward new API
    """
    # import warnings
    # message = f"{old_name} is deprecated"
    # if new_name:
    #     message += f" and will be removed in version {version}. Use {new_name} instead."
    # else:
    #     message += f" and will be removed in version {version}."
    # warnings.warn(message, DeprecationWarning, stacklevel=3)
    pass


# Alias classes for backward compatibility
# These ensure existing imports continue to work exactly as before

# Main validator class - already updated with backward compatibility
# KemValidator is now the compatibility wrapper that delegates to multi-court system

# Legacy validator preserved for direct access if needed
# LegacyKemValidator contains the original logic

# Config class - no changes needed, fully backward compatible
# Config class already supports new fields with defaults

# File processor - enhanced but backward compatible
# FileProcessor.process_file() works with existing signatures

# Database manager - enhanced but backward compatible
# DatabaseManager methods work with existing signatures, new court_code parameter optional

# OCR processors - no changes, fully backward compatible
TesseractOcr = TesseractOcr
OpenAiOcr = OpenAiOcr
AzureDocIntelligence = AzureDocIntelligence
PdfProcessor = PdfProcessor

# File watcher - no changes, fully backward compatible
FileWatcher = FileWatcher

# CLI interface - no changes, fully backward compatible
KemValidatorCLI = KemValidatorCLI


# Additional compatibility functions for edge cases
def get_validator():
    """
    Factory function for getting a validator instance
    Returns the backward-compatible KemValidator
    """
    # _deprecation_warning("get_validator()", "KemValidator", "2.0")
    return KemValidator()


def validate_kem_text(text: str):
    """
    Standalone function for text validation (if used anywhere)
    Delegates to the main KemValidator
    """
    # _deprecation_warning("validate_kem_text()", "KemValidator.validate_text()", "2.0")
    return KemValidator.validate_text(text)


def parse_kem_id(line: str):
    """
    Standalone function for ID parsing (if used anywhere)
    Delegates to the main KemValidator
    """
    # _deprecation_warning("parse_kem_id()", "KemValidator.parse_kem_line()", "2.0")
    return KemValidator.parse_kem_line(line)


# Module-level constants for backward compatibility
KEM_MIN_DIGITS = 9
KEM_MAX_DIGITS = 13
DEFAULT_COURT = 'KEM'

# Export list for explicit imports
__all__ = [
    # Core classes
    'Config',
    'KemValidator',
    'LegacyKemValidator',
    'CourtValidator',
    'FileProcessor',
    'DatabaseManager',

    # OCR classes
    'OcrProcessor',
    'TesseractOcr',
    'OpenAiOcr',
    'AzureDocIntelligence',
    'PdfProcessor',

    # Infrastructure classes
    'FileWatcher',
    'KemValidatorCLI',

    # Compatibility functions
    'get_validator',
    'validate_kem_text',
    'parse_kem_id',

    # Constants
    'KEM_MIN_DIGITS',
    'KEM_MAX_DIGITS',
    'DEFAULT_COURT'
]


# Verification that existing patterns work
def _verify_backward_compatibility():
    """
    Internal verification that common usage patterns still work
    This function is for internal testing and is not part of the public API
    """
    try:
        # Test 1: Basic validator usage
        validator = KemValidator()
        result = KemValidator.validate_kem_id('123456789')
        assert len(result) == 4, "validate_kem_id should return 4-tuple"

        # Test 2: Static methods work
        parsed = KemValidator.parse_kem_line('KEM\t123456789\tTest')
        assert parsed == '123456789', "parse_kem_line should work"

        # Test 3: Text validation works
        results = KemValidator.validate_text('KEM\t123456789\tTest')
        assert len(results) > 0, "validate_text should return results"

        # Test 4: FileProcessor creation
        config = Config()
        processor = FileProcessor(config)
        assert hasattr(processor, 'validator'), "FileProcessor should have validator"

        # Test 5: Database manager creation
        db = DatabaseManager(':memory:')  # In-memory database for testing
        assert hasattr(db, 'save_processing_result'), "DatabaseManager should have save method"

        return True
    except Exception as e:
        logger.error(f"Backward compatibility verification failed: {e}")
        return False


# Run verification on import (in debug mode only)
if __name__ != "__main__":
    # Only run verification when imported, not when run directly
    import os
    if os.environ.get('KEM_VALIDATOR_DEBUG'):
        if _verify_backward_compatibility():
            logger.debug("Backward compatibility verification passed")
        else:
            logger.warning("Backward compatibility verification failed")


# ==================== Main Entry Point ====================
if __name__ == "__main__":
    cli = KemValidatorCLI()
    cli.run()
