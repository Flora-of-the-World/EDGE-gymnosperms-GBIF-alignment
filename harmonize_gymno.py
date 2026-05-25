"""
Harmonize the EDGE-gymnosperm GBIF resolution into the angio-compatible
deliverable format used by Flora of the World (FotW).

Inputs
------
  edge_gymno_taxonomy_resolved.csv             — 2018 paper, 1,090 species,
                                                 GBIF-resolved (raw source).
  EDGE2024_gymnosperms_top_list_resolved.csv   — 2024 EDGE priority list,
                                                 258 species, GBIF-resolved.
                                                 Adds current IUCN categories,
                                                 EDGE2 scores, common names,
                                                 distribution.

Output (single combined file)
-----------------------------
  edge_gymno_taxonomy_complete.csv
    All 1,090 EDGE rows from 2018 (record_type = "edge_original")
    + N new accepted-name rows for synonyms whose accepted binomial is NOT
      itself in the 2018 list (record_type = "gbif_accepted_new"), mirroring
      build_edge_complete.py for the angio pipeline.

Column-name harmonization (so FotW can use ONE import for both clades)
----------------------------------------------------------------------
  2018 column            → angio-compatible name
  ------------------------------------------------------------
  Taxon                  → Species          (with underscore: "Genus_epithet")
  IUCN categories        → threat
  Median ED scores       → ed.med
  EDGE IUCN50 scores     → edge.med
  Rank EDGE IUCN50       → EDGE.rank

Columns preserved from 2018 with non-angio names (no angio equivalent):
  ED.SD, ED.rank (= Rank ED), EDGE.ISAAC, EDGE.ISAAC.rank

Columns added from the 2024 EDGE list (populated only for the 258 priority
species; blank for the other 832):
  EDGE.List           — "y"/"n"; mirrors angio's EDGE.List
  Family, Order       — taxonomic placement (2018 paper omitted these)
  Class               — gymnosperm class (e.g., PINOPSIDA)
  common_name         — vernacular name
  tbl.med             — terminal branch length (median, Myr) from EDGE2 model
  edge2.med           — EDGE2 median score (Gumbs et al. 2023 methodology)
  EDGE2.rank          — global EDGE2 rank for gymnosperms
  threat_2024         — current IUCN Red List category (may differ from 2018)
  distribution_code   — ISO 3166-1 alpha-2 country code(s)
  distribution_name   — country name(s)
  red_list_id         — IUCN Red List taxon ID

Plus three administrative columns:
  clade               — always "gymno"
  record_type         — "edge_original" | "gbif_accepted_new"
  synonym_edge_keys   — for new accepted rows, the EDGE keys that pointed here

Three manual taxonomic overrides handle GBIF genus splits that disconnect
2018 names from current 2024 names but refer to the same biological species:
  Cupressus vietnamensis (2018) ↔ Xanthocyparis vietnamensis (2024)
  Cupressus goveniana    (2018) ↔ Hesperocyparis goveniana    (2024)
  Cupressus guadalupensis(2018) ↔ Hesperocyparis guadalupensis(2024)

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
IN_2018   = os.path.join(BASE, "edge_gymno_taxonomy_resolved.csv")
IN_2024   = os.path.join(BASE, "EDGE2024_gymnosperms_top_list_resolved.csv")
OUT_FULL  = os.path.join(BASE, "edge_gymno_taxonomy_complete.csv")
OUT_NEW   = os.path.join(BASE, "edge_gymno_new_accepted_names.csv")

SYNONYM_STATUSES = {
    "SYNONYM", "HETEROTYPIC_SYNONYM", "HOMOTYPIC_SYNONYM",
    "PROPARTE_SYNONYM", "MISAPPLIED",
}

# Manual overrides: 2018 Genus_epithet → 2024 Kew.name (same biological species,
# resolved to different GBIF taxa due to genus splits)
NAME_OVERRIDES_2018_TO_2024 = {
    "Cupressus_vietnamensis":  "Xanthocyparis vietnamensis",
    "Cupressus_goveniana":     "Hesperocyparis goveniana",
    "Cupressus_guadalupensis": "Hesperocyparis guadalupensis",
}

# ── Output schema ────────────────────────────────────────────────────────────
# Shared GBIF block (identical to angio + FotW pipelines)
GBIF_FIELDS = [
    "taxonID", "scientificName", "genus", "specificEpithet",
    "infraspecificEpithet", "scientificNameID", "gbif_id",
    "lookup_method", "gbif_status", "gbif_confidence",
    "accepted_name", "accepted_gbif_id", "accepted_gbif_url", "error",
]

# Angio-compatible EDGE fields (semantically aligned)
ANGIO_COMPAT_FIELDS = [
    "Species", "EDGE.rank", "Family", "Order",
    "edge.med", "ed.med", "tbl.med",
    "threat", "EDGE.List",
]

# Gymno-only fields preserved from 2018
GYMNO_2018_FIELDS = [
    "ED.SD", "ED.rank", "EDGE.ISAAC", "EDGE.ISAAC.rank",
]

# Fields added from the 2024 EDGE list (priority species only)
EDGE2024_FIELDS = [
    "Class", "common_name",
    "edge2.med", "EDGE2.rank",
    "threat_2024",
    "distribution_code", "distribution_name",
    "red_list_id",
]

ADMIN_FIELDS = ["clade", "record_type", "synonym_edge_keys"]

OUT_FIELDS = (
    ["record_type", "clade"]
    + GBIF_FIELDS
    + ANGIO_COMPAT_FIELDS
    + GYMNO_2018_FIELDS
    + EDGE2024_FIELDS
    + ["synonym_edge_keys"]
)


def strip_q(s):
    return s.strip().strip('"') if s else ""


def load_2024_lookup():
    """
    Build three lookups for the 2024 EDGE list:
      by_id        accepted_gbif_id -> payload
      by_name      Kew.name         -> payload
      by_kew_full  Kew.name         -> full source row (needed to build synthetic
                                       gbif_accepted_new rows for overrides)
    """
    by_id      = {}
    by_name    = {}
    by_kew_full = {}
    with open(IN_2024, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            payload = {
                "Class"             : strip_q(r.get("Class", "")),
                "Order"             : strip_q(r.get("Order", "")),
                "Family"            : strip_q(r.get("Family", "")),
                "common_name"       : strip_q(r.get("Common.name", "")),
                "tbl.med"           : strip_q(r.get("TBL.median", "")),
                "edge2.med"         : strip_q(r.get("EDGE.median", "")),
                "EDGE2.rank"        : strip_q(r.get("EDGE.Rank", "")),
                "threat_2024"       : strip_q(r.get("RL.category", "")),
                "distribution_code" : strip_q(r.get("Distribution.code", "")),
                "distribution_name" : strip_q(r.get("Distribution.name", "")),
                "red_list_id"       : strip_q(r.get("RL.ID", "")),
            }
            aid = strip_q(r.get("accepted_gbif_id", ""))
            if aid:
                by_id[aid] = payload
            kew = strip_q(r.get("Kew.name", ""))
            if kew:
                by_name[kew] = payload
                by_kew_full[kew] = r
    return by_id, by_name, by_kew_full


def lookup_2024(r2018, by_id, by_name):
    """
    Find the 2024 entry that corresponds to a 2018 row, using:
      1) accepted_gbif_id match
      2) manual override (2018 Genus_epithet → 2024 Kew.name)
      3) None
    """
    aid = strip_q(r2018.get("accepted_gbif_id", ""))
    if aid and aid in by_id:
        return by_id[aid]
    override_name = NAME_OVERRIDES_2018_TO_2024.get(strip_q(r2018.get("taxonID", "")))
    if override_name and override_name in by_name:
        return by_name[override_name]
    return None


def harmonize_row(r2018, by_id, by_name):
    """Build a harmonized output row from a 2018 source row."""
    taxon_2018 = strip_q(r2018.get("Taxon", ""))
    species_underscored = taxon_2018.replace(" ", "_")

    out = {
        "record_type"        : "edge_original",
        "clade"              : "gymno",
        # GBIF block — passes through verbatim
        **{f: strip_q(r2018.get(f, "")) for f in GBIF_FIELDS},
        # Angio-compatible block
        "Species"            : species_underscored,
        "EDGE.rank"          : strip_q(r2018.get("Rank EDGE IUCN50", "")),
        "Family"             : "",  # filled below if 2024 match
        "Order"              : "",
        "edge.med"           : strip_q(r2018.get("EDGE IUCN50 scores", "")),
        "ed.med"             : strip_q(r2018.get("Median ED scores", "")),
        "tbl.med"            : "",  # 2018 didn't compute TBL; filled from 2024 if matched
        "threat"             : strip_q(r2018.get("IUCN categories", "")),
        "EDGE.List"          : "n",
        # Gymno-2018-specific
        "ED.SD"              : strip_q(r2018.get("ED SD", "")),
        "ED.rank"            : strip_q(r2018.get("Rank ED", "")),
        "EDGE.ISAAC"         : strip_q(r2018.get("EDGE ISAAC scores", "")),
        "EDGE.ISAAC.rank"    : strip_q(r2018.get("Rank EDGE ISAAC", "")),
        # 2024 enrichment (blank by default)
        "Class"              : "",
        "common_name"        : "",
        "edge2.med"          : "",
        "EDGE2.rank"         : "",
        "threat_2024"        : "",
        "distribution_code"  : "",
        "distribution_name"  : "",
        "red_list_id"        : "",
        "synonym_edge_keys"  : "",
    }

    enrich = lookup_2024(r2018, by_id, by_name)
    if enrich is not None:
        out["EDGE.List"] = "y"
        out["Family"]    = enrich["Family"]
        out["Order"]     = enrich["Order"]
        out["tbl.med"]   = enrich["tbl.med"]
        for f in EDGE2024_FIELDS:
            out[f] = enrich[f]
    return out


def build_new_accepted_rows(rows_2018, by_id, by_name):
    """
    For 2018 SYNONYM rows whose accepted_name is NOT itself a 2018 EDGE species,
    create new placeholder rows so the deliverable has one row per unique
    accepted GBIF taxon — mirrors build_edge_complete.py for angio.
    """
    edge_keys = {strip_q(r.get("taxonID", "")) for r in rows_2018}
    new_accepted = {}              # acc_id -> output row
    synonym_links = defaultdict(list)

    for r in rows_2018:
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

        # Try to enrich the new accepted-name row from the 2024 list
        enrich = by_id.get(acc_id)

        row = {
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
            # EDGE scores blank — this species was not scored in 2018
            "Species"            : acc_key,
            "EDGE.rank"          : "",
            "Family"             : "",
            "Order"              : "",
            "edge.med"           : "",
            "ed.med"             : "",
            "tbl.med"            : "",
            "threat"             : "",
            "EDGE.List"          : "n",
            "ED.SD"              : "",
            "ED.rank"            : "",
            "EDGE.ISAAC"         : "",
            "EDGE.ISAAC.rank"    : "",
            "Class"              : "",
            "common_name"        : "",
            "edge2.med"          : "",
            "EDGE2.rank"         : "",
            "threat_2024"        : "",
            "distribution_code"  : "",
            "distribution_name"  : "",
            "red_list_id"        : "",
            "synonym_edge_keys"  : "",
        }
        if enrich is not None:
            row["EDGE.List"] = "y"
            row["Family"]    = enrich["Family"]
            row["Order"]     = enrich["Order"]
            row["tbl.med"]   = enrich["tbl.med"]
            for f in EDGE2024_FIELDS:
                row[f] = enrich[f]
        new_accepted[acc_id] = row

    # Attach the list of EDGE keys that point at each new accepted row
    for acc_id, row in new_accepted.items():
        row["synonym_edge_keys"] = ";".join(synonym_links[acc_id])

    return list(new_accepted.values())


def build_override_rows(by_kew_full):
    """
    For each manual override, emit a synthetic gbif_accepted_new row carrying
    the 2024 GBIF id and EDGE.List=y, so FotW lookup on the 2024 accepted name
    finds the priority flag. The corresponding 2018 row (with its older GBIF id)
    is also flagged via lookup_2024 — so both points of entry resolve.
    """
    rows = []
    for old_key, new_name in NAME_OVERRIDES_2018_TO_2024.items():
        src = by_kew_full.get(new_name)
        if src is None:
            continue
        acc_id   = strip_q(src.get("accepted_gbif_id", ""))
        acc_name = strip_q(src.get("accepted_name", "")) or strip_q(src.get("Kew.name", ""))
        if not acc_id or not acc_name:
            continue
        parts = acc_name.split()
        acc_key = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else acc_name.replace(" ", "_")
        rows.append({
            "record_type"        : "gbif_accepted_new",
            "clade"              : "gymno",
            "taxonID"            : acc_key,
            "scientificName"     : acc_name,
            "genus"              : parts[0] if parts else "",
            "specificEpithet"    : parts[1] if len(parts) >= 2 else "",
            "infraspecificEpithet": "",
            "scientificNameID"   : "",
            "gbif_id"            : acc_id,
            "lookup_method"      : "manual_override_to_2024",
            "gbif_status"        : "ACCEPTED",
            "gbif_confidence"    : "",
            "accepted_name"      : acc_name,
            "accepted_gbif_id"   : acc_id,
            "accepted_gbif_url"  : f"https://gbif.org/species/{acc_id}",
            "error"              : "",
            "Species"            : acc_key,
            "EDGE.rank"          : "",
            "Family"             : strip_q(src.get("Family", "")),
            "Order"              : strip_q(src.get("Order", "")),
            "edge.med"           : "",
            "ed.med"             : "",
            "tbl.med"            : strip_q(src.get("TBL.median", "")),
            "threat"             : strip_q(src.get("RL.category", "")),
            "EDGE.List"          : "y",
            "ED.SD"              : "",
            "ED.rank"            : "",
            "EDGE.ISAAC"         : "",
            "EDGE.ISAAC.rank"    : "",
            "Class"              : strip_q(src.get("Class", "")),
            "common_name"        : strip_q(src.get("Common.name", "")),
            "edge2.med"          : strip_q(src.get("EDGE.median", "")),
            "EDGE2.rank"         : strip_q(src.get("EDGE.Rank", "")),
            "threat_2024"        : strip_q(src.get("RL.category", "")),
            "distribution_code"  : strip_q(src.get("Distribution.code", "")),
            "distribution_name"  : strip_q(src.get("Distribution.name", "")),
            "red_list_id"        : strip_q(src.get("RL.ID", "")),
            "synonym_edge_keys"  : old_key,
        })
    return rows


def main():
    print("Loading 2018 resolved EDGE table …")
    with open(IN_2018, newline="", encoding="utf-8") as fh:
        rows_2018 = list(csv.DictReader(fh))
    print(f"  {len(rows_2018):,} rows")

    print("Loading 2024 EDGE priority list …")
    by_id, by_name, by_kew_full = load_2024_lookup()
    print(f"  {len(by_id):,} unique accepted_gbif_id")
    print(f"  {len(by_name):,} unique Kew.name")

    print("Harmonizing 2018 rows …")
    harmonized = [harmonize_row(r, by_id, by_name) for r in rows_2018]
    edge_list_count = sum(1 for r in harmonized if r["EDGE.List"] == "y")
    print(f"  EDGE.List = y : {edge_list_count:,} of {len(harmonized):,}")

    print("Building new accepted-name rows from synonyms …")
    new_rows = build_new_accepted_rows(rows_2018, by_id, by_name)
    print(f"  {len(new_rows):,} new rows added")

    print("Building synthetic rows for manual taxonomic overrides …")
    override_rows = build_override_rows(by_kew_full)
    print(f"  {len(override_rows):,} override rows added")

    all_rows = harmonized + new_rows + override_rows
    new_rows_combined = new_rows + override_rows

    print(f"Writing {os.path.basename(OUT_FULL)} …")
    with open(OUT_FULL, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    print(f"Writing {os.path.basename(OUT_NEW)} …")
    with open(OUT_NEW, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(new_rows_combined)

    # Sanity-check the EDGE.List count against the 2024 source
    n_2024_priority = len(by_name)
    n_flagged = sum(1 for r in all_rows if r["EDGE.List"] == "y")
    print()
    print("=" * 65)
    print(f"  2024 EDGE list size              : {n_2024_priority:>5}")
    print(f"  Rows flagged EDGE.List = y       : {n_flagged:>5}")
    print(f"  Original 2018 EDGE rows          : {len(rows_2018):>5,}")
    print(f"  New accepted-name rows (synonym) : {len(new_rows):>5,}")
    print(f"  Override rows (taxonomy split)   : {len(override_rows):>5,}")
    print(f"  Combined total                   : {len(all_rows):>5,}")
    print("=" * 65)
    print(f"  Combined file : {OUT_FULL}")
    print(f"  New-only file : {OUT_NEW}")


if __name__ == "__main__":
    main()
