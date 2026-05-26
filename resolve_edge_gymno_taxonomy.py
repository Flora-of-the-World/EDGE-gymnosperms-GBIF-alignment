"""
Resolve taxonomic status of EDGE gymnosperm species against the GBIF backbone.

For each species in Gymnosperm_EDGE2_scores_2024.csv (Gumbs et al. 2024 EDGE2
gymnosperm scores — 1,083 species, all with EDGE2 metrics):
  Query /v1/species/match?kingdom=Plantae&name=Genus epithet

Mirrors EDGE_flowering_plants/resolve_edge_taxonomy.py so the GBIF-derived
columns are identical and the resolved gymnosperm table can be joined with
fotw_taxonomy_resolved.csv (and the angiosperm table) on `accepted_gbif_id`.

In addition to the standard 14 GBIF-derived columns, this resolver also
captures `family` and `order` from the GBIF response (the source EDGE file
does not carry them).

Output columns (edge_gymno_taxonomy_resolved.csv)
-------------------------------------------------
GBIF-derived block (14 cols, identical names/order to fotw_taxonomy_resolved.csv
and edge_taxonomy_resolved.csv):
  taxonID              — Genus_epithet derived from EDGE Species
  scientificName       — EDGE binomial (space-separated)
  genus                — first token of Species
  specificEpithet      — second token of Species
  infraspecificEpithet — blank
  scientificNameID     — blank
  gbif_id              — blank (discovered via match)
  lookup_method        — always "name_match"
  gbif_status          — ACCEPTED | SYNONYM | DOUBTFUL | NO_MATCH | ERROR
  gbif_confidence      — confidence score from /species/match
  accepted_name        — accepted binomial
  accepted_gbif_id     — GBIF species key of accepted name
  accepted_gbif_url    — https://gbif.org/species/{accepted_gbif_id}
  error                — error message if any

Plus two columns derived from the GBIF response (kept here so downstream
joins have higher taxonomy without an extra lookup):
  gbif_family          — family per GBIF backbone
  gbif_order           — order per GBIF backbone

EDGE-source block (verbatim from Gymnosperm_EDGE2_scores_2024.csv):
  Species, RL.cat, TBL.median, ED.median, EDGE.median,
  no.above.median, EDGE.species

Usage
-----
    python3 resolve_edge_gymno_taxonomy.py
    python3 resolve_edge_gymno_taxonomy.py --workers 12 --delay 0.25

The script is resumable: already-resolved taxonIDs are skipped on re-run.
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

csv.field_size_limit(sys.maxsize)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE     = os.path.dirname(os.path.abspath(__file__))
EDGE_CSV = os.path.join(BASE, "Gymnosperm_EDGE2_scores_2024.csv")
OUT_CSV  = os.path.join(BASE, "edge_gymno_taxonomy_resolved.csv")

GBIF_MATCH_URL = (
    "https://api.gbif.org/v1/species/match"
    "?kingdom=Plantae&verbose=false&name={name}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; EDGE-FotW-research-bot/1.0; "
        "Boise State University; contact: sven.buerki@boisestate.edu)"
    ),
    "Accept": "application/json",
}

GBIF_FIELDS = [
    "taxonID", "scientificName", "genus", "specificEpithet",
    "infraspecificEpithet", "scientificNameID", "gbif_id",
    "lookup_method", "gbif_status", "gbif_confidence",
    "accepted_name", "accepted_gbif_id", "accepted_gbif_url", "error",
    "gbif_family", "gbif_order",
]

EDGE_FIELDS = [
    "Species", "RL.cat", "TBL.median", "ED.median", "EDGE.median",
    "no.above.median", "EDGE.species",
]

OUT_FIELDS = GBIF_FIELDS + EDGE_FIELDS


def fetch_url(url):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve_by_name(name):
    """
    Name-match via /v1/species/match.
    Returns (gbif_status, gbif_confidence, accepted_name, accepted_gbif_id,
             family, order, error).
    """
    url = GBIF_MATCH_URL.format(name=name.replace(" ", "%20"))
    try:
        data = fetch_url(url)
    except (HTTPError, URLError, Exception) as exc:
        return "ERROR", "", "", "", "", "", str(exc)

    if data.get("matchType") == "NONE":
        return "NO_MATCH", "0", "", "", "", "", ""

    status     = data.get("status", "").upper()
    confidence = str(data.get("confidence", ""))
    usage_key  = str(data.get("usageKey", ""))

    species_full = data.get("species", "")
    parts = species_full.split()
    accepted_name = f"{parts[0]} {parts[1]}" if len(parts) >= 2 else species_full

    accepted_key = str(data.get("acceptedUsageKey", "")) or usage_key
    family = data.get("family", "") or ""
    order  = data.get("order", "") or ""
    return status, confidence, accepted_name, accepted_key, family, order, ""


def load_edge(edge_csv):
    with open(edge_csv, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_done(out_csv):
    done = set()
    if os.path.exists(out_csv):
        with open(out_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done.add(row["taxonID"])
    return done


def strip_q(s):
    return s.strip().strip('"') if s else ""


def resolve_one(row, delay):
    time.sleep(delay)

    sci_name = strip_q(row.get("Species", ""))
    edge_key = sci_name.replace(" ", "_")
    parts    = sci_name.split()
    genus    = parts[0] if parts else ""
    epithet  = parts[1] if len(parts) >= 2 else ""

    status, conf, acc_name, acc_id, family, order, err = resolve_by_name(sci_name)
    acc_url = f"https://gbif.org/species/{acc_id}" if acc_id else ""

    out = {
        "taxonID"             : edge_key,
        "scientificName"      : sci_name,
        "genus"               : genus,
        "specificEpithet"     : epithet,
        "infraspecificEpithet": "",
        "scientificNameID"    : "",
        "gbif_id"             : "",
        "lookup_method"       : "name_match",
        "gbif_status"         : status,
        "gbif_confidence"     : conf,
        "accepted_name"       : acc_name,
        "accepted_gbif_id"    : acc_id,
        "accepted_gbif_url"   : acc_url,
        "error"               : err,
        "gbif_family"         : family,
        "gbif_order"          : order,
    }
    for col in EDGE_FIELDS:
        out[col] = strip_q(row.get(col, ""))
    return out


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--workers", type=int, default=8,
                        help="Concurrent workers (default: 8)")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Pause per worker between requests (default: 0.3s)")
    parser.add_argument("--min-conf", type=int, default=80,
                        help="Min confidence to count as a 'good' name match (default: 80)")
    args = parser.parse_args()

    print("Loading EDGE gymnosperm table …")
    rows = load_edge(EDGE_CSV)
    print(f"  {len(rows):,} rows")

    print("Checking for previous run …")
    done_keys = load_done(OUT_CSV)
    todo = [r for r in rows
            if strip_q(r.get("Species", "")).replace(" ", "_") not in done_keys]
    print(f"  Already resolved: {len(done_keys):,}  |  Remaining: {len(todo):,}")

    est_min = len(todo) * args.delay / max(args.workers, 1) / 60
    print(f"  Estimated time: ~{est_min:.1f} min "
          f"({args.workers} workers, {args.delay}s delay)\n")

    is_new = not os.path.exists(OUT_CSV)
    out_fh = open(OUT_CSV, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_fh, fieldnames=OUT_FIELDS)
    if is_new:
        writer.writeheader()

    total = len(todo)
    done = errors = synonyms = no_match = low_conf_hits = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(resolve_one, row, args.delay): row for row in todo}

        for future in as_completed(futures):
            result = future.result()
            done += 1

            if result["error"]:
                errors += 1
            if result["gbif_status"] == "SYNONYM":
                synonyms += 1
            if result["gbif_status"] == "NO_MATCH":
                no_match += 1

            conf = result["gbif_confidence"]
            low_conf = (conf != "" and conf.isdigit() and int(conf) < args.min_conf
                        and result["gbif_status"] not in ("NO_MATCH", "ERROR"))
            if low_conf:
                low_conf_hits += 1

            writer.writerow(result)
            out_fh.flush()

            elapsed = time.time() - t0
            rate    = done / elapsed if elapsed else 0
            eta     = (total - done) / rate if rate else 0
            flag = (" [LOW]" if low_conf else
                    " [SYN]" if result["gbif_status"] == "SYNONYM" else
                    " [NM]"  if result["gbif_status"] == "NO_MATCH" else "")
            name_disp = result["scientificName"][:38]
            print(
                f"  [{done:>5}/{total}]  {name_disp:<40}  "
                f"{result['gbif_status']:<10}{flag}  |  ETA {eta/60:.1f}min",
                end="\r", flush=True,
            )

    out_fh.close()

    print(f"\n\n{'='*65}")
    print("Done.")
    print(f"  Resolved this run : {done:,}")
    print(f"  Synonyms          : {synonyms:,}")
    print(f"  No-match          : {no_match:,}")
    print(f"  Low-confidence    : {low_conf_hits:,}")
    print(f"  Errors            : {errors:,}")
    print(f"  Output file       : {OUT_CSV}")

    status_counts = Counter()
    with open(OUT_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            status_counts[row["gbif_status"]] += 1
    print("\nCumulative status breakdown:")
    for status, count in status_counts.most_common():
        print(f"  {status:<12} {count:>7,}")


if __name__ == "__main__":
    main()
