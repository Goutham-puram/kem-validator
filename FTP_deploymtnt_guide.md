# 🌐 KEM Validator - FTP Deployment Guide

## 📋 **Understanding Your Manager's Requirements**


1. **Connect** to FTP server at `40.65.119.170`
2. **Monitor** the `/PAMarchive/SeaTac/` directory
3. **Download** files for KEM validation
4. **Process** them using your validator
5. **Upload** results back to the FTP server
6. **Archive** processed files appropriately

---

## 🚀 **Step-by-Step Implementation**

### **Step 1: Install Additional Dependencies**

```powershell
# Activate your virtual environment
.\venv\Scripts\Activate

# Install FTP-related packages
pip install schedule paramiko

# Verify installation
pip list | Select-String "schedule"
```

### **Step 2: Add FTP Files to Your Project**

Create these new files in your project directory:

```
kem-validator/
├── ftp_processor.py        # NEW: FTP integration module
├── ftp_config.json         # NEW: FTP configuration
├── streamlit_ftp_app.py    # NEW: FTP web interface
├── requirements_ftp.txt    # NEW: Additional requirements
└── [existing files...]
```

### **Step 3: Configure FTP Settings**

Edit `ftp_config.json` with your required credentials:

```json
{
  "ftp_server": "40.65.119.170",
  "ftp_port": 21,
  "ftp_username": "Ocourt",
  "ftp_password": "ptg_123",
  "ftp_base_path": "/PAMarchive/SeaTac/",
  "ftp_inbox": "/PAMarchive/SeaTac/kem-inbox/",
  "ftp_results": "/PAMarchive/SeaTac/kem-results/",
  "ftp_processed": "/PAMarchive/SeaTac/processed-archive/",
  "ftp_invalid": "/PAMarchive/SeaTac/invalid-archive/"
}
```

### **Step 4: Test FTP Connection**

```powershell
# Run the FTP processor
python ftp_processor.py

# Select option 1 to test connection
# This will verify:
# - Connection to server
# - Login credentials
# - Directory access
# - Read/write permissions
```

### **Step 5: Create FTP Directory Structure**

The script will automatically create these directories on the FTP server:
```
/PAMarchive/SeaTac/
├── kem-inbox/          # Input files
├── kem-results/        # CSV outputs
├── processed-archive/  # Valid files
└── invalid-archive/    # Invalid files
```

### **Step 6: Run the Application**

#### **Option A: Web Interface (Recommended)**
```powershell
# Run the FTP-enabled web interface
streamlit run streamlit_ftp_app.py

# Open browser to http://localhost:8501
# Click "Connect" to establish FTP connection
```

#### **Option B: Command Line Interface**
```powershell
# Run the FTP CLI
python ftp_processor.py

# Menu options:
# 1. Test Connection
# 2. List Files
# 3. Process Single File
# 4. Process Batch
# 5. Continuous Processing
```

#### **Option C: Automated Processing**
```powershell
# Create a scheduled task for continuous processing
python -c "from ftp_processor import FTPProcessor; FTPProcessor().run_continuous(5)"
```

---

## 📊 **Processing Workflow**

### **1. File Upload (External System)**
Files are placed in `/PAMarchive/SeaTac/kem-inbox/` by external systems

### **2. Detection & Download**
```python
# System monitors FTP inbox
# Downloads new files to local temp directory
ftp://40.65.119.170/PAMarchive/SeaTac/kem-inbox/file.txt
→ Local: ftp_temp/downloads/file.txt
```

### **3. KEM Validation**
```python
# Process with existing validator
# Apply 9-13 digit rule
# Generate CSV report
```

### **4. Results Upload**
```python
# Upload CSV to FTP results folder
Local: kem-results/file_validation_passed_20240109.csv
→ ftp://40.65.119.170/PAMarchive/SeaTac/kem-results/
```

### **5. File Archival**
```python
# Move original file on FTP
From: /PAMarchive/SeaTac/kem-inbox/file.txt
To:   /PAMarchive/SeaTac/processed-archive/  (if passed)
Or:   /PAMarchive/SeaTac/invalid-archive/    (if failed)
```

---

## 🔧 **Configuration Options**

### **Processing Modes**

| Mode | Description | Use Case |
|------|-------------|----------|
| **Single File** | Process one specific file | Testing/debugging |
| **Batch** | Process N files at once | Regular processing |
| **Continuous** | Auto-process every X minutes | Production |
| **On-Demand** | Web UI triggered | Manual oversight |

### **Key Settings in `ftp_config.json`**

```json
{
  "process_interval_minutes": 5,    // How often to check for new files
  "batch_size": 10,                 // Files per batch
  "delete_after_download": false,   // Keep originals on FTP
  "upload_results": true,           // Upload CSVs to FTP
  "archive_on_ftp": true           // Move files to archive folders
}
```

---

## 🖥️ **Windows Task Scheduler Setup**

Create an automated task to run every 5 minutes:

### **1. Create PowerShell Script**
Save as `run_ftp_processor.ps1`:
```powershell
# FTP Processor Scheduled Task
Set-Location "C:\path\to\kem-validator"
& ".\venv\Scripts\Activate.ps1"
python -c "from ftp_processor import FTPProcessor; FTPProcessor().process_batch()"
```

### **2. Create Scheduled Task**
```powershell
# Run as Administrator
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\path\to\run_ftp_processor.ps1"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -Action $action -Trigger $trigger `
    -TaskName "KEM_Validator_FTP" -Description "Process KEM files from FTP"
```

---

## 🔍 **Monitoring & Logs**

### **Check Processing Status**
```powershell
# View logs
Get-Content ftp_processor.log -Tail 50

# Check database for history
python -c "from kem_validator_local import DatabaseManager; print(DatabaseManager('kem_validator.db').get_history(10))"
```

### **Log Files**
- `ftp_processor.log` - FTP operations
- `kem_validator.log` - Validation details
- `streamlit.log` - Web interface

---

## 🚨 **Troubleshooting**

### **Issue: Connection Refused**
```python
# Check firewall settings
# Verify FTP port 21 is open
# Try passive mode:
ftp.set_pasv(True)
```

### **Issue: Permission Denied**
```python
# Verify credentials
# Check directory permissions
# Contact IT for FTP access rights
```

### **Issue: Files Not Processing**
```python
# Check file extensions (.txt, .pdf, .csv)
# Verify file encoding (UTF-8)
# Check file size limits (default 10MB)
```

---

## 📈 **Performance Optimization**

### **For Large Files**
```python
# Increase timeout
"connection_timeout": 60  # seconds

# Process in smaller batches
"batch_size": 5
```

### **For Many Files**
```python
# Parallel processing (future enhancement)
# Use connection pooling
# Implement caching
```

---

## 🔒 **Security Best Practices**

1. **Never commit credentials** to Git
2. **Use environment variables** for passwords
3. **Implement **SSL/TLS** if available (FTPS)
4. **Rotate passwords** regularly
5. **Monitor access logs** for anomalies

### **Secure Configuration**
```python
# Use .env file
FTP_PASSWORD=ptg_123

# Load in code
from dotenv import load_dotenv
load_dotenv()
password = os.getenv('FTP_PASSWORD')
```

---

## 📊 **Success Metrics**

Monitor these KPIs:
- **Files Processed**: Target 100% within SLA
- **Processing Time**: <2 seconds per file
- **Error Rate**: <1%
- **Uptime**: 99.9%

---

## 🎯 **Quick Test**

### **1. Upload Test File to FTP**
Create `test_kem.txt`:
```
KEM	123456789	Test Valid
KEM	12345	Test Invalid
```

### **2. Upload via FTP Client**
Use FileZilla or command line:
```bash
ftp 40.65.119.170
> user Ocourt
> pass ptg_123
> cd /PAMarchive/SeaTac/kem-inbox/
> put test_kem.txt
> quit
```

### **3. Process File**
```powershell
python ftp_processor.py
# Choose option 3: Process Single File
# Enter: test_kem.txt
```

### **4. Verify Results**
- Check `/PAMarchive/SeaTac/kem-results/` for CSV
- Check `/PAMarchive/SeaTac/invalid-archive/` for archived file
- View processing history in web UI

---

## ✅ **Deployment Checklist**

- [ ] FTP credentials configured
- [ ] Connection test successful
- [ ] Directories created on FTP
- [ ] Test file processed successfully
- [ ] Results uploaded to FTP
- [ ] Archive folders working
- [ ] Scheduled task created (if needed)
- [ ] Monitoring in place
- [ ] Documentation updated
- [ ] Manager notified of completion

---

## 📞 **Support Contacts**

- **FTP Issues**: Contact IT/Network Admin
- **Application Issues**: Review logs and documentation
- **Validation Logic**: Check KEM rules (9-13 digits)

---

**Your KEM Validator is now FTP-enabled and ready for production use!** 🚀