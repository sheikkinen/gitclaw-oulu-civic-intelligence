#!/usr/bin/env bash
# ktweb-probe.sh — Two-level KTweb probe (index + detail)
#
# Usage:
#   ./probes/ktweb-probe.sh --level index [--depth 5] [--hva Lappi]
#   ./probes/ktweb-probe.sh --level detail --items items.json
#
# Index: lists all § items from recent meetings (via RSS + meeting page drill-down)
# Detail: fetches full memo text from fileshow URLs, collapses KTweb anti-copy spacing
#
# Output: JSON to stdout (common probe contract)
set -euo pipefail

LEVEL="index"
DEPTH=5
ITEMS_FILE=""
TIMEOUT=15
FILTER_HVA=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --level) LEVEL="$2"; shift 2 ;;
        --depth) DEPTH="$2"; shift 2 ;;
        --items) ITEMS_FILE="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --hva) FILTER_HVA="$2"; shift 2 ;;
        -h|--help) echo "Usage: $0 --level index|detail [--depth N] [--hva NAME] [--items FILE]"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

exec python3 - "$LEVEL" "$DEPTH" "$TIMEOUT" "$ITEMS_FILE" "$FILTER_HVA" <<'PYEOF'
import sys, re, json, subprocess, time
from datetime import datetime, timezone

level, depth, timeout, items_file, filter_hva = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]

INSTANCES = [
    ("Varha", "https://varha-julkaisu.triplancloud.fi"),
    ("Lappi", "https://lapinhva-julkaisu.triplancloud.fi"),
    ("Kanta-Häme", "https://omahame-julkaisu.tweb.fi"),
    ("Päijät-Häme", "https://phhyky-julkaisu.tweb.fi"),
    ("Etelä-Pohjanmaa", "https://hyvaep-julkaisu.tweb.fi"),
    ("Kymenlaakso", "https://julkaisut.kymenhva.fi:8443"),
    ("HUS-yhtymä", "https://hus-julkaisu.tweb.fi"),
]

def curl_fetch(url, t=None, strip_nulls=False):
    try:
        r = subprocess.run(["curl", "-s", "--max-time", str(t or timeout), url],
                           capture_output=True, timeout=(t or timeout) + 5)
        raw = r.stdout
        # KTweb detail pages are UTF-16-LE without BOM (null bytes between ASCII chars)
        if strip_nulls:
            raw = raw.replace(b'\x00', b'')
        try: return raw.decode("utf-8")
        except: return raw.decode("windows-1252", errors="replace")
    except:
        return ""

