"""
Create comprehensive sample test files for Multi-Court Validator
This script generates test cases for KEM, SEA, TAC courts and edge cases
"""

import os
from pathlib import Path
from datetime import datetime
import json

def load_court_configurations():
    """Load court configurations to understand validation rules"""
    try:
        with open("courts_config.json", "r") as f:
            config = json.load(f)
        return config.get("courts", {})
    except FileNotFoundError:
        # Return default configurations if file doesn't exist
        return {
            "KEM": {
                "name": "Kirkland Court",
                "validation_rules": {"min_digits": 9, "max_digits": 13, "prefix": "KEM"}
            },
            "SEA": {
                "name": "Seattle Court",
                "validation_rules": {"min_digits": 8, "max_digits": 12, "prefix": "SEA"}
            },
            "TAC": {
                "name": "Tacoma Court",
                "validation_rules": {"min_digits": 10, "max_digits": 14, "prefix": "TAC"}
            }
        }

def create_kem_samples():
    """Create KEM-specific sample files (9-13 digits)"""

    # KEM Sample 1: Mixed valid/invalid
    kem_mixed = f"""KEM COURT VALIDATION TEST - MIXED CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Kirkland Court Equipment Inventory
===================================

VALID KEM IDs (9-13 digits):
KEM	123456789	Hydraulic Pump Model A - Valid (9 digits - minimum)
KEM	1234567890	Control Module B - Valid (10 digits)
KEM	12345678901	Sensor Unit C - Valid (11 digits)
KEM	123456789012	Valve Assembly D - Valid (12 digits)
KEM	1234567890123	Maximum Equipment E - Valid (13 digits - maximum)
KEM	987654321	Standard Item F - Valid (9 digits)
KEM	4152500182618	Legacy Item G - Valid (13 digits)

INVALID KEM IDs (outside 9-13 range):
KEM	12345678	Too Short Item H - Invalid (8 digits - below minimum)
KEM	1234567	Very Short Item I - Invalid (7 digits)
KEM	12345678901234	Too Long Item J - Invalid (14 digits - above maximum)
KEM	123456789012345	Extra Long Item K - Invalid (15 digits)
KEM	ABCDEFGH	No Digits Item L - Invalid (no numeric digits)
KEM	ABC123DEF456	Mixed Alpha Item M - Invalid (only 6 digits)
KEM		Empty ID Item N - Invalid (empty ID)

EDGE CASES:
KEM	000000000	All Zeros - Valid (9 digits)
KEM	9999999999999	All Nines - Valid (13 digits)
KEM	123-456-789	With Dashes - Valid (9 digits extracted)
KEM	(123)456-7890	Phone Format - Valid (10 digits extracted)

===================================
Expected Results:
- Valid entries: 11
- Invalid entries: 7
- Total KEM lines: 18
- Non-KEM informational lines: Multiple
"""

    # KEM Sample 2: All valid cases
    kem_valid = f"""KEM COURT - ALL VALID TEST CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
===================================

Testing all valid ranges for KEM (9-13 digits):

Minimum Length (9 digits):
KEM	123456789	Equipment Alpha
KEM	987654321	Equipment Beta
KEM	555444333	Equipment Gamma

Mid Range (10-12 digits):
KEM	1234567890	Ten Digit Item
KEM	12345678901	Eleven Digit Item
KEM	123456789012	Twelve Digit Item

Maximum Length (13 digits):
KEM	1234567890123	Maximum Length Item A
KEM	9876543210987	Maximum Length Item B
KEM	1111111111111	Maximum Length Item C

Special Valid Cases:
KEM	000000000	All Zeros (9 digits)
KEM	0000000000000	All Zeros Max (13 digits)
KEM	123.456.789.012	Dots Removed (12 digits)
KEM	A1B2C3D4E5F6G7H8I9	Alphanumeric (9 digits extracted)

===================================
All 16 entries should PASS validation
Expected success rate: 100%
"""

    # KEM Sample 3: All invalid cases
    kem_invalid = f"""KEM COURT - ALL INVALID TEST CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
===================================

Testing invalid cases for KEM (must be 9-13 digits):

Too Short (< 9 digits):
KEM	1	Single Digit
KEM	12	Two Digits
KEM	123	Three Digits
KEM	1234567	Seven Digits
KEM	12345678	Eight Digits

Too Long (> 13 digits):
KEM	12345678901234	Fourteen Digits
KEM	123456789012345	Fifteen Digits
KEM	1234567890123456	Sixteen Digits
KEM	12345678901234567890	Twenty Digits

No Valid Digits:
KEM	ABCDEFGHIJK	Pure Letters
KEM	!!!@@@###	Special Characters
KEM		Empty ID
KEM	---...---	Punctuation Only
KEM	αβγδεζηθι	Unicode Characters

Mixed Invalid:
KEM	ABC123	Only 3 digits in alphanumeric
KEM	12AB34CD56	Only 6 digits scattered
KEM	Phone: 123-456-7890	Text with 10 digits (but formatted)

===================================
All 18 entries should FAIL validation
Expected success rate: 0%
"""

    return [
        ("KEM_sample.txt", kem_mixed, "KEM mixed valid/invalid cases"),
        ("KEM_valid_only.txt", kem_valid, "KEM all valid cases"),
        ("KEM_invalid_only.txt", kem_invalid, "KEM all invalid cases")
    ]

