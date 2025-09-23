import streamlit as st
import traceback
import sys

print("=" * 60)
print("DIAGNOSIS: Finding NoneType Error")
print("=" * 60)

# Check 1: Config Manager
try:
    from court_config_manager import CourtConfigManager
    ccm = CourtConfigManager()
    courts = ccm.get_all_courts()
    if courts is None:
        print("❌ get_all_courts() returns None!")
    else:
        print(f"✅ get_all_courts() returns: {type(courts)}")
        print(f"   Contains {len(courts)} courts")
except Exception as e:
    print(f"❌ Error with CourtConfigManager: {e}")

# Check 2: Look for common None assignments
print("\n" + "=" * 60)
print("Checking for None assignments in code...")

files_to_check = ['streamlit_ftp_app.py', 'ftp_processor.py', 'court_config_manager.py']

for filename in files_to_check:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                # Look for patterns that might cause None assignment
                if 'None[' in line or ('= None' in line and '[' in line):
                    print(f"⚠️ {filename}:{i+1}: {line.strip()}")
    except Exception as e:
        print(f"Could not check {filename}: {e}")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
