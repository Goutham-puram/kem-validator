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
from datetime import datetime
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
# ==================== Configuration ====================
class Config:
    """Application configuration"""
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

    # Additional config sections
    validation_rules: dict = field(default_factory=dict)
    file_settings: dict = field(default_factory=dict)
    logging: dict = field(default_factory=dict)
    web_interface: dict = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, path: str) -> 'Config':
        """Load configuration from JSON file"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return cls(**json.load(f))
        return cls()
    
    def save(self, path: str):
        """Save configuration to JSON file"""
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)


# ==================== Core Validator ====================
class KemValidator:
    """Core KEM validation logic"""
    
    @staticmethod
    def parse_kem_line(line: str) -> Optional[str]:
        """Extract KEM ID from a line"""
        # First try tab-separated format
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2 and parts[0] == 'KEM':
                return parts[1]
        
        # Fall back to regex for space-separated format
        match = re.search(r'\bKEM\s+(\S+)', line)
        if match:
            return match.group(1)
        
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
            kem_id = KemValidator.parse_kem_line(line)
            
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
                is_valid, digits, count, reason = KemValidator.validate_kem_id(kem_id)
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
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single file"""
        logger.info(f"Processing file: {file_path}")
        
        file_name = os.path.basename(file_path)
        file_ext = Path(file_path).suffix.lower()
        
        # Extract text based on file type
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
                self._archive_file(file_path, self.config.invalid_dir, "unsupported_type")
                return {"status": "failed", "reason": "unsupported_file_type"}
            
            # Validate content
            validation_results = self.validator.validate_text(text_content)
            
            # Calculate statistics
            stats = self._calculate_stats(validation_results)
            
            # Generate and save CSV
            csv_path = self._save_csv(file_name, validation_results, stats)
            
            # Save to database
            self.db.save_processing_result(file_name, stats, csv_path)
            
            # Archive original file
            archive_dir = self.config.processed_dir if stats['validation_status'] == 'passed' else self.config.invalid_dir
            self._archive_file(file_path, archive_dir, stats['validation_status'])
            
            logger.info(f"File processed successfully: {file_name} - {stats['validation_status']}")
            
            return {
                "status": "success",
                "file": file_name,
                "validation_status": stats['validation_status'],
                "stats": stats,
                "csv_path": csv_path
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_name}: {e}")
            self._archive_file(file_path, self.config.invalid_dir, "processing_error")
            return {"status": "failed", "reason": str(e)}
    
    def _calculate_stats(self, results: List[Dict]) -> Dict:
        """Calculate validation statistics"""
        total_lines = len(results)
        kem_lines = sum(1 for r in results if r['fail_reason'] != 'not_a_KEM_line')
        valid_lines = sum(1 for r in results if r['fail_reason'] != 'not_a_KEM_line' and r['is_valid'])
        failed_lines = sum(1 for r in results if r['fail_reason'] != 'not_a_KEM_line' and not r['is_valid'])
        
        validation_status = 'passed' if failed_lines == 0 else 'failed'
        
        return {
            'total_lines': total_lines,
            'kem_lines': kem_lines,
            'valid_lines': valid_lines,
            'failed_lines': failed_lines,
            'info_lines': total_lines - kem_lines,
            'validation_status': validation_status,
            'success_rate': (valid_lines / kem_lines * 100) if kem_lines > 0 else 0
        }
    
    def _save_csv(self, original_name: str, results: List[Dict], stats: Dict) -> str:
        """Save validation results to CSV"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%SZ')
        base_name = Path(original_name).stem
        status = 'validation_passed' if stats['validation_status'] == 'passed' else 'validation_failed'
        csv_name = f"{base_name}_{status}_{timestamp}.csv"
        csv_path = os.path.join(self.config.output_dir, csv_name)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['line_number', 'kem_id_raw', 'kem_digits', 'digits_count', 
                         'is_valid', 'fail_reason', 'raw']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        return csv_path
    
    def _archive_file(self, source_path: str, dest_dir: str, status: str):
        """Archive processed file"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        file_name = os.path.basename(source_path)
        dest_name = f"{timestamp}_{status}_{file_name}"
        dest_path = os.path.join(dest_dir, dest_name)
        
        os.rename(source_path, dest_path)
        logger.info(f"File archived: {dest_path}")


# ==================== Database Manager ====================
class DatabaseManager:
    """SQLite database for tracking processing history"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
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
                file_hash TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_processing_result(self, file_name: str, stats: Dict, csv_path: str):
        """Save processing result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO processing_history 
            (file_name, validation_status, total_lines, kem_lines, valid_lines, 
             failed_lines, success_rate, csv_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (file_name, stats['validation_status'], stats['total_lines'],
              stats['kem_lines'], stats['valid_lines'], stats['failed_lines'],
              stats['success_rate'], csv_path))
        
        conn.commit()
        conn.close()
    
    def get_history(self, limit: int = 100) -> pd.DataFrame:
        """Get processing history"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT * FROM processing_history ORDER BY processed_at DESC LIMIT ?",
            conn, params=(limit,)
        )
        conn.close()
        return df
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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


# ==================== Main Entry Point ====================
if __name__ == "__main__":
    cli = KemValidatorCLI()
    cli.run()