def create_sea_samples():
    """Create SEA-specific sample files (8-12 digits)"""

    # SEA Sample 1: Mixed valid/invalid
    sea_mixed = f"""SEA COURT VALIDATION TEST - MIXED CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Seattle Court Equipment Registry
===================================

VALID SEA IDs (8-12 digits):
SEA	12345678	Marine Equipment A - Valid (8 digits - minimum)
SEA	123456789	Harbor Tool B - Valid (9 digits)
SEA	1234567890	Port Device C - Valid (10 digits)
SEA	12345678901	Ferry Part D - Valid (11 digits)
SEA	123456789012	Ship Component E - Valid (12 digits - maximum)
SEA	87654321	Standard Item F - Valid (8 digits)
SEA	555666777	Regular Equipment G - Valid (9 digits)

INVALID SEA IDs (outside 8-12 range):
SEA	1234567	Too Short Item H - Invalid (7 digits - below minimum)
SEA	123456	Very Short Item I - Invalid (6 digits)
SEA	1234567890123	Too Long Item J - Invalid (13 digits - above maximum)
SEA	12345678901234	Extra Long Item K - Invalid (14 digits)
SEA	SEATTLEPORT	No Digits Item L - Invalid (no numeric digits)
SEA	SEA123DOCK	Mixed Alpha Item M - Invalid (only 3 digits)
SEA		Empty ID Item N - Invalid (empty ID)

EDGE CASES:
SEA	00000000	All Zeros - Valid (8 digits)
SEA	999999999999	All Nines - Valid (12 digits)
SEA	123-456-78	With Dashes - Valid (8 digits extracted)
SEA	(206)555-1234	Phone Format - Valid (10 digits extracted)

===================================
Expected Results:
- Valid entries: 11
- Invalid entries: 7
- Total SEA lines: 18
"""

    # SEA Sample 2: All valid cases
    sea_valid = f"""SEA COURT - ALL VALID TEST CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
===================================

Testing all valid ranges for SEA (8-12 digits):

Minimum Length (8 digits):
SEA	12345678	Seattle Item Alpha
SEA	87654321	Seattle Item Beta
SEA	11223344	Seattle Item Gamma

Mid Range (9-11 digits):
SEA	123456789	Nine Digit Seattle Item
SEA	1234567890	Ten Digit Seattle Item
SEA	12345678901	Eleven Digit Seattle Item

Maximum Length (12 digits):
SEA	123456789012	Maximum Seattle Item A
SEA	987654321098	Maximum Seattle Item B
SEA	111222333444	Maximum Seattle Item C

Special Valid Cases:
SEA	00000000	All Zeros Min (8 digits)
SEA	000000000000	All Zeros Max (12 digits)
SEA	206.555.1234	Local Phone (10 digits)
SEA	P1O2R3T4S5E6A7T8	Alphanumeric (8 digits extracted)

===================================
All 15 entries should PASS validation
Expected success rate: 100%
"""

    # SEA Sample 3: All invalid cases
    sea_invalid = f"""SEA COURT - ALL INVALID TEST CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
===================================

Testing invalid cases for SEA (must be 8-12 digits):

Too Short (< 8 digits):
SEA	1	Single Digit
SEA	12	Two Digits
SEA	1234567	Seven Digits

Too Long (> 12 digits):
SEA	1234567890123	Thirteen Digits
SEA	12345678901234	Fourteen Digits
SEA	123456789012345	Fifteen Digits

No Valid Digits:
SEA	SEATTLE	Pure Letters
SEA	PORTSEATTLE	Port Name
SEA	@#$%^&*	Special Characters
SEA		Empty ID
SEA	ΑΒΓΔΕΖΗΘ	Greek Letters

Mixed Invalid:
SEA	SEA123	Only 3 digits
SEA	PORT456DOCK	Only 3 digits scattered
SEA	Container#789	Only 3 digits with text

===================================
All 15 entries should FAIL validation
Expected success rate: 0%
"""

    return [
        ("SEA_sample.txt", sea_mixed, "SEA mixed valid/invalid cases"),
        ("SEA_valid_only.txt", sea_valid, "SEA all valid cases"),
        ("SEA_invalid_only.txt", sea_invalid, "SEA all invalid cases")
    ]

