#!/usr/bin/env bash
# hilma-probe.sh — Hilma (hankintailmoitukset.fi) procurement notices probe
#
# Usage:
#   ./probes/hilma-probe.sh --level index [--cpv 48000000,72000000] [--top 50]
#   ./probes/hilma-probe.sh --level detail --items items.json
#
# Index: searches eForm notices by CPV codes
# Detail: fetches individual notice details (not yet available via public API)
#
# Output: JSON to stdout (common probe contract)
set -euo pipefail

LEVEL="index"
CPV_CODES="48000000,72000000"
TOP=50
ITEMS_FILE=""
FILTER_HVA=""
SEARCH=""
CATEGORY="hva"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --level) LEVEL="$2"; shift 2 ;;
        --cpv) CPV_CODES="$2"; shift 2 ;;
        --top) TOP="$2"; shift 2 ;;
        --items) ITEMS_FILE="$2"; shift 2 ;;
        --hva) FILTER_HVA="$2"; shift 2 ;;
        --search) SEARCH="$2"; shift 2 ;;
        --category) CATEGORY="$2"; shift 2 ;;
        -h|--help) echo "Usage: $0 --level index|detail [--cpv CODES] [--top N] [--search TERM] [--category hva|university|defence|border-guard|justice|immigration|all]"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

exec python3 - "$LEVEL" "$CPV_CODES" "$TOP" "$ITEMS_FILE" "$FILTER_HVA" "$SEARCH" "$CATEGORY" <<'PYEOF'
import sys, re, json, subprocess, time
from datetime import datetime, timezone
from urllib.parse import quote

level = sys.argv[1]
cpv_codes = sys.argv[2].split(',')
top = int(sys.argv[3])
items_file = sys.argv[4]
filter_hva = sys.argv[5]
search_term = sys.argv[6]
category = sys.argv[7] if len(sys.argv) > 7 else "hva"

BASE = "https://www.hankintailmoitukset.fi/search/eformnotices"

# Known HVA organization names for matching
HVA_ORGS = [
    "hyvinvointialue", "Pohde", "Pirha", "Varha", "Vantaan ja Keravan",
    "Itä-Uudenmaan", "Länsi-Uudenmaan", "Keski-Uudenmaan", "Keski-Suomen",
    "Pohjois-Savon", "Etelä-Savon", "Pohjois-Karjalan", "Pohjois-Pohjanmaan",
    "Kainuun", "Lapin", "Kanta-Hämeen", "Päijät-Hämeen", "Kymenlaakson",
    "Etelä-Karjalan", "Satakunnan", "Etelä-Pohjanmaan", "Pohjanmaan",
    "Keski-Pohjanmaan"
]

# Universities (yliopisto) and university-affiliated entities. Verified
# 2026-08 to appear under their own org names in Hilma's public feed
# (autonomous public-law corporations, not part of the HVA/ministry chain).
UNIVERSITY_ORGS = [
    "yliopisto", "Aalto-yliopisto", "Helsingin yliopisto", "Itä-Suomen yliopisto",
    "Jyväskylän yliopisto", "Lappeenrannan-Lahden teknillinen yliopisto",
    "Oulun yliopisto", "Tampereen korkeakoulusäätiö", "Turun yliopisto",
    "Vaasan yliopisto", "Åbo Akademi",
]

# Defence sector: Puolustusvoimat (Defence Forces) and its logistics/
# facilities entities. Verified 2026-08 — above-threshold notices are
# published in Hilma same as any other contracting authority.
DEFENCE_ORGS = [
    "Puolustusvoimat", "Puolustusvoimien logistiikkalaitos",
    "Puolustuskiinteistöt", "Puolustusministeriö", "Rajavartiolaitos",
]

# Border Guard sector: Rajavartiolaitos (Finnish Border Guard), a
# separate contracting authority from Puolustusvoimat despite being
# under the same Ministry of the Interior/Defence-adjacent remit.
# Verified 2026-08-12 — has its own above-threshold Hilma notices
# (confirmed via a direct search, e.g. EF-54360 "Kalliomurske", org
# nationalRegistrationNumber 0246003-5) that the "defence" category's
# hardcoded "puolustusvoimat" search keyword was silently missing.
BORDER_GUARD_ORGS = ["Rajavartiolaitos"]

# Justice / prisons / law-enforcement bodies verified live in Hilma
# during the 2026-08-12 justice-sector pass. Covers police, prisons,
# and prison healthcare; excludes courts, whose decisions are covered
# elsewhere and whose procurement footprint is less central here.
JUSTICE_ORGS = [
    "Poliisihallitus", "Rikosseuraamuslaitos", "Vankiterveydenhuollon yksikkö",
]

# Immigration sector: Maahanmuuttovirasto (Migri), verified live in Hilma
# during the 2026-08-12 immigration-sector pass (a "git-first" gh-search-
# code trial). Confirmed real above-threshold notices via direct search
# (e.g. EF-54342, "Maahanmuuttoviraston viesti- ja hälytysjärjestelmä").
IMMIGRATION_ORGS = ["Maahanmuuttovirasto"]

