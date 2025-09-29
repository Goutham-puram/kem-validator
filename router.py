"""
Content-based router for multi-court document classification.
Analyzes files using multiple signals to determine the appropriate court.
"""

import re
import json
import hashlib
from typing import Dict, Tuple, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CourtRouter:
    """
    Routes files to appropriate courts based on content analysis and scoring.
    """
    
    # Fixed scoring weights (tunable in future versions)
    WEIGHT_FILENAME = 50
    WEIGHT_PATH = 30
    WEIGHT_CONTENT_PER_MATCH = 3
    WEIGHT_CONTENT_MAX = 10
    WEIGHT_VALID_RATIO_MULTIPLIER = 100
    WEIGHT_DATE_RECENCY = 10
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    def classify_court(
        self,
        file_meta: Dict[str, Any],
        text: str,
        courts: Dict[str, Dict],
        default_code: str,
        router_cfg: Dict[str, Any]
    ) -> Tuple[str, int, str, str]:
        """
        Classify a file to determine which court it belongs to.
        
        Args:
            file_meta: Dictionary with 'filename', 'remote_path', 'size', 'mtime'
            text: Extracted text content from the file
            courts: Court configurations from CourtConfigManager
            default_code: Default court code if classification fails
            router_cfg: Router configuration with thresholds and mode
            
        Returns:
            Tuple of (winner_code, confidence, explanation, scores_json)
        """
        try:
            # Calculate scores for each enabled court
            court_scores = {}
            scoring_details = {}
            
            for court_code, court_config in courts.items():
                if not court_config.get('enabled', True):
                    continue
                    
                score, details = self._score_court(
                    file_meta, text, court_code, court_config
                )
                court_scores[court_code] = score
                scoring_details[court_code] = details
            
            # Determine winner based on threshold and margin rules
            winner_code, confidence, explanation = self._determine_winner(
                court_scores, 
                router_cfg.get('routing_threshold', 80),
                router_cfg.get('routing_margin', 20),
                default_code
            )
            
            # Prepare scores JSON for audit
            scores_data = {
                'scores': court_scores,
                'details': scoring_details,
                'winner': winner_code,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }
            scores_json = json.dumps(scores_data, separators=(',', ':'))
            
            return winner_code, confidence, explanation, scores_json
            
        except Exception as e:
            self.logger.error(f"Error in classify_court: {e}")
            # Fail safe to default court
            return default_code, 0, f"Classification error: {str(e)}", "{}"
    
    def _score_court(
        self, 
        file_meta: Dict,
        text: str,
        court_code: str,
        court_config: Dict
    ) -> Tuple[int, Dict]:
        """
        Calculate score for a specific court based on multiple signals.
        
        Returns:
            Tuple of (total_score, scoring_details)
        """
        score = 0
        details = {
            'filename_match': False,
            'path_match': False,
            'content_matches': 0,
            'valid_ratio': 0.0,
            'date_recent': False,
            'breakdown': {}
        }
        
        routing_hints = court_config.get('routing_hints', {})
        
        # 1. Filename prefix scoring (+50)
        filename = file_meta.get('filename', '').upper()
        filename_prefixes = routing_hints.get('filename_prefixes', [])
        if not filename_prefixes:
            # Default: check if filename starts with court code
            filename_prefixes = [f"{court_code}_", f"{court_code.lower()}_"]
        
        for prefix in filename_prefixes:
            if filename.startswith(prefix.upper()):
                score += self.WEIGHT_FILENAME
                details['filename_match'] = True
                details['breakdown']['filename'] = self.WEIGHT_FILENAME
                break
        
        # 2. Path pattern scoring (+30)
        remote_path = file_meta.get('remote_path', '')
        path_patterns = routing_hints.get('path_patterns', [])
        
        for pattern in path_patterns:
            if re.search(pattern, remote_path, re.IGNORECASE):
                score += self.WEIGHT_PATH
                details['path_match'] = True
                details['breakdown']['path'] = self.WEIGHT_PATH
                break
        
        # 3. Content prefix scoring (+3 per match, max +10)
        content_prefixes = routing_hints.get('content_prefixes', [])
        if content_prefixes and text:
            # Check first N lines (default 100)
            lines = text.split('\n')[:100]
            content_text = '\n'.join(lines)
            
            content_score = 0
            for pattern in content_prefixes:
                try:
                    matches = len(re.findall(pattern, content_text, re.IGNORECASE))
                    details['content_matches'] += matches
                    content_score += matches * self.WEIGHT_CONTENT_PER_MATCH
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern {pattern}: {e}")
            
            # Cap content score at max weight
            content_score = min(content_score, self.WEIGHT_CONTENT_MAX)
            score += content_score
            if content_score > 0:
                details['breakdown']['content'] = content_score
        
        # 4. Validation ratio scoring (+0 to +100)
        valid_ratio = self._calculate_valid_ratio(text, court_config)
        ratio_score = int(valid_ratio * self.WEIGHT_VALID_RATIO_MULTIPLIER)
        score += ratio_score
        details['valid_ratio'] = valid_ratio
        if ratio_score > 0:
            details['breakdown']['valid_ratio'] = ratio_score
        
        # 5. Date recency scoring (+10)
        date_recency_days = routing_hints.get('date_recency_days')
        if date_recency_days:
            if self._is_date_recent(file_meta, text, date_recency_days):
                score += self.WEIGHT_DATE_RECENCY
                details['date_recent'] = True
                details['breakdown']['date_recency'] = self.WEIGHT_DATE_RECENCY
        
        return score, details
    
    def _calculate_valid_ratio(self, text: str, court_config: Dict) -> float:
        """
        Calculate ratio of valid lines for this court's validation rules.
        This is a simplified version - actual implementation would call
        the court's validator.
        """
        if not text:
            return 0.0
        
        lines = text.split('\n')
        if not lines:
            return 0.0
        
        # Simple heuristic based on court validation rules
        validation_rule = court_config.get('validation_rule', 'digit_range')
        
        if validation_rule == 'digit_range':
            min_digits = court_config.get('min_digits', 9)
            max_digits = court_config.get('max_digits', 13)
            
            valid_count = 0
            total_count = 0
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty/comment lines
                    continue
                    
                total_count += 1
                # Extract digits from line
                digits = ''.join(c for c in line if c.isdigit())
                if min_digits <= len(digits) <= max_digits:
                    valid_count += 1
            
            return valid_count / total_count if total_count > 0 else 0.0
        
        # Default for unknown validation rules
        return 0.5
    
    def _is_date_recent(
        self, 
        file_meta: Dict,
        text: str,
        recency_days: int
    ) -> bool:
        """
        Check if file contains recent dates within the recency window.
        """
        try:
            # Check filename for date pattern (YYYYMMDD or similar)
            filename = file_meta.get('filename', '')
            date_patterns = [
                r'(\d{8})',  # YYYYMMDD
                r'(\d{4}[-_]\d{2}[-_]\d{2})',  # YYYY-MM-DD or YYYY_MM_DD
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, filename)
                if match:
                    date_str = match.group(1).replace('-', '').replace('_', '')
                    try:
                        file_date = datetime.strptime(date_str[:8], '%Y%m%d')
                        days_diff = (datetime.now() - file_date).days
                        if 0 <= days_diff <= recency_days:
                            return True
                    except ValueError:
                        pass
            
            # Could also check content for dates, but keeping simple for now
            
        except Exception as e:
            self.logger.debug(f"Error checking date recency: {e}")
        
        return False
    
    def _determine_winner(
        self,
        court_scores: Dict[str, int],
        threshold: int,
        margin: int,
        default_code: str
    ) -> Tuple[str, int, str]:
        """
        Determine winning court based on scores, threshold, and margin.
        
        Returns:
            Tuple of (winner_code, confidence, explanation)
        """
        if not court_scores:
            return default_code, 0, "No courts available for classification"
        
        # Sort courts by score (descending)
        sorted_courts = sorted(
            court_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        top_court, top_score = sorted_courts[0]
        
        # Check if top score meets threshold
        if top_score < threshold:
            return "UNKNOWN", top_score, f"Top score {top_score} below threshold {threshold}"
        
        # Check margin if there's a second court
        if len(sorted_courts) > 1:
            second_court, second_score = sorted_courts[1]
            score_margin = top_score - second_score
            
            if score_margin < margin:
                return "UNKNOWN", top_score, \
                    f"Margin {score_margin} between {top_court}({top_score}) " \
                    f"and {second_court}({second_score}) below required {margin}"
        
        # Winner found
        confidence = min(100, top_score)  # Cap confidence at 100
        
        # Build explanation
        explanation = f"Classified as {top_court} with score {top_score}"
        if len(sorted_courts) > 1:
            explanation += f" (next: {sorted_courts[1][0]}={sorted_courts[1][1]})"
        
        return top_court, confidence, explanation


def classify_court(
    file_meta: Dict[str, Any],
    text: str,
    courts: Dict[str, Dict],
    default_code: str,
    router_cfg: Dict[str, Any]
) -> Tuple[str, int, str, str]:
    """
    Module-level function for court classification.
    
    This is the main entry point for the router module.
    
    Args:
        file_meta: Dictionary with 'filename', 'remote_path', 'size', 'mtime'
        text: Extracted text content from the file
        courts: Court configurations from CourtConfigManager
        default_code: Default court code if classification fails
        router_cfg: Router configuration with thresholds and mode
        
    Returns:
        Tuple of (winner_code, confidence, explanation, scores_json)
    """
    router = CourtRouter()
    return router.classify_court(file_meta, text, courts, default_code, router_cfg)


def generate_idempotency_key(file_meta: Dict[str, Any]) -> str:
    """
    Generate a unique key for idempotent processing.
    
    Args:
        file_meta: Dictionary with 'remote_path', 'size', 'mtime'
        
    Returns:
        SHA256 hash as hex string
    """
    remote_path = file_meta.get('remote_path', '')
    size = file_meta.get('size', 0)
    mtime = file_meta.get('mtime', '')
    
    # Create composite key
    key_parts = f"{remote_path}|{size}|{mtime}"
    
    # Generate SHA256 hash
    return hashlib.sha256(key_parts.encode('utf-8')).hexdigest()


def create_quarantine_report(
    file_meta: Dict[str, Any],
    court_scores: Dict[str, int],
    explanation: str,
    text_preview: str = None,
    preview_lines: int = 20
) -> List[Dict]:
    """
    Create a CSV-ready report for quarantined files.
    
    Args:
        file_meta: File metadata
        court_scores: Scores for each court
        explanation: Routing explanation
        text_preview: Optional text content for preview
        preview_lines: Number of lines to include in preview
        
    Returns:
        List of dictionaries for CSV writing
    """
    report_data = []
    
    # Sort courts by score for top 5
    sorted_scores = sorted(
        court_scores.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:5]
    
    # Base record
    record = {
        'filename': file_meta.get('filename', ''),
        'remote_path': file_meta.get('remote_path', ''),
        'file_size': file_meta.get('size', 0),
        'modified_time': file_meta.get('mtime', ''),
        'routing_explanation': explanation,
        'timestamp': datetime.now().isoformat()
    }
    
    # Add top 5 court scores
    for i, (court, score) in enumerate(sorted_scores, 1):
        record[f'court_{i}'] = court
        record[f'score_{i}'] = score
    
    # Add text preview if available
    if text_preview:
        lines = text_preview.split('\n')[:preview_lines]
        record['preview_lines'] = len(lines)
        record['text_preview'] = '\n'.join(lines)[:1000]  # Limit preview size
    
    report_data.append(record)
    
    return report_data