# ═══════════════════════════════════════════════════════════════
# INDEX MODE
# ═══════════════════════════════════════════════════════════════
if level == "index":
    instances = INSTANCES
    if filter_hva:
        instances = [(n, u) for n, u in instances if filter_hva.lower() in n.lower()]

    items = []
    errors = []
    stats = {"hvas_attempted": len(instances), "hvas_succeeded": 0, "items_total": 0}
    t0 = time.time()

    for hva_name, base_url in instances:
        try:
            rss = curl_fetch(f"{base_url}/ktwebscr/pk_rssfeed.htm")
            if not rss:
                errors.append({"hva": hva_name, "error": "RSS fetch failed"})
                continue

            meeting_links = re.findall(r'<link>([^<]*pk_asil[^<]*)</link>', rss)[:depth]
            if not meeting_links:
                errors.append({"hva": hva_name, "error": "No meeting links in RSS"})
                continue

            hva_count = 0
            for meeting_url in meeting_links:
                page = curl_fetch(meeting_url)
                if not page:
                    continue

                # Extract date from page
                meeting_date = None
                dm = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', page)
                if dm:
                    d, m, y = dm.groups()
                    meeting_date = f"{y}-{int(m):02d}-{int(d):02d}"

                # Extract board from <title>
                tm = re.search(r'<title>([^<]+)</title>', page)
                board = tm.group(1).split(':')[0].strip() if tm else "Tuntematon"

                # Extract numbered items: <td>NNN</td><td><a href="...">Title</a>
                numbered = re.findall(
                    r'<td[^>]*>\s*(\d+)\s*</td>\s*<td[^>]*>\s*<a\s+href="([^"]*)"[^>]*>([^<]+)</a>',
                    page, re.DOTALL
                )
                for num, href, title in numbered:
                    title = title.strip()
                    if len(title) < 5:
                        continue
                    # Build detail URL
                    detail_url = ""
                    if href:
                        if href.startswith("http"):
                            detail_url = href
                        elif href.startswith("/"):
                            detail_url = base_url + href
                        else:
                            detail_url = base_url + "/ktwebscr/" + href
                    
                    slug = re.sub(r'[^a-z0-9]', '-', hva_name.lower().replace('ä','a').replace('ö','o'))
                    item_id = f"ktweb-{slug}-{meeting_date or 'unknown'}-{num}"

                    items.append({
                        "id": item_id,
                        "hva": hva_name,
                        "board": board,
                        "meeting_date": meeting_date,
                        "meeting_type": "pöytäkirja",
                        "section": int(num),
                        "title": title,
                        "detail_url": detail_url,
                        "source_url": meeting_url
                    })
                    hva_count += 1

            if hva_count > 0:
                stats["hvas_succeeded"] += 1
            stats["items_total"] += hva_count

        except Exception as e:
            errors.append({"hva": hva_name, "error": str(e)})

    stats["duration_ms"] = int((time.time() - t0) * 1000)
    output = {
        "source": "ktweb", "level": "index", "version": "1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "hvas": [n for n, _ in instances],
        "config": {"depth": depth},
        "items": items, "errors": errors, "stats": stats
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════════════
# DETAIL MODE
# ═══════════════════════════════════════════════════════════════
elif level == "detail":
    if not items_file:
        json.dump({"error": "detail mode requires --items <file.json>"}, sys.stderr)
        sys.exit(1)

    with open(items_file) as f:
        to_fetch = json.load(f)

    results = []
    errs = []
    t0 = time.time()

    for item in to_fetch:
        item_id = item.get("id", "")
        url = item.get("detail_url", "")
        if not url:
            errs.append({"id": item_id, "error": "no detail_url"})
            continue

        html = curl_fetch(url, strip_nulls=True)
        if not html:
            errs.append({"id": item_id, "error": "fetch failed"})
            continue

        # Strip HTML → plain text
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'</(h[12345]|p|li|ol|ul|div|header)>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&sect;', '§').replace('&auml;', 'ä').replace('&ouml;', 'ö')
        text = text.replace('&Auml;', 'Ä').replace('&Ouml;', 'Ö').replace('&amp;', '&')
        text = text.replace('&nbsp;', ' ')

        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text).strip()

        # Extract structured fields
        result = {"id": item_id, "body": "", "decision": "", "preparer": "",
                  "docket": "", "previous_handling": [], "attachments": []}

        # Docket
        dm = re.search(r'([A-ZÄÖ]{2,10}(?:Dno)?[-/]\d{4}[-/][\d.]+(?:/\d+)?)', text)
        if dm:
            result["docket"] = dm.group(1)

        # Split by headings
        sections = re.split(
            r'\n(Asiaselostus|Päätösehdotus|Päätös|Valmistelija|Aikaisemmat käsittelyvaiheet|Liitteet|Lisätietoja|Tiivistelmä)\s*\n',
            text
        )
        for i in range(1, len(sections)-1, 2):
            heading = sections[i].strip()
            content = sections[i+1].strip()[:2000]
            if heading == "Asiaselostus":
                result["body"] = content
            elif heading == "Päätös":
                result["decision"] = content
            elif heading == "Valmistelija":
                result["preparer"] = content.split('\n')[0].strip()
            elif heading == "Aikaisemmat käsittelyvaiheet":
                refs = re.findall(r'[A-Za-zäöÄÖ\s-]+\d{1,2}\.\d{1,2}\.\d{4}\s*§?\s*\d+', content)
                result["previous_handling"] = [r.strip() for r in refs[:10]]
            elif heading == "Liitteet":
                result["attachments"] = [a.strip() for a in content.split('\n') if a.strip() and len(a.strip()) > 3][:20]

        if not result["body"] and len(text) > 50:
            result["body"] = text[:2000]

        results.append(result)

    output = {
        "source": "ktweb", "level": "detail", "version": "1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": results, "errors": errs,
        "stats": {"items_requested": len(to_fetch), "items_succeeded": len(results),
                  "duration_ms": int((time.time() - t0) * 1000)}
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)

else:
    json.dump({"error": f"Unknown level: {level}"}, sys.stderr)
    sys.exit(1)
PYEOF
