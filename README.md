# SMARTMoraga — 2026 Election Results Widget

A lightweight, responsive election-results widget for the November 3, 2026 Contra Costa County election, designed to be embedded into SMARTMoraga's Wix Classic website.

## Three selected contests
- Moraga Town Council (two seats)
- Acalanes Union High School District Measure W (two-thirds YES threshold)
- Moraga-Orinda Fire District, Division 3

## Hosting

GitHub Pages, using **Settings → Pages → Build and deployment → Source: GitHub Actions**.

Public URL after a successful GitHub Pages deployment:
https://bpmeyers-ai.github.io/smartmoraga-election-results/

The widget loads the last validated data snapshot from `docs/data.json`. The initial numbers are a timestamped **sample/baseline** from the county's November 3, 2026 8:05:10 PM PST report; they must not be represented as a verified live feed.

## Automated data updates

`.github/workflows/election-widget.yml` runs every 15 minutes and on pushes. It uses the official Clarity Elections data-feed candidates, validates all three contests and candidate rosters, and publishes to Pages. Invalid or inaccessible feed responses never overwrite verified results. Read the GitHub Actions logs for the retrieval status.

The Clarity feed paths are not yet independently verified for this county election. Additional county PDF fallback support can be added after confirming live feed response formats.

## Embed in Wix Classic

After the public Pages URL serves the widget successfully:

1. In Wix Editor select **Add Elements → Embed Code → Embed a Site**.
2. Paste the public URL above into the website address.
3. Adjust the embed element width and height for desktop and mobile; check the actual rendered output before publication.

## Privacy and limitations

No voter-specific information is collected. The widget shows *unofficial* election results until county certification. A candidate lead is not an official race call.