CATEGORY_ORGS = {
    "hva": HVA_ORGS,
    "university": UNIVERSITY_ORGS,
    "defence": DEFENCE_ORGS,
    "border-guard": BORDER_GUARD_ORGS,
    "justice": JUSTICE_ORGS,
    "immigration": IMMIGRATION_ORGS,
    "all": HVA_ORGS + UNIVERSITY_ORGS + DEFENCE_ORGS + JUSTICE_ORGS + IMMIGRATION_ORGS,
}

def curl_fetch(url):
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "20", url],
                           capture_output=True, timeout=25)
        return r.stdout.decode("utf-8", errors="replace")
    except:
        return ""

def is_hva(org_name):
    if not org_name:
        return False
    orgs = CATEGORY_ORGS.get(category, HVA_ORGS)
    return any(h.lower() in org_name.lower() for h in orgs)

# ═══════════════════════════════════════════════════════════════
# INDEX MODE
# ═══════════════════════════════════════════════════════════════
if level == "index":
    items = []
    errors = []
    t0 = time.time()

    CATEGORY_KEYWORDS = {
        "hva": "hyvinvointialue",
        "university": "yliopisto",
        "defence": "puolustusvoimat",
        "border-guard": "rajavartiolaitos",
        "justice": "",
        "immigration": "maahanmuuttovirasto",
        "all": "hyvinvointialue",
    }

    for cpv in cpv_codes:
        keyword = CATEGORY_KEYWORDS.get(category, 'hyvinvointialue')
        search = cpv if not keyword else f"{keyword} {cpv}"
        if search_term:
            search = search_term
        url = f"{BASE}?search={quote(search)}&queryType=full&$top={top}&$orderby=datePublished+desc"

        raw = curl_fetch(url)
        if not raw:
            errors.append({"cpv": cpv, "error": "fetch failed"})
            continue

        try:
            data = json.loads(raw)
        except:
            errors.append({"cpv": cpv, "error": "invalid JSON response"})
            continue

        notices = data.get("value", [])
        for n in notices:
            org = n.get("organisationNameFi", "") or n.get("organisationNameEn", "")

            # Filter to HVA-related only (unless custom search)
            if not search_term and not is_hva(org):
                continue

            # Filter by specific HVA if requested
            if filter_hva and filter_hva.lower() not in org.lower():
                continue

            notice_id = n.get("id", "")
            notice_num_id = n.get("noticeId", "")
            procedure_id = n.get("procedureId", "")
            title = n.get("titleFi", "") or n.get("titleEn", "")
            pub_date = n.get("datePublished", "")[:10]
            deadline = n.get("deadline", "")
            notice_type = n.get("type", "")
            proc_url = n.get("procurementDocumentsUrl", "")

            # Hilma's SPA only resolves notice detail pages via the
            # /fi/public/procedure/{procedureId}/enotice/{noticeId}/ path;
            # /fi/notice/{id} and /fi/notice/-/notice/{num} silently redirect
            # to the homepage (verified 2026-08-11).
            if procedure_id and notice_num_id:
                detail_url = f"https://www.hankintailmoitukset.fi/fi/public/procedure/{procedure_id}/enotice/{notice_num_id}/"
            else:
                detail_url = f"https://www.hankintailmoitukset.fi/fi/search?search={quote(notice_id)}"

            item_id = f"hilma-{notice_id}"
            items.append({
                "id": item_id,
                "hva": org,
                "board": None,
                "meeting_date": pub_date,
                "meeting_type": "hankintailmoitus",
                "section": None,
                "title": title,
                "detail_url": detail_url,
                "source_url": url,
                "notice_type": notice_type,
                "deadline": deadline,
                "procurement_docs_url": proc_url,
                "cpv_codes": n.get("cpvCodes", ""),
                "procedure_type": n.get("procedureType", ""),
            })

    # Deduplicate by notice_id
    seen = set()
    deduped = []
    for item in items:
        if item["id"] not in seen:
            seen.add(item["id"])
            deduped.append(item)

    stats = {
        "cpv_codes_searched": len(cpv_codes),
        "items_total": len(deduped),
        "duration_ms": int((time.time() - t0) * 1000)
    }

    output = {
        "source": "hilma", "level": "index", "version": "1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "hvas": [],
        "config": {"cpv_codes": cpv_codes, "top": top, "category": category},
        "items": deduped, "errors": errors, "stats": stats
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════════════
# DETAIL MODE (limited — Hilma doesn't expose full text via public API)
# ═══════════════════════════════════════════════════════════════
elif level == "detail":
    # Hilma detail pages are rendered client-side (Vue SPA)
    # Can only provide the public URL for manual inspection
    if not items_file:
        json.dump({"error": "detail mode requires --items <file.json>"}, sys.stderr)
        sys.exit(1)

    with open(items_file) as f:
        to_fetch = json.load(f)

    results = []
    for item in to_fetch:
        results.append({
            "id": item.get("id", ""),
            "body": f"Hilma notice - view at {item.get('detail_url', '')}",
            "decision": "",
            "preparer": "",
            "docket": "",
            "procurement_docs_url": item.get("procurement_docs_url", ""),
            "note": "Hilma is a Vue SPA; full text requires browser rendering or TED API"
        })

    output = {
        "source": "hilma", "level": "detail", "version": "1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": results, "errors": [],
        "stats": {"items_requested": len(to_fetch), "items_succeeded": len(results),
                  "duration_ms": 0}
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

else:
    json.dump({"error": f"Unknown level: {level}"}, sys.stderr)
    sys.exit(1)
PYEOF
