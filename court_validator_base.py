"""
Court Validator Base Classes
Provides flexible validation framework for multiple court systems
"""

import re
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    """Structured validation result"""

    def __init__(self, is_valid: bool, digits_only: str, digit_count: int,
                 fail_reason: str = "", raw_id: str = ""):
        self.is_valid = is_valid
        self.digits_only = digits_only
        self.digit_count = digit_count
        self.fail_reason = fail_reason
        self.raw_id = raw_id

    def to_dict(self) -> Dict:
        """Convert to dictionary format (compatible with existing code)"""
        return {
            'is_valid': self.is_valid,
            'digits_only': self.digits_only,
            'digit_count': self.digit_count,
            'fail_reason': self.fail_reason,
            'raw_id': self.raw_id
        }


class CourtValidator(ABC):
    """Abstract base class for court-specific validators"""

    def __init__(self, court_code: str, config: Dict):
        self.court_code = court_code
        self.config = config
        self.validation_rules = config.get('validation_rules', {})
        self.prefix = self.validation_rules.get('prefix', court_code)
        self.prefix_required = self.validation_rules.get('prefix_required', True)
        self.case_sensitive = self.validation_rules.get('case_sensitive', False)

    @abstractmethod
    def validate_id(self, document_id: str) -> ValidationResult:
        """Validate a document ID according to court-specific rules"""
        pass

    @abstractmethod
    def parse_line(self, line: str) -> Optional[str]:
        """Extract document ID from a line of text"""
        pass

    def validate_text(self, text: str) -> List[Dict]:
        """
        Validate all lines in text (compatible with existing KemValidator.validate_text)
        Returns list of validation results in legacy format
        """
        results = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip blank lines
            if not line.strip():
                continue

            # Try to parse document ID from line
            doc_id = self.parse_line(line)

            if doc_id is None:
                # Not a document line - informational only
                results.append({
                    'line_number': line_num,
                    'kem_id_raw': '',  # Keep legacy field name for compatibility
                    'kem_digits': '',  # Keep legacy field name for compatibility
                    'digits_count': 0,
                    'is_valid': True,
                    'fail_reason': f'not_a_{self.court_code}_line',
                    'raw': line
                })
            else:
                # Validate the document ID
                result = self.validate_id(doc_id)
                results.append({
                    'line_number': line_num,
                    'kem_id_raw': result.raw_id,  # Keep legacy field name
                    'kem_digits': result.digits_only,  # Keep legacy field name
                    'digits_count': result.digit_count,
                    'is_valid': result.is_valid,
                    'fail_reason': result.fail_reason,
                    'raw': line
                })

        return results


class DigitRangeValidator(CourtValidator):
    """Validator for courts that use digit count validation (like KEM)"""

    def __init__(self, court_code: str, config: Dict):
        super().__init__(court_code, config)
        self.min_digits = self.validation_rules.get('min_digits', 9)
        self.max_digits = self.validation_rules.get('max_digits', 13)
        self.allow_alphanumeric = self.validation_rules.get('allow_alphanumeric', True)

        # Create regex patterns for parsing
        self._create_patterns()

    def _create_patterns(self):
        """Create regex patterns for parsing based on configuration"""
        prefix = re.escape(self.prefix)
        flags = 0 if self.case_sensitive else re.IGNORECASE

        # Pattern for parsing lines
        self.line_pattern = re.compile(rf'\b{prefix}\s+(\S+)', flags)

    def parse_line(self, line: str) -> Optional[str]:
        """Extract document ID from a line"""
        # First try tab-separated format
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                prefix_check = parts[0].strip()
                if self.case_sensitive:
                    if prefix_check == self.prefix:
                        return parts[1].strip()
                else:
                    if prefix_check.upper() == self.prefix.upper():
                        return parts[1].strip()

        # Fall back to regex for space-separated format
        match = self.line_pattern.search(line)
        if match:
            return match.group(1)

        return None

    def validate_id(self, document_id: str) -> ValidationResult:
        """
        Validate a document ID based on digit count rules
        Compatible with existing KemValidator.validate_kem_id logic
        """
        if self.allow_alphanumeric:
            # Extract only digits from alphanumeric ID
            digits_only = ''.join(c for c in document_id if c.isdigit())
        else:
            # For numeric-only validation, the ID should already be digits
            if not document_id.isdigit():
                return ValidationResult(
                    is_valid=False,
                    digits_only='',
                    digit_count=0,
                    fail_reason="non_numeric_characters",
                    raw_id=document_id
                )
            digits_only = document_id

        digit_count = len(digits_only)

        if digit_count == 0:
            return ValidationResult(
                is_valid=False,
                digits_only=digits_only,
                digit_count=digit_count,
                fail_reason="no_digits_found",
                raw_id=document_id
            )

        if self.min_digits <= digit_count <= self.max_digits:
            return ValidationResult(
                is_valid=True,
                digits_only=digits_only,
                digit_count=digit_count,
                fail_reason="",
                raw_id=document_id
            )
        else:
            return ValidationResult(
                is_valid=False,
                digits_only=digits_only,
                digit_count=digit_count,
                fail_reason="digit_count_out_of_range",
                raw_id=document_id
            )