def create_tac_samples():
    """Create TAC-specific sample files (10-14 digits)"""

    # TAC Sample 1: Mixed valid/invalid
    tac_mixed = f"""TAC COURT VALIDATION TEST - MIXED CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Tacoma Court Industrial Registry
===================================

VALID TAC IDs (10-14 digits):
TAC	1234567890	Industrial Unit A - Valid (10 digits - minimum)
TAC	12345678901	Factory Tool B - Valid (11 digits)
TAC	123456789012	Plant Device C - Valid (12 digits)
TAC	1234567890123	Facility Part D - Valid (13 digits)
TAC	12345678901234	Complex Component E - Valid (14 digits - maximum)
TAC	9876543210	Standard Item F - Valid (10 digits)
TAC	5554443332221	Regular Equipment G - Valid (13 digits)

INVALID TAC IDs (outside 10-14 range):
TAC	123456789	Too Short Item H - Invalid (9 digits - below minimum)
TAC	12345678	Very Short Item I - Invalid (8 digits)
TAC	123456789012345	Too Long Item J - Invalid (15 digits - above maximum)
TAC	1234567890123456	Extra Long Item K - Invalid (16 digits)
TAC	TACOMAPLANT	No Digits Item L - Invalid (no numeric digits)
TAC	TAC123MILL	Mixed Alpha Item M - Invalid (only 3 digits)
TAC		Empty ID Item N - Invalid (empty ID)

EDGE CASES:
TAC	0000000000	All Zeros - Valid (10 digits)
TAC	99999999999999	All Nines - Valid (14 digits)
TAC	253-555-1234	With Dashes - Valid (10 digits extracted)
TAC	(253)555-12345	Phone Plus - Valid (11 digits extracted)

===================================
Expected Results:
- Valid entries: 11
- Invalid entries: 7
- Total TAC lines: 18
"""

    # TAC Sample 2: All valid cases
    tac_valid = f"""TAC COURT - ALL VALID TEST CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
===================================

Testing all valid ranges for TAC (10-14 digits):

Minimum Length (10 digits):
TAC	1234567890	Tacoma Item Alpha
TAC	9876543210	Tacoma Item Beta
TAC	1122334455	Tacoma Item Gamma

Mid Range (11-13 digits):
TAC	12345678901	Eleven Digit Tacoma Item
TAC	123456789012	Twelve Digit Tacoma Item
TAC	1234567890123	Thirteen Digit Tacoma Item

Maximum Length (14 digits):
TAC	12345678901234	Maximum Tacoma Item A
TAC	98765432109876	Maximum Tacoma Item B
TAC	11112222333344	Maximum Tacoma Item C

Special Valid Cases:
TAC	0000000000	All Zeros Min (10 digits)
TAC	00000000000000	All Zeros Max (14 digits)
TAC	253.555.1234.56	Extended Phone (11 digits)
TAC	T1A2C3O4M5A6789012	Alphanumeric (10 digits extracted)

===================================
All 15 entries should PASS validation
Expected success rate: 100%
"""

    # TAC Sample 3: All invalid cases
    tac_invalid = f"""TAC COURT - ALL INVALID TEST CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
===================================

Testing invalid cases for TAC (must be 10-14 digits):

Too Short (< 10 digits):
TAC	1	Single Digit
TAC	123456789	Nine Digits

Too Long (> 14 digits):
TAC	123456789012345	Fifteen Digits
TAC	1234567890123456	Sixteen Digits
TAC	12345678901234567890	Twenty Digits

No Valid Digits:
TAC	TACOMA	Pure Letters
TAC	INDUSTRIAL	Industry Name
TAC	@#$%^&*()	Special Characters
TAC		Empty ID
TAC	ΩΦΨΧΥΤΣΡ	Greek Letters

Mixed Invalid:
TAC	TAC123	Only 3 digits
TAC	PLANT456MILL	Only 3 digits scattered
TAC	Factory#789ABC	Only 3 digits with text

===================================
All 15 entries should FAIL validation
Expected success rate: 0%
"""

    return [
        ("TAC_sample.txt", tac_mixed, "TAC mixed valid/invalid cases"),
        ("TAC_valid_only.txt", tac_valid, "TAC all valid cases"),
        ("TAC_invalid_only.txt", tac_invalid, "TAC all invalid cases")
    ]

