#!/usr/bin/env bash
# digitraffic-marine-probe.sh — Finnish harbour vessel traffic (Fintraffic Digitraffic Marine)
#
# Answers "when is the next ship arriving at port X, and what cargo/vessel type"
# (acceptance-test Q3, docs/acceptance-test-questions.md) using Fintraffic's
# public, no-auth Port Call API. Unlike education/defence governance data,
# this is a live, structured, real-time operational feed — the easiest source
# in the toolkit's acceptance-test set.
#
# Source: https://meri.digitraffic.fi/api/port-call/v1/port-calls
# Auth: none. Requires gzip-compressed responses (curl --compressed).
#
# Usage:
#   ./probes/digitraffic-marine-probe.sh --level index --locode FIOUL [--top 20]
#   ./probes/digitraffic-marine-probe.sh --level detail --items items.json
#
# Index: fetches all known port calls for a LOCODE (UN/LOCODE, e.g. FIOUL =
#        Oulu, FIHEL = Helsinki, FIKOK = Kokkola), sorted by earliest berth
#        ETA, and flags whether each call is upcoming (ETA in the future) or
#        already in progress/past.
# Detail: re-fetches the same feed and returns the full raw record for the
#         requested portCallId(s) — Digitraffic doesn't expose a single-call
#         lookup endpoint, so detail mode re-filters the index response.
#
# Cargo caveat: exact commodity/customs manifest is not public. Vessel type
# code, IMO cargo-declaration flags, and discharge counts give strong
# inference (e.g. vesselTypeCode 80 = tanker) but not a named commodity.
#
# Output: JSON to stdout (common probe contract, same envelope shape as
# hilma-probe.sh / ted-probe.sh)
set -euo pipefail

LEVEL="index"
LOCODE="FIOUL"
TOP=20
ITEMS_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --level) LEVEL="$2"; shift 2 ;;
        --locode) LOCODE="$2"; shift 2 ;;
        --top) TOP="$2"; shift 2 ;;
        --items) ITEMS_FILE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 --level index|detail --locode FIOUL [--top N] [--items file.json]"
            exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

exec python3 - "$LEVEL" "$LOCODE" "$TOP" "$ITEMS_FILE" <<'PYEOF'
import sys, json, subprocess, time
from datetime import datetime, timezone
from urllib.parse import quote

level = sys.argv[1]
locode = sys.argv[2]
top = int(sys.argv[3])
items_file = sys.argv[4]

BASE = "https://meri.digitraffic.fi/api/port-call/v1/port-calls"

# Vessel type codes (subset, per IMO/Digitraffic convention) for cargo inference
VESSEL_TYPE_HINTS = {
    70: "cargo ship (general)",
    71: "cargo ship (hazardous category A)",
    79: "cargo ship (other)",
    80: "tanker",
    89: "tanker (other)",
}

def curl_fetch(url):
    try:
        r = subprocess.run(["curl", "-s", "--compressed", "--max-time", "20", url],
                           capture_output=True, timeout=25)
        return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""

def earliest_eta(port_call):
    etas = [a.get("eta") for a in port_call.get("portAreaDetails", []) if a.get("eta")]
    return min(etas) if etas else None

def to_item(pc):
    eta = earliest_eta(pc)
    now_iso = datetime.now(timezone.utc).isoformat()
    upcoming = bool(eta and eta > now_iso)
    vessel_type = pc.get("vesselTypeCode")
    return {
        "id": f"digitraffic-marine-{pc.get('portCallId')}",
        "hva": None,
        "board": None,
        "meeting_date": eta,
        "meeting_type": "port_call",
        "section": None,
        "title": f"{pc.get('vesselName', '?')} ({pc.get('prevPort','?')} -> {pc.get('nextPort','?')})",
        "detail_url": f"{BASE}?locode={quote(locode)}",
        "source_url": f"{BASE}?locode={quote(locode)}",
        "vessel_name": pc.get("vesselName"),
        "imo_lloyds": pc.get("imoLloyds"),
        "mmsi": pc.get("mmsi"),
        "nationality": pc.get("nationality"),
        "prev_port": pc.get("prevPort"),
        "next_port": pc.get("nextPort"),
        "vessel_type_code": vessel_type,
        "vessel_type_hint": VESSEL_TYPE_HINTS.get(vessel_type, "unknown — see IMO vessel type code table"),
        "arrival_with_cargo": pc.get("arrivalWithCargo"),
        "eta": eta,
        "port_area_details": pc.get("portAreaDetails", []),
        "upcoming": upcoming,
    }

# ═══════════════════════════════════════════════════════════════
# INDEX MODE
# ═══════════════════════════════════════════════════════════════
if level == "index":
    t0 = time.time()
    errors = []
    url = f"{BASE}?locode={quote(locode)}"
    raw = curl_fetch(url)

    if not raw:
        errors.append({"locode": locode, "error": "fetch failed"})
        data = {"portCalls": []}
    else:
        try:
            data = json.loads(raw)
        except Exception:
            errors.append({"locode": locode, "error": "invalid JSON response"})
            data = {"portCalls": []}

    port_calls = data.get("portCalls", [])
    items = [to_item(pc) for pc in port_calls]

    # Sort by ETA ascending (soonest first); calls with no ETA sort last.
    items.sort(key=lambda i: (i["eta"] is None, i["eta"] or ""))
    items = items[:top]

    stats = {
        "locode": locode,
        "items_total": len(items),
        "upcoming_count": sum(1 for i in items if i["upcoming"]),
        "duration_ms": int((time.time() - t0) * 1000),
    }

    output = {
        "source": "digitraffic-marine", "level": "index", "version": "1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "hvas": [],
        "config": {"locode": locode, "top": top},
        "items": items, "errors": errors, "stats": stats,
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════════════
# DETAIL MODE (re-fetch + filter, no dedicated per-call endpoint exists)
# ═══════════════════════════════════════════════════════════════
elif level == "detail":
    if not items_file:
        json.dump({"error": "detail mode requires --items <file.json>"}, sys.stderr)
        sys.exit(1)

    with open(items_file) as f:
        to_fetch = json.load(f)
    wanted_ids = {str(item.get("id", "")).replace("digitraffic-marine-", "") for item in to_fetch}

    url = f"{BASE}?locode={quote(locode)}"
    raw = curl_fetch(url)
    try:
        data = json.loads(raw) if raw else {"portCalls": []}
    except Exception:
        data = {"portCalls": []}

    results = []
    for pc in data.get("portCalls", []):
        if str(pc.get("portCallId")) in wanted_ids:
            item = to_item(pc)
            item["raw"] = pc
            results.append(item)

    output = {
        "source": "digitraffic-marine", "level": "detail", "version": "1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": results, "errors": [],
        "stats": {"items_requested": len(to_fetch), "items_succeeded": len(results),
                  "duration_ms": 0},
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

else:
    json.dump({"error": f"unknown level: {level}"}, sys.stderr)
    sys.exit(1)
PYEOF
