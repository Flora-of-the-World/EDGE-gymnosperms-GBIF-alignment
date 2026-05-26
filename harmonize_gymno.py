"""
Harmonize the GBIF-resolved EDGE-gymnosperm table into the angio-compatible
deliverable format used by Flora of the World (FotW).

Single source: Gymnosperm_EDGE2_scores_2024.csv (Gumbs et al. 2024 EDGE2
gymnosperm scores — 1,083 species, ALL with EDGE2 metrics under the same
methodology as the flowering-plants release).

Input
-----
  edge_gymno_taxonomy_resolved.csv  — produced by resolve_edge_gymno_taxonomy.py.
                                      1,083 species, GBIF-resolved, with Family
                                      and Order captured from the GBIF response.

Output (single combined file)
-----------------------------
  edge_gymno_taxonomy_complete.csv
    All 1,083 EDGE rows from the 2024 list (record_type = "edge_original")
    + N new accepted-name rows for synonyms whose accepted binomial is NOT
      itself in the 2024 list (record_type = "gbif_accepted_new"). Mirrors
      build_edge_complete.py for angio.

Column-name harmonization (so FotW can use ONE import for both clades)
----------------------------------------------------------------------
  2024 source column   → angio-compatible name
  ------------------------------------------------------
  Species              → Species (with underscore: "Genus_epithet")
  RL.cat               → threat
  ED.median            → ed.med
  EDGE.median          → edge.med
  TBL.median           → tbl.med
  no.above.median      → above.med.tot       (out of 100 MCMC draws)
                       → above.med.perc      (no.above.median / 100)
                       → above.med           ("y" if ≥ 95, else "n")
  EDGE.species         → EDGE.List           ("y" if YES, else "n")
  (computed)           → EDGE.rank           (rank by edge.med descending)
  (from GBIF)          → Family, Order

Plus three administrative columns matching the angio deliverable:
  clade               — always "gymno"
  record_type         — "edge_original" | "gbif_accepted_new"
  synonym_edge_keys   — for new accepted rows, the EDGE keys that pointed here

Usage
-----
    python3 harmonize_gymno.py
"""

import csv
import os
import sys
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

BASE      = os.path.dirname(os.path.abspath(__file__))
IN_CSV    = os.path.join(BASE, "edge_gymno_taxonomy_resolved.csv")
OUT_FULL  = os.path.join(BASE, "edge_gymno_taxonomy_complete.csv")
OUT_NEW   = os.path.join(BASE, "edge_gymno_new_accepted_names.csv")

SYNONYM_STATUSES = {
    "SYNONYM", "HETEROTYPIC_SYNONYM", "HOMOTYPIC_SYNONYM",
    "PROPARTE_SYNONYM", "MISAPPLIED",
}

# Output schema — shared GBIF block first (matches angio + FotW), then
# angio-compatible EDGE block, then admin columns.

GBIF_FIELDS = [
    "taxonID", "scientificName", "genus", "specificEpithet",
    "infraspecificEpithet", "scientificNameID", "gbif_id",
    "lookup_method", "gbif_status", "gbif_confidence",
    "accepted_name", "accepted_gbif_id", "accepted_gbif_url", "error",
]

ANGIO_COMPAT_FIELDS = [
    "Species", "EDGE.rank", "Family", "Order",
    "edge.med", "ed.med", "tbl.med",
    "above.med.tot", "above.med.perc", "above.med",
    "threat", "EDGE.List",
]

OUT_FIELDS = (
    ["record_type", "clade"]
    + GBIF_FIELDS
    + ANGIO_COMPAT_FIELDS
    + ["synonym_edge_keys"]
)


def strip_q(s):
    return s.strip().strip('"') if s else ""


def harmonize_row(r, rank_by_key):
    """Build a harmonized output row from a resolved source row."""
    taxon = strip_q(r.get("Species", ""))
    species_underscored = taxon.replace(" ", "_")

    # Compute above.med fields from no.above.median (out of 100 MCMC draws)
    try:
        n_above = int(strip_q(r.get("no.above.median", "")))
    except ValueError:
        n_above = None
    if n_above is not None:
        above_tot  = str(n_above)
        above_perc = f"{n_above/100:.4f}"
        above_flag = "y" if n_above >= 95 else "n"
    else:
        above_tot = above_perc = above_flag = ""

    edge_list = "y" if strip_q(r.get("EDGE.species", "")).upper() == "YES" else "n"

    return {
        "record_type"        : "edge_original",
        "clade"              : "gymno",
        # GBIF block
        "taxonID"            : strip_q(r.get("taxonID", "")),
        "scientificName"     : strip_q(r.get("scientificName", "")),
        "genus"              : strip_q(r.get("genus", "")),
        "specificEpithet"    : strip_q(r.get("specificEpithet", "")),
        "infraspecificEpithet": "",
        "scientificNameID"   : "",
        "gbif_id"            : strip_q(r.get("gbif_id", "")),
        "lookup_method"      : strip_q(r.get("lookup_method", "")),
        "gbif_status"        : strip_q(r.get("gbif_status", "")),
        "gbif_confidence"    : strip_q(r.get("gbif_confidence", "")),
        "accepted_name"      : strip_q(r.get("accepted_name", "")),
        "accepted_gbif_id"   : strip_q(r.get("accepted_gbif_id", "")),
        "accepted_gbif_url"  : strip_q(r.get("accepted_gbif_url", "")),
        "error"              : strip_q(r.get("error", "")),
        # Angio-compatible EDGE block
        "Species"            : species_underscored,
        "EDGE.rank"          : str(rank_by_key.get(species_underscored, "")),
        "Family"             : strip_q(r.get("gbif_family", "")),
        "Order"              : strip_q(r.get("gbif_order", "")),
        "edge.med"           : strip_q(r.get("EDGE.median", "")),
        "ed.med"             : strip_q(r.get("ED.median", "")),
        "tbl.med"            : strip_q(r.get("TBL.median", "")),
        "above.med.tot"      : above_tot,
        "above.med.perc"     : above_perc,
        "above.med"          : above_flag,
        "threat"             : strip_q(r.get("RL.cat", "")),
        "EDGE.List"          : edge_list,
        "synonym_edge_keys"  : "",
    }