def create_mixed_court_samples():
    """Create mixed-court batch test files"""

    # Mixed court batch 1: All courts together
    mixed_batch1 = f"""MULTI-COURT BATCH TEST - ALL COURTS
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Testing multiple courts in single file
===================================

KEM COURT ENTRIES (9-13 digits):
KEM	123456789	KEM Equipment 1 - Valid
KEM	1234567890123	KEM Equipment 2 - Valid
KEM	12345678	KEM Equipment 3 - Invalid (too short)
KEM	12345678901234	KEM Equipment 4 - Invalid (too long)

SEA COURT ENTRIES (8-12 digits):
SEA	12345678	SEA Equipment 1 - Valid
SEA	123456789012	SEA Equipment 2 - Valid
SEA	1234567	SEA Equipment 3 - Invalid (too short)
SEA	1234567890123	SEA Equipment 4 - Invalid (too long)

TAC COURT ENTRIES (10-14 digits):
TAC	1234567890	TAC Equipment 1 - Valid
TAC	12345678901234	TAC Equipment 2 - Valid
TAC	123456789	TAC Equipment 3 - Invalid (too short)
TAC	123456789012345	TAC Equipment 4 - Invalid (too long)

CROSS-COURT CONFUSION TESTS:
KEM	12345678	KEM with SEA-valid length - Invalid for KEM
SEA	123456789012345	SEA with TAC-invalid length - Invalid for SEA
TAC	12345678	TAC with SEA-valid length - Invalid for TAC

===================================
Expected Results by Court:
- KEM: 2 valid, 3 invalid
- SEA: 2 valid, 3 invalid
- TAC: 2 valid, 3 invalid
Total: 6 valid, 9 invalid
"""

    # Mixed court batch 2: Realistic data mix
    mixed_batch2 = f"""MULTI-COURT REALISTIC DATA MIX
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Simulating real-world multi-court processing
===================================

Daily Equipment Log - Multiple Jurisdictions
Date: {datetime.now().strftime("%Y-%m-%d")}

Morning Shift - Kirkland Operations:
KEM	4152500182618	Hydraulic System Primary
KEM	987654321	Control Panel Alpha
Equipment maintenance scheduled for next week.
KEM	1234567890123	Backup Generator Unit

Afternoon Shift - Seattle Harbor:
SEA	206555123	Marine Pump Station
SEA	87654321	Harbor Light Controller
Port operations running smoothly today.
SEA	555666777888	Navigation Equipment

Evening Shift - Tacoma Industrial:
TAC	2535551234567	Factory Conveyor System
TAC	1122334455	Industrial Press Unit
Manufacturing targets met for today.
TAC	9876543210123	Quality Control Station

Cross-Reference Items:
KEM	REFERENCE: SEA-87654321	Cross-reference note
SEA	REFERENCE: TAC-1122334455	Cross-reference note
TAC	REFERENCE: KEM-987654321	Cross-reference note

Mixed Format Lines:
KEM 123456789 Space-separated KEM item
SEA	12345678	Tab-separated SEA item
TAC   1234567890   Multiple-space TAC item

===================================
Expected Processing Results:
- Multiple courts in single file
- Various formatting styles
- Cross-references and notes
- Realistic data patterns
"""

    # Mixed court batch 3: Edge cases across courts
    mixed_edge_cases = f"""MULTI-COURT EDGE CASES BATCH
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Testing edge cases across all courts
===================================

MINIMUM LENGTH TESTS:
KEM	123456789	KEM minimum (9 digits) - Valid
SEA	12345678	SEA minimum (8 digits) - Valid
TAC	1234567890	TAC minimum (10 digits) - Valid

MAXIMUM LENGTH TESTS:
KEM	1234567890123	KEM maximum (13 digits) - Valid
SEA	123456789012	SEA maximum (12 digits) - Valid
TAC	12345678901234	TAC maximum (14 digits) - Valid

BOUNDARY VIOLATIONS:
KEM	12345678	One below KEM minimum - Invalid
SEA	1234567	One below SEA minimum - Invalid
TAC	123456789	One below TAC minimum - Invalid
KEM	12345678901234	One above KEM maximum - Invalid
SEA	1234567890123	One above SEA maximum - Invalid
TAC	123456789012345	One above TAC maximum - Invalid

ALL ZEROS TESTS:
KEM	000000000	KEM all zeros (9) - Valid
SEA	00000000	SEA all zeros (8) - Valid
TAC	0000000000	TAC all zeros (10) - Valid

ALL NINES TESTS:
KEM	9999999999999	KEM all nines (13) - Valid
SEA	999999999999	SEA all nines (12) - Valid
TAC	99999999999999	TAC all nines (14) - Valid

SPECIAL CHARACTER EXTRACTION:
KEM	123-456-789	KEM with dashes - Valid (9 digits)
SEA	(206)555-12	SEA phone format - Valid (8 digits)
TAC	253.555.1234	TAC dot format - Valid (10 digits)

ALPHANUMERIC MIXED:
KEM	A1B2C3D4E5F6G7H8I9	KEM alphanumeric - Valid (9 digits)
SEA	S1E2A3T4T5L6E78	SEA alphanumeric - Valid (8 digits)
TAC	T1A2C3O4M5A6789012	TAC alphanumeric - Valid (10 digits)

===================================
Comprehensive edge case testing across all courts
Tests minimum, maximum, boundaries, and special formats
"""

    return [
        ("mixed_court_batch1.txt", mixed_batch1, "Multi-court batch test - all courts"),
        ("mixed_court_realistic.txt", mixed_batch2, "Multi-court realistic data mix"),
        ("mixed_court_edge_cases.txt", mixed_edge_cases, "Multi-court edge cases batch")
    ]

