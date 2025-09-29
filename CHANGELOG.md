# CHANGELOG - Content-Based Routing Feature

## Version 2.0.0 - Multi-Court Content-Based Routing

### 🎯 Overview
Added intelligent content-based routing to automatically classify and route court documents from a shared FTP inbox to the appropriate court processing pipeline.

### 🚀 New Features

#### Content-Based Router
- Automatic Court Detection: Files are analyzed using multiple signals to determine the correct court
- Scoring System: Weighted scoring based on:
  - Filename prefixes (+50 points)
  - Path patterns (+30 points)
  - Content matches (+3 per match, max +10)
  - Validation ratio (0–100 points based on valid lines)
  - Date recency (+10 points if recent)
- Quarantine System: Low-confidence files are quarantined with detailed reports
- Three Operating Modes:
  - `off`: Traditional behavior (backwards compatible)
  - `shadow`: Logs routing predictions without changing behavior
  - `enforce`: Routes files based on classification

#### Idempotency
- Prevents duplicate processing using SHA256 hash of file metadata
- Tracks processed files in database
- Automatic skip of already-processed files

### 📝 Configuration Changes

#### New Router Configuration (ftp_config.json)
```jsonc
{
  "router": {
    "enable_content_based_routing": true,
    "router_mode": "enforce",  // "off" | "shadow" | "enforce"
    "quarantine_dir": "/PAMarchive/SeaTac/unknown/",
    "routing_threshold": 80,    // Minimum score to route
    "routing_margin": 20        // Minimum margin over second place
  }
}
```

### 📦 Migration
- Database migrations for router fields are applied automatically on startup (idempotent).
  - Adds columns to `processing_history`: `routed_court_code`, `routing_confidence`, `routing_explanation`, `router_scores_json`, `idempotency_key`, `router_mode`, `quarantined`.
  - Creates `processed_ledger` table for idempotency tracking.
  - Creates indexes to improve query performance.

### 🧪 Tests
- Router unit tests cover filename/path/content/date signals, unknown classification, margin enforcement, idempotency key generation, and quarantine report formatting.

### 🔧 Notes
- To enable content-based routing, set the `router` block in `ftp_config.json` as shown above.
- When `router_mode` is `enforce`, low-confidence files (below threshold or margin) are quarantined to `quarantine_dir` with a CSV-ready report.
- When `router_mode` is `shadow`, routing decisions are logged/audited but do not alter processing.