def compute_ranks(rows):
    """Compute EDGE.rank across all source species by edge.med descending."""
    ranked = []
    for r in rows:
        try:
            score = float(strip_q(r.get("EDGE.median", "")))
        except ValueError:
            continue
        key = strip_q(r.get("Species", "")).replace(" ", "_")
        ranked.append((score, key))
    ranked.sort(reverse=True)
    return {key: i+1 for i, (_, key) in enumerate(ranked)}


def build_new_accepted_rows(rows):
    """
    For SYNONYM rows whose accepted_name is NOT itself in the 2024 list,
    create new placeholder rows so the deliverable has one row per unique
    accepted GBIF taxon — mirrors build_edge_complete.py for angio.
    """
    edge_keys = {strip_q(r.get("taxonID", "")) for r in rows}
    new_accepted = {}
    synonym_links = defaultdict(list)

    for r in rows:
        status = strip_q(r.get("gbif_status", "")).upper()
        if status not in SYNONYM_STATUSES:
            continue
        acc_name = strip_q(r.get("accepted_name", ""))
        acc_id   = strip_q(r.get("accepted_gbif_id", ""))
        if not acc_name or not acc_id:
            continue
        parts = acc_name.split()
        if len(parts) < 2:
            continue
        acc_key = f"{parts[0]}_{parts[1]}"
        if acc_key in edge_keys:
            continue

        synonym_links[acc_id].append(strip_q(r.get("taxonID", "")))
        if acc_id in new_accepted:
            continue

        new_accepted[acc_id] = {
            "record_type"        : "gbif_accepted_new",
            "clade"              : "gymno",
            "taxonID"            : acc_key,
            "scientificName"     : acc_name,
            "genus"              : parts[0],
            "specificEpithet"    : parts[1],
            "infraspecificEpithet": "",
            "scientificNameID"   : "",
            "gbif_id"            : acc_id,
            "lookup_method"      : "inferred_from_synonym",
            "gbif_status"        : "ACCEPTED",
            "gbif_confidence"    : "",
            "accepted_name"      : acc_name,
            "accepted_gbif_id"   : acc_id,
            "accepted_gbif_url"  : strip_q(r.get("accepted_gbif_url", "")),
            "error"              : "",
            # EDGE scores blank — this species was not scored in the 2024 list
            "Species"            : acc_key,
            "EDGE.rank"          : "",
            "Family"             : strip_q(r.get("gbif_family", "")),
            "Order"              : strip_q(r.get("gbif_order", "")),
            "edge.med"           : "",
            "ed.med"             : "",
            "tbl.med"            : "",
            "above.med.tot"      : "",
            "above.med.perc"     : "",
            "above.med"          : "",
            "threat"             : "",
            "EDGE.List"          : "n",
            "synonym_edge_keys"  : "",
        }

    for acc_id, row in new_accepted.items():
        row["synonym_edge_keys"] = ";".join(synonym_links[acc_id])

    return list(new_accepted.values())


def main():
    print("Loading resolved EDGE table …")
    with open(IN_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    print(f"  {len(rows):,} rows")

    print("Computing EDGE ranks from edge.med …")
    rank_by_key = compute_ranks(rows)
    print(f"  Ranked {len(rank_by_key):,} species")

    print("Harmonizing rows …")
    harmonized = [harmonize_row(r, rank_by_key) for r in rows]
    n_priority = sum(1 for r in harmonized if r["EDGE.List"] == "y")
    print(f"  EDGE.List = y : {n_priority:,} of {len(harmonized):,}")

    print("Building new accepted-name rows from synonyms …")
    new_rows = build_new_accepted_rows(rows)
    print(f"  {len(new_rows):,} new rows added")

    all_rows = harmonized + new_rows

    print(f"Writing {os.path.basename(OUT_FULL)} …")
    with open(OUT_FULL, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    print(f"Writing {os.path.basename(OUT_NEW)} …")
    with open(OUT_NEW, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(new_rows)

    print()
    print("=" * 65)
    print(f"  Source species (2024 EDGE2)       : {len(rows):>5,}")
    print(f"  Priority species (EDGE.List = y)  : {n_priority:>5,}")
    print(f"  New accepted-name rows            : {len(new_rows):>5,}")
    print(f"  Combined total                    : {len(all_rows):>5,}")
    print("=" * 65)
    print(f"  Combined file : {OUT_FULL}")
    print(f"  New-only file : {OUT_NEW}")


if __name__ == "__main__":
    main()
