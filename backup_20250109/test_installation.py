"""
Test script to verify all components are installed correctly
Run this after setup to ensure everything is working
"""

import sys
import importlib
from pathlib import Path

def test_import(module_name, package_name=None):
    """Test if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} installed successfully")
        return True
    except ImportError as e:
        print(f"❌ {module_name} not found. Install with: pip install {package_name or module_name}")
        print(f"   Error: {e}")
        return False

def test_directories():
    """Test if required directories exist"""
    dirs = ["kem-inbox", "kem-results", "processed-archive", "invalid-archive"]
    all_exist = True
    
    print("\n📁 Checking directories:")
    for dir_name in dirs:
        if Path(dir_name).exists():
            print(f"✅ {dir_name} exists")
        else:
            print(f"❌ {dir_name} missing - creating...")
            Path(dir_name).mkdir(exist_ok=True)
            all_exist = False
    
    return all_exist

def test_tesseract():
    """Test if Tesseract is installed"""
    print("\n🔍 Checking Tesseract OCR:")
    try:
        import pytesseract
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract installed: {version}")
        return True
    except Exception as e:
        print(f"❌ Tesseract not found or not configured")
        print("   Install from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False

def test_config():
    """Test if config.json exists"""
    print("\n⚙️ Checking configuration:")
    if Path("config.json").exists():
        print("✅ config.json found")
        try:
            import json
            with open("config.json", "r") as f:
                config = json.load(f)
            print(f"   Input dir: {config.get('input_dir', 'Not set')}")
            print(f"   Output dir: {config.get('output_dir', 'Not set')}")
            print(f"   OCR provider: {config.get('ocr_provider', 'Not set')}")
            return True
        except Exception as e:
            print(f"❌ Error reading config.json: {e}")
            return False
    else:
        print("❌ config.json not found")
        return False

def main():
    print("=" * 50)
    print("  KEM Validator - Installation Test")
    print("=" * 50)
    
    # Test required packages
    print("\n📦 Checking Python packages:")
    packages = [
        ("pandas", None),
        ("numpy", None),
        ("streamlit", None),
        ("plotly", None),
        ("watchdog", None),
        ("PyPDF2", None),
        ("PIL", "Pillow"),
        ("pytesseract", None),
    ]
    
    all_installed = True
    for module, package in packages:
        if not test_import(module, package):
            all_installed = False
    
    # Test optional packages
    print("\n📦 Checking optional packages:")
    optional = [
        ("openai", None),
        ("azure.ai.formrecognizer", "azure-ai-formrecognizer"),
    ]
    
    for module, package in optional:
        test_import(module, package)
    
    # Test directories
    dirs_exist = test_directories()
    
    # Test Tesseract
    tesseract_ok = test_tesseract()
    
    # Test config
    config_ok = test_config()
    
    # Test local modules
    print("\n🐍 Checking local modules:")
    try:
        import kem_validator_local
        print("✅ kem_validator_local.py found")
    except ImportError as e:
        print(f"❌ kem_validator_local.py not found: {e}")
        all_installed = False
    
    try:
        import streamlit_app
        print("✅ streamlit_app.py found")
    except ImportError as e:
        print(f"❌ streamlit_app.py not found: {e}")
        all_installed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_installed and dirs_exist and config_ok:
        print("✅ All required components are installed!")
        print("\nYou can now run:")
        print("  streamlit run streamlit_app.py")
        print("\nOr for CLI:")
        print("  python kem_validator_local.py")
    else:
        print("⚠️ Some components are missing.")
        print("Run: pip install -r requirements.txt")
        if not tesseract_ok:
            print("\n⚠️ Tesseract OCR needs to be installed separately")
            print("Download from: https://github.com/UB-Mannheim/tesseract/wiki")
    
    print("=" * 50)

if __name__ == "__main__":
    main()