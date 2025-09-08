"""
Streamlit Web Interface for KEM Validator
Full-featured local web application
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from pathlib import Path
import json
import time

# Import our main application
from kem_validator_local import (
    Config, FileProcessor, DatabaseManager, 
    KemValidator, FileWatcher
)

# Page configuration
st.set_page_config(
    page_title="KEM Validator Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .success-box {
        background-color: #d4edda;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    .info-box {
        background-color: #d1ecf1;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #bee5eb;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'config' not in st.session_state:
    st.session_state.config = Config.from_json("config.json")
if 'processor' not in st.session_state:
    st.session_state.processor = FileProcessor(st.session_state.config)
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False


def main():
    """Main application"""
    
    # Sidebar navigation
    st.sidebar.title("🔍 KEM Validator")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "📤 Upload & Process", "📁 Batch Processing", 
         "📈 Analytics", "⚙️ Settings", "📚 Help"]
    )
    
    # Auto-refresh toggle
    st.sidebar.markdown("---")
    st.session_state.auto_refresh = st.sidebar.checkbox(
        "Auto-refresh (5s)", 
        st.session_state.auto_refresh
    )
    
    if st.session_state.auto_refresh:
        time.sleep(5)
        st.rerun()
    
    # Page routing
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📤 Upload & Process":
        show_upload_page()
    elif page == "📁 Batch Processing":
        show_batch_processing()
    elif page == "📈 Analytics":
        show_analytics()
    elif page == "⚙️ Settings":
        show_settings()
    elif page == "📚 Help":
        show_help()


def show_dashboard():
    """Dashboard page"""
    st.title("📊 KEM Validator Dashboard")
    
    # Get statistics
    db = st.session_state.processor.db
    stats = db.get_statistics()
    history = db.get_history(10)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Files Processed",
            stats['total_files'],
            delta=f"↑ {stats['passed_files']} passed"
        )
    
    with col2:
        success_rate = (stats['passed_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
        st.metric(
            "Success Rate",
            f"{success_rate:.1f}%",
            delta=f"{stats['failed_files']} failed"
        )
    
    with col3:
        st.metric(
            "Total Lines Processed",
            f"{stats['total_lines_processed']:,}",
            delta=f"{stats['total_kem_lines']:,} KEM lines"
        )
    
    with col4:
        validity_rate = (stats['total_valid_lines'] / stats['total_kem_lines'] * 100) if stats['total_kem_lines'] > 0 else 0
        st.metric(
            "KEM Validity Rate",
            f"{validity_rate:.1f}%",
            delta=f"{stats['total_failed_lines']:,} invalid"
        )
    
    # Processing status chart
    if stats['total_files'] > 0:
        st.markdown("### 📊 Processing Status Distribution")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Pie chart for file status
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Passed', 'Failed'],
                values=[stats['passed_files'], stats['failed_files']],
                hole=0.3,
                marker_colors=['#28a745', '#dc3545']
            )])
            fig_pie.update_layout(height=300, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bar chart for recent processing
            if not history.empty:
                history['hour'] = pd.to_datetime(history['processed_at']).dt.floor('H')
                hourly_counts = history.groupby(['hour', 'validation_status']).size().reset_index(name='count')
                
                fig_bar = px.bar(
                    hourly_counts, 
                    x='hour', 
                    y='count', 
                    color='validation_status',
                    color_discrete_map={'passed': '#28a745', 'failed': '#dc3545'},
                    title="Recent Processing Activity"
                )
                fig_bar.update_layout(height=300)
                st.plotly_chart(fig_bar, use_container_width=True)
    
    # Recent files table
    st.markdown("### 📝 Recent Processing History")
    if not history.empty:
        # Format the dataframe for display
        display_df = history[['file_name', 'processed_at', 'validation_status', 'kem_lines', 'valid_lines', 'success_rate']].copy()
        display_df['status'] = display_df['validation_status'].apply(
            lambda x: '✅ Passed' if x == 'passed' else '❌ Failed'
        )
        display_df['success_rate'] = display_df['success_rate'].apply(lambda x: f"{x:.1f}%")
        display_df = display_df.drop('validation_status', axis=1)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "file_name": "File Name",
                "processed_at": st.column_config.DatetimeColumn("Processed At", format="DD/MM/YYYY HH:mm"),
                "status": "Status",
                "kem_lines": "KEM Lines",
                "valid_lines": "Valid Lines",
                "success_rate": "Success Rate"
            }
        )
        
        # Download button for full history
        csv = history.to_csv(index=False)
        st.download_button(
            label="📥 Download Full History",
            data=csv,
            file_name=f"kem_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No processing history available yet. Upload files to get started!")


def show_upload_page():
    """Upload and process page"""
    st.title("📤 Upload & Process Files")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to process",
        type=['txt', 'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'],
        accept_multiple_files=True,
        help="Supported formats: TXT, PDF, and images (PNG, JPG, TIFF, BMP)"
    )
    
    if uploaded_files:
        st.markdown(f"### 📁 {len(uploaded_files)} file(s) selected")
        
        # Process button
        if st.button("🚀 Process Files", type="primary"):
            progress_bar = st.progress(0)
            status_container = st.container()
            
            results = []
            for idx, uploaded_file in enumerate(uploaded_files):
                # Save uploaded file temporarily
                temp_path = os.path.join(st.session_state.config.input_dir, uploaded_file.name)
                with open(temp_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                # Process file
                with status_container:
                    st.info(f"Processing: {uploaded_file.name}")
                
                result = st.session_state.processor.process_file(temp_path)
                results.append(result)
                
                # Update progress
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            # Show results
            st.markdown("### ✅ Processing Complete")
            
            for result in results:
                if result['status'] == 'success':
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.success(f"✅ {result['file']}")
                    with col2:
                        if result['validation_status'] == 'passed':
                            st.markdown('<div class="success-box">PASSED</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="error-box">FAILED</div>', unsafe_allow_html=True)
                    with col3:
                        # Download CSV button
                        if 'csv_path' in result:
                            with open(result['csv_path'], 'r') as f:
                                csv_content = f.read()
                            st.download_button(
                                "📥 CSV",
                                csv_content,
                                file_name=os.path.basename(result['csv_path']),
                                mime="text/csv",
                                key=f"download_{result['file']}"
                            )
                    
                    # Show statistics
                    with st.expander(f"📊 Details for {result['file']}"):
                        stats = result['stats']
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Lines", stats['total_lines'])
                        with col2:
                            st.metric("KEM Lines", stats['kem_lines'])
                        with col3:
                            st.metric("Valid", stats['valid_lines'])
                        with col4:
                            st.metric("Invalid", stats['failed_lines'])
                else:
                    st.error(f"❌ {result.get('file', 'Unknown')} - {result.get('reason', 'Processing failed')}")
    
    # Manual text input option
    st.markdown("---")
    st.markdown("### 📝 Or paste text directly")
    
    text_input = st.text_area(
        "Paste KEM data here",
        height=200,
        placeholder="KEM\t4152500182618\tDescription\nKEM\t230471171\tAnother item..."
    )
    
    if text_input and st.button("🔍 Validate Text"):
        validator = KemValidator()
        results = validator.validate_text(text_input)
        
        # Calculate stats
        total = len(results)
        kem_lines = sum(1 for r in results if r['fail_reason'] != 'not_a_KEM_line')
        valid = sum(1 for r in results if r['fail_reason'] != 'not_a_KEM_line' and r['is_valid'])
        failed = sum(1 for r in results if r['fail_reason'] != 'not_a_KEM_line' and not r['is_valid'])
        
        # Display results
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Lines", total)
        with col2:
            st.metric("KEM Lines", kem_lines)
        with col3:
            st.metric("Valid", valid)
        with col4:
            st.metric("Invalid", failed)
        
        # Show detailed results
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, height=400)


def show_batch_processing():
    """Batch processing page"""
    st.title("📁 Batch Processing")
    
    # Directory monitoring
    st.markdown("### 📂 Directory Monitoring")
    
    input_dir = st.session_state.config.input_dir
    files = list(Path(input_dir).glob("*"))
    
    if files:
        st.info(f"Found {len(files)} file(s) in {input_dir}")
        
        # Show files
        file_list = []
        for file in files:
            if file.is_file():
                file_list.append({
                    "File Name": file.name,
                    "Size (KB)": f"{file.stat().st_size / 1024:.2f}",
                    "Modified": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        if file_list:
            df = pd.DataFrame(file_list)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Process all button
            if st.button("🚀 Process All Files", type="primary"):
                progress_bar = st.progress(0)
                results_container = st.container()
                
                success_count = 0
                fail_count = 0
                
                for idx, file in enumerate(files):
                    if file.is_file():
                        result = st.session_state.processor.process_file(str(file))
                        
                        with results_container:
                            if result['status'] == 'success':
                                st.success(f"✅ {file.name} - {result['validation_status']}")
                                success_count += 1
                            else:
                                st.error(f"❌ {file.name} - Failed")
                                fail_count += 1
                        
                        progress_bar.progress((idx + 1) / len(files))
                
                st.markdown("---")
                st.success(f"Batch processing complete! Success: {success_count}, Failed: {fail_count}")
    else:
        st.warning(f"No files found in {input_dir}")
    
    # File watcher status
    st.markdown("### 👁️ Auto-Processing (File Watcher)")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start File Watcher"):
            st.info("File watcher started! New files will be processed automatically.")
            st.warning("Note: File watcher runs in the background. Use the CLI version for continuous monitoring.")
    
    with col2:
        if st.button("⏹️ Stop File Watcher"):
            st.info("File watcher stopped.")


def show_analytics():
    """Analytics page"""
    st.title("📈 Analytics & Insights")
    
    db = st.session_state.processor.db
    history = db.get_history(1000)  # Get more data for analytics
    
    if history.empty:
        st.warning("No data available for analytics. Process some files first!")
        return
    
    # Date range filter
    st.markdown("### 📅 Date Range")
    col1, col2 = st.columns(2)
    
    history['date'] = pd.to_datetime(history['processed_at']).dt.date
    min_date = history['date'].min()
    max_date = history['date'].max()
    
    with col1:
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    
    # Filter data
    mask = (history['date'] >= start_date) & (history['date'] <= end_date)
    filtered_history = history.loc[mask]
    
    # Analytics charts
    st.markdown("### 📊 Processing Trends")
    
    # Daily processing volume
    daily_counts = filtered_history.groupby(['date', 'validation_status']).size().reset_index(name='count')
    
    fig1 = px.line(
        daily_counts,
        x='date',
        y='count',
        color='validation_status',
        title="Daily Processing Volume",
        color_discrete_map={'passed': '#28a745', 'failed': '#dc3545'}
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Success rate over time
    daily_stats = filtered_history.groupby('date').agg({
        'validation_status': lambda x: (x == 'passed').sum() / len(x) * 100,
        'success_rate': 'mean'
    }).reset_index()
    daily_stats.columns = ['date', 'file_success_rate', 'avg_line_success_rate']
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['file_success_rate'],
        mode='lines+markers',
        name='File Success Rate',
        line=dict(color='#28a745')
    ))
    fig2.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['avg_line_success_rate'],
        mode='lines+markers',
        name='Line Success Rate',
        line=dict(color='#007bff')
    ))
    fig2.update_layout(
        title="Success Rates Over Time",
        yaxis_title="Success Rate (%)",
        xaxis_title="Date"
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Distribution of KEM lines per file
    st.markdown("### 📊 KEM Lines Distribution")
    
    fig3 = px.histogram(
        filtered_history,
        x='kem_lines',
        nbins=30,
        title="Distribution of KEM Lines per File",
        labels={'kem_lines': 'Number of KEM Lines', 'count': 'Number of Files'}
    )
    st.plotly_chart(fig3, use_container_width=True)
    
    # Top failure reasons (if we had detailed data)
    st.markdown("### ❌ Common Issues")
    
    col1, col2 = st.columns(2)
    with col1:
        avg_failed = filtered_history['failed_lines'].mean()
        st.metric("Average Failed Lines per File", f"{avg_failed:.1f}")
    
    with col2:
        total_failed = filtered_history['failed_lines'].sum()
        st.metric("Total Failed Lines", f"{total_failed:,}")


def show_settings():
    """Settings page"""
    st.title("⚙️ Settings")
    
    config = st.session_state.config
    
    # Directory settings
    st.markdown("### 📁 Directory Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        config.input_dir = st.text_input("Input Directory", config.input_dir)
        config.output_dir = st.text_input("Output Directory", config.output_dir)
    
    with col2:
        config.processed_dir = st.text_input("Processed Archive", config.processed_dir)
        config.invalid_dir = st.text_input("Invalid Archive", config.invalid_dir)
    
    # OCR settings
    st.markdown("### 🔍 OCR Configuration")
    
    config.ocr_provider = st.selectbox(
        "OCR Provider",
        ["tesseract", "openai", "azure"],
        index=["tesseract", "openai", "azure"].index(config.ocr_provider)
    )
    
    if config.ocr_provider == "openai":
        config.openai_api_key = st.text_input(
            "OpenAI API Key",
            config.openai_api_key,
            type="password"
        )
        st.info("OpenAI Vision API will be used for OCR processing")
    
    elif config.ocr_provider == "azure":
        config.azure_endpoint = st.text_input("Azure Document Intelligence Endpoint", config.azure_endpoint)
        config.azure_key = st.text_input("Azure Key", config.azure_key, type="password")
        st.info("Azure Document Intelligence will be used for OCR processing")
    
    else:
        st.info("Tesseract OCR will be used (free, local processing)")
        st.warning("Make sure Tesseract is installed: `pip install pytesseract` and install Tesseract binary")
    
    # Processing settings
    st.markdown("### ⚡ Processing Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        config.auto_watch = st.checkbox("Enable Auto-Watch", config.auto_watch)
    with col2:
        config.process_interval = st.number_input(
            "Process Interval (seconds)",
            min_value=1,
            max_value=60,
            value=config.process_interval
        )
    
    # Save settings
    if st.button("💾 Save Settings", type="primary"):
        config.save("config.json")
        st.session_state.config = config
        st.session_state.processor = FileProcessor(config)
        st.success("Settings saved successfully!")
        st.rerun()
    
    # Export/Import settings
    st.markdown("### 📤 Export/Import Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export Configuration"):
            config_json = json.dumps(asdict(config), indent=2)
            st.download_button(
                "Download config.json",
                config_json,
                file_name="config.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_config = st.file_uploader("Import Configuration", type="json")
        if uploaded_config:
            try:
                config_data = json.load(uploaded_config)
                new_config = Config(**config_data)
                new_config.save("config.json")
                st.session_state.config = new_config
                st.success("Configuration imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing configuration: {e}")


def show_help():
    """Help page"""
    st.title("📚 Help & Documentation")
    
    st.markdown("""
    ## 🎯 KEM Validator - User Guide
    
    ### What is KEM Validator?
    KEM Validator is a powerful tool for validating Key Equipment/Material (KEM) identifiers 
    based on digit count rules. It processes text files, PDFs, and images to extract and 
    validate KEM codes.
    
    ### ✅ Validation Rules
    - **Valid KEM**: Contains 9-13 digits (alphanumeric IDs are allowed, only digits are counted)
    - **Invalid KEM**: Contains <9 or >13 digits
    - **Informational Lines**: Non-KEM lines that don't affect validation status
    
    ### 📁 Supported File Formats
    - **Text Files**: `.txt` (UTF-8 encoded)
    - **PDFs**: `.pdf` (text extraction)
    - **Images**: `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp` (OCR processing)
    
    ### 🚀 Quick Start
    1. **Upload Files**: Go to "Upload & Process" and select your files
    2. **Process**: Click "Process Files" to validate
    3. **Download Results**: Get CSV reports with detailed validation results
    
    ### 📊 Understanding Results
    - **validation_passed**: All KEM lines in the file are valid
    - **validation_failed**: At least one KEM line is invalid
    - **CSV Output**: Contains line-by-line validation details
    
    ### 🔍 OCR Options
    - **Tesseract**: Free, local OCR processing
    - **OpenAI Vision**: High-quality OCR using GPT-4 Vision
    - **Azure Document Intelligence**: Enterprise-grade OCR service
    
    ### 💡 Tips
    - Use tab-separated format for best results: `KEM<TAB>ID<TAB>Description`
    - Batch processing is more efficient for multiple files
    - Enable auto-watch for automatic processing of new files
    
    ### ❓ FAQs
    
    **Q: Why is my file marked as invalid?**
    A: Check if any KEM IDs have fewer than 9 or more than 13 digits.
    
    **Q: Can I process scanned documents?**
    A: Yes! Configure OCR in Settings and upload image files or PDFs.
    
    **Q: Where are my processed files?**
    A: Check the configured archive directories (processed-archive or invalid-archive).
    
    **Q: How do I process files automatically?**
    A: Use the File Watcher feature or run the CLI version for continuous monitoring.
    
    ### 📞 Support
    For issues or questions, check the GitHub repository or documentation.
    """)


if __name__ == "__main__":
    main()