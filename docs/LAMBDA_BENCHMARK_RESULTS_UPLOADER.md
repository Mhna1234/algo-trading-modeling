# Lambda: Upload Benchmark Strategy Results to S3

## Goal

Implement an AWS Lambda (in a new project folder) to receive benchmark backtest outputs (per strategy, per run), validate them, and write them to S3 in a partitioned, dashboard-friendly structure. This Lambda is write-only (S3 PutObject/multipart upload) and can be invoked from local scripts or AWS workflows after a benchmark run.

---

## 1. Key Concepts & Data Semantics

- **Benchmark Output Includes:**
  - NAV series (Net Asset Value) over time, cumulative return, etc.
  - Weights per rebalancing date (or daily)
  - Metrics summary per run (CAGR, vol, Sharpe, drawdown, turnover, etc.)
  - Optional: trades/turnover or transaction cost attribution

---

## 2. Folder/Module Structure

```
lambda/
  benchmark_results_uploader/
    README.md
    requirements.txt
    src/
      __init__.py
      handler.py
      config.py
      s3_paths.py
      schema.py
      serialize.py
      upload.py
      validation.py
    tests/
      test_paths.py
      test_validation.py
    Makefile
```
- Keep Lambda code isolated under `/lambda/` to avoid coupling with main repo logic.

---

## 3. S3 Layout (Partitioned & Stable Keys)

- **Bucket:** One dashboard input bucket (e.g., `my-dashboard-bucket`)
- **Prefix:**
  - `benchmarks/dataset=<DATASET_ID>/frequency=1d/run_date=YYYY-MM-DD/run_id=<UUID>/`
  - Option A (recommended):
    - `.../run_id=<UUID>/strategies/<strategy_name>/nav.parquet`
    - `.../run_id=<UUID>/strategies/<strategy_name>/weights.parquet`
    - `.../run_id=<UUID>/strategies/<strategy_name>/metrics.json`
- **Partition fields:** dataset, frequency, run_date, run_id
- **File formats:** Parquet for time series, JSON for metadata, CSV optional for debug

---

## 4. Data Contracts (Schemas)

- **manifest.json:** Top-level run metadata (schema_version, dataset_id, frequency, run_id, run_date, created_at_utc, strategies, time_range, notes)
- **metrics.json:** Aggregated run metrics by strategy
- **nav.parquet:** Columns: date, strategy, nav (plus optional: cash, benchmark_nav)
- **returns.parquet:** Columns: date, strategy, return
- **weights.parquet:** Columns: date, strategy, asset, weight (plus optional: is_target, rebalance_flag)

---

## 5. Lambda Interface & Invocation

- **Payload:** Accepts either base64-encoded artifacts or pointers to S3 staging files
- **Recommended:** Caller uploads large artifacts to staging S3, Lambda validates and copies to final structure, writes manifest/metrics
- **Event contract (direct upload):**
  - dataset_id, frequency, run_date, run_id, strategies, artifacts (base64 or JSON)
- **Response:** Bucket, prefix, list of object keys, validation warnings

---

## 6. IAM & Environment Variables

- **IAM:** s3:PutObject, s3:AbortMultipartUpload, s3:ListBucket, s3:PutObjectTagging (optional), restricted to bucket/prefix
- **Env Vars:**
  - RESULTS_BUCKET
  - RESULTS_PREFIX
  - DEFAULT_ACL (optional)
  - ENABLE_GZIP_JSON
  - LOG_LEVEL

---

## 7. Implementation Plan (Step-by-Step)

1. **Config & S3 Key Builder**
   - config.py, s3_paths.py: Read/validate env vars, build deterministic keys
2. **Validation Layer**
   - validation.py: Validate required fields, strategies, tabular columns, monotonic dates, NaN handling
3. **Serialization Helpers**
   - serialize.py: Decode base64, handle JSON, compress if needed
4. **Upload Module**
   - upload.py: Use boto3 for S3 put/multipart, attach metadata tags
5. **Lambda Handler**
   - handler.py: Parse event, call validation, build prefix, upload all artifacts, return response
6. **Packaging & Deployment**
   - README.md: Instructions for zip, deployment, env vars
   - Use minimal dependencies; prefer uploading Parquet from caller

---

## 8. Dashboard Compatibility Checklist

- Artifacts support dashboard listing, leaderboard, plots, and allocation charts
- Partitioned S3 layout for efficient Athena/Glue/Spark queries

---

## 9. Testing & Operational Notes

- **Unit tests:** s3_paths, validation
- **Dry run mode:** Validate and return keys without writing if `dry_run: true`
- **Idempotency:** Overwrite or fail if objects exist, unless `overwrite: true`
- **Logging:** CloudWatch logs for start, per-object upload, and observability fields in response

---

## 10. Explicit Non-Goals

- No computation of Parquet in Lambda (prefer upload from caller)
- No dashboard or Athena integration logic
- No read/modify/delete of existing S3 objects (write-only)
- No business logic for benchmark computation
- No direct broker or trading integration

---

**Document Version:** 1.0  
**Last Updated:** December 22, 2025  
**Status:** Implementation Plan – Ready for Engineering
