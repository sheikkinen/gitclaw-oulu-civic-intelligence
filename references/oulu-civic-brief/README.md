# Background material: Oulu daily civic-intelligence brief

This folder is an export of the existing repo material identified as
background/reusable for building a scheduled feature that publishes one
concise Markdown civic-intelligence brief per day for Oulu, Finland,
using only unauthenticated public sources, with exactly three sections
(Harbour, Procurement, Municipal decisions) plus a mandatory
Source health table and fail-closed behavior if all three sources fail.

Files here are **copies** taken from the main repo at the time of
export — treat the originals (`probes/`, `docs/`, `scripts/`,
`probes/config/`) as the source of truth; this folder is a curated
snapshot for a specific downstream task, not a fork to maintain in
parallel.

## Probes (directly reusable, no new build needed for the retrieval logic)

| Section | Probe | Notes |
|---|---|---|
| Harbour | `probes/digitraffic-marine-probe.sh` | Exactly this spec — `--level index --locode FIOUL` returns port calls sorted by ETA (vessel name, ETA, previous/next port, berth, vessel-type code). Already verified live (acceptance test Q3); already documents the "never state cargo as fact" caveat inline. |
| Procurement | `probes/hilma-probe.sh` | `--level index --search Oulu` or `--category` filters; returns title, contracting authority, publication date, deadline, source URL — common JSON envelope. Also `probes/procurement-pipeline.sh` and `probes/ted-probe.sh` if EU-wide notices ever need cross-referencing. |
| Municipal decisions | `probes/ktweb-probe.sh` | Oulu's platform is confirmed as **KTweb/Triplan** (`config/municipalities.csv` row `564\|Oulu\|triplan\|https://asiakirjat.ouka.fi/ktwebscr`). `--level index` lists § items from recent meetings (governing body, date, source URL) via RSS + drill-down. Can also invoke via `probes/municipality-kit.sh 564 --section municipal`. |

## Docs (context, prior findings, caveats already worked out)

- `docs/acceptance-test-questions.md` (Q3) — exact prior live
  verification of the harbour case, including the "cargo not public,
  vessel type only" constraint the new task also specifies.
- `docs/municipality-probe-kit.md` — explains the KTweb dispatch and
  per-city config pattern.
- `docs/intelligence-sources.md` — Oulu-specific source inventory
  (Digitraffic Marine live example, avoindata.fi 115 Oulu datasets,
  oulunliikenne.fi).
- `docs/api-platform-catalog.md` (§6) — Digitraffic platform overview
  (marine/rail/road APIs, no-auth).
- `docs/hva-procurement-bulletin-plan.md` + `scripts/hva-procurement-bulletin.sh`
  — closest existing precedent for a **scheduled bulletin-generation
  pipeline** (retrieval → deterministic field selection → LLM
  condensation split), worth reusing as the architectural pattern for
  the source-health-table + fail-closed behavior.
- `docs/sample-osint-report-oulu.md` — general Oulu-source context
  (not decision/procurement, but confirms port/traffic source
  reliability).

## Gap: no existing source-health / fail-closed orchestration layer

No existing probe currently emits a "source health" ok/unavailable/
invalid table or enforces the fail-all-three-closed rule — that
orchestration/report-assembly layer would be new, sitting on top of
these three probes (each already returns a common JSON envelope with
`http_status`/`errors`, which is the natural input to a health-table
step).

## Config

- `config/municipalities.csv` — full municipality registry (code, name,
  platform, base_url, fmi_place, lat/lon, events_rss,
  sotkanet_region); Oulu is code `564`, platform `triplan` (KTweb).
