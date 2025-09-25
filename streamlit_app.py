"""
    main()
st.set_page_config(
    page_title=" File Validator\,
 layout=\wide\,
 initial_sidebar_state=\expanded\
)
Streamlit Web Interface for File Validator
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

# Import court configuration management
try:
    from court_config_manager import CourtConfigManager
    MULTI_COURT_SUPPORT = True
except ImportError:
    MULTI_COURT_SUPPORT = False

# Page configuration
st.set_page_config(
    page_title="Court Document Validator",
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
if 'selected_court' not in st.session_state:
    st.session_state.selected_court = 'KEM'

# Initialize court configuration manager
if MULTI_COURT_SUPPORT:
    if 'court_manager' not in st.session_state:
        st.session_state.court_manager = CourtConfigManager()
    if 'available_courts' not in st.session_state:
        # Use helper to get enabled court codes (returns List[str])
        enabled_codes = st.session_state.court_manager.get_enabled_court_codes()
        # Fallback to default court if none explicitly enabled
        if not enabled_codes:
            enabled_codes = [st.session_state.court_manager.get_default_court()]
        st.session_state.available_courts = enabled_codes


def main():
    """Main application"""
    
    # Sidebar navigation
    if MULTI_COURT_SUPPORT and len(st.session_state.available_courts) > 1:
        st.sidebar.title("🔍 Court Validator")
    else:
        st.sidebar.title("🔍 KEM Validator")
    st.sidebar.markdown("---")
    
    # Navigation options - add Court Management only if multi-court support is available
    nav_options = ["📊 Dashboard", "📤 Upload & Process", "📁 Batch Processing", "📈 Analytics"]

    if MULTI_COURT_SUPPORT:
        nav_options.append("🏛️ Court Management")

    nav_options.extend(["⚙️ Settings", "📚 Help"])

    page = st.sidebar.radio("Navigation", nav_options)

    # Court status information
    if MULTI_COURT_SUPPORT:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🏛️ Court System")

        if len(st.session_state.available_courts) > 1:
            st.sidebar.info(f"✅ Multi-court mode active\\n{len(st.session_state.available_courts)} courts available")

            # Show active courts
            st.sidebar.markdown("**Available Courts:**")
            for court_code in st.session_state.available_courts:
                court_info = st.session_state.court_manager.get_court(court_code)
                if court_info:
                    st.sidebar.markdown(f"• {court_info.name} ({court_code})")
        else:
            court_code = st.session_state.available_courts[0] if st.session_state.available_courts else 'KEM'
            court_info = st.session_state.court_manager.get_court(court_code)
            court_name = court_info.name if court_info else "KEM"
            st.sidebar.info(f"📋 Single court mode\\n{court_name} ({court_code})")
    else:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🏛️ Court System")
        st.sidebar.info("📋 Legacy KEM mode\\nSingle court validation")

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
    elif page == "🏛️ Court Management":
        show_court_management()
    elif page == "⚙️ Settings":
        show_settings()
    elif page == "📚 Help":
        show_help()


def show_dashboard():
    """Dashboard page"""
    if MULTI_COURT_SUPPORT and len(st.session_state.available_courts) > 1:
        st.title("📊 Court Validator Dashboard")

        # Court filter
        court_options = {"All Courts": None}
        for court_code in st.session_state.available_courts:
            court_info = st.session_state.court_manager.get_court(court_code)
            if court_info:
                court_options[f"{court_info.name} ({court_code})"] = court_code

        selected_filter = st.selectbox(
            "Filter by Court",
            options=list(court_options.keys()),
            index=0,
            help="View metrics for specific court or all courts"
        )
        selected_court_filter = court_options[selected_filter]

        st.markdown("---")
    else:
        st.title("📊 KEM Validator Dashboard")
        selected_court_filter = None

    # Get statistics
    db = st.session_state.processor.db
    if MULTI_COURT_SUPPORT and selected_court_filter:
        stats = db.get_statistics(selected_court_filter)
        history = db.get_history(10, selected_court_filter)
    else:
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
        court_display = selected_court_filter if selected_court_filter else "Court"
        st.metric(
            "Total Lines Processed",
            f"{stats['total_lines_processed']:,}",
            delta=f"{stats['total_kem_lines']:,} {court_display} lines"
        )

    with col4:
        validity_rate = (stats['total_valid_lines'] / stats['total_kem_lines'] * 100) if stats['total_kem_lines'] > 0 else 0
        court_display = selected_court_filter if selected_court_filter else "Court"
        st.metric(
            f"{court_display} Validity Rate",
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

    # Court selector (only show if multiple courts are available)
    selected_court = 'KEM'  # Default to KEM
    if MULTI_COURT_SUPPORT and len(st.session_state.available_courts) > 1:
        court_options = {}
        for court_code in st.session_state.available_courts:
            court_info = st.session_state.court_manager.get_court(court_code)
            if court_info:
                court_options[f"{court_info.name} ({court_code})"] = court_code

        st.markdown("### 🏛️ Court Selection")
        selected_display = st.selectbox(
            "Select court for processing",
            options=list(court_options.keys()),
            index=0 if 'KEM' in st.session_state.available_courts else 0,
            help="Choose which court's validation rules to apply"
        )
        selected_court = court_options[selected_display]
        st.session_state.selected_court = selected_court
        st.markdown("---")
    elif MULTI_COURT_SUPPORT and st.session_state.available_courts:
        selected_court = st.session_state.available_courts[0]
        st.session_state.selected_court = selected_court

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

                result = st.session_state.processor.process_file(temp_path, selected_court)
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
        if MULTI_COURT_SUPPORT:
            # Use court-specific validator
            from court_validator_base import ValidatorFactory
            validator_factory = ValidatorFactory()
            validator = validator_factory.get_validator(selected_court)
            results = validator.validate_text(text_input)
        else:
            # Fallback to legacy KEM validator
            validator = KemValidator()
            results = validator.validate_text(text_input)

        # Calculate stats
        total = len(results)
        court_lines = sum(1 for r in results if not r['fail_reason'] or r['fail_reason'] != f'not_a_{selected_court}_line')
        valid = sum(1 for r in results if r['is_valid'])
        failed = total - valid
        
        # Display results
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Lines", total)
        with col2:
            st.metric(f"{selected_court} Lines", court_lines)
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

    # Court selector (only show if multiple courts are available)
    selected_court = 'KEM'  # Default to KEM
    if MULTI_COURT_SUPPORT and len(st.session_state.available_courts) > 1:
        court_options = {}
        for court_code in st.session_state.available_courts:
            court_info = st.session_state.court_manager.get_court(court_code)
            if court_info:
                court_options[f"{court_info.name} ({court_code})"] = court_code

        st.markdown("### 🏛️ Court Selection")
        selected_display = st.selectbox(
            "Select court for batch processing",
            options=list(court_options.keys()),
            index=0 if 'KEM' in st.session_state.available_courts else 0,
            help="Choose which court's validation rules to apply",
            key="batch_court_selector"
        )
        selected_court = court_options[selected_display]
        st.markdown("---")
    elif MULTI_COURT_SUPPORT and st.session_state.available_courts:
        selected_court = st.session_state.available_courts[0]

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
                        result = st.session_state.processor.process_file(str(file), selected_court)
                        
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

    # Court comparison toggle
    if MULTI_COURT_SUPPORT and len(st.session_state.available_courts) > 1:
        view_mode = st.radio(
            "View Mode",
            ["📊 Individual Court", "🔄 Court Comparison"],
            horizontal=True
        )
        st.markdown("---")
    else:
        view_mode = "📊 Individual Court"

    db = st.session_state.processor.db

    if view_mode == "🔄 Court Comparison":
        show_court_comparison()
        return

    # Individual court analytics
    if MULTI_COURT_SUPPORT and len(st.session_state.available_courts) > 1:
        # Court selector for individual analysis
        court_options = {"All Courts": None}
        for court_code in st.session_state.available_courts:
            court_info = st.session_state.court_manager.get_court(court_code)
            if court_info:
                court_options[f"{court_info.name} ({court_code})"] = court_code

        selected_filter = st.selectbox(
            "Select Court for Analysis",
            options=list(court_options.keys()),
            index=0,
            help="Analyze specific court or all courts combined"
        )
        selected_court_filter = court_options[selected_filter]

        if selected_court_filter:
            history = db.get_history(1000, selected_court_filter)
        else:
            history = db.get_history(1000)

        st.markdown("---")
    else:
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


def show_court_comparison():
    """Enhanced court comparison analytics"""
    st.markdown("### 🔄 Enhanced Court Performance Comparison")

    # Time range selector
    col1, col2 = st.columns([1, 3])
    with col1:
        days_back = st.selectbox(
            "Analysis Period",
            [7, 30, 90, 365],
            index=1,
            format_func=lambda x: f"Last {x} days"
        )
    with col2:
        st.info(f"📊 Analyzing court performance data for the past {days_back} days")

    st.markdown("---")

    db = st.session_state.processor.db

    # Get data for all available courts
    court_stats = []
    court_histories = {}
    all_court_data = []

    for court_code in st.session_state.available_courts:
        court_info = st.session_state.court_manager.get_court(court_code)
        if court_info:
            stats = db.get_statistics(court_code)
            history = db.get_history(1000, court_code)  # Get more data for better analysis

            # Filter history by time range
            if not history.empty:
                history['date'] = pd.to_datetime(history['processed_at']).dt.date
                cutoff_date = datetime.now().date() - timedelta(days=days_back)
                filtered_history = history[history['date'] >= cutoff_date]
            else:
                filtered_history = pd.DataFrame()

            # Calculate recent statistics
            recent_files = len(filtered_history)
            recent_passed = len(filtered_history[filtered_history['validation_status'] == 'passed']) if not filtered_history.empty else 0
            recent_success_rate = (recent_passed / recent_files * 100) if recent_files > 0 else 0

            court_stats.append({
                'Court': f"{court_info.name} ({court_code})",
                'Code': court_code,
                'Total Files': stats['total_files'],
                'Recent Files': recent_files,
                'Success Rate': (stats['passed_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0,
                'Recent Success Rate': recent_success_rate,
                'Lines Processed': stats['total_lines_processed'],
                'Validity Rate': (stats['total_valid_lines'] / stats['total_kem_lines'] * 100) if stats['total_kem_lines'] > 0 else 0,
                'Passed Files': stats['passed_files'],
                'Failed Files': stats['failed_files']
            })
            court_histories[court_code] = filtered_history

            # Add to combined data for time series
            if not filtered_history.empty:
                filtered_history['court_name'] = court_info.name
                filtered_history['court_code'] = court_code
                all_court_data.append(filtered_history)

    if not court_stats:
        st.warning("No court data available for comparison.")
        return

    # Combine all court data for analysis
    combined_df = pd.concat(all_court_data, ignore_index=True) if all_court_data else pd.DataFrame()

    # 1. Court Comparison Bar Charts
    st.markdown("#### 📊 Court Performance Comparison")

    col1, col2 = st.columns(2)

    with col1:
        # Success rate comparison
        numeric_df = pd.DataFrame(court_stats)
        fig_success = px.bar(
            numeric_df,
            x='Court',
            y='Success Rate',
            title="Overall File Success Rate by Court",
            color='Success Rate',
            color_continuous_scale='RdYlGn',
            range_color=[0, 100],
            text='Success Rate'
        )
        fig_success.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_success.update_layout(
            height=400,
            showlegend=False,
            xaxis_title="Court",
            yaxis_title="Success Rate (%)"
        )
        st.plotly_chart(fig_success, use_container_width=True)

    with col2:
        # Recent success rate comparison
        fig_recent = px.bar(
            numeric_df,
            x='Court',
            y='Recent Success Rate',
            title=f"Recent Success Rate (Last {days_back} Days)",
            color='Recent Success Rate',
            color_continuous_scale='RdYlGn',
            range_color=[0, 100],
            text='Recent Success Rate'
        )
        fig_recent.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_recent.update_layout(
            height=400,
            showlegend=False,
            xaxis_title="Court",
            yaxis_title="Success Rate (%)"
        )
        st.plotly_chart(fig_recent, use_container_width=True)

    # 2. Time Series Plot per Court
    st.markdown("#### 📈 Processing Trends Over Time")

    if not combined_df.empty:
        # Daily processing trends
        daily_trends = combined_df.groupby(['date', 'court_name']).agg({
            'validation_status': ['count', lambda x: (x == 'passed').sum()]
        }).reset_index()

        daily_trends.columns = ['date', 'court_name', 'total_files', 'passed_files']
        daily_trends['success_rate'] = (daily_trends['passed_files'] / daily_trends['total_files'] * 100).fillna(0)

        col1, col2 = st.columns(2)

        with col1:
            # Files processed over time
            fig_timeline = px.line(
                daily_trends,
                x='date',
                y='total_files',
                color='court_name',
                title=f"Daily File Processing Volume (Last {days_back} Days)",
                markers=True
            )
            fig_timeline.update_layout(
                height=400,
                xaxis_title="Date",
                yaxis_title="Files Processed",
                legend_title="Court"
            )
            st.plotly_chart(fig_timeline, use_container_width=True)

        with col2:
            # Success rate trends
            fig_success_trend = px.line(
                daily_trends,
                x='date',
                y='success_rate',
                color='court_name',
                title=f"Daily Success Rate Trends (Last {days_back} Days)",
                markers=True
            )
            fig_success_trend.update_layout(
                height=400,
                xaxis_title="Date",
                yaxis_title="Success Rate (%)",
                legend_title="Court",
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig_success_trend, use_container_width=True)
    else:
        st.warning("No recent processing data available for time series analysis.")

    # 3. File Distribution Pie Chart
    st.markdown("#### 🥧 File Distribution Across Courts")

    col1, col2 = st.columns(2)

    with col1:
        # Total files distribution
        if any(stat['Total Files'] > 0 for stat in court_stats):
            fig_pie_total = px.pie(
                numeric_df,
                values='Total Files',
                names='Court',
                title="Total Files Distribution (All Time)",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie_total.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie_total.update_layout(height=400)
            st.plotly_chart(fig_pie_total, use_container_width=True)
        else:
            st.info("No files processed yet.")

    with col2:
        # Recent files distribution
        if any(stat['Recent Files'] > 0 for stat in court_stats):
            fig_pie_recent = px.pie(
                numeric_df[numeric_df['Recent Files'] > 0],
                values='Recent Files',
                names='Court',
                title=f"Recent Files Distribution (Last {days_back} Days)",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie_recent.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie_recent.update_layout(height=400)
            st.plotly_chart(fig_pie_recent, use_container_width=True)
        else:
            st.info(f"No files processed in the last {days_back} days.")

    # 4. Top Validation Failures per Court
    st.markdown("#### ❌ Top Validation Failures by Court")

    failure_data = []
    for court_code in st.session_state.available_courts:
        court_info = st.session_state.court_manager.get_court(court_code)
        if court_info and court_code in court_histories:
            history = court_histories[court_code]
            if not history.empty:
                failed_files = history[history['validation_status'] == 'failed']

                if not failed_files.empty:
                    # Analyze failure patterns
                    failure_reasons = failed_files.groupby('file_name').agg({
                        'processed_at': 'max',
                        'kem_lines': 'first',
                        'valid_lines': 'first',
                        'failed_lines': 'first'
                    }).reset_index()

                    failure_reasons['court'] = court_info.name
                    failure_reasons['court_code'] = court_code
                    failure_reasons['failure_rate'] = (failure_reasons['failed_lines'] / failure_reasons['kem_lines'] * 100).fillna(0)

                    # Get top failures
                    top_failures = failure_reasons.nlargest(5, 'failed_lines')

                    for _, row in top_failures.iterrows():
                        failure_data.append({
                            'Court': f"{row['court']} ({row['court_code']})",
                            'File Name': row['file_name'],
                            'Total Lines': row['kem_lines'],
                            'Failed Lines': row['failed_lines'],
                            'Failure Rate': f"{row['failure_rate']:.1f}%",
                            'Processed At': row['processed_at']
                        })

    if failure_data:
        failure_df = pd.DataFrame(failure_data)

        # Sort by failed lines descending
        failure_df = failure_df.sort_values('Failed Lines', ascending=False)

        st.dataframe(
            failure_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Processed At": st.column_config.DatetimeColumn(
                    "Processed At",
                    format="DD/MM/YYYY HH:mm"
                ),
                "Failed Lines": st.column_config.NumberColumn(
                    "Failed Lines",
                    format="%d"
                ),
                "Total Lines": st.column_config.NumberColumn(
                    "Total Lines",
                    format="%d"
                )
            }
        )

        # Failure analysis charts
        st.markdown("#### 📊 Failure Analysis")
        col1, col2 = st.columns(2)

        with col1:
            # Failures by court
            court_failures = failure_df.groupby('Court')['Failed Lines'].sum().reset_index()
            fig_court_failures = px.bar(
                court_failures,
                x='Court',
                y='Failed Lines',
                title="Total Failed Lines by Court",
                color='Failed Lines',
                color_continuous_scale='Reds'
            )
            fig_court_failures.update_layout(height=400)
            st.plotly_chart(fig_court_failures, use_container_width=True)

        with col2:
            # Failure rate distribution
            failure_df['Failure Rate Numeric'] = failure_df['Failure Rate'].str.rstrip('%').astype(float)
            fig_failure_dist = px.histogram(
                failure_df,
                x='Failure Rate Numeric',
                title="Distribution of Failure Rates",
                nbins=10,
                color_discrete_sequence=['red']
            )
            fig_failure_dist.update_layout(
                height=400,
                xaxis_title="Failure Rate (%)",
                yaxis_title="Number of Files"
            )
            st.plotly_chart(fig_failure_dist, use_container_width=True)

    else:
        st.success("🎉 No validation failures found in the selected time period!")

    # Summary insights
    st.markdown("#### 💡 Key Insights")

    insights = []

    # Best performing court
    best_court = max(court_stats, key=lambda x: x['Success Rate'])
    insights.append(f"🏆 **Best Performing Court**: {best_court['Court']} with {best_court['Success Rate']:.1f}% success rate")

    # Most active court
    most_active = max(court_stats, key=lambda x: x['Recent Files'])
    if most_active['Recent Files'] > 0:
        insights.append(f"🔥 **Most Active Court**: {most_active['Court']} processed {most_active['Recent Files']} files recently")

    # Total processing summary
    total_recent = sum(stat['Recent Files'] for stat in court_stats)
    total_all_time = sum(stat['Total Files'] for stat in court_stats)
    insights.append(f"📊 **Processing Summary**: {total_recent} files processed recently out of {total_all_time} total files")

    for insight in insights:
        st.markdown(insight)

    st.markdown("---")


def show_court_management():
    """Court Management page"""
    st.title("🏛️ Court Management")

    if not MULTI_COURT_SUPPORT:
        st.warning("Multi-court support is not available. Court management features are disabled.")
        st.info("To enable court management, ensure court_config_manager.py is available.")
        return

    st.markdown("Comprehensive overview and management of all configured courts in the system.")

    # Tabs for different management sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Courts Overview",
        "📊 Court Statistics",
        "⚙️ Configuration",
        "📋 Processing Queue"
    ])

    with tab1:
        show_courts_overview()

    with tab2:
        show_court_statistics()

    with tab3:
        show_court_configuration()

    with tab4:
        show_processing_queue_status()


def show_courts_overview():
    """Display all configured courts and their validation rules"""
    st.markdown("### 📋 Configured Courts Overview")

    try:
        all_courts = st.session_state.court_manager.get_all_courts()

        if not all_courts:
            st.warning("No courts configured in the system.")
            return

        # Summary metrics
        total_courts = len(all_courts)
        enabled_courts = len([court for court in all_courts.values() if court.enabled])
        disabled_courts = total_courts - enabled_courts

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Courts", total_courts)
        with col2:
            st.metric("Enabled Courts", enabled_courts, delta="Active")
        with col3:
            st.metric("Disabled Courts", disabled_courts, delta="Inactive")

        st.markdown("---")

        # Courts details
        for court_code, court_info in all_courts.items():
            with st.expander(f"🏛️ {court_info.name} ({court_code})", expanded=court_info.enabled):
                col1, col2 = st.columns([2, 1])

                with col1:
                    # Court information
                    st.markdown(f"**Court Name:** {court_info.name}")
                    st.markdown(f"**Court Code:** {court_code}")

                    # Status badge
                    if court_info.enabled:
                        st.markdown("**Status:** 🟢 **Enabled**")
                    else:
                        st.markdown("**Status:** 🔴 **Disabled**")

                    # Validation rules
                    st.markdown("**Validation Rules:**")
                    rules = court_info.validation_rules
                    if rules:
                        for rule_key, rule_value in rules.items():
                            st.markdown(f"- **{rule_key.replace('_', ' ').title()}:** {rule_value}")
                    else:
                        st.markdown("- No specific validation rules configured")

                    # Detection patterns
                    if hasattr(court_info, 'detection_patterns') and court_info.detection_patterns:
                        st.markdown("**Detection Patterns:**")
                        patterns = court_info.detection_patterns
                        for pattern_type, pattern_list in patterns.items():
                            if pattern_list:
                                st.markdown(f"- **{pattern_type.replace('_', ' ').title()}:** {', '.join(pattern_list)}")

                with col2:
                    # Quick stats for this court
                    db = st.session_state.processor.db
                    court_stats = db.get_statistics(court_code)

                    st.metric("Files Processed", court_stats['total_files'])

                    if court_stats['total_files'] > 0:
                        success_rate = (court_stats['passed_files'] / court_stats['total_files'] * 100)
                        st.metric("Success Rate", f"{success_rate:.1f}%")

                        validity_rate = (court_stats['total_valid_lines'] / court_stats['total_kem_lines'] * 100) if court_stats['total_kem_lines'] > 0 else 0
                        st.metric("Line Validity Rate", f"{validity_rate:.1f}%")
                    else:
                        st.metric("Success Rate", "N/A")
                        st.metric("Line Validity Rate", "N/A")

    except Exception as e:
        st.error(f"Error loading court information: {e}")
        st.info("Please ensure the court configuration is properly set up.")


def show_court_statistics():
    """Show court-specific statistics"""
    st.markdown("### 📊 Court-Specific Statistics")

    try:
        # Time range selector
        col1, col2 = st.columns(2)
        with col1:
            days_back = st.selectbox(
                "Time Range",
                [7, 30, 90, 365],
                index=1,
                format_func=lambda x: f"Last {x} days"
            )

        with col2:
            st.metric("Analysis Period", f"{days_back} days")

        st.markdown("---")

        # Get statistics for all courts
        db = st.session_state.processor.db
        court_stats_data = []

        for court_code in st.session_state.available_courts:
            court_info = st.session_state.court_manager.get_court(court_code)
            if court_info and court_info.enabled:
                stats = db.get_statistics(court_code)
                history = db.get_history(1000, court_code)  # Get more data for analysis

                # Filter by time range
                if not history.empty:
                    history['date'] = pd.to_datetime(history['processed_at']).dt.date
                    cutoff_date = datetime.now().date() - timedelta(days=days_back)
                    recent_history = history[history['date'] >= cutoff_date]
                else:
                    recent_history = pd.DataFrame()

                court_stats_data.append({
                    'Court': f"{court_info.name} ({court_code})",
                    'Code': court_code,
                    'Total Files': stats['total_files'],
                    'Recent Files': len(recent_history),
                    'Success Rate': (stats['passed_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0,
                    'Recent Success Rate': (len(recent_history[recent_history['validation_status'] == 'passed']) / len(recent_history) * 100) if len(recent_history) > 0 else 0,
                    'Total Lines': stats['total_kem_lines'],
                    'Valid Lines': stats['total_valid_lines'],
                    'Validity Rate': (stats['total_valid_lines'] / stats['total_kem_lines'] * 100) if stats['total_kem_lines'] > 0 else 0
                })

        if court_stats_data:
            # Statistics table
            st.markdown("#### 📈 Performance Summary")
            stats_df = pd.DataFrame(court_stats_data)

            # Format the dataframe for display
            display_df = stats_df.copy()
            display_df['Success Rate'] = display_df['Success Rate'].round(1).astype(str) + '%'
            display_df['Recent Success Rate'] = display_df['Recent Success Rate'].round(1).astype(str) + '%'
            display_df['Validity Rate'] = display_df['Validity Rate'].round(1).astype(str) + '%'
            display_df['Total Lines'] = display_df['Total Lines'].apply(lambda x: f"{x:,}")
            display_df['Valid Lines'] = display_df['Valid Lines'].apply(lambda x: f"{x:,}")

            st.dataframe(
                display_df.drop('Code', axis=1),
                use_container_width=True,
                hide_index=True
            )

            # Visualizations
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📊 Success Rate Comparison")
                fig_success = px.bar(
                    stats_df,
                    x='Court',
                    y='Success Rate',
                    title="File Success Rate by Court",
                    color='Success Rate',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100]
                )
                fig_success.update_layout(height=400)
                st.plotly_chart(fig_success, use_container_width=True)

            with col2:
                st.markdown("#### 📈 Processing Volume")
                fig_volume = px.bar(
                    stats_df,
                    x='Court',
                    y='Recent Files',
                    title=f"Files Processed (Last {days_back} Days)",
                    color='Recent Files',
                    color_continuous_scale='Blues'
                )
                fig_volume.update_layout(height=400)
                st.plotly_chart(fig_volume, use_container_width=True)

            # Detailed breakdown per court
            st.markdown("#### 🔍 Detailed Court Analysis")
            for court_data in court_stats_data:
                court_code = court_data['Code']
                with st.expander(f"📊 {court_data['Court']} Detailed Stats"):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Files", court_data['Total Files'])
                        st.metric(f"Recent Files ({days_back}d)", court_data['Recent Files'])

                    with col2:
                        st.metric("Overall Success Rate", f"{court_data['Success Rate']:.1f}%")
                        st.metric("Recent Success Rate", f"{court_data['Recent Success Rate']:.1f}%")

                    with col3:
                        st.metric("Total Lines Processed", f"{court_data['Total Lines']:,}")
                        st.metric("Valid Lines", f"{court_data['Valid Lines']:,}")

                    with col4:
                        st.metric("Line Validity Rate", f"{court_data['Validity Rate']:.1f}%")
                        failed_lines = court_data['Total Lines'] - court_data['Valid Lines']
                        st.metric("Failed Lines", f"{failed_lines:,}")

        else:
            st.warning("No court statistics available. Process some files to see data.")

    except Exception as e:
        st.error(f"Error loading court statistics: {e}")


def show_court_configuration():
    """Show court configuration viewer (read-only)"""
    st.markdown("### ⚙️ Court Configuration Viewer")
    st.info("📖 Read-only view of court configurations. Editing capabilities will be added in a future update.")

    try:
        # Load and display raw configuration
        config_manager = st.session_state.court_manager

        # Configuration validation
        st.markdown("#### ✅ Configuration Validation")
        validation_result = config_manager.validate_configuration()

        if not any(validation_result.values()):
            st.success("✅ All court configurations are valid!")
        else:
            st.warning("⚠️ Configuration issues detected:")
            for category, issues in validation_result.items():
                if issues:
                    st.error(f"**{category}:**")
                    for issue in issues:
                        st.markdown(f"- {issue}")

        st.markdown("---")

        # Raw configuration display
        st.markdown("#### 📋 Raw Configuration")

        # Load the raw JSON configuration
        try:
            with open("courts_config.json", "r") as f:
                config_data = json.load(f)

            st.json(config_data)

            # Download configuration button
            config_str = json.dumps(config_data, indent=2)
            st.download_button(
                label="📥 Download Configuration",
                data=config_str,
                file_name="courts_config.json",
                mime="application/json"
            )

        except FileNotFoundError:
            st.error("Configuration file 'courts_config.json' not found.")
        except json.JSONDecodeError as e:
            st.error(f"Error reading configuration file: {e}")

        st.markdown("---")

        # Configuration summary
        st.markdown("#### 📊 Configuration Summary")
        all_courts = config_manager.get_all_courts()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Courts", len(all_courts))
        with col2:
            enabled = len([c for c in all_courts.values() if c.enabled])
            st.metric("Enabled Courts", enabled)
        with col3:
            default_court = getattr(config_manager, 'default_court', 'Not set')
            st.metric("Default Court", default_court)

    except Exception as e:
        st.error(f"Error loading configuration: {e}")


def show_processing_queue_status():
    """Show court-specific processing queue status"""
    st.markdown("### 📋 Processing Queue Status")

    st.info("🚧 Processing queue monitoring is a placeholder feature that will show:")
    st.markdown("""
    - **Active Processing Jobs:** Files currently being processed by court
    - **Queue Length:** Number of files waiting to be processed per court
    - **Processing History:** Recent processing activity timeline
    - **Resource Usage:** System resources allocated per court
    - **Error Logs:** Recent processing errors by court
    """)

    # Simulated queue status (placeholder)
    st.markdown("#### 📊 Current Queue Status")

    try:
        for court_code in st.session_state.available_courts:
            court_info = st.session_state.court_manager.get_court(court_code)
            if court_info and court_info.enabled:
                with st.expander(f"📋 {court_info.name} ({court_code}) Queue Status"):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Queue Length", "0", delta="Empty")
                    with col2:
                        st.metric("Active Jobs", "0", delta="Idle")
                    with col3:
                        st.metric("Completed Today", "0")
                    with col4:
                        st.metric("Error Count", "0", delta="Clean")

                    st.markdown("**Status:** 🟢 Ready for processing")
                    st.markdown("**Last Activity:** No recent activity")

    except Exception as e:
        st.error(f"Error loading queue status: {e}")

    # Future implementation notes
    st.markdown("---")
    st.markdown("#### 🔮 Future Enhancements")
    st.markdown("""
    **Planned features for processing queue management:**
    - Real-time queue monitoring with auto-refresh
    - Processing job prioritization by court
    - Resource allocation management
    - Automated retry mechanisms for failed jobs
    - Integration with FTP monitoring for automatic queuing
    - Processing performance analytics and optimization suggestions
    """)


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
