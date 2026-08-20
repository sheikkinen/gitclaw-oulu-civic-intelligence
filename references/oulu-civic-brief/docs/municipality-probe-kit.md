# Municipality Probe Kit — Reference

## Overview

A parameterized intelligence probe system that works for any Finnish municipality.
National APIs are universal; only the municipal decision platform varies by city.

## Architecture

```
probes/
  municipality-kit.sh              # Orchestrator
  config/
    municipalities.csv             # Master index: code, name, platform, base_url
    oulu.conf                      # Per-city config (reference)
  lib/
    national-apis.sh               # Universal: Paavo, PRH, Hilma, StatFin, Sotkanet, FMI, MML
    ktweb-triplan.sh               # Municipal: Triplan KTweb scraper
    ktweb-dynasty.sh               # Municipal: Dynasty/Innofactor scraper
```

## Source Classification

### Universal (national APIs, work with municipality code only)

| Source | Identifier | Coverage |
|--------|-----------|----------|
| Paavo (demographics) | Postcode | All 3,019 postcodes |
| Energiatodistus | Address + postcode | National |
| PRH KREK (companies) | Y-tunnus, address | National (822K companies) |
| PRH XBRL (financials) | Y-tunnus | National (62K+ statements) |
| Hilma (procurement) | Search term, CPV | National |
| StatFin (crime) | Municipality code (KU564) | All 309 municipalities |
| Sotkanet (welfare) | Municipality code | All 309 + 23 wellbeing counties |
| FMI (weather) | Place name | National (160 stored queries) |
| Digitraffic | Lat/lon | National (road/rail/marine) |
| MML (cadastral) | Kiinteistötunnus, bbox | National |
| Finlex (courts) | Search term | National |
| Eduskunta | — | National (parliament) |

### Municipality-specific (decision platforms)

| Platform | Vendor | ~Municipalities | Scraping method |
|----------|--------|-----------------|-----------------|
| KTweb | Triplan Oy | ~50 | curl + sed (server-rendered HTML) |
| Dynasty | Innofactor | ~100 | Playwright (JS SPA) |
| Ahjo | Helsinki (custom) | 1 | REST API (paatokset.hel.fi) |
| CaseM | Innofactor (newer) | ~30 | Varies |
| Other/legacy | Various | ~80 | Manual discovery needed |

## Municipality Config Format

```bash
# config/oulu.conf
MUNICIPALITY_CODE=564
MUNICIPALITY_NAME="Oulu"
MUNICIPALITY_NAME_EN="Oulu"
POPULATION=210000

# Decision platform
PLATFORM_TYPE="triplan"  # triplan | dynasty | ahjo | none
KTWEB_BASE="https://asiakirjat.ouka.fi/ktwebscr"

# Geographic
FMI_PLACE="oulu"
CENTER_LAT=65.01
CENTER_LON=25.47

# RSS/Events (optional)
EVENTS_RSS="https://visitoulu.fi/feed/"
EVENTS_API="https://visitoulu.fi/wp-json/wp/v2/posts"
```

## KTweb (Triplan) Endpoints

Standard URL patterns when `KTWEB_BASE` is known:

| Endpoint | Path | Content |
|----------|------|---------|
| Kuulutukset (notices) | `/kuullist_tweb.htm` | Building permits, noise, zoning |
| Pöytäkirjat (minutes) | `/pk_tek_tweb.htm` | Committee meeting minutes |
| Esityslistat (agendas) | `/epj_tek_tweb.htm` | Upcoming meeting agendas |
| Viranhaltijapäätökset | `/vparhaku_tweb.htm` | Officer decisions |
| Document download | `/fileshow?doctype=3&docid={ID}` | PDF attachments |
| Search | `/pk_tek_tweb.htm` (POST) | Full-text search in minutes |

## KTweb Auto-Discovery

Known URL patterns to try:

