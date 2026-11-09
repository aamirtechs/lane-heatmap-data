"""Command line interface for lane-heatmap-data.

Usage examples (run from the repo root):

    python -m lane_heatmap examples/sample-lanes.json
    python -m lane_heatmap examples/sample-lanes.json --format csv
    python -m lane_heatmap examples/sample-lanes.json --format both --out report
    python -m lane_heatmap examples/sample-lanes.json --json
    python -m lane_heatmap examples/sample-lanes.json --check
"""

from __future__ import annotations

import argparse
import json
import sys

from . import LaneBookError, aggregate, load_lanes, render_csv, render_markdown


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lane-heatmap",
        description="Convert a lane book JSON file into a state-pair rate matrix.",
    )
    parser.add_argument("input", help="path to a lane book JSON file")
    parser.add_argument(
        "--format",
        choices=["csv", "md", "both"],
        default="md",
        help="output format (default: md)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="base path for output files: writes <out>.md and/or <out>.csv "
        "instead of printing to stdout",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="also emit the full report as JSON (to stdout, or to <out>.json "
        "when --out is given)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="only validate the input file; exit non-zero on any bad row",
    )
    return parser


def _fail(errors):
    for error in errors:
        print("error: %s" % error, file=sys.stderr)
    return 2


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        lanes, errors = load_lanes(args.input)
    except LaneBookError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    if errors:
        return _fail(errors)
    if args.check:
        print("OK: %d lane(s) valid, 0 errors" % len(lanes))
        return 0

    report = aggregate(lanes)
    outputs = {}
    if args.format in ("md", "both"):
        outputs["md"] = render_markdown(report)
    if args.format in ("csv", "both"):
        outputs["csv"] = render_csv(report)

    if args.out:
        for key, text in outputs.items():
            path = "%s.%s" % (args.out, key)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            print("wrote %s" % path)
        if args.json:
            path = "%s.json" % args.out
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2)
                handle.write("\n")
            print("wrote %s" % path)
    else:
        for text in outputs.values():
            print(text, end="")
        if args.json:
            print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
