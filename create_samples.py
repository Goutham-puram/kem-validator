"""
Create sample test files for KEM Validator
This script generates various test cases
"""

import os
from pathlib import Path
from datetime import datetime

def create_sample_files():
    """Create sample files with various test cases"""
    
    # Ensure kem-inbox directory exists
    inbox_dir = Path("kem-inbox")
    inbox_dir.mkdir(exist_ok=True)
    
    # Sample 1: Mixed valid/invalid KEM IDs
    sample1 = """HEADER: Equipment Inventory Report
Date: {}
Company: Test Corporation
================================

KEM	4152500182618	Hydraulic Pump Model A - Valid (13 digits)
KEM	41525000142927	Pressure Valve Type B - Invalid (14 digits - too many)
KEM	230471171	Control Module C - Valid (9 digits)
KEM	12345678	Sensor Unit D - Invalid (8 digits - too few)

This is an informational line about maintenance procedures.
No KEM code here, just general information.

KEM	5A0185948B	Alphanumeric Serial - Has 9 digits when extracted
KEM	ABCDEFGH	Pure Letters - Invalid (no digits at all)
KEM	9876543210	Standard Equipment - Valid (10 digits)

Additional notes and comments about the equipment.
These lines don't affect validation status.

KEM	1234567890123	Maximum Valid - Valid (exactly 13 digits)
KEM	123456789012	Near Maximum - Valid (12 digits)
KEM	12345678901	Mid-Range - Valid (11 digits)
KEM	999999999	Minimum Valid - Valid (exactly 9 digits)
KEM	88888888	Below Minimum - Invalid (8 digits)
KEM	12345678901234	Over Maximum - Invalid (14 digits)

FOOTER: End of equipment report
Total items: 12 KEM entries
Expected: 8 valid, 4 invalid
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Sample 2: All valid KEM IDs
    sample2 = """KEM VALIDATION TEST - ALL VALID
================================
KEM	123456789	Equipment 1 - 9 digits
KEM	1234567890	Equipment 2 - 10 digits
KEM	12345678901	Equipment 3 - 11 digits
KEM	123456789012	Equipment 4 - 12 digits
KEM	1234567890123	Equipment 5 - 13 digits
KEM	A1B2C3D4E5F6G7H8I9	Mixed alphanumeric - 9 digits extracted
KEM	SN987654321XX	Serial with prefix/suffix - 9 digits
================================
All entries should pass validation
"""
    
    # Sample 3: All invalid KEM IDs
    sample3 = """KEM VALIDATION TEST - ALL INVALID
================================
KEM	1234567	Too few - 7 digits
KEM	12345678	Too few - 8 digits
KEM	12345678901234	Too many - 14 digits
KEM	123456789012345	Too many - 15 digits
KEM	NODIGITS	No digits at all
KEM	X	Single character
KEM		Empty ID
================================
All entries should fail validation
"""
    
    # Sample 4: Tab vs Space separated
    sample4 = """FORMAT TEST - TAB AND SPACE SEPARATION
================================
Tab-separated (preferred):
KEM	123456789	Tab-separated entry
KEM	987654321	Another tab entry

Space-separated (fallback):
KEM 123456789 Space-separated entry
KEM 987654321 Another space entry

Mixed formatting:
KEM	123456789 Mixed tab and space
KEM  123456789  Multiple spaces
================================
All numeric entries are valid (9 digits)
"""
    
    # Sample 5: Edge cases
    sample5 = """EDGE CASES TEST
================================
KEM	000000000	All zeros - Valid (9 digits)
KEM	000000001	Leading zeros - Valid (9 digits)
KEM	1000000000	One and zeros - Valid (10 digits)
KEM	9999999999999	All nines - Valid (13 digits)
KEM	99999999999999	Too many nines - Invalid (14 digits)

Special characters in ID:
KEM	123-456-789	With dashes - Valid (9 digits extracted)
KEM	123.456.7890	With dots - Valid (10 digits extracted)
KEM	(123)456-7890	Phone format - Valid (10 digits extracted)
KEM	123/456/78901	With slashes - Valid (11 digits extracted)

Unicode and special cases:
KEM	①②③④⑤⑥⑦⑧⑨	Unicode numbers (may not extract properly)
KEM	12３４56789	Mixed ASCII and fullwidth - Depends on extraction
================================
Various edge cases for testing
"""
    
    # Write sample files
    files_created = []
    
    samples = [
        ("sample_mixed.txt", sample1, "Mixed valid/invalid KEM IDs"),
        ("sample_all_valid.txt", sample2, "All valid KEM IDs"),
        ("sample_all_invalid.txt", sample3, "All invalid KEM IDs"),
        ("sample_formats.txt", sample4, "Different formatting styles"),
        ("sample_edge_cases.txt", sample5, "Edge cases and special characters"),
    ]
    
    for filename, content, description in samples:
        filepath = inbox_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        files_created.append((filename, description))
        print(f"✅ Created: {filename} - {description}")
    
    # Create a CSV sample
    csv_content = """kem_id,description,quantity,location
KEM	123456789,Pump Assembly,5,Warehouse A
KEM	987654321,Valve Unit,12,Warehouse B
KEM	456789012,Control Panel,3,Site C
KEM	12345,Sensor Pack,25,Storage D
Non-KEM line for testing CSV processing
KEM	ABCD56789,Special Equipment,1,Lab E
"""
    
    csv_path = inbox_dir / "sample_data.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    files_created.append(("sample_data.csv", "CSV format test"))
    print(f"✅ Created: sample_data.csv - CSV format test")
    
    return files_created

def main():
    print("=" * 50)
    print("  Creating Sample Test Files")
    print("=" * 50)
    print()
    
    files = create_sample_files()
    
    print()
    print("=" * 50)
    print(f"✅ Created {len(files)} sample files in kem-inbox/")
    print()
    print("Test these files to verify:")
    print("1. Valid KEM IDs (9-13 digits) pass")
    print("2. Invalid KEM IDs (<9 or >13 digits) fail")
    print("3. Non-KEM lines are marked as informational")
    print("4. Different formats are handled correctly")
    print()
    print("Run the validator:")
    print("  streamlit run streamlit_app.py")
    print("Or process directly:")
    print("  python kem_validator_local.py")
    print("=" * 50)

if __name__ == "__main__":
    main()