class PatternValidator(CourtValidator):
    """Validator for courts that use regex pattern validation"""

    def __init__(self, court_code: str, config: Dict):
        super().__init__(court_code, config)
        self.pattern = self.validation_rules.get('pattern', r'\d+')
        self.pattern_flags = re.IGNORECASE if not self.case_sensitive else 0

        # Compile validation pattern
        self.validation_pattern = re.compile(self.pattern, self.pattern_flags)

        # Create line parsing pattern
        self._create_patterns()

    def _create_patterns(self):
        """Create regex patterns for parsing based on configuration"""
        prefix = re.escape(self.prefix)
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self.line_pattern = re.compile(rf'\b{prefix}\s+(\S+)', flags)

    def parse_line(self, line: str) -> Optional[str]:
        """Extract document ID from a line (same logic as DigitRangeValidator)"""
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                prefix_check = parts[0].strip()
                if self.case_sensitive:
                    if prefix_check == self.prefix:
                        return parts[1].strip()
                else:
                    if prefix_check.upper() == self.prefix.upper():
                        return parts[1].strip()

        match = self.line_pattern.search(line)
        if match:
            return match.group(1)

        return None

    def validate_id(self, document_id: str) -> ValidationResult:
        """Validate document ID using regex pattern"""
        match = self.validation_pattern.fullmatch(document_id)

        if match:
            # Extract digits for compatibility with existing stats
            digits_only = ''.join(c for c in document_id if c.isdigit())
            return ValidationResult(
                is_valid=True,
                digits_only=digits_only,
                digit_count=len(digits_only),
                fail_reason="",
                raw_id=document_id
            )
        else:
            digits_only = ''.join(c for c in document_id if c.isdigit())
            return ValidationResult(
                is_valid=False,
                digits_only=digits_only,
                digit_count=len(digits_only),
                fail_reason="pattern_mismatch",
                raw_id=document_id
            )


