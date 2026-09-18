# Reproducing the report

The canonical local app is `outputs/bonsai-report` in the parent workspace. This directory preserves its authored report content and reviewed snapshot; the protected Data runtime is supplied by the installed data-analytics plugin.

1. Run `python3 scripts/bonsai/build_report_data.py /absolute/path/to/reviewed.json --complete` from the Lucebox checkout. This verifies coverage before marking the report complete and rebuilds the Markdown/CSV analysis from preserved measurements.
2. Use the Data plugin's `scripts/prepare-data-app.mjs --surface report --output /absolute/new-report --snapshot /absolute/path/to/reviewed.json` for a new app. For the existing local app, update its snapshot in place; preserve its stable ID.
3. Copy `ReportContent.jsx` and `report.css` into the app's `src/content/report/` directory.
4. Follow the generated app's AGENTS.md. Build with the Data plugin's `scripts/data-app.mjs build --project-dir /absolute/report --separate-data`; serve the complete dist directory on localhost.

No external data service is required. Measurements are in the parent results.json, dflash-followup/results.json and dflash-remaining/results.json. Logs preserve speculative/ordinary step counters. Runtime/library hashes, arguments and model provenance are retained alongside the data. Production was restored to Swift with DFlash2 after the measurements; no production executable or configuration was replaced.
