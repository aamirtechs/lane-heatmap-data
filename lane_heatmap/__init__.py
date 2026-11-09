"""lane-heatmap-data: turn a lane book JSON file into a state-pair rate matrix.

A lane is one dict with:

- ``origin_state``: two letter US state code, for example ``"TX"``.
- ``destination_state``: two letter US state code, for example ``"OK"``.
- ``rate``: total pay for the load in dollars, must be greater than zero.
- ``miles``: loaded miles, must be greater than zero.
- ``load_count`` (optional): how many loads this row represents, default 1.

Averages are load-weighted: a row with ``load_count`` 3 counts three times
in the average rate and in the average rate per mile. Malformed rows are
never dropped silently: :func:`validate_lanes` returns one error string per
bad row, and the CLI exits non-zero when any error is present.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict

__version__ = "1.0.0"

REQUIRED_FIELDS = ("origin_state", "destination_state", "rate", "miles")


class LaneBookError(ValueError):
    """Raised when a lane book file cannot be read or parsed as JSON."""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_state(value, field, errors):
    if not isinstance(value, str):
        errors.append("%s must be a string, got %r" % (field, value))
        return None
    code = value.strip().upper()
    if len(code) != 2 or not code.isalpha():
        errors.append("%s must be a two letter state code, got %r" % (field, value))
        return None
    return code


def _validate_positive_number(value, field, errors):
    if not _is_number(value):
        errors.append("%s must be a number, got %r" % (field, value))
        return None
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        errors.append("%s must be greater than zero, got %r" % (field, value))
        return None
    return number


def validate_lanes(data):
    """Validate raw parsed JSON and return ``(lanes, errors)``.

    ``lanes`` holds only the rows that passed every check, each normalized
    to ``origin_state``, ``destination_state``, ``rate`` (float),
    ``miles`` (float) and ``load_count`` (int). ``errors`` holds one
    human readable string per bad row, prefixed with its row index, so a
    caller can report every problem instead of stopping at the first one.
    """
    errors = []
    lanes = []
    if not isinstance(data, list):
        return [], ["input must be a JSON list of lanes, got %s" % type(data).__name__]
    for index, row in enumerate(data):
        prefix = "row %d" % index
        if not isinstance(row, dict):
            errors.append("%s: lane must be an object, got %r" % (prefix, row))
            continue
        row_errors = []
        for field in REQUIRED_FIELDS:
            if field not in row:
                row_errors.append("%s is missing" % field)
        origin = destination = None
        if "origin_state" in row:
            origin = _validate_state(row["origin_state"], "origin_state", row_errors)
        if "destination_state" in row:
            destination = _validate_state(row["destination_state"], "destination_state", row_errors)
        rate = miles = None
        if "rate" in row:
            rate = _validate_positive_number(row["rate"], "rate", row_errors)
        if "miles" in row:
            miles = _validate_positive_number(row["miles"], "miles", row_errors)
        load_count = 1
        if "load_count" in row:
            raw = row["load_count"]
            if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
                row_errors.append("load_count must be a positive integer, got %r" % (raw,))
            else:
                load_count = raw
        if row_errors:
            errors.append("%s: %s" % (prefix, "; ".join(row_errors)))
            continue
        lanes.append(
            {
                "origin_state": origin,
                "destination_state": destination,
                "rate": rate,
                "miles": miles,
                "load_count": load_count,
            }
        )
    return lanes, errors


def load_lanes(path):
    """Read a lane book JSON file and return ``(lanes, errors)``."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise LaneBookError("file not found: %s" % path)
    except json.JSONDecodeError as exc:
        raise LaneBookError("invalid JSON in %s: %s" % (path, exc))
    except OSError as exc:
        raise LaneBookError("cannot read %s: %s" % (path, exc))
    return validate_lanes(data)