```
https://asiakirjat.{domain}/ktwebscr/kuullist_tweb.htm
https://{city}.tweb.fi/ktwebscr/kuullist_tweb.htm
https://www.{city}.fi/ktwebscr/kuullist_tweb.htm
https://{city}.ktweb.fi/ktwebscr/kuullist_tweb.htm
```

## Known Municipality Platforms (top 20 by population)

| Code | City | Pop. | Platform | Base URL | Status |
|------|------|------|----------|----------|--------|
| 91 | Helsinki | 670K | Ahjo | `paatokset.hel.fi` | Needs discovery (old API dead) |
| 49 | Espoo | 300K | Dynasty | TBD | Needs Playwright |
| 837 | Tampere | 250K | CaseM | `tampere.cloudnc.fi` | ✅ Working (Playwright) |
| 564 | Oulu | 210K | KTweb | `asiakirjat.ouka.fi/ktwebscr` | ✅ Working |
| 853 | Turku | 200K | Dynasty? | TBD | Needs discovery |
| 398 | Lahti | 120K | ? | TBD | Needs discovery |
| 179 | Jyväskylä | 145K | ? | TBD | Needs discovery |
| 694 | Riihimäki | 30K | KTweb? | TBD | Needs discovery |
| 609 | Pori | 84K | ? | TBD | Needs discovery |
| 405 | Lappeenranta | 73K | ? | TBD | Needs discovery |
| 297 | Kuopio | 123K | ? | TBD | Needs discovery |
| 698 | Rovaniemi | 65K | ? | TBD | Needs discovery |
| 529 | Naantali | 20K | KTweb | `asiakirjat.naantali.fi/ktwebscr`? | Needs verification |
| 444 | Lohja | 47K | ? | TBD | Needs discovery |
| 186 | Järvenpää | 45K | KTweb? | TBD | Needs discovery |
| 245 | Kerava | 40K | ? | TBD | Needs discovery |
| 734 | Salo | 52K | ? | TBD | Needs discovery |
| 106 | Hyvinkää | 47K | ? | TBD | Needs discovery |
| 638 | Porvoo | 50K | ? | TBD | Needs discovery |
| 286 | Kouvola | 80K | ? | TBD | Needs discovery |

## Kiinteistötunnus Format

Property identifiers from building permits link to MML:

```
564-4-9-1
 │   │ │ └─ Lot (tontti)
 │   │ └─── Block (kortteli)
 │   └───── Village/district (kylä/kaupunginosa)
 └───────── Municipality code

MML API format: zero-padded 14 digits
564-4-9-1 → 56400400090001
  3   3   4    4 digits
```

## Integration Identifiers

How sources link together:

```
Municipality code (564)
  ├── StatFin: "KU564"
  ├── Sotkanet: region code 564
  ├── Paavo: postcodes in municipality (90100, 90120, 90140...)
  ├── MML: kiinteistötunnus prefix "564-*"
  └── Hilma: buyer location filter

Y-tunnus (0185466-5)
  ├── PRH KREK: company details
  ├── PRH XBRL: financial statements
  ├── Hilma: contract awards (winner ID)
  └── KTweb: text search in decisions

Kiinteistötunnus (564-4-9-1)
  ├── MML: coordinates + lot polygon
  ├── KTweb kuulutukset: building permits
  └── Energiatodistus: linked via address

Postcode (90100)
  ├── Paavo: 100+ demographic variables
  ├── Energiatodistus: search by postcode
  └── Geographic clustering
```

## Probe Execution Order

For a full municipality snapshot:

```
1. DEMOGRAPHICS    → Paavo (postcode) + Sotkanet (municipality)
2. SAFETY          → StatFin crime + Sotkanet indicators
3. CORPORATE       → PRH companies at municipality + top employers
4. PROCUREMENT     → Hilma tenders + awards for municipality
5. MUNICIPAL       → KTweb/Dynasty kuulutukset + recent decisions
6. INFRASTRUCTURE  → Building permits + MML property register
7. ENVIRONMENT     → FMI weather + Digitraffic transport
8. EVENTS          → RSS feeds + Visit* sites
9. LEGAL           → Finlex court decisions mentioning municipality
```

