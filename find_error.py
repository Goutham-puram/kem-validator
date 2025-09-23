# find_error.py
print("Looking for the exact error location...")

# Test the FTP processor initialization
try:
    from ftp_processor import FTPProcessor, FTPConfig
    ftp = FTPProcessor()
    print("✅ FTPProcessor created")
    
    # Check if config is properly initialized
    if hasattr(ftp, 'ftp_config'):
        print(f"   FTP Config: {type(ftp.ftp_config)}")
    if hasattr(ftp, 'kem_config'):
        print(f"   KEM Config: {type(ftp.kem_config)}")
        
except Exception as e:
    print(f"❌ FTPProcessor error: {e}")
    import traceback
    traceback.print_exc()

# Test database manager
try:
    from kem_validator_local import DatabaseManager
    # Don't initialize yet, just check import
    print("✅ DatabaseManager imported")
except Exception as e:
    print(f"❌ DatabaseManager error: {e}")

# Check for None assignments in session state
print("\nChecking critical initializations...")

critical_checks = [
    "from ftp_processor import FTPProcessor; fp = FTPProcessor(); print('FTP court_paths:', getattr(fp.ftp_config, 'court_paths', 'NOT FOUND'))",
    "from court_config_manager import CourtConfigManager; cm = CourtConfigManager(); print('Courts loaded:', len(cm.get_all_courts()))"
]

for check in critical_checks:
    try:
        exec(check)
    except Exception as e:
        print(f"❌ Check failed: {e}")
