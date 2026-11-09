"""Tests for lane-heatmap-data. Run with: python -m unittest discover -s tests -v"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lane_heatmap import aggregate, load_lanes, render_csv, render_markdown, validate_lanes

GOOD = [
    {"origin_state": "TX", "destination_state": "OK", "rate": 1000, "miles": 500, "load_count": 2},
    {"origin_state": "TX", "destination_state": "OK", "rate": 800, "miles": 400},
    {"origin_state": "OH", "destination_state": "PA", "rate": 600, "miles": 300},
]


class TestValidation(unittest.TestCase):
    def test_valid_rows_normalize_state_codes(self):
        lanes, errors = validate_lanes(
            [{"origin_state": "tx", "destination_state": " ok ", "rate": 900, "miles": 450}]
        )
        self.assertEqual(errors, [])
        self.assertEqual(lanes[0]["origin_state"], "TX")
        self.assertEqual(lanes[0]["destination_state"], "OK")
        self.assertEqual(lanes[0]["load_count"], 1)

    def test_missing_field_is_an_error(self):
        _, errors = validate_lanes(
            [{"origin_state": "TX", "destination_state": "OK", "rate": 900}]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("row 0", errors[0])
        self.assertIn("miles is missing", errors[0])

    def test_bad_state_code_is_an_error(self):
        _, errors = validate_lanes(
            [{"origin_state": "TEXAS", "destination_state": "OK", "rate": 900, "miles": 400}]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("origin_state", errors[0])

    def test_zero_and_negative_numbers_are_errors(self):
        _, errors = validate_lanes(
            [
                {"origin_state": "TX", "destination_state": "OK", "rate": 0, "miles": 400},
                {"origin_state": "TX", "destination_state": "OK", "rate": 900, "miles": -5},
            ]
        )
        self.assertEqual(len(errors), 2)

    def test_bad_load_count_is_an_error(self):
        _, errors = validate_lanes(
            [{"origin_state": "TX", "destination_state": "OK", "rate": 900, "miles": 400, "load_count": 0}]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("load_count", errors[0])

    def test_non_list_and_non_dict_rows_are_errors(self):
        _, errors = validate_lanes({"not": "a list"})
        self.assertEqual(len(errors), 1)
        _, errors = validate_lanes(["not a dict"])
        self.assertEqual(len(errors), 1)

    def test_all_bad_rows_reported_not_just_first(self):
        _, errors = validate_lanes(
            [
                {"origin_state": "TX", "destination_state": "OK", "rate": 0, "miles": 400},
                {"origin_state": "TX", "destination_state": "OK", "rate": 900, "miles": 0},
            ]
        )
        self.assertEqual(len(errors), 2)
        self.assertIn("row 0", errors[0])
        self.assertIn("row 1", errors[1])

    def test_bad_rows_are_not_silently_dropped(self):
        lanes, errors = validate_lanes(GOOD[:1] + [
            {"origin_state": "TX", "destination_state": "OK", "rate": -1, "miles": 400},
        ])
        self.assertEqual(len(lanes), 1)
        self.assertEqual(len(errors), 1)


class TestAggregation(unittest.TestCase):
    def test_load_weighted_averages(self):
        lanes, _ = validate_lanes(GOOD)
        report = aggregate(lanes)
        tx_ok = [p for p in report["pairs"] if p["pair"] == "TX>OK"][0]
        # (1000*2 + 800*1) / 3 = 933.33; rpm (2.0*2 + 2.0*1) / 3 = 2.0
        self.assertAlmostEqual(tx_ok["average_rate"], 933.33, places=2)
        self.assertAlmostEqual(tx_ok["average_rate_per_mile"], 2.0, places=2)
        self.assertEqual(tx_ok["load_count"], 3)
        self.assertEqual(tx_ok["min_rate"], 800)
        self.assertEqual(tx_ok["max_rate"], 1000)

    def test_pairs_sorted_best_rate_per_mile_first(self):
        lanes, _ = validate_lanes(GOOD)
        report = aggregate(lanes)
        rpms = [p["average_rate_per_mile"] for p in report["pairs"]]
        self.assertEqual(rpms, sorted(rpms, reverse=True))

    def test_summary_totals_and_best_worst(self):
        lanes, _ = validate_lanes(GOOD)
        summary = aggregate(lanes)["summary"]
        self.assertEqual(summary["total_lanes"], 3)
        self.assertEqual(summary["total_loads"], 4)
        self.assertEqual(summary["pair_count"], 2)
        self.assertEqual(summary["best_rate_per_mile_pair"], "OH>PA")
        self.assertEqual(summary["worst_rate_per_mile_pair"], "TX>OK")

    def test_empty_lane_list_summary(self):
        report = aggregate([])
        self.assertEqual(report["pairs"], [])
        self.assertIsNone(report["summary"]["best_rate_per_mile_pair"])

    def test_csv_and_markdown_contain_pair_rows(self):
        lanes, _ = validate_lanes(GOOD)
        report = aggregate(lanes)
        self.assertIn("TX,OK,933.33,2.00,3,800,1000", render_csv(report))
        self.assertIn("| TX | OK | $933.33 | $2.00 | 3 | $800 | $1000 |", render_markdown(report))
        self.assertIn("Total loads: 4", render_markdown(report))


def _run_cli(*args):
    root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        [sys.executable, "-m", "lane_heatmap", *args],
        cwd=root, capture_output=True, text=True, timeout=30,
    )


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.good = self.dir / "good.json"
        self.good.write_text(json.dumps(GOOD), encoding="utf-8")
        self.bad = self.dir / "bad.json"
        self.bad.write_text(json.dumps([
            {"origin_state": "TX", "destination_state": "OK", "rate": 900, "miles": 400},
            {"origin_state": "TX", "destination_state": "OK", "miles": 400},
        ]), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_valid_exits_zero(self):
        result = _run_cli(str(self.good), "--check")
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK:", result.stdout)

    def test_check_invalid_exits_nonzero_and_names_row(self):
        result = _run_cli(str(self.bad), "--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("row 1", result.stderr)

    def test_default_run_rejects_bad_rows(self):
        result = _run_cli(str(self.bad))
        self.assertNotEqual(result.returncode, 0)

    def test_csv_format_output(self):
        result = _run_cli(str(self.good), "--format", "csv")
        self.assertEqual(result.returncode, 0)
        self.assertIn("origin_state,destination_state", result.stdout)
        self.assertIn("TX,OK", result.stdout)

    def test_out_writes_files(self):
        out = self.dir / "report"
        result = _run_cli(str(self.good), "--format", "both", "--out", str(out), "--json")
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.dir / "report.md").exists())
        self.assertTrue((self.dir / "report.csv").exists())
        self.assertTrue((self.dir / "report.json").exists())
        data = json.loads((self.dir / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["total_loads"], 4)

    def test_json_stdout_output(self):
        result = _run_cli(str(self.good), "--json")
        self.assertEqual(result.returncode, 0)
        parsed = json.loads(result.stdout[result.stdout.index("{"):])
        self.assertEqual(parsed["summary"]["total_lanes"], 3)


if __name__ == "__main__":
    unittest.main()
