# Changelog

All notable changes to this project will be documented in this file.

## 1.0.0 (2026-11-02)

- First release.
- Zero-dependency Python CLI plus importable library.
- Converts a lane book JSON file into a state-pair rate matrix as CSV
  and as a Markdown report.
- Per-pair average rate, average rate per mile, load count, min rate,
  and max rate, sorted best rate per mile first.
- Overall summary: total lanes, total loads, pair count, and the best
  and worst rate-per-mile pairs.
- `--json` output, `--check` validation mode that exits non-zero on bad
  rows, `--format csv|md|both`, and `--out` for file output.
- Malformed rows are reported as errors with their row index, never
  dropped silently.
- Sample lane book in `examples/sample-lanes.json` and 19 passing tests.