def aggregate(lanes):
    """Aggregate lanes into per-pair stats plus an overall summary.

    Pairs are sorted by average rate per mile, best first, so the most
    profitable lanes sit at the top of both the CSV and the report.
    """
    grouped = defaultdict(list)
    for lane in lanes:
        grouped[(lane["origin_state"], lane["destination_state"])].append(lane)

    pairs = []
    for (origin, destination), rows in grouped.items():
        loads = sum(row["load_count"] for row in rows)
        total_rate = sum(row["rate"] * row["load_count"] for row in rows)
        total_rpm = sum(
            (row["rate"] / row["miles"]) * row["load_count"] for row in rows
        )
        rates = [row["rate"] for row in rows]
        pairs.append(
            {
                "origin_state": origin,
                "destination_state": destination,
                "pair": "%s>%s" % (origin, destination),
                "average_rate": round(total_rate / loads, 2),
                "average_rate_per_mile": round(total_rpm / loads, 2),
                "load_count": loads,
                "min_rate": min(rates),
                "max_rate": max(rates),
            }
        )
    pairs.sort(key=lambda p: (-p["average_rate_per_mile"], p["pair"]))

    total_loads = sum(lane["load_count"] for lane in lanes)
    summary = {
        "total_lanes": len(lanes),
        "total_loads": total_loads,
        "pair_count": len(pairs),
        "best_rate_per_mile_pair": pairs[0]["pair"] if pairs else None,
        "best_rate_per_mile": pairs[0]["average_rate_per_mile"] if pairs else None,
        "worst_rate_per_mile_pair": pairs[-1]["pair"] if pairs else None,
        "worst_rate_per_mile": pairs[-1]["average_rate_per_mile"] if pairs else None,
    }
    return {"pairs": pairs, "summary": summary}


def render_csv(report):
    """Render the per-pair matrix as CSV text."""
    lines = [
        "origin_state,destination_state,average_rate,average_rate_per_mile,"
        "load_count,min_rate,max_rate"
    ]
    for pair in report["pairs"]:
        lines.append(
            "%s,%s,%.2f,%.2f,%d,%s,%s"
            % (
                pair["origin_state"],
                pair["destination_state"],
                pair["average_rate"],
                pair["average_rate_per_mile"],
                pair["load_count"],
                _format_money(pair["min_rate"]),
                _format_money(pair["max_rate"]),
            )
        )
    return "\n".join(lines) + "\n"


def _format_money(value):
    if float(value).is_integer():
        return str(int(value))
    return "%.2f" % value


def render_markdown(report):
    """Render the matrix plus summary as a Markdown report."""
    summary = report["summary"]
    lines = [
        "# Lane rate heatmap",
        "",
        "Total lanes: %d" % summary["total_lanes"],
        "Total loads: %d" % summary["total_loads"],
        "State pairs: %d" % summary["pair_count"],
    ]
    if summary["best_rate_per_mile_pair"] is not None:
        lines.append(
            "Best rate per mile: %s at $%.2f/mile"
            % (summary["best_rate_per_mile_pair"], summary["best_rate_per_mile"])
        )
        lines.append(
            "Worst rate per mile: %s at $%.2f/mile"
            % (summary["worst_rate_per_mile_pair"], summary["worst_rate_per_mile"])
        )
    lines += [
        "",
        "| Origin | Destination | Avg rate | Avg $/mile | Loads | Min rate | Max rate |",
        "|--------|-------------|----------|------------|-------|----------|----------|",
    ]
    for pair in report["pairs"]:
        lines.append(
            "| %s | %s | $%.2f | $%.2f | %d | $%s | $%s |"
            % (
                pair["origin_state"],
                pair["destination_state"],
                pair["average_rate"],
                pair["average_rate_per_mile"],
                pair["load_count"],
                _format_money(pair["min_rate"]),
                _format_money(pair["max_rate"]),
            )
        )
    return "\n".join(lines) + "\n"


def to_json_dict(report):
    """Return the report as a plain JSON-serializable dict."""
    return report
