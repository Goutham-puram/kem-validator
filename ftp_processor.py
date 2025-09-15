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
import schedule

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


class FTPConfig:
    """FTP Configuration"""
    def __init__(self, config_path: str = "ftp_config.json"):
        self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """Load FTP configuration from JSON file"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            # Default configuration based on given credentials
            config = {
                "ftp_server": "40.65.119.170",
                "ftp_port": 21,
                "ftp_username": "Ocourt",
                "ftp_password": "ptg_123",
                "ftp_base_path": "/PAMarchive/SeaTac/",
                "ftp_inbox": "/PAMarchive/SeaTac/kem-inbox/",
                "ftp_results": "/PAMarchive/SeaTac/kem-results/",
                "ftp_processed": "/PAMarchive/SeaTac/processed-archive/",
                "ftp_invalid": "/PAMarchive/SeaTac/invalid-archive/",
                "local_temp_dir": "ftp_temp",
                "process_interval_minutes": 5,
                "batch_size": 10,
                "delete_after_download": False,
                "upload_results": True,
                "archive_on_ftp": True
            }
            # Save default config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        
        # Set attributes
        for key, value in config.items():
            setattr(self, key, value)


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
        """Verify inbox exists exactly; create results/archives if missing."""
        # 1) Inbox must already exist (exact path & case)
        inbox = self.ftp_config.ftp_inbox.rstrip("/")
        try:
            ftp.cwd(inbox)  # fail if wrong/mismatched case
            logger.info(f"Inbox OK: {inbox}")
        except ftplib.error_perm as e:
            raise RuntimeError(
                f"Inbox does not exist or path/case is wrong: '{inbox}'. "
                f"Fix ftp_config.json to match WinSCP exactly. ({e})"
            )

        # 2) Auto-create the outbound and archive folders if missing
        for raw_path in (
            self.ftp_config.ftp_results,
            self.ftp_config.ftp_processed,
            self.ftp_config.ftp_invalid,
        ):
            path = raw_path.rstrip("/")
            try:
                ftp.cwd(path)            # already exists
            except ftplib.error_perm:
                try:
                    ftp.mkd(path)        # create if missing
                    logger.info(f"Created FTP directory: {path}")
                except Exception as e:
                    logger.warning(f"Could not create FTP directory '{path}': {e}")

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
    
    def process_ftp_file(self, filename: str) -> Dict:
        """Download, process, and upload results for a single file"""
        
        # Setup paths - clean up any double slashes
        remote_inbox_path = f"{self.ftp_config.ftp_inbox.rstrip('/')}/{filename}"
        local_download_path = os.path.join(
            self.ftp_config.local_temp_dir, "downloads", filename
        )
        
        try:
            # Step 1: Download file
            if not self.download_file(remote_inbox_path, local_download_path):
                return {"status": "failed", "reason": "download_failed"}
            
            # Step 2: Process with KEM Validator
            logger.info(f"Processing file: {filename}")
            result = self.file_processor.process_file(local_download_path)
            
            # Step 3: Upload results if successful
            if result['status'] == 'success' and self.ftp_config.upload_results:
                # Upload CSV result
                if 'csv_path' in result:
                    csv_filename = os.path.basename(result['csv_path'])
                    remote_csv_path = f"{self.ftp_config.ftp_results.rstrip('/')}/{csv_filename}"
                    self.upload_file(result['csv_path'], remote_csv_path)
                    result['ftp_csv_path'] = remote_csv_path
                
                # Archive original file on FTP
                if self.ftp_config.archive_on_ftp:
                    if result['validation_status'] == 'passed':
                        archive_dir = self.ftp_config.ftp_processed.rstrip('/')
                    else:
                        archive_dir = self.ftp_config.ftp_invalid.rstrip('/')
                    
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    archive_name = f"{timestamp}_{result['validation_status']}_{filename}"
                    archive_path = f"{archive_dir}/{archive_name}"
                    
                    # Move file on FTP with improved method
                    if self.move_ftp_file(remote_inbox_path, archive_path):
                        result['ftp_archive_path'] = archive_path
                        logger.info(f"File successfully archived to: {archive_path}")
                    else:
                        logger.error(f"Failed to archive file on FTP, file remains in inbox")
                        # Don't fail the whole process if archive fails
                        result['archive_warning'] = "File processed but not archived"
                
                elif self.ftp_config.delete_after_download:
                    # Delete from FTP inbox
                    self.delete_ftp_file(remote_inbox_path)
            
            # Step 4: Cleanup local temp file
            if os.path.exists(local_download_path):
                os.remove(local_download_path)
            
            logger.info(f"Successfully processed: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            # Cleanup on error
            if os.path.exists(local_download_path):
                os.remove(local_download_path)
            return {"status": "failed", "reason": str(e)}
    
    def process_batch(self, max_files: int = None) -> List[Dict]:
        """Process a batch of files from FTP"""
        max_files = max_files or self.ftp_config.batch_size
        
        try:
            # Connect to FTP
            self.connect_ftp()
            
            # List files in inbox
            files = self.list_ftp_files(self.ftp_config.ftp_inbox)
            
            if not files:
                logger.info("No files to process")
                return []
            
            # Process files (up to batch_size)
            results = []
            files_to_process = files[:max_files]
            
            logger.info(f"Processing batch of {len(files_to_process)} files")
            
            for filename in files_to_process:
                # Skip directories and hidden files
                if filename.startswith('.'):
                    continue
                
                result = self.process_ftp_file(filename)
                result['filename'] = filename
                results.append(result)
            
            # Disconnect
            self.disconnect_ftp()
            
            # Summary
            success_count = sum(1 for r in results if r['status'] == 'success')
            logger.info(f"Batch complete: {success_count}/{len(results)} succeeded")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            self.disconnect_ftp()
            return []
    
    def run_continuous(self, interval_minutes: int = None):
        """Run continuous processing at specified interval"""
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