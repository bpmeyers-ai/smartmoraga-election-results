# SMARTMoraga — 2026 election results widget

A public, mobile-responsive widget tracking exactly three November 3, 2026 Contra Costa County contests:
- Moraga Town Council (two seats)
- Acalanes Union High School District Measure W (two-thirds YES requirement; $168 parcel tax)
- Moraga-Orinda Fire Protection District, Division 3

## Public widget

https://bpmeyers-ai.github.io/smartmoraga-election-results/

To embed in Wix Classic: **Add Elements → Embed Code → Embed a Site**. Paste the public widget URL. Adjust width and height in Wix's desktop and mobile editors.

## Official data and refresh

The GitHub Actions workflow runs approximately every 15 minutes. It reads the county's official [election results page](https://www.contracostavote.gov/election/november-3-2026-general-election/), discovers the actively published election-summary PDF (ignoring commented-out future report links), downloads it, extracts all three specified contests, validates every expected candidate/choice and its count against the reported percentages, and publishes only complete, non-older results to docs/data.json.

A known 9:20 PM election-night PDF is retained as a fallback. The Clarity Elections structured-data endpoint json/sum.json is also supported (including its Contests/C/CH/V schema), but Clarity currently returns empty HTTP 202 responses to GitHub Actions even though it loads in a browser. The county PDF is therefore the active source.

The front end refreshes its displayed data every five minutes while open. **County report as-of time** and **successful fetch time** are separately labeled. All results are unofficial until certified; the widget makes no winner or measure-passage calls.

## Safeguards

- No partial roster, candidate mismatch, wrong contest, zero-vote record, inconsistent vote subtotals, or conflicting PDF percentages can overwrite valid results.
- An older report cannot replace a newer published report.
- Temporary source failures leave the last verified snapshot intact.
- Tests run before every deployment.
- Official source link and report timestamp are displayed.

## Development

Core files: docs/index.html, docs/app.js, docs/style.css, docs/data.json, scripts/update.py, scripts/pdf_extract.py, tests/.

Workflow: .github/workflows/election-widget.yml.

Run tests locally with Python 3.12+ and pypdf installed:

    pip install pypdf
    python -m unittest discover -s tests -v

The widget is independent of SMARTMoraga's existing Wix website and transcript-search application.
