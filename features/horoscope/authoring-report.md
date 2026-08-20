# Authoring Report — horoscope

Pre-shipped fixture, authored 2026-08-20 via the yamlgraph sole
authoring route (see docs/authoring-report-2026-08-20-bootstrap.md
for the full record).

- Lint: `yamlgraph graph lint features/horoscope/graph.yaml` — clean.
- Smoke/run: `yamlgraph graph run features/horoscope/graph.yaml --var date=2026-08-20 --json`
  — green; produced horoscope text (see outputs/2026-08-20-horoscope.md
  from the local cron witness run).