def create_no_prefix_samples():
    """Create files without court prefixes to test default behavior"""

    # No prefix sample 1: Pure numeric data
    no_prefix1 = f"""NO PREFIX TEST - PURE NUMERIC DATA
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Testing default court assignment for data without prefixes
===================================

Equipment Registry - No Court Prefixes
Should default to KEM court validation (9-13 digits)

Equipment List:
123456789	Equipment Alpha - Should be valid for default KEM
1234567890123	Equipment Beta - Should be valid for default KEM
12345678	Equipment Gamma - Should be invalid for default KEM (too short)
12345678901234	Equipment Delta - Should be invalid for default KEM (too long)

87654321	Equipment Echo - Should be invalid for default KEM (8 digits)
987654321	Equipment Foxtrot - Should be valid for default KEM (9 digits)
1111111111111	Equipment Golf - Should be valid for default KEM (13 digits)
11111111111111	Equipment Hotel - Should be invalid for default KEM (14 digits)

Additional Data Lines:
This is a descriptive line without any court prefix.
No validation should be attempted on this line.

000000000	All zeros equipment - Should be valid for default KEM
9999999999999	All nines equipment - Should be valid for default KEM

===================================
Expected Results (assuming KEM default):
- Lines without prefixes should use default court rules
- Valid for KEM (9-13 digits): 6 items
- Invalid for KEM: 4 items
- Non-data lines: ignored
"""

    # No prefix sample 2: Mixed format without prefixes
    no_prefix2 = f"""NO PREFIX TEST - MIXED FORMATS
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Testing various data formats without court prefixes
===================================

CSV-style data (no prefixes):
123456789,Pump Assembly,Location A
87654321,Valve Unit,Location B
1234567890123,Control Panel,Location C
12345678,Sensor Pack,Location D

Tab-separated data (no prefixes):
987654321	Motor Unit	Building 1
1111111111111	Generator Set	Building 2
222222222	Transformer	Building 3
33333333333333	Switch Gear	Building 4

Space-separated data (no prefixes):
444444444 Relay Panel Room 5
5555555555555 Circuit Breaker Room 6
66666666 Distribution Board Room 7
777777777777777 Control System Room 8

Descriptive text without numeric data:
This equipment inventory covers all major components.
Regular maintenance is scheduled quarterly.
Contact facility management for access requirements.

Mixed alphanumeric (no prefixes):
A1B2C3D4E5F6G7H8I9	Mixed Alpha Equipment 1
X8Y9Z0W1V2U3T4S5R6Q7	Mixed Alpha Equipment 2

===================================
Expected Results (assuming default court behavior):
- Should process numeric portions using default court rules
- Format variations should not affect validation
- Non-numeric lines should be ignored or marked as informational
"""

    # No prefix sample 3: Edge cases without prefixes
    no_prefix3 = f"""NO PREFIX TEST - EDGE CASES
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Testing edge cases without court prefixes
===================================

Boundary length testing (no court specified):
1	Single digit
12	Two digits
123	Three digits
1234	Four digits
12345	Five digits
123456	Six digits
1234567	Seven digits
12345678	Eight digits - SEA valid, KEM/TAC invalid
123456789	Nine digits - KEM valid, SEA/TAC varies
1234567890	Ten digits - All courts potentially valid
12345678901	Eleven digits - KEM/SEA valid, TAC valid
123456789012	Twelve digits - KEM/SEA valid, TAC valid
1234567890123	Thirteen digits - KEM valid, SEA invalid, TAC valid
12345678901234	Fourteen digits - TAC valid, KEM/SEA invalid
123456789012345	Fifteen digits - All courts invalid

Special formatting (no prefixes):
123-456-789	Dashed format
(123)456-7890	Phone format
123.456.7890	Dotted format
123 456 7890	Spaced format

All same digits (no prefixes):
000000000	All zeros (9 digits)
111111111	All ones (9 digits)
999999999	All nines (9 digits)
0000000000000	All zeros (13 digits)
9999999999999	All nines (13 digits)

===================================
Expected Results:
- Should demonstrate default court assignment behavior
- Various lengths test different court compatibility
- Formatting should not affect digit extraction
- System should handle edge cases gracefully
"""

    return [
        ("no_prefix_numeric.txt", no_prefix1, "No prefix - pure numeric data"),
        ("no_prefix_mixed_formats.txt", no_prefix2, "No prefix - mixed data formats"),
        ("no_prefix_edge_cases.txt", no_prefix3, "No prefix - edge cases testing")
    ]

