"""
FTP Processor for KEM Validator
Integrates with FTP server to download, process, and upload files
IMPROVED VERSION - Fixes archive move operation while preserving all existing functionality
"""

import ftplib
import os
import json
import logging
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time

# Import your existing KEM validator
from kem_validator_local import (
    Config, FileProcessor, KemValidator, DatabaseManager
)

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


class FTPConfig:
    """Enhanced FTP Configuration with multi-court support"""
    def __init__(self, config_path: str = "ftp_config.json"):
        self.load_config(config_path)

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
            logger.info(f"✓ Can access base path: {self.ftp_config.ftp_base_path}")
            
            # Test file listing
            files = self.list_ftp_files(self.ftp_config.ftp_inbox)
            logger.info(f"✓ Can list files in inbox: {len(files)} files found")
            
            # Test write permission (create and delete a test file)
            test_file = "test_permission.txt"
            test_path = f"{self.ftp_config.ftp_results.rstrip('/')}/{test_file}"
            local_test = os.path.join(self.ftp_config.local_temp_dir, test_file)
            
            with open(local_test, 'w') as f:
                f.write("KEM Validator FTP Test")
            
            if self.upload_file(local_test, test_path):
                logger.info("✓ Can upload files")
                if self.delete_ftp_file(test_path):
                    logger.info("✓ Can delete files")
            
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
                    logger.info("✓ Can move files between directories")
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
            
            logger.info("✅ FTP connection test successful!")
            return True
            
        except Exception as e:
            logger.error(f"❌ FTP connection test failed: {e}")
            self.disconnect_ftp()
            return False


# ==================== CLI Interface ====================
def main():
    """Main CLI for FTP Processor"""
    print("=" * 60)
    print("  KEM Validator - FTP Processor")
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
                status = "✓" if r['status'] == 'success' else "✗"
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