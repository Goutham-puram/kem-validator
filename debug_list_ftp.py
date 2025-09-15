"""
Comprehensive FTP Debug - Check all directories and permissions
"""

import ftplib
import json

# Load config
with open('ftp_config.json', 'r') as f:
    config = json.load(f)

def debug_ftp_comprehensive():
    """Comprehensive FTP debugging"""
    
    print("=" * 60)
    print("Comprehensive FTP Debug")
    print("=" * 60)
    
    # Connect
    ftp = ftplib.FTP()
    ftp.connect(config['ftp_server'], config['ftp_port'])
    ftp.login(config['ftp_username'], config['ftp_password'])
    print(f"Connected as: {config['ftp_username']}")
    print(f"Initial directory: {ftp.pwd()}")
    print()
    
    # Check root directory
    print("ROOT DIRECTORY LISTING:")
    print("-" * 40)
    try:
        ftp.cwd("/")
        lines = []
        ftp.retrlines('LIST', lines.append)
        for line in lines:
            print(f"  {line}")
    except Exception as e:
        print(f"Error listing root: {e}")
    print()
    
    # Check PAMarchive
    print("CHECKING /PAMarchive:")
    print("-" * 40)
    try:
        ftp.cwd("/PAMarchive")
        print(f"Successfully changed to: {ftp.pwd()}")
        lines = []
        ftp.retrlines('LIST', lines.append)
        for line in lines:
            print(f"  {line}")
    except Exception as e:
        print(f"Error accessing /PAMarchive: {e}")
    print()
    
    # Check SeaTac
    print("CHECKING /PAMarchive/SeaTac:")
    print("-" * 40)
    try:
        ftp.cwd("/PAMarchive/SeaTac")
        print(f"Successfully changed to: {ftp.pwd()}")
        lines = []
        ftp.retrlines('LIST', lines.append)
        for line in lines:
            print(f"  {line}")
    except Exception as e:
        print(f"Error accessing /PAMarchive/SeaTac: {e}")
    print()
    
    # Try different paths for kem-inbox
    test_paths = [
        "/PAMarchive/SeaTac/kem-inbox",
        "/PAMarchive/SeaTac/Kem-inbox",
        "/PAMarchive/SeaTac/KEM-inbox",
        "/PAMarchive/SeaTac/kem-Inbox",
        "/PAMarchive/SeaTac/Kem-Inbox",
        "/PAMarchive/SeaTac/KEM-INBOX"
    ]
    
    print("TESTING VARIOUS INBOX PATHS:")
    print("-" * 40)
    for path in test_paths:
        try:
            ftp.cwd(path)
            print(f"✓ Found valid path: {path}")
            print(f"  Current directory: {ftp.pwd()}")
            
            # List contents
            lines = []
            ftp.retrlines('LIST', lines.append)
            if lines:
                print(f"  Contents ({len(lines)} items):")
                for line in lines:
                    print(f"    {line}")
            else:
                print(f"  Directory is EMPTY")
            break
        except ftplib.error_perm as e:
            print(f"✗ {path}: {e}")
    print()
    
    # Check if file was placed in wrong location
    print("CHECKING OTHER DIRECTORIES FOR YOUR FILE:")
    print("-" * 40)
    
    # Check base SeaTac directory
    try:
        ftp.cwd("/PAMarchive/SeaTac")
        lines = []
        ftp.retrlines('LIST', lines.append)
        txt_files = [line for line in lines if '.txt' in line.lower() or 'KEM' in line]
        if txt_files:
            print("Found potential KEM files in SeaTac directory:")
            for line in txt_files:
                print(f"  {line}")
    except:
        pass
    
    # Try STOR permission test
    print("\nTESTING UPLOAD PERMISSIONS:")
    print("-" * 40)
    test_content = "TEST"
    try:
        # Try to upload to kem-inbox
        ftp.cwd("/PAMarchive/SeaTac")
        
        # Create test file
        from io import BytesIO
        test_file = BytesIO(test_content.encode())
        
        # Try upload
        test_filename = "permission_test.txt"
        ftp.storbinary(f'STOR kem-inbox/{test_filename}', test_file)
        print(f"✓ Successfully uploaded test file to kem-inbox")
        
        # Try to list it
        ftp.cwd("/PAMarchive/SeaTac/kem-inbox")
        lines = []
        ftp.retrlines('LIST', lines.append)
        print(f"After upload, directory contains {len(lines)} items")
        
        # Clean up
        try:
            ftp.delete(test_filename)
            print(f"✓ Successfully deleted test file")
        except:
            pass
            
    except Exception as e:
        print(f"✗ Upload test failed: {e}")
    
    print("\nDEBUG COMPLETE!")
    print("\nSUMMARY:")
    print("- If directories are empty, files might be in wrong location")
    print("- If paths fail, check exact case sensitivity in WinSCP")
    print("- If upload fails, might be permissions issue")
    
    ftp.quit()

if __name__ == "__main__":
    debug_ftp_comprehensive()