def create_performance_test_files():
    """Create large files for performance testing"""

    # Large mixed court file
    large_content = f"""PERFORMANCE TEST - LARGE MULTI-COURT FILE
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Testing system performance with large datasets
===================================

"""

    # Generate 1000 entries across all courts
    for i in range(1000):
        court = ["KEM", "SEA", "TAC"][i % 3]

        # Generate valid IDs based on court rules
        if court == "KEM":
            # KEM: 9-13 digits, generate 9-13 digit numbers
            digits = 9 + (i % 5)  # 9, 10, 11, 12, 13
            id_num = str(1000000000 + i)[:digits]
        elif court == "SEA":
            # SEA: 8-12 digits, generate 8-12 digit numbers
            digits = 8 + (i % 5)  # 8, 9, 10, 11, 12
            id_num = str(100000000 + i)[:digits]
        else:  # TAC
            # TAC: 10-14 digits, generate 10-14 digit numbers
            digits = 10 + (i % 5)  # 10, 11, 12, 13, 14
            id_num = str(10000000000 + i)[:digits]

        large_content += f"{court}\t{id_num}\tPerformance Test Item {i+1:04d}\n"

        # Add some non-court lines for realistic mix
        if i % 50 == 0:
            large_content += f"--- Batch {i//50 + 1} Status Report ---\n"

    large_content += f"""
===================================
Performance Test Summary:
- Total entries: 1000
- Courts: KEM (~333), SEA (~333), TAC (~334)
- All entries should be valid within their court rules
- Non-court informational lines: ~20
Expected processing time: Monitor for performance baseline
"""

    return [("performance_test_large.txt", large_content, "Performance test - 1000 multi-court entries")]

