"""
Streamlit Web Interface for File Validator with FTP Integration (cleaned)
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from ftp_processor import FTPProcessor, FTPConfig, DatabaseManager

try:
    from court_config_manager import CourtConfigManager
    MULTI_COURT_SUPPORT = True
except Exception:
    CourtConfigManager = None  # type: ignore
    MULTI_COURT_SUPPORT = False


st.set_page_config(page_title="Court Validator - FTP", page_icon="📁", layout="wide")

# Session state
if 'ftp_processor' not in st.session_state:
    st.session_state.ftp_processor = FTPProcessor()
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'selected_court' not in st.session_state:
    st.session_state.selected_court = 'KEM'

# Courts
if MULTI_COURT_SUPPORT:
    if 'court_manager' not in st.session_state:
        st.session_state.court_manager = CourtConfigManager()  # type: ignore
    if 'available_courts' not in st.session_state:
        try:
            courts = st.session_state.court_manager.get_all_courts()
            st.session_state.available_courts = [c for c, v in courts.items() if getattr(v, 'enabled', False)]
        except Exception:
            st.session_state.available_courts = ['KEM']


def main():
    # Header + court selection
    if MULTI_COURT_SUPPORT and len(st.session_state.get('available_courts', [])) > 1:
        st.title("File Validator - FTP Integration")
        court_options = {}
        for code in st.session_state.available_courts:
            ci = st.session_state.court_manager.get_court(code)
            name = getattr(ci, 'name', code)
            court_options[f"{name} ({code})"] = code
        label = st.selectbox("Select court", list(court_options.keys()))
        st.session_state.selected_court = court_options[label]
    else:
        st.title("File Validator - FTP Integration")

    # Sidebar connection
    st.sidebar.title("FTP Connection")
    if st.session_state.connected:
        st.sidebar.success("Connected to FTP")
    else:
        st.sidebar.warning("Not connected")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.button("Connect", disabled=st.session_state.connected):
            connect_to_ftp()
    with c2:
        if st.button("Disconnect", disabled=not st.session_state.connected):
            disconnect_from_ftp()

    # Nav
    page = st.sidebar.radio("Navigation", ["Dashboard", "FTP Files", "Process Files", "Analytics", "FTP Settings", "Help"])
    if page == "Dashboard":
        show_dashboard()
    elif page == "FTP Files":
        show_ftp_files()
    elif page == "Process Files":
        show_process_files()
    elif page == "Analytics":
        show_analytics()
    elif page == "FTP Settings":
        show_ftp_settings()
    else:
        show_help()


def connect_to_ftp():
    try:
        with st.spinner("Connecting..."):
            st.session_state.ftp_processor.connect_ftp()
            st.session_state.connected = True
            st.success("Connected")
    except Exception as e:
        st.error(f"Failed: {e}")
        st.session_state.connected = False


def disconnect_from_ftp():
    st.session_state.ftp_processor.disconnect_ftp()
    st.session_state.connected = False
    st.info("Disconnected")


def show_dashboard():
    st.header("Dashboard")
    db = DatabaseManager(st.session_state.ftp_processor.kem_config.db_path)
    stats = db.get_statistics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("FTP", "Connected" if st.session_state.connected else "Disconnected")
    c2.metric("Files", stats['total_files'])
    rate = (stats['passed_files'] / stats['total_files'] * 100) if stats['total_files'] else 0
    c3.metric("Success %", f"{rate:.1f}%")
    c4.metric("Court Lines", stats['total_kem_lines'])
    st.subheader("Recent History")
    hist = db.get_history(20)
    if not hist.empty:
        st.dataframe(hist[['file_name', 'processed_at', 'validation_status', 'kem_lines', 'success_rate']], use_container_width=True)
    else:
        st.info("No history yet")


def show_ftp_files():
    st.header("FTP Files")
    if not st.session_state.connected:
        st.warning("Connect first")
        return
    cfg = st.session_state.ftp_processor.ftp_config
    court = st.session_state.selected_court
    paths = cfg.get_court_paths(court) or {
        'inbox': cfg.ftp_inbox,
        'results': cfg.ftp_results,
        'processed': cfg.ftp_processed,
        'invalid': cfg.ftp_invalid,
    }
    dir_label = st.selectbox("Directory", ["inbox", "results", "processed", "invalid"])
    ftp_path = paths[dir_label]
    st.caption(ftp_path)
    files = st.session_state.ftp_processor.list_ftp_files(ftp_path)
    if files:
        df = pd.DataFrame({"Filename": files, "Select": [False]*len(files)})
        edited = st.data_editor(df, hide_index=True, use_container_width=True, disabled=["Filename"])
        selected = edited[edited["Select"]]["Filename"].tolist() if not edited.empty else []
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Process Selected", disabled=not selected):
                process_selected_files(selected, ftp_path)
        with c2:
            if st.button("Download Selected", disabled=not selected):
                download_selected_files(selected, ftp_path)
    else:
        st.info("No files found")


def show_process_files():
    st.header("Process Files")
    if not st.session_state.connected:
        st.warning("Connect first")
        return
    files = st.session_state.ftp_processor.list_ftp_files(st.session_state.ftp_processor.ftp_config.ftp_inbox)
    if files:
        f = st.selectbox("Select file", files)
        if st.button("Process File"):
            with st.spinner("Processing..."):
                res = st.session_state.ftp_processor.process_ftp_file(f, court_code=st.session_state.selected_court)
            if res['status'] == 'success':
                st.success("Processed")
                st.json({k: v for k, v in res.items() if k in ('validation_status', 'stats', 'ftp_csv_path')})
            else:
                st.error(res.get('reason', 'Failed'))
    bs = st.number_input("Batch Size", min_value=1, max_value=100, value=10)
    if st.button("Process Batch"):
        process_batch(bs)


def show_analytics():
    st.header("Analytics & Archives")

    # High-level processing metrics + charts
    db = DatabaseManager(st.session_state.ftp_processor.kem_config.db_path)
    history = db.get_history(1000)
    if history.empty:
        st.info("No data available yet. Process some files to populate analytics.")
    else:
        # Date/time preparation
        history['processed_at_dt'] = pd.to_datetime(history['processed_at'])
        history['date'] = history['processed_at_dt'].dt.date

        # Quick time window (relative to now)
        time_window = st.selectbox(
            "Quick Time Window",
            [
                "All",
                "Last 1 hour",
                "Last 6 hours",
                "Last 12 hours",
                "Last 24 hours",
                "Last 7 days",
            ],
            index=0,
            help="Apply a relative time window filter based on current time",
        )

        filtered = history
        if time_window != "All":
            import datetime as _dt
            now = _dt.datetime.now()
            delta = {
                "Last 1 hour": _dt.timedelta(hours=1),
                "Last 6 hours": _dt.timedelta(hours=6),
                "Last 12 hours": _dt.timedelta(hours=12),
                "Last 24 hours": _dt.timedelta(hours=24),
                "Last 7 days": _dt.timedelta(days=7),
            }[time_window]
            cutoff = now - delta
            filtered = filtered[filtered['processed_at_dt'] >= cutoff]
        else:
            # Date + optional time-of-day filters
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", history['date'].min())
            with col2:
                end_date = st.date_input("End Date", history['date'].max())
            mask = (history['date'] >= start_date) & (history['date'] <= end_date)
            filtered = history.loc[mask]

            # Optional time-of-day filter
            use_time = st.checkbox("Filter by time of day", value=False, help="Further restrict results to a time-of-day range")
            if use_time:
                import datetime as _dt
                t1 = st.time_input("Start Time", value=_dt.time(0, 0))
                t2 = st.time_input("End Time", value=_dt.time(23, 59))
                times = filtered['processed_at_dt'].dt.time
                if t1 <= t2:
                    filtered = filtered[(times >= t1) & (times <= t2)]
                else:
                    # Cross-midnight window
                    filtered = filtered[(times >= t1) | (times <= t2)]

        # Metrics
        colm1, colm2, colm3, colm4 = st.columns(4)
        with colm1:
            st.metric("Total Files", len(filtered))
        with colm2:
            passed = int((filtered['validation_status'] == 'passed').sum())
            st.metric("Passed", passed)
        with colm3:
            failed = int((filtered['validation_status'] == 'failed').sum())
            st.metric("Failed", failed)
        with colm4:
            avg_rate = float(filtered['success_rate'].mean()) if not filtered.empty else 0.0
            st.metric("Avg Success Rate", f"{avg_rate:.1f}%")

        # Charts (best-effort if plotly available)
        try:
            import plotly.express as px
            import plotly.graph_objects as go

            colc1, colc2 = st.columns(2)
            with colc1:
                fig = go.Figure(data=[go.Pie(labels=['Passed', 'Failed'], values=[passed, failed], hole=0.3,
                                             marker_colors=['#28a745', '#dc3545'])])
                fig.update_layout(title="Validation Status Distribution", height=380)
                st.plotly_chart(fig, use_container_width=True)
            with colc2:
                daily = filtered.groupby('date').agg({'validation_status': lambda x: (x == 'passed').sum()}).reset_index()
                daily.columns = ['date', 'passed_count']
                fig = px.line(daily, x='date', y='passed_count', title="Daily Passed Count")
                fig.update_layout(height=380)
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.caption("Charts unavailable (plotly not installed)")

    st.markdown("---")
    st.subheader("Archive Management")

    # Archive tools
    sel_court = None
    if MULTI_COURT_SUPPORT and 'available_courts' in st.session_state:
        opts = {"All Courts": None}
        for code in st.session_state.available_courts:
            opts[code] = code
        label = st.selectbox("Select court for archive actions", list(opts.keys()), index=0)
        sel_court = opts[label]

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Migrate Legacy Archives"):
            with st.spinner("Migrating legacy archives..."):
                res = st.session_state.ftp_processor.file_processor.migrate_legacy_archives_to_court_structure()
            st.success("Migration completed")
            st.json(res)
    with c2:
        if st.button("Cleanup Expired (Dry Run)"):
            with st.spinner("Scanning expired archives..."):
                res = st.session_state.ftp_processor.file_processor.cleanup_expired_archives(sel_court, dry_run=True)
            st.info("Dry run completed")
            st.json(res)
    with c3:
        if st.button("Cleanup Expired (Apply)"):
            with st.spinner("Deleting expired archives..."):
                res = st.session_state.ftp_processor.file_processor.cleanup_expired_archives(sel_court, dry_run=False)
            st.success("Cleanup completed")
            st.json(res)

    st.subheader("Archive Statistics")
    stats = st.session_state.ftp_processor.file_processor.get_archive_statistics(sel_court)

    def _render_single_court_stats(s: dict):
        dbs = s.get('database_tracking', {})
        dir_analysis = s.get('directory_analysis', {})
        monthly = dir_analysis.get('monthly_breakdown', {})
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            st.metric("Total Files", dbs.get('total_files', 0))
        with cc2:
            st.metric("Processed Files", dbs.get('processed_files', 0))
        with cc3:
            st.metric("Invalid Files", dbs.get('invalid_files', 0))
        with cc4:
            st.metric("Expired Files", dbs.get('expired_files', 0))

        st.markdown("#### Directory Summary")
        rows = []
        for key in ['processed_dir', 'invalid_dir']:
            if key in dir_analysis:
                row = dir_analysis[key]
                rows.append({'Directory': 'Processed' if key == 'processed_dir' else 'Invalid',
                             'Files': row.get('files', 0), 'Size (MB)': round(row.get('size_mb', 0), 2)})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if monthly:
            st.markdown("#### Monthly Breakdown")
            month_rows = [{'Month': m, 'Files': r.get('files', 0), 'Size (MB)': round(r.get('size_mb', 0), 2)} for m, r in monthly.items()]
            st.dataframe(pd.DataFrame(month_rows).sort_values('Month'), use_container_width=True, hide_index=True)

    if isinstance(stats, dict) and 'database_tracking' in stats:
        _render_single_court_stats(stats)
    elif isinstance(stats, dict):
        rows = []
        for court_code, s in stats.items():
            dbs = s.get('database_tracking', {})
            rows.append({'Court': court_code,
                        'Total Files': dbs.get('total_files', 0),
                        'Processed': dbs.get('processed_files', 0),
                        'Invalid': dbs.get('invalid_files', 0),
                        'Expired': dbs.get('expired_files', 0),
                        'Total Size (MB)': dbs.get('total_size_mb', 0),
                        'Oldest': dbs.get('oldest_file', ''),
                        'Newest': dbs.get('newest_file', ''),
                        })
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values('Court'), use_container_width=True, hide_index=True)
        else:
            st.info("No archive statistics available.")


def show_ftp_settings():
    st.header("FTP Settings")
    cfg: FTPConfig = st.session_state.ftp_processor.ftp_config
    c1, c2 = st.columns(2)
    with c1:
        server = st.text_input("Server", cfg.ftp_server)
        user = st.text_input("Username", cfg.ftp_username)
        inbox = st.text_input("Inbox", cfg.ftp_inbox)
        processed = st.text_input("Processed", cfg.ftp_processed)
    with c2:
        port = st.number_input("Port", value=int(cfg.ftp_port))
        pw = st.text_input("Password", cfg.ftp_password, type="password")
        results = st.text_input("Results", cfg.ftp_results)
        invalid = st.text_input("Invalid", cfg.ftp_invalid)
    c1, c2, c3 = st.columns(3)
    with c1:
        batch = st.number_input("Batch Size", value=int(cfg.batch_size))
        upload_results = st.checkbox("Upload Results", cfg.upload_results)
    with c2:
        interval = st.number_input("Interval (min)", value=int(cfg.process_interval_minutes))
        archive_on_ftp = st.checkbox("Archive on FTP", cfg.archive_on_ftp)
    with c3:
        tempdir = st.text_input("Local Temp Dir", cfg.local_temp_dir)
        delete_after = st.checkbox("Delete After Download", cfg.delete_after_download)
    if st.button("Save"):
        data = {
            "ftp_server": server,
            "ftp_port": int(port),
            "ftp_username": user,
            "ftp_password": pw,
            "ftp_inbox": inbox,
            "ftp_results": results,
            "ftp_processed": processed,
            "ftp_invalid": invalid,
            "batch_size": int(batch),
            "process_interval_minutes": int(interval),
            "local_temp_dir": tempdir,
            "upload_results": upload_results,
            "archive_on_ftp": archive_on_ftp,
            "delete_after_download": delete_after,
        }
        with open("ftp_config.json", "w") as f:
            json.dump(data, f, indent=2)
        st.success("Saved")
    # Test connection control mirrored here
    if st.button("Test Connection"):
        with st.spinner("Testing FTP connection..."):
            ok = st.session_state.ftp_processor.test_connection()
        if ok:
            st.success("FTP connection test successful")
        else:
            st.error("FTP connection test failed")
    st.markdown("---")
    st.subheader("Archive Tools")
    sel = None
    if MULTI_COURT_SUPPORT and 'available_courts' in st.session_state:
        opts = {"All Courts": None}
        for code in st.session_state.available_courts:
            opts[code] = code
        label = st.selectbox("Cleanup court", list(opts.keys()), key="settings_cleanup_court")
        sel = opts[label]
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Migrate Archives", key="settings_migrate"):
            st.json(st.session_state.ftp_processor.file_processor.migrate_legacy_archives_to_court_structure())
    with c2:
        if st.button("Cleanup (Dry Run)", key="settings_cleanup_dry"):
            st.json(st.session_state.ftp_processor.file_processor.cleanup_expired_archives(sel, True))
    with c3:
        if st.button("Cleanup (Apply)", key="settings_cleanup_apply"):
            st.json(st.session_state.ftp_processor.file_processor.cleanup_expired_archives(sel, False))


def show_help():
    st.header("Help")
    st.markdown("Connect, browse, and process files. Use Analytics/Settings for archive tools.")


def process_batch(batch_size=None):
    res = st.session_state.ftp_processor.process_batch(batch_size)
    if res:
        st.success(f"Processed {len(res)} files")
        for r in res:
            icon = '✔' if r['status'] == 'success' else '✖'
            st.write(f"{icon} {r.get('filename','?')}: {r.get('validation_status', r.get('reason','N/A'))}")
    else:
        st.info("No files")


def process_selected_files(files, directory):
    for f in files:
        with st.spinner(f"Processing {f}..."):
            r = st.session_state.ftp_processor.process_ftp_file(f, court_code=st.session_state.selected_court, source_path=directory)
        icon = '✔' if r['status'] == 'success' else '✖'
        st.write(f"{icon} {f}: {r.get('validation_status', r.get('reason','N/A'))}")


def download_selected_files(files, directory):
    for f in files:
        st.info(f"Downloading {f} from {directory}")


# Override helpers with cleaned icons display
def process_batch(batch_size=None):
    results = st.session_state.ftp_processor.process_batch(batch_size)
    if results:
        st.success(f"Processed {len(results)} files")
        for r in results:
            icon = '✔' if r['status'] == 'success' else '✖'
            st.write(f"{icon} {r.get('filename','?')}: {r.get('validation_status', r.get('reason','N/A'))}")
    else:
        st.info("No files")


def process_selected_files(files, directory):
    for f in files:
        with st.spinner(f"Processing {f}..."):
            r = st.session_state.ftp_processor.process_ftp_file(
                f,
                court_code=st.session_state.selected_court,
                source_path=directory,
            )
        icon = '✔' if r['status'] == 'success' else '✖'
        st.write(f"{icon} {f}: {r.get('validation_status', r.get('reason','N/A'))}")


if __name__ == "__main__":
    main()
