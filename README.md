# SMARTMoraga — 2026 election results widget

A public, mobile-responsive widget tracking exactly three November 3, 2026 Contra Costa County contests:
- Moraga Town Council (two seats)
- Acalanes Union High School District Measure W (two-thirds YES requirement; $168 parcel tax)
- Moraga-Orinda Fire Protection District, Division 3

## Public widget

https://results.smartmoraga.com/

To embed in Wix Classic: **Add Elements → Embed Code → Embed a Site**. Paste the public widget URL. Adjust width and height in Wix's desktop and mobile editors.

## Official data and refresh

The GitHub Actions workflow requests a run every 15 minutes; GitHub may delay scheduled runs. It reads the county's official [results page](https://www.contracostavote.gov/november-3-2026-election-results/) and general-election page, discovers the actively published election-summary PDF (ignoring commented-out future report links), downloads it, extracts all three specified contests, validates every expected candidate/choice and its count against the reported percentages, and publishes only complete, non-older results to docs/data.json.

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

## Updater and deployment recovery

PDF extraction accepts both vertical fields and horizontal candidate rows, but
requires the exact roster, row arithmetic, contest totals and percentages.
Published PDF links are parsed as HTML (comments are ignored) and restricted to
the official county uploads host. The last verified source and four bounded
successor filenames provide fallback discovery. Every rejected PDF is logged;
only the newest completely validated report is selected by its embedded time.

The obsolete one-time installer workflow has been removed. The remaining
publisher uses one non-cancelling concurrency group and checks out current main
after entering that queue. Pages can still report a prior deployment as active
after its Actions run ends. The deployment helper retries only that specific
HTTP 400 response, at most 12 attempts 15 seconds apart. It polls the accepted
deployment for success for up to five minutes; errors/timeouts fail the run.
It never cancels a competing deployment. Unchanged scheduled runs still deploy
so a previous failed publication can recover without a new vote update.

Additional regression checks:

    node --test tests/deploy_pages.test.cjs