def create_sample_files():
    """Create all sample files"""

    # Ensure sample directory exists
    sample_dir = Path("sample-files")
    sample_dir.mkdir(exist_ok=True)

    # Also ensure kem-inbox exists for backward compatibility
    inbox_dir = Path("kem-inbox")
    inbox_dir.mkdir(exist_ok=True)

    print("Loading court configurations...")
    courts_config = load_court_configurations()

    print(f"Found {len(courts_config)} court configurations:")
    for code, court in courts_config.items():
        rules = court.get('validation_rules', {})
        min_d = rules.get('min_digits', 'N/A')
        max_d = rules.get('max_digits', 'N/A')
        print(f"  - {code}: {court.get('name', 'Unknown')} ({min_d}-{max_d} digits)")

    files_created = []

    print("\nCreating sample files...")

    # Create all sample file types
    all_samples = []
    all_samples.extend(create_kem_samples())
    all_samples.extend(create_sea_samples())
    all_samples.extend(create_tac_samples())
    all_samples.extend(create_mixed_court_samples())
    all_samples.extend(create_no_prefix_samples())
    all_samples.extend(create_performance_test_files())

    # Write all files
    for filename, content, description in all_samples:
        filepath = sample_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        files_created.append((filename, description))
        print(f"[OK] Created: {filename}")

    # Create legacy samples in kem-inbox for backward compatibility
    print("\nCreating backward compatibility samples in kem-inbox/...")
    kem_samples = create_kem_samples()
    for filename, content, description in kem_samples:
        filepath = inbox_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Legacy: {filename} (in kem-inbox/)")

    return files_created

def main():
    print("=" * 70)
    print("  MULTI-COURT SAMPLE FILE GENERATOR")
    print("=" * 70)
    print()

    files = create_sample_files()

    print()
    print("=" * 70)
    print(f"[SUCCESS] Created {len(files)} sample files in sample-files/")
    print()

    print("File Categories Created:")
    print("  [COURT] Court-Specific Samples:")
    print("     - KEM_sample.txt (9-13 digits)")
    print("     - SEA_sample.txt (8-12 digits)")
    print("     - TAC_sample.txt (10-14 digits)")
    print()
    print("  [MIXED] Mixed-Court Batches:")
    print("     - mixed_court_batch1.txt")
    print("     - mixed_court_realistic.txt")
    print("     - mixed_court_edge_cases.txt")
    print()
    print("  [NO-PREFIX] No-Prefix Tests:")
    print("     - no_prefix_numeric.txt")
    print("     - no_prefix_mixed_formats.txt")
    print("     - no_prefix_edge_cases.txt")
    print()
    print("  [PERFORMANCE] Performance Tests:")
    print("     - performance_test_large.txt (1000 entries)")
    print()

    print("Testing Instructions:")
    print("  1. Upload individual court files to test specific validation rules")
    print("  2. Process mixed-court batches to test multi-court handling")
    print("  3. Use no-prefix files to test default court assignment")
    print("  4. Run performance tests to verify system scaling")
    print()

    print("Validation Expectations:")
    print("  [OK] KEM: 9-13 digits valid")
    print("  [OK] SEA: 8-12 digits valid")
    print("  [OK] TAC: 10-14 digits valid")
    print("  [OK] No-prefix: Uses default court rules")
    print("  [OK] Mixed files: Court-specific validation per line")
    print()

    print("Run the validator:")
    print("  streamlit run streamlit_app.py")
    print("Or process directly:")
    print("  python kem_validator_local.py")
    print("=" * 70)

if __name__ == "__main__":
    main()