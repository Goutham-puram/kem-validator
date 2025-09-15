"""
Streamlit Web Interface for KEM Validator with FTP Integration
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time
from pathlib import Path

# Import FTP processor
from sftp_processor import FTPProcessor, FTPConfig
from kem_validator_local import DatabaseManager

# Page configuration
st.set_page_config(
    page_title="KEM Validator - FTP Edition",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'ftp_processor' not in st.session_state:
    st.session_state.ftp_processor = FTPProcessor()
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'processing' not in st.session_state:
    st.session_state.processing = False

def main():
    """Main application"""
    
    # Header
    st.title("🌐 KEM Validator - FTP Integration")
    st.markdown("Process KEM validation files directly from FTP server")
    
    # Sidebar
    st.sidebar.title("🔌 FTP Connection")
    
    # Connection status
    if st.session_state.connected:
        st.sidebar.success("✅ Connected to FTP")
    else:
        st.sidebar.warning("⚠️ Not connected")
    
    # Connection controls
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔗 Connect", disabled=st.session_state.connected):
            connect_to_ftp()
    with col2:
        if st.button("🔌 Disconnect", disabled=not st.session_state.connected):
            disconnect_from_ftp()
    
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "📁 FTP Files", "⚡ Process Files", 
         "📈 Analytics", "⚙️ FTP Settings", "📚 Help"]
    )
    
    # Page routing
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📁 FTP Files":
        show_ftp_files()
    elif page == "⚡ Process Files":
        show_process_files()
    elif page == "📈 Analytics":
        show_analytics()
    elif page == "⚙️ FTP Settings":
        show_ftp_settings()
    elif page == "📚 Help":
        show_help()

def connect_to_ftp():
    """Connect to FTP server"""
    try:
        with st.spinner("Connecting to FTP server..."):
            st.session_state.ftp_processor.connect_ftp()
            st.session_state.connected = True
            st.success("Successfully connected to FTP server!")
    except Exception as e:
        st.error(f"Connection failed: {e}")
        st.session_state.connected = False

def disconnect_from_ftp():
    """Disconnect from FTP server"""
    st.session_state.ftp_processor.disconnect_ftp()
    st.session_state.connected = False
    st.info("Disconnected from FTP server")

def show_dashboard():
    """Dashboard page"""
    st.header("📊 FTP Processing Dashboard")
    
    # FTP Status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "FTP Status",
            "Connected" if st.session_state.connected else "Disconnected",
            delta="Active" if st.session_state.connected else None
        )
    
    # Get database statistics
    db = DatabaseManager(st.session_state.ftp_processor.kem_config.db_path)
    stats = db.get_statistics()
    
    with col2:
        st.metric(
            "Files Processed",
            stats['total_files'],
            delta=f"{stats['passed_files']} passed"
        )
    
    with col3:
        success_rate = (stats['passed_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        st.metric(
            "Success Rate",
            f"{success_rate:.1f}%",
            delta=f"{stats['failed_files']} failed"
        )
    
    with col4:
        st.metric(
            "Total KEM Lines",
            f"{stats['total_kem_lines']:,}",
            delta=f"{stats['total_valid_lines']:,} valid"
        )
    
    # Recent Processing History
    st.markdown("### 📝 Recent Processing History")
    history = db.get_history(20)
    
    if not history.empty:
        # Format for display
        display_df = history[['file_name', 'processed_at', 'validation_status', 'kem_lines', 'success_rate']].copy()
        display_df['status'] = display_df['validation_status'].apply(
            lambda x: '✅' if x == 'passed' else '❌'
        )
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "file_name": "File",
                "processed_at": st.column_config.DatetimeColumn("Processed", format="DD/MM HH:mm"),
                "status": "Status",
                "kem_lines": st.column_config.NumberColumn("KEM Lines", format="%d"),
                "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%")
            }
        )
    else:
        st.info("No processing history yet. Process some files to see results here.")
    
    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Process Batch", type="primary", disabled=not st.session_state.connected):
            process_batch()
    
    with col2:
        if st.button("📊 Refresh Stats"):
            st.rerun()
    
    with col3:
        if st.button("🧪 Test Connection"):
            test_connection()

def show_ftp_files():
    """FTP Files browser"""
    st.header("📁 FTP File Browser")
    
    if not st.session_state.connected:
        st.warning("Please connect to FTP server first")
        if st.button("Connect Now"):
            connect_to_ftp()
        return
    
    # Directory selector
    directories = {
        "Inbox": st.session_state.ftp_processor.ftp_config.ftp_inbox,
        "Results": st.session_state.ftp_processor.ftp_config.ftp_results,
        "Processed": st.session_state.ftp_processor.ftp_config.ftp_processed,
        "Invalid": st.session_state.ftp_processor.ftp_config.ftp_invalid
    }
    
    selected_dir = st.selectbox("Select Directory", list(directories.keys()))
    ftp_path = directories[selected_dir]
    
    # List files
    with st.spinner(f"Loading files from {selected_dir}..."):
        try:
            files = st.session_state.ftp_processor.list_ftp_files(ftp_path)
            
            if files:
                st.success(f"Found {len(files)} files in {selected_dir}")
                
                # Create DataFrame for display
                file_data = []
                for file in files:
                    file_data.append({
                        "📄 Filename": file,
                        "📁 Directory": selected_dir,
                        "Select": False
                    })
                
                df = pd.DataFrame(file_data)
                
                # Display with selection
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["📄 Filename", "📁 Directory"]
                )
                
                # Process selected files
                selected_files = edited_df[edited_df["Select"]]["📄 Filename"].tolist()
                
                if selected_files:
                    st.info(f"Selected {len(selected_files)} files")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🚀 Process Selected", type="primary"):
                            process_selected_files(selected_files, ftp_path)
                    
                    with col2:
                        if st.button("📥 Download Selected"):
                            download_selected_files(selected_files, ftp_path)
            else:
                st.warning(f"No files found in {selected_dir}")
                
        except Exception as e:
            st.error(f"Error listing files: {e}")

def show_process_files():
    """Process files page"""
    st.header("⚡ Process Files")
    
    if not st.session_state.connected:
        st.warning("Please connect to FTP server first")
        return
    
    tab1, tab2, tab3 = st.tabs(["Single File", "Batch Process", "Continuous Processing"])
    
    with tab1:
        st.markdown("### Process Single File")
        
        # List files in inbox
        files = st.session_state.ftp_processor.list_ftp_files(
            st.session_state.ftp_processor.ftp_config.ftp_inbox
        )
        
        if files:
            selected_file = st.selectbox("Select file to process", files)
            
            if st.button("🔄 Process File", type="primary"):
                with st.spinner(f"Processing {selected_file}..."):
                    result = st.session_state.ftp_processor.process_ftp_file(selected_file)
                    
                    if result['status'] == 'success':
                        st.success(f"✅ Successfully processed: {selected_file}")
                        
                        # Show results
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Validation Status", result['validation_status'].upper())
                        with col2:
                            st.metric("KEM Lines", result['stats']['kem_lines'])
                        with col3:
                            st.metric("Success Rate", f"{result['stats']['success_rate']:.1f}%")
                        
                        # Show CSV path
                        if 'ftp_csv_path' in result:
                            st.info(f"CSV uploaded to: {result['ftp_csv_path']}")
                    else:
                        st.error(f"❌ Failed to process: {result.get('reason', 'Unknown error')}")
        else:
            st.warning("No files in inbox to process")
    
    with tab2:
        st.markdown("### Batch Processing")
        
        batch_size = st.number_input("Batch Size", min_value=1, max_value=100, value=10)
        
        if st.button("🚀 Process Batch", type="primary"):
            process_batch(batch_size)
    
    with tab3:
        st.markdown("### Continuous Processing")
        
        interval = st.number_input("Process Interval (minutes)", min_value=1, max_value=60, value=5)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start Continuous", type="primary", disabled=st.session_state.processing):
                st.session_state.processing = True
                st.info(f"Continuous processing started (every {interval} minutes)")
                st.warning("Note: This runs in background. Use CLI version for true continuous processing.")
        
        with col2:
            if st.button("⏹️ Stop Continuous", disabled=not st.session_state.processing):
                st.session_state.processing = False
                st.info("Continuous processing stopped")

def show_analytics():
    """Analytics page"""
    st.header("📈 Processing Analytics")
    
    db = DatabaseManager(st.session_state.ftp_processor.kem_config.db_path)
    history = db.get_history(1000)
    
    if history.empty:
        st.warning("No data available for analytics")
        return
    
    # Date filter
    col1, col2 = st.columns(2)
    history['date'] = pd.to_datetime(history['processed_at']).dt.date
    
    with col1:
        start_date = st.date_input("Start Date", history['date'].min())
    with col2:
        end_date = st.date_input("End Date", history['date'].max())
    
    # Filter data
    mask = (history['date'] >= start_date) & (history['date'] <= end_date)
    filtered = history.loc[mask]
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Files", len(filtered))
    with col2:
        passed = sum(filtered['validation_status'] == 'passed')
        st.metric("Passed", passed)
    with col3:
        failed = sum(filtered['validation_status'] == 'failed')
        st.metric("Failed", failed)
    with col4:
        avg_rate = filtered['success_rate'].mean()
        st.metric("Avg Success Rate", f"{avg_rate:.1f}%")
    
    # Charts
    import plotly.express as px
    import plotly.graph_objects as go
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        fig = go.Figure(data=[go.Pie(
            labels=['Passed', 'Failed'],
            values=[passed, failed],
            hole=0.3,
            marker_colors=['#28a745', '#dc3545']
        )])
        fig.update_layout(title="Validation Status Distribution", height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Time series
        daily = filtered.groupby('date').agg({
            'validation_status': lambda x: (x == 'passed').sum()
        }).reset_index()
        daily.columns = ['date', 'passed_count']
        
        fig = px.line(daily, x='date', y='passed_count', title="Daily Processing Trend")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

def show_ftp_settings():
    """FTP Settings page"""
    st.header("⚙️ FTP Configuration")
    
    config = st.session_state.ftp_processor.ftp_config
    
    # Server settings
    st.markdown("### 🖥️ Server Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        server = st.text_input("FTP Server", config.ftp_server)
        username = st.text_input("Username", config.ftp_username)
    
    with col2:
        port = st.number_input("Port", value=config.ftp_port)
        password = st.text_input("Password", config.ftp_password, type="password")
    
    # Directory settings
    st.markdown("### 📁 Directory Settings")
    
    base_path = st.text_input("Base Path", config.ftp_base_path)
    
    col1, col2 = st.columns(2)
    with col1:
        inbox = st.text_input("Inbox Directory", config.ftp_inbox)
        results = st.text_input("Results Directory", config.ftp_results)
    
    with col2:
        processed = st.text_input("Processed Archive", config.ftp_processed)
        invalid = st.text_input("Invalid Archive", config.ftp_invalid)
    
    # Processing settings
    st.markdown("### ⚡ Processing Settings")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        batch_size = st.number_input("Batch Size", value=config.batch_size)
    with col2:
        interval = st.number_input("Process Interval (min)", value=config.process_interval_minutes)
    with col3:
        local_temp = st.text_input("Local Temp Dir", config.local_temp_dir)
    
    # Options
    st.markdown("### 🔧 Options")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        upload_results = st.checkbox("Upload Results", config.upload_results)
    with col2:
        archive_on_ftp = st.checkbox("Archive on FTP", config.archive_on_ftp)
    with col3:
        delete_after = st.checkbox("Delete After Download", config.delete_after_download)
    
    # Save button
    if st.button("💾 Save Configuration", type="primary"):
        # Update config
        new_config = {
            "ftp_server": server,
            "ftp_port": port,
            "ftp_username": username,
            "ftp_password": password,
            "ftp_base_path": base_path,
            "ftp_inbox": inbox,
            "ftp_results": results,
            "ftp_processed": processed,
            "ftp_invalid": invalid,
            "batch_size": batch_size,
            "process_interval_minutes": interval,
            "local_temp_dir": local_temp,
            "upload_results": upload_results,
            "archive_on_ftp": archive_on_ftp,
            "delete_after_download": delete_after
        }
        
        # Save to file
        with open("ftp_config.json", "w") as f:
            json.dump(new_config, f, indent=2)
        
        st.success("Configuration saved! Restart the application to apply changes.")

def show_help():
    """Help page"""
    st.header("📚 Help & Documentation")
    
    st.markdown("""
    ## 🌐 FTP Integration Guide
    
    ### Quick Start
    1. **Connect**: Click "Connect" in the sidebar to establish FTP connection
    2. **Browse**: Go to "FTP Files" to see available files
    3. **Process**: Use "Process Files" to validate KEM data
    4. **Results**: CSV reports are uploaded back to FTP
    
    ### FTP Directory Structure
    ```
    /PAMarchive/SeaTac/
    ├── kem-inbox/          # Place files here for processing
    ├── kem-results/        # CSV validation reports
    ├── processed-archive/  # Successfully validated files
    └── invalid-archive/    # Failed validation files
    ```
    
    ### Processing Workflow
    1. Files are downloaded from `kem-inbox`
    2. KEM validation is performed locally
    3. CSV results are uploaded to `kem-results`
    4. Original files are moved to archive folders
    
    ### Validation Rules
    - **Valid KEM**: 9-13 digits in the ID
    - **Invalid KEM**: <9 or >13 digits
    - Files with any invalid KEM line are marked as failed
    
    ### Troubleshooting
    
    **Connection Failed**
    - Check server address and port
    - Verify username and password
    - Ensure network connectivity
    
    **No Files Found**
    - Check directory paths in settings
    - Verify FTP permissions
    - Ensure files are in the correct format
    
    **Processing Errors**
    - Check file encoding (UTF-8 preferred)
    - Verify file format (TXT, PDF, CSV)
    - Review error logs for details
    """)

# Helper functions
def process_batch(batch_size=None):
    """Process a batch of files"""
    with st.spinner("Processing batch..."):
        results = st.session_state.ftp_processor.process_batch(batch_size)
        
        if results:
            success = sum(1 for r in results if r['status'] == 'success')
            st.success(f"Processed {len(results)} files: {success} succeeded")
            
            # Show results
            for r in results:
                if r['status'] == 'success':
                    st.write(f"✅ {r['filename']}: {r['validation_status']}")
                else:
                    st.write(f"❌ {r['filename']}: {r.get('reason', 'Failed')}")
        else:
            st.warning("No files to process")

def test_connection():
    """Test FTP connection"""
    with st.spinner("Testing connection..."):
        if st.session_state.ftp_processor.test_connection():
            st.success("✅ FTP connection test successful!")
        else:
            st.error("❌ FTP connection test failed")

def process_selected_files(files, directory):
    """Process selected files"""
    for file in files:
        with st.spinner(f"Processing {file}..."):
            # Implementation depends on directory
            st.info(f"Processing {file} from {directory}")

def download_selected_files(files, directory):
    """Download selected files"""
    for file in files:
        st.info(f"Downloading {file} from {directory}")

if __name__ == "__main__":
    main()