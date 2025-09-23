print("Tracing the processing error...")

# Test processing a file directly using current API
import os
from kem_validator_local import Config
from kem_validator_local import FileProcessor

# Prefer an existing sample file for reproducibility
default_sample = os.path.join("sample-files", "KEM_sample.txt")

# Original path kept for reference; update if you have a real file there
legacy_path = os.path.join("ftp_temp", "downloads", "KEM_KEM_20250501083031.txt")

test_file = default_sample if os.path.exists(default_sample) else legacy_path

if os.path.exists(test_file):
    print(f"OK. Test file exists: {test_file}")
    print(f"   File size: {os.path.getsize(test_file)} bytes")

    try:
        # Initialize processor using config.json if present
        config = Config.from_json("config.json")
        processor = FileProcessor(config)

        print("\nAttempting to process file...")
        result = processor.process_file(test_file, court_code='KEM')
        print("OK. Processing succeeded.")
        print("Result:")
        print(result)
    except Exception as e:
        print(f"ERR Processing failed: {e}")

        # Get more details
        import traceback
        print("\nDetailed error trace:")
        traceback.print_exc()

        # Quick config visibility
        try:
            print("\nConfig snapshot:")
            print(f"DB path: {config.db_path}")
            print(f"Input dir: {config.input_dir}")
            print(f"Output dir: {config.output_dir}")
            print(f"Processed dir: {config.processed_dir}")
            print(f"Invalid dir: {config.invalid_dir}")
        except Exception:
            pass
else:
    print(f"ERR File doesn't exist: {test_file}")
    print("Available files in sample-files:")
    if os.path.exists("sample-files"):
        for f in os.listdir("sample-files"):
            print(f"  - sample-files/{f}")
    print("\nAvailable files in ftp_temp/downloads:")
    if os.path.exists(os.path.join("ftp_temp", "downloads")):
        for f in os.listdir(os.path.join("ftp_temp", "downloads")):
            print(f"  - ftp_temp/downloads/{f}")