## Adding a New Municipality: Checklist

```
□ Find municipality code (Wikipedia / StatFin)
□ Identify decision platform (Google "{city} pöytäkirjat")
□ Find KTweb/Dynasty base URL
□ Test kuulutukset endpoint
□ Find city RSS / events source
□ Create config/{code}.conf
□ Test: ./probes/municipality-kit.sh {code}
□ Add to municipalities.csv
```

## Scaling Considerations

- **309 municipalities** in Finland (2026)
- **~150** have some form of online decision archive
- **~50** use Triplan KTweb (easiest to automate)
- **~100** use Dynasty/CaseM (need Playwright)
- **~50** have PDF-only or no online system
- **Top 20 cities = 65% of population** — pragmatic starting point

---

## Platform Discovery Results (Aug 2026)

### Working Platforms

**KTweb (Triplan)** — plain curl, server-rendered:
| City | URL | Notes |
|------|-----|-------|
| Oulu | `asiakirjat.ouka.fi/ktwebscr/kuullist_tweb.htm` | Reference implementation |
| Hämeenlinna | `hameenlinna.tweb.fi/ktwebscr/kuullist_tweb.htm` | Rich: zoning, env, vehicles |
| Jyväskylä | `julkinen.jkl.fi/ktwebbin/dbisa.dll/ktwebscr/kuullist_tweb.htm` | Older ISAPI variant, empty default page |

**Dynasty (cloudnc/oncloudos)** — plain curl, server-rendered:
| City | URL | Notes |
|------|-----|-------|
| Pori | `pori.cloudnc.fi/fi-FI/Kuulutukset` | 12+ notices, wind power, env permits |
| Rovaniemi | `rovaniemi.cloudnc.fi/fi-FI/Kuulutukset` | 12+ notices, building permits, mining |

**Helsinki (Ahjo/Drupal)** — REST search:
| City | URL | Notes |
|------|-----|-------|
| Helsinki | `paatokset.hel.fi/fi/api/v1/search?q=TERM` | General search, not decision-specific |

### Working with Playwright

