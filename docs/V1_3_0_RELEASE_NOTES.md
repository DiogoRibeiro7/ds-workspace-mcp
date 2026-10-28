# v1.3.0 Release Notes

`ds-workspace-mcp` `v1.3.0` adds read-only time-series resampling and missing-interval
guidance, completing the v1.3 richer-analytics roadmap.

## Added

- `resample_time_series_dataset_tool`, a bounded MCP tool for numeric time-series
  aggregation across CSV, Parquet, JSON, and Excel datasets.
- Explicit time-bucket frequencies for seconds, minutes, hours, days, weeks, and
  calendar months. Timestamps are normalized to UTC, and grouped time series
  are processed independently.
- Six aggregation methods (`mean`, `sum`, `min`, `max`, `median`, `count`) with a
  capped result preview and a sample of missing timestamps.
- Opt-in fill methods (`forward_fill`, `backward_fill`, `linear_interpolation`,
  and `zero`). Output distinguishes missing time buckets from observed rows with
  null values, and flags look-ahead leakage risks for forecasting.
- `MCP_MAX_RESAMPLE_INTERVALS`, which limits generated time buckets to `5000` by
  default across all groups. The existing `MCP_MAX_PREVIEW_ROWS` limit also applies.

## Compatibility and safety

- Python `>=3.11,<3.13` remains supported, with no new required runtime
  dependencies.
- Existing MCP tools and result contracts remain compatible; the new tool and
  environment variable are additive.
- All resampling is read-only. Source datasets are not overwritten or exported.
- Resampling requires an explicit supported frequency and numeric observations.
  It rejects unparseable timestamps, nonnumeric values, and excessive interval
  expansion; at most 20 groups are supported.
- Filling is disabled by default. Backward filling and interpolation may use
  future observations, while zero filling is appropriate only when a missing
  interval truly means zero activity.

## Richer analytics roadmap

The existing profiling histograms, outlier and duplicate diagnostics,
seasonal-naive forecast baseline, and reproducible evaluation manifests remain
available. These capabilities were introduced in earlier releases; resampling
completes the remaining v1.3 roadmap item.

## Installation

After the `v1.3.0` Git tag has been published through PyPI Trusted Publishing:

```bash
python -m pip install --upgrade ds-workspace-mcp==1.3.0
```
