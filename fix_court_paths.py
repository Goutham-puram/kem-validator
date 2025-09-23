# fix_court_paths.py
print("Fixing court_paths initialization...")

# Read the ftp_processor.py file
with open('ftp_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Backup
with open('ftp_processor_backup.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("✅ Backup saved as ftp_processor_backup.py")

# Find FTPConfig class and add court_paths
fixed = False
for i, line in enumerate(lines):
    # Look for FTPConfig class __init__ or where attributes are set
    if 'class FTPConfig' in line:
        print(f"Found FTPConfig at line {i+1}")
        # Look for __init__ method in next ~20 lines
        for j in range(i, min(i+30, len(lines))):
            if 'def __init__' in lines[j]:
                print(f"Found __init__ at line {j+1}")
                # Find where to add court_paths initialization
                for k in range(j, min(j+50, len(lines))):
                    if 'self.' in lines[k] and 'court_paths' not in lines[k]:
                        # Add court_paths initialization after other self. assignments
                        if k+1 < len(lines) and ('self.' not in lines[k+1] or 'def ' in lines[k+1]):
                            indent = len(lines[k]) - len(lines[k].lstrip())
                            new_line = ' ' * indent + 'self.court_paths = {}  # Initialize court paths dictionary\n'
                            lines.insert(k+1, new_line)
                            print(f"✅ Added court_paths initialization at line {k+2}")
                            fixed = True
                            break
                if fixed:
                    break
        break

if not fixed:
    print("⚠️ Could not find exact location, adding manual fix...")
    # Alternative: Look for any __init__ in FTPConfig and add it there
    for i, line in enumerate(lines):
        if 'FTPConfig' in line and '__init__' in lines[i:i+10]:
            for j in range(i, min(i+20, len(lines))):
                if '__init__' in lines[j]:
                    # Add after the first self. assignment
                    for k in range(j, min(j+30, len(lines))):
                        if 'self.ftp_' in lines[k]:  # Look for FTP-related attributes
                            indent = len(lines[k]) - len(lines[k].lstrip())
                            new_line = ' ' * indent + 'self.court_paths = {}  # Initialize court paths\n'
                            if 'court_paths' not in ''.join(lines[k:k+5]):
                                lines.insert(k+1, new_line)
                                print(f"✅ Added court_paths at line {k+2}")
                                fixed = True
                                break
                    break
            break

# Write the fixed file
with open('ftp_processor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Fixed ftp_processor.py")

# Verify the fix
print("\nVerifying fix...")
from importlib import reload
import ftp_processor
reload(ftp_processor)
from ftp_processor import FTPProcessor
fp = FTPProcessor()
if hasattr(fp.ftp_config, 'court_paths'):
    print("✅ SUCCESS: court_paths now exists!")
    print(f"   Type: {type(fp.ftp_config.court_paths)}")
else:
    print("❌ Still not fixed, manual intervention needed")