| City | Platform | Data Available |
|------|----------|----------------|
| Tampere | CaseM (Innofactor) | Toimielimet (30+ committees, valtuustoaloitteet), Viranhaltijat (officer decisions with dates/diary#) |

### Not Working / Needs Investigation

| City | Platform | Issue |
|------|----------|-------|
| Espoo | oncloudos | Page returns empty (may need session/cookie) |
| Kuopio | oncloudos | Same as Espoo |
| Vantaa | Dynasty | Redirects, not verified |
| Turku | Unknown (`ah.turku.fi`) | Returns empty on redirect |

### Key Technical Findings

1. **Dynasty is server-rendered** — no Playwright/JS needed. `curl` + `sed` works.
2. **KTweb has 2 variants**: standard (`/ktwebscr/`) and ISAPI (`/ktwebbin/dbisa.dll/ktwebscr/`)
3. **Hilma migrated** to OData: `GET /search/eformnotices?search=X&$top=N`
4. **Sotkanet** uses internal region IDs (not municipality codes). Must filter client-side.
5. **StatFin** variable codes change over time (versioned: `alue_23_20230101`)
6. **Helsinki** old Ahjo API dead. New Drupal site has general search only.
7. **CaseM (Tampere, HVAs)** is a full JS SPA — requires Playwright. Use `domcontentloaded` + 5s wait.

## Hyvinvointialue (Wellbeing County) Decision Platforms

Hyvinvointialueet are democratic entities with elected councils (aluevaltuusto),
executive boards (aluehallitus), and officer decisions (viranhaltijapäätökset).

### Discovered Platforms — ALL 22 HVAs

| HVA | Platform | URL | Method |
|-----|----------|-----|--------|
| Pohjois-Pohjanmaa (Pohde) | CaseM/cloudnc | `pohde.cloudnc.fi` | Playwright |
| Pirkanmaa (Pirha) | CaseM/cloudnc | `pirha.cloudnc.fi` | Playwright |
| Itä-Uusimaa | CaseM/cloudnc | `itauusimaa.cloudnc.fi` | Playwright |
| Satakunta | CaseM/cloudnc | `sata.cloudnc.fi` | Playwright |
| Vantaa-Kerava | CaseM/cloudnc | `vakehyva.cloudnc.fi` | Playwright |
| Kainuu | CaseM/cloudnc | `kainuunhyvinvointialue.cloudnc.fi` | Playwright |
| Keski-Uusimaa | CaseM/cloudnc | `keuh.cloudnc.fi` | Playwright |
| Varsinais-Suomi (Varha) | KTweb/Triplan | `varha-julkaisu.triplancloud.fi` | curl |
| Lappi (Lapha) | KTweb/Triplan | `lapinhva-julkaisu.triplancloud.fi` | curl |
| Kanta-Häme (Oma Häme) | KTweb + Dynasty | `omahame-julkaisu.tweb.fi` / `kantahameenhva.oncloudos.com` | curl |
| Päijät-Häme | KTweb | `phhyky-julkaisu.tweb.fi` | curl |
| Etelä-Pohjanmaa | KTweb | `hyvaep-julkaisu.tweb.fi` | curl |
| Kymenlaakso | KTweb | `julkaisut.kymenhva.fi:8443` | curl |
| Länsi-Uusimaa | Dynasty/DREQUEST | `luhva-d10julk.oncloudos.com` | curl |
| Keski-Suomi (Hyvaks) | Dynasty/DREQUEST | `hyvaks-d10julk.oncloudos.com` | curl |
| Keski-Pohjanmaa (Soite) | Dynasty/DREQUEST | `kpshp-hva.oncloudos.com` | curl |
| Etelä-Savo (Eloisa) | Dynasty/DREQUEST | `etela-savonhva.oncloudos.com` | curl |
| Pohjois-Savo | Dynasty/DREQUEST | `pshva.oncloudos.com` | curl |
| Pohjanmaa | Dynasty/DREQUEST | `ovph-d10julk.oncloudos.com` | curl |
| Pohjois-Karjala | Dynasty/DREQUEST | `dynastyjulkaisu.pohjoiskarjala.net` | curl |
| Etelä-Karjala | M-Files | `mfiles.ekhva.fi/Kokoukset/ekhva/` | curl |
| Helsinki | Drupal | `paatokset.hel.fi` | curl |

**Platform distribution**: CaseM (7) · KTweb (6) · Dynasty/DREQUEST (8) · M-Files (1) · Drupal (1)

### Available Data

- **Toimielimet**: Aluevaltuusto, Aluehallitus, lautakunnat, valiokunnat, jaostot
- **Viranhaltijat**: Officer decisions with dates, diary numbers (PPHVADno-YYYY-XXXXX), § numbers
- Decision types: procurement, hiring, service provider approvals, restructuring, policy

### Usage

```bash
node probes/casem-playwright-probe.js --city pohde --section viranhaltijat
node probes/casem-playwright-probe.js --city pirha --section toimielimet

# "agenda" drills into one board's most recent/upcoming meeting and extracts
# its § agenda items — works for any CaseM city/HVA, pass --organ with the
# board's URL segment as listed under Toimielimet (default: Aluehallitus)
node probes/casem-playwright-probe.js --city pohde --section agenda --organ Aluehallitus
node probes/casem-playwright-probe.js --city tampere --section agenda --organ Kaupunginhallitus
```

### Welfare Statistics (Sotkanet)

All 22 hyvinvointialueet have indicators in Sotkanet (231 Kela + THL indicators):
```bash
bash probes/regional-welfare-probe.sh 973  # Pohjois-Pohjanmaa
bash probes/regional-welfare-probe.sh 970  # Pirkanmaa
```
