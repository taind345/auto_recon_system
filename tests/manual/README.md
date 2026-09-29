# Manual UI tests (NOT part of `run_all.py` — need real Firefox)

- `ui_flow_selenium.py` — 10 steps: rail/lang-vi/theme+lang toggle/scan+tree/
  detail-7-tabs/filters+search/nav-9-cats/notes-export-diff/check-session.
- `ui_audit_selenium.py` — 26 checks: h-overflow per tab, rail geometry,
  raw-i18n keys, broken chars, CSS vars, responsive 700px, light theme.

Setup: `pip install selenium` + geckodriver in PATH, then e.g.
`python3 tests/manual/ui_flow_selenium.py`. Scripts start their own
fixture + app servers on ephemeral ports.
