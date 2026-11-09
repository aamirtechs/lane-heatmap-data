# Good first issues

New contributors welcome. Pick one issue, open a pull request, and include
a test that covers the new behavior.

## 1. Add a `--sort` option for the pair table

Problem: pairs are always sorted by average rate per mile, best first.
Some users want to sort by average rate, load count, or pair name instead.

Task: add a `--sort` flag accepting `rpm` (default), `rate`, `loads`,
and `pair`. Sort the pairs accordingly before rendering, in both CSV and
Markdown output, and add CLI tests for each sort key.

## 2. Support CSV input files as well as JSON

Problem: many dispatchers keep lane books in spreadsheets, so their data
starts life as CSV, not JSON.

Task: accept `.csv` input files with the columns `origin_state`,
`destination_state`, `rate`, `miles`, and optional `load_count`. Reuse
the existing validation so bad CSV rows produce the same row-indexed
errors as bad JSON rows, and add tests for a valid and an invalid CSV file.

## 3. Add a `--min-loads` filter to hide thin pairs

Problem: a pair with a single load can top the table on one lucky rate
and mislead pricing decisions.

Task: add a `--min-loads N` flag that excludes pairs with fewer than N
loads from the rendered output. The summary should still report the
unfiltered totals, and add tests proving the filter and the totals.

## 4. Add a plain-text heatmap bar chart to the Markdown report

Problem: the Markdown table shows the numbers but does not make the
spread between pairs obvious at a glance.

Task: append a simple text bar chart to the Markdown report, one bar per
pair scaled to its average rate per mile, using only ASCII characters.
Keep the existing table unchanged, and add a test that checks the bars
appear in the same best-first order as the table.
