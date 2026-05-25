# EDGE Gymnosperms × GBIF — Alignment for Flora of the World

GBIF-backbone alignment of the EDGE gymnosperm dataset (Forest et al., 2018, *Scientific Reports*) enriched with the 2024 EDGE gymnosperm priority list (EDGE2 methodology, Gumbs et al. 2023). Produced for integration of EDGE scores into [Flora of the World (FotW)](https://floraoftheworld.org) taxon pages.

This is the gymnosperm companion to [`EDGE-flowering-plants-GBIF-alignment`](https://github.com/Flora-of-the-World/EDGE-flowering-plants-GBIF-alignment). The output schema is intentionally aligned with the angiosperm release so a **single FotW import logic** can consume both clades.

> ## ⚠️ Important — two ED columns, two EDGE columns, and "blank ≠ zero"
>
> The deliverable carries two independent ED measurements and two independent EDGE scores for every priority species. **Do not confuse them, and do not treat blank cells as zeros.**
>
> | Column | Source | Methodology | Populated for |
> |---|---|---|---|
> | `ed.med` | 2018 paper | Fair Proportion ED, 100-tree posterior | **All 1,090** species |
> | `ed2.med` | 2024 EDGE list | Fair Proportion ED, EDGE2 phylogeny | **258 priority species only** |
> | `edge.med` | 2018 paper | Isaac et al. 2007, IUCN50 transformation | **All 1,090** species |
> | `edge2.med` | 2024 EDGE list | Gumbs et al. 2023, EDGE2 protocol | **258 priority species only** |
> | `tbl.med` | 2024 EDGE list | Terminal branch length from EDGE2 model | **258 priority species only** |
>
> - **`ed.med` and `ed2.med` are NOT the same value.** Same metric definition, but computed on different phylogenies. For *Wollemia nobilis*: `ed.med` = 139.59 Myr (2018) vs `ed2.med` = 136.10 Myr (2024). Only 1 of 255 paired species has identical values (*Ginkgo biloba*, by coincidence).
> - **`edge.med` and `edge2.med` use entirely different formulas.** 2018 IUCN50 (`ln(1+ED) + GE·ln(2)`) yields small values (~0.7–4.9 range). EDGE2 yields large values in units of Myr-of-history-at-risk (up to 151 for *Ginkgo*). They are not interchangeable.
> - **Blank means "not published", not zero.** For the 832 non-priority species, `ed2.med`, `edge2.med`, `tbl.med`, `EDGE2.rank`, `threat_2024`, `common_name`, `distribution_*`, `red_list_id`, `Class`, `Family`, `Order` are all blank because they were not published in the 2024 EDGE list. Plotting or scoring code MUST treat these as missing values; substituting zero will misrank the dataset.
> - **For display: prefer `ed2.med`/`edge2.med` for the 258 priority species** (more recent, current IUCN), and fall back to `ed.med`/`edge.med` for the other 832 with a "2018 score" caption so users know the methodology differs.

---

## What's in here

| File | Purpose |
|---|---|
| `edge_gymno_taxonomy_complete.csv` | **Primary deliverable.** 1,098 rows: 1,090 EDGE rows from 2018 + 5 GBIF synonym-derived accepted-name rows + 3 manual taxonomic-override rows. 35 columns. |
| `edge_gymno_new_accepted_names.csv` | Subset: the 8 new accepted-name rows only. |
| `EDGE_gymno_CSV_data_dictionary.md` | Reference documentation for every column. Start here for field definitions. |
| `Forest_etal_2018_EDGEgymno_tableS3.csv` | Source: Table S3 from Forest et al. 2018 (1,090 species × 9 columns). Cleaned export from `41598_2018_24365_MOESM2_ESM.xlsx`. |
| `EDGE2024_gymnosperms_top_list.csv` | Source: Gymnosperms tab from the 2024 ZSL EDGE species external list (258 species × 13 columns). |
| `resolve_edge_gymno_taxonomy.py` | **Step 1.** Resolves every 2018 species name against the GBIF backbone. Produces `edge_gymno_taxonomy_resolved.csv`. |
| `harmonize_gymno.py` | **Step 2.** Joins 2018 GBIF-resolved data with the 2024 EDGE list; emits the angio-compatible deliverable. |
| `LICENSE` | CC BY 4.0. |

---

## Pipeline

```
Forest_etal_2018_EDGEgymno_tableS3.csv         EDGE2024_gymnosperms_top_list.csv
            │                                              │
            ▼                                              ▼
[Step 1] resolve_edge_gymno_taxonomy.py        [Step 1b] inline name-match (in harmonize)
            │                                              │
            ▼                                              ▼
edge_gymno_taxonomy_resolved.csv               EDGE2024_gymnosperms_top_list_resolved.csv
            │                                              │
            └────────────────────┬─────────────────────────┘
                                 ▼
                  [Step 2] harmonize_gymno.py
                                 │
                                 ▼
              edge_gymno_taxonomy_complete.csv   (deliverable)
              edge_gymno_new_accepted_names.csv  (subset)
```

### Step 1 — Resolve 2018 names against GBIF

```bash
python3 resolve_edge_gymno_taxonomy.py
```

For each of the 1,090 species, queries `https://api.gbif.org/v1/species/match?kingdom=Plantae&name=Genus epithet`. Mirrors `resolve_edge_taxonomy.py` from the angio pipeline — same 14 GBIF-derived columns, same resumability. Runs in ~1 min on 8 workers.

| GBIF status | Count |
|---|---:|
| ACCEPTED | 1,042 |
| SYNONYM | 47 |
| HETEROTYPIC_SYNONYM | 1 |
| NO_MATCH | 0 |
| ERROR | 0 |

### Step 2 — Harmonize and join

```bash
python3 harmonize_gymno.py
```

Renames 2018 columns to angio-compatible names and joins the 2024 EDGE priority list on `accepted_gbif_id`. Adds the `EDGE.List` Y/N flag (mirroring the angio `EDGE.List`) plus 9 enrichment columns from the 2024 list: `Class`, `common_name`, `tbl.med`, `ed2.med`, `edge2.med`, `EDGE2.rank`, `threat_2024`, `distribution_*`, `red_list_id`.

### Column harmonization

| 2018 column | → | angio-compatible name |
|---|---|---|
| `Taxon` | → | `Species` (underscored) |
| `IUCN categories` | → | `threat` |
| `Median ED scores` | → | `ed.med` |
| `EDGE IUCN50 scores` | → | `edge.med` |
| `Rank EDGE IUCN50` | → | `EDGE.rank` |

Gymno-only fields preserved alongside: `ED.SD`, `ED.rank`, `EDGE.ISAAC`, `EDGE.ISAAC.rank`.

### Manual taxonomic overrides

Three species changed genus between the 2018 paper and the 2024 list (genus splits not reflected in GBIF as synonyms), so the `EDGE.List` flag would otherwise miss them. The override list:

| 2018 name | 2024 name |
|---|---|
| *Cupressus vietnamensis* | *Xanthocyparis vietnamensis* |
| *Cupressus goveniana* | *Hesperocyparis goveniana* |
| *Cupressus guadalupensis* | *Hesperocyparis guadalupensis* |

For each, the 2018 row is flagged `EDGE.List = y` and a synthetic `gbif_accepted_new` row with `lookup_method = "manual_override_to_2024"` is added carrying the 2024 GBIF id. This ensures FotW lookup finds `EDGE.List = y` under either taxonomy.

---

## How to join with FotW

```
FotW (fotw_taxonomy_resolved.csv).accepted_gbif_id
    ↔
EDGE-gymno (edge_gymno_taxonomy_complete.csv).accepted_gbif_id
```

The join key is identical to the angio deliverable. **The same FotW import code can process both clades**; the `clade` column distinguishes them where needed.

### Reading the file

```python
import pandas as pd
df = pd.read_csv("edge_gymno_taxonomy_complete.csv")
```

```r
df <- read.csv("edge_gymno_taxonomy_complete.csv")
```

### Suggested derived booleans (compute at import time)

| Boolean | Definition |
|---|---|
| `is_edge_species` | true if FotW taxon's `accepted_gbif_id` matches any row in the combined EDGE-angio + EDGE-gymno tables. Gates whether the EDGE panel renders. |
| `is_edge_list_priority` | true if `EDGE.List = "y"`. Drives the "EDGE Priority Species" badge. |
| `is_edge2_priority` *(gymno-specific)* | true if `EDGE2.rank` is populated. Lets the page surface the EDGE2 score and rank alongside (or instead of) the 2018 IUCN50 score for gymnosperms. |

---

## What to display on the FotW taxon page (gymnosperms)

The same tiering as the angio release applies. Gymno-specific additions:

| Column | Suggested label | Notes |
|---|---|---|
| `edge2.med` | *"EDGE2 score: X.XX Myr"* | Preferred display for gymnosperms — units are interpretable (millions of years of evolutionary history at risk). Available only for the 258 priority species. |
| `EDGE2.rank` | *"EDGE2 rank: #N of 1,090 gymnosperms"* | The 2024 EDGE2 rank under current methodology. Pair with `edge2.med`. |
| `ed2.med` | *"Evolutionary Distinctiveness (EDGE2): X.XX Myr"* | The 2024-recomputed ED. Prefer over `ed.med` for priority species. |
| `common_name` | inline subtitle | Vernacular name where available. |
| `distribution_name` | small caption | Country range from the 2024 list. |
| `threat_2024` | IUCN-style tag | Current IUCN category. Use this in preference to `threat` (which is the 2018 paper's snapshot) where both are present. |
| `red_list_id` | link target | Link the threat tag to `https://www.iucnredlist.org/species/{red_list_id}/...`. |

For non-priority species (the other 832 in the 1,090 list), display `EDGE.rank`, `edge.med`, `ed.med` from the 2018 paper with a small note that the EDGE2 score has not been published for this species. **Do not show "0" or "—" for blank 2024 fields**; either omit the row from the EDGE2 panel or render an explicit "Not assessed under EDGE2" placeholder.

---

## Citations

If you use this repository, please cite both source publications and the 2024 EDGE list, plus this repository.

**2018 EDGE gymnosperms paper (source of 1,090 species and 2018 EDGE scores)**

> Forest, F., Moat, J., Baloch, E., Brummitt, N. A., Bachman, S. P., Ickert-Bond, S., Hollingsworth, P. M., Liston, A., Little, D. P., Mathews, S., Rai, H., Rydin, C., Stevenson, D. W., Thomas, P., **Buerki, S.** (2018). Gymnosperms on the EDGE. *Scientific Reports* 8: 6053. <https://doi.org/10.1038/s41598-018-24365-4>

**EDGE2 methodology (source of 2024 priority list scoring)**

> Gumbs, R., Gray, C. L., Böhm, M., et al. (2023). The EDGE2 protocol: Advancing the prioritisation of Evolutionarily Distinct and Globally Endangered species for practical conservation action. *PLoS Biology* 21(2): e3001991. <https://doi.org/10.1371/journal.pbio.3001991>

**2024 EDGE species list (source of priority flags and EDGE2 scores)**

> EDGE of Existence Programme, Zoological Society of London (2024). EDGE species lists 2024 (amphibians, birds, gymnosperms, mammals, ray-finned fish, reptiles, sharks and rays). <https://www.edgeofexistence.org/edge-lists/>

**This repository**

> Buerki, S. (2026). EDGE Gymnosperms × GBIF — alignment for Flora of the World. <https://github.com/Flora-of-the-World/EDGE-gymnosperms-GBIF-alignment>

---

## License

Released under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/legalcode). Full legal code in [LICENSE](LICENSE).

You are free to share and adapt the material — including code, GBIF-resolved EDGE-gymnosperm outputs, and the combined deliverable — for any purpose, including commercially, provided that you give appropriate credit to the source publications and dataset cited above, indicate any changes made, and do not suggest endorsement by the authors of either work.

---

## Maintainer

Flora of the World Foundation, Boise, ID, USA — <https://floraoftheworld.org>
