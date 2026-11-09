# lane-heatmap-data
**Live tool:** https://aamirtechs.github.io/lane-heatmap-data/ (runs in your browser, no install)

A zero-dependency Python CLI and importable library that turns a lane book
JSON file into a state-pair rate matrix, as CSV and as a Markdown report.

Small dispatchers usually price lanes from memory or from a messy
spreadsheet. This tool answers one question from real booked lanes: which
state pairs actually pay best per mile, and which ones quietly lose money.

## Input format

A JSON list of lanes. Each lane needs an origin state, a destination state,
a rate in dollars, and miles. `load_count` is optional and defaults to 1.

```json
[
  {"origin_state": "TX", "destination_state": "OK", "rate": 950, "miles": 400, "load_count": 3},
  {"origin_state": "TX", "destination_state": "OK", "rate": 1100, "miles": 420},
  {"origin_state": "TX", "destination_state": "GA", "rate": 1800, "miles": 900, "load_count": 2}
]
```

Averages are load-weighted: a row with `load_count` 3 counts three times.
Malformed rows are errors, never silent drops. The CLI lists every bad row
by index and exits non-zero.

## Install and run

No dependencies. Python 3.9 or newer.

```sh
python -m lane_heatmap examples/sample-lanes.json
python -m lane_heatmap examples/sample-lanes.json --format csv
python -m lane_heatmap examples/sample-lanes.json --format both --out report
python -m lane_heatmap examples/sample-lanes.json --json
python -m lane_heatmap examples/sample-lanes.json --check
```

Flags:

- `--format csv|md|both` (default `md`): what to emit.
- `--out <base>`: write `<base>.md` and/or `<base>.csv` instead of printing.
- `--json`: also emit the full report as JSON (to stdout, or to `<base>.json` with `--out`).
- `--check`: only validate the file. Prints `OK` and exits 0 when valid,
  or lists every bad row and exits non-zero when invalid.

Use it as a library too:

```python
from lane_heatmap import load_lanes, aggregate, render_markdown

lanes, errors = load_lanes("examples/sample-lanes.json")
assert not errors
print(render_markdown(aggregate(lanes)))
```

## Real example output

Running the CLI on `examples/sample-lanes.json` (6 lanes, 9 loads) prints
this Markdown report:

```
# Lane rate heatmap

Total lanes: 6
Total loads: 9
State pairs: 4
Best rate per mile: TX>OK at $2.44/mile
Worst rate per mile: CA>AZ at $1.55/mile

| Origin | Destination | Avg rate | Avg $/mile | Loads | Min rate | Max rate |
|--------|-------------|----------|------------|-------|----------|----------|
| TX | OK | $987.50 | $2.44 | 4 | $950 | $1100 |
| OH | PA | $670.00 | $2.20 | 2 | $640 | $700 |
| TX | GA | $1800.00 | $2.00 | 2 | $1800 | $1800 |
| CA | AZ | $850.00 | $1.55 | 1 | $850 | $850 |
```

The same input with `--format csv` prints:

```
origin_state,destination_state,average_rate,average_rate_per_mile,load_count,min_rate,max_rate
TX,OK,987.50,2.44,4,950,1100
OH,PA,670.00,2.20,2,640,700
TX,GA,1800.00,2.00,2,1800,1800
CA,AZ,850.00,1.55,1,850,850
```

And `--check` prints:

```
OK: 6 lane(s) valid, 0 errors
```

A file with a bad row fails loudly instead of dropping it:

```
error: row 0: miles is missing
```

with exit code 2.

## Tests

```sh
python -m unittest discover -s tests -v
```

19 tests, all passing: validation, load-weighted aggregation, sorting,
summary stats, CSV and Markdown rendering, and CLI behavior including
`--check`, `--format`, `--out`, and `--json`.

## License

MIT. See [LICENSE](LICENSE).