class ValidatorFactory:
    """Factory class for creating court-specific validators"""

    def __init__(self, courts_config_path: str = "courts_config.json"):
        self.courts_config_path = courts_config_path
        self.courts_config = self._load_courts_config()
        self._validator_cache = {}

    def _load_courts_config(self) -> Dict:
        """Load courts configuration from JSON file"""
        try:
            if Path(self.courts_config_path).exists():
                with open(self.courts_config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Courts config file not found: {self.courts_config_path}")
                # Return minimal KEM config for backward compatibility
                return {
                    "default_court": "KEM",
                    "courts": {
                        "KEM": {
                            "name": "Kirkland Court",
                            "enabled": True,
                            "validation_rules": {
                                "min_digits": 9,
                                "max_digits": 13,
                                "prefix": "KEM",
                                "prefix_required": True,
                                "allow_alphanumeric": True,
                                "case_sensitive": False
                            }
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Error loading courts config: {e}")
            raise

    def get_validator(self, court_code: str = None) -> CourtValidator:
        """Get validator for specified court, or default court if not specified"""
        if court_code is None:
            court_code = self.courts_config.get('default_court', 'KEM')

        # Return cached validator if available
        if court_code in self._validator_cache:
            return self._validator_cache[court_code]

        # Check if court exists and is enabled
        if court_code not in self.courts_config.get('courts', {}):
            logger.warning(f"Court '{court_code}' not found in config, using default")
            court_code = self.courts_config.get('default_court', 'KEM')

        court_config = self.courts_config['courts'][court_code]

        if not court_config.get('enabled', False):
            logger.warning(f"Court '{court_code}' is disabled, using default")
            court_code = self.courts_config.get('default_court', 'KEM')
            court_config = self.courts_config['courts'][court_code]

        # Determine validator type based on configuration
        validation_rules = court_config.get('validation_rules', {})

        if 'pattern' in validation_rules:
            # Use pattern-based validator
            validator = PatternValidator(court_code, court_config)
        else:
            # Use digit range validator (default, compatible with KEM)
            validator = DigitRangeValidator(court_code, court_config)

        # Cache the validator
        self._validator_cache[court_code] = validator

        logger.info(f"Created {validator.__class__.__name__} for court '{court_code}'")
        return validator

    def get_available_courts(self) -> List[str]:
        """Get list of available and enabled courts"""
        courts = []
        for code, config in self.courts_config.get('courts', {}).items():
            if config.get('enabled', False):
                courts.append(code)
        return courts

    def detect_court_from_content(self, content: str) -> str:
        """Detect court code from file content"""
        detection_config = self.courts_config.get('court_detection', {})
        content_prefixes = detection_config.get('content_prefixes', {})

        for court_code, patterns in content_prefixes.items():
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    if self.courts_config['courts'][court_code].get('enabled', False):
                        return court_code

        # Return default court if no detection
        return self.courts_config.get('default_court', 'KEM')

    def detect_court_from_path(self, file_path: str) -> str:
        """Detect court code from file path"""
        detection_config = self.courts_config.get('court_detection', {})
        path_patterns = detection_config.get('path_patterns', {})

        for court_code, patterns in path_patterns.items():
            for pattern in patterns:
                if pattern in file_path:
                    if self.courts_config['courts'][court_code].get('enabled', False):
                        return court_code

        # Return default court if no detection
        return self.courts_config.get('default_court', 'KEM')


# Backward compatibility wrapper to maintain existing API
class LegacyKemValidator:
    """
    Wrapper class to maintain compatibility with existing KemValidator usage
    This allows existing code to work unchanged while using the new system
    """

    def __init__(self):
        self.factory = ValidatorFactory()
        self.validator = self.factory.get_validator('KEM')

    @staticmethod
    def parse_kem_line(line: str) -> Optional[str]:
        """Legacy method - delegates to KEM validator"""
        factory = ValidatorFactory()
        validator = factory.get_validator('KEM')
        return validator.parse_line(line)

    @staticmethod
    def validate_kem_id(kem_id: str) -> Tuple[bool, str, int, str]:
        """Legacy method - returns tuple format for backward compatibility"""
        factory = ValidatorFactory()
        validator = factory.get_validator('KEM')
        result = validator.validate_id(kem_id)
        return (result.is_valid, result.digits_only, result.digit_count, result.fail_reason)

    @staticmethod
    def validate_text(text: str) -> List[Dict]:
        """Legacy method - maintains exact same return format"""
        factory = ValidatorFactory()
        validator = factory.get_validator('KEM')
        return validator.validate_text(text)


# For backward compatibility, provide the original static methods
class KemValidator:
    """Backward compatibility class that matches original KemValidator interface"""

    @staticmethod
    def parse_kem_line(line: str) -> Optional[str]:
        return LegacyKemValidator.parse_kem_line(line)

    @staticmethod
    def validate_kem_id(kem_id: str) -> Tuple[bool, str, int, str]:
        return LegacyKemValidator.validate_kem_id(kem_id)

    @staticmethod
    def validate_text(text: str) -> List[Dict]:
        return LegacyKemValidator.validate_text(text)