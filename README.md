# EDGE Gymnosperms × GBIF — Alignment for Flora of the World

GBIF-backbone alignment of the **2024 EDGE2 gymnosperm dataset** (Gumbs et al. 2024 — 1,083 species, EDGE2 methodology of Gumbs et al. 2023, *PLoS Biology*). Produced for integration of EDGE scores into [Flora of the World (FotW)](https://floraoftheworld.org) taxon pages.

This is the gymnosperm companion to [`EDGE-flowering-plants-GBIF-alignment`](https://github.com/Flora-of-the-World/EDGE-flowering-plants-GBIF-alignment). The output schema is intentionally aligned with the angiosperm release so a **single FotW import logic** can consume both clades — and because both releases now use the same EDGE2 methodology, all scores are directly interpretable on the same scale (millions of years of potential evolutionary history at risk).

---

## What's in here

| File | Purpose |
|---|---|
| `edge_gymno_taxonomy_complete.csv` | **Primary deliverable.** 1,090 rows × 29 columns: 1,083 EDGE rows + 7 GBIF synonym-derived accepted-name rows. |
| `edge_gymno_new_accepted_names.csv` | Subset: the 7 new accepted-name rows only. |
| `EDGE_gymno_CSV_data_dictionary.md` | Reference documentation for every column. Start here for field definitions. |
| `Gymnosperm_EDGE2_scores_2024.csv` | Source: 2024 EDGE2 gymnosperm scores (1,083 species × 7 columns). |
| `resolve_edge_gymno_taxonomy.py` | **Step 1.** Resolves every source species name against the GBIF backbone; also captures Family and Order from the GBIF response. |
| `harmonize_gymno.py` | **Step 2.** Renames source columns to angio-compatible names and emits the deliverable. |
| `LICENSE` | CC BY 4.0. |

---

## Pipeline

```
Gymnosperm_EDGE2_scores_2024.csv
            │
            ▼
[Step 1] resolve_edge_gymno_taxonomy.py    (~1 min, GBIF name-match for 1,083 species)
            │
            ▼
edge_gymno_taxonomy_resolved.csv           (intermediate file)
            │
            ▼
[Step 2] harmonize_gymno.py                (rename columns, compute ranks, build synonym rows)
            │
            ▼
edge_gymno_taxonomy_complete.csv           (deliverable)
edge_gymno_new_accepted_names.csv          (subset)
```

### Step 1 — Resolve names against GBIF

```bash
python3 resolve_edge_gymno_taxonomy.py
```

For each of the 1,083 species, queries `https://api.gbif.org/v1/species/match?kingdom=Plantae&name=Genus epithet`. Same endpoint and same 14 GBIF-derived columns as the angio resolver, plus `gbif_family` / `gbif_order` captured from the GBIF response. Resumable.

| GBIF status | Count |
|---|---:|
| ACCEPTED | 1,040 |
| SYNONYM | 42 |
| HETEROTYPIC_SYNONYM | 1 |
| NO_MATCH | 0 |
| ERROR | 0 |

### Step 2 — Harmonize

```bash
python3 harmonize_gymno.py
```

Renames source columns to angio-compatible names, computes `EDGE.rank` from `EDGE.median` descending, derives `above.med.*` from `no.above.median`, and emits 7 `gbif_accepted_new` rows for synonyms whose accepted name is not itself in the 2024 list.

### Column harmonization

| 2024 source | → | angio-compatible name |
|---|---|---|
| `Species` | → | `Species` (underscored) |
| `RL.cat` | → | `threat` |
| `ED.median` | → | `ed.med` |
| `EDGE.median` | → | `edge.med` |
| `TBL.median` | → | `tbl.med` |
| `no.above.median` (out of 100) | → | `above.med.tot`, `above.med.perc`, `above.med` |
| `EDGE.species` (`YES`/`NO`) | → | `EDGE.List` (`y`/`n`) |
| *(computed from sort)* | → | `EDGE.rank` |
| *(from GBIF response)* | → | `Family`, `Order` |

---

## How to join with FotW

```
FotW (fotw_taxonomy_resolved.csv).accepted_gbif_id
    ↔
EDGE-gymno (edge_gymno_taxonomy_complete.csv).accepted_gbif_id
```

The join key is identical to the angio deliverable. **The same FotW import code processes both clades.** The `clade` column distinguishes them where needed.

### Suggested derived booleans (compute at import time)

| Boolean | Definition |
|---|---|
| `is_edge_species` | true if FotW taxon's `accepted_gbif_id` matches any row in the combined EDGE-angio + EDGE-gymno tables. Gates whether the EDGE panel renders. |
| `is_edge_list_priority` | true if `EDGE.List = "y"`. Drives the "EDGE Priority Species" badge. |

---

## What to display on the FotW taxon page

Both clades now use the same EDGE2 methodology, so the same display rules apply.

| Column | Suggested label | Notes |
|---|---|---|
| `edge.med` | *"EDGE2 score: X.XX Myr"* | Millions of years of evolutionary history at risk. Available for **all** gymnosperms in the dataset. Comparable in units to the angio `edge.med`. |
| `EDGE.rank` | *"EDGE rank: #N of 1,083 gymnosperms"* | Global rank by `edge.med` descending. |
| `ed.med` | *"Evolutionary Distinctiveness: X Myr"* | Fair Proportion ED. |
| `threat` | IUCN-style tag (CR / EN / VU / NT / LC / DD / EW / NA) | IUCN Red List category. NA = Not Assessed. |
| `EDGE.List` | "EDGE Priority Species" badge | Y when species is threatened (CR/EN/VU/EW) AND robustly above median EDGE for the gymnosperm clade. |

---

## Key results

| Metric | Value |
|---|---:|
| Source species | 1,083 |
| GBIF ACCEPTED | 1,040 |
| GBIF SYNONYM (resolved) | 43 |
| New accepted-name rows added | 7 |
| Total deliverable rows | 1,090 |
| Priority species (`EDGE.List = y`) | 282 |
| Unique gymno GBIF taxa documented in FotW | 149 |
| Priority gymnosperms in FotW | 41 of 282 (14.5%) |

---

## Citations

If you use this repository, please cite both source publications and this repository.

**2024 EDGE gymnosperm scores (source dataset)**

> Gumbs, R., Pipins, S., et al. (2024). EDGE2 scores for gymnosperms. Released by the EDGE of Existence Programme, Zoological Society of London. <https://www.edgeofexistence.org/edge-lists/>

**EDGE2 methodology**

> Gumbs, R., Gray, C. L., Böhm, M., Burfield, I. J., Couchman, O. R., Faith, D. P., Forest, F., Hoffmann, M., Isaac, N. J. B., Jetz, W., Mace, G. M., Mooers, A. O., Safi, K., Scott, O., Steel, M., Tucker, C. M., Pearse, W. D., Owen, N. R., Rosindell, J. (2023). The EDGE2 protocol: Advancing the prioritisation of Evolutionarily Distinct and Globally Endangered species for practical conservation action. *PLoS Biology* 21(2): e3001991. <https://doi.org/10.1371/journal.pbio.3001991>

**Historical 2018 gymnosperm EDGE paper (precursor, no longer used here)**

> Forest, F., Moat, J., Baloch, E., Brummitt, N. A., Bachman, S. P., Ickert-Bond, S., Hollingsworth, P. M., Liston, A., Little, D. P., Mathews, S., Rai, H., Rydin, C., Stevenson, D. W., Thomas, P., **Buerki, S.** (2018). Gymnosperms on the EDGE. *Scientific Reports* 8: 6053. <https://doi.org/10.1038/s41598-018-24365-4>

**This repository**

> Buerki, S. (2026). EDGE Gymnosperms × GBIF — alignment for Flora of the World. <https://github.com/Flora-of-the-World/EDGE-gymnosperms-GBIF-alignment>

---

## License

Released under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/legalcode). Full legal code in [LICENSE](LICENSE).

You are free to share and adapt the material — including code, GBIF-resolved EDGE-gymnosperm outputs, and the combined deliverable — for any purpose, including commercially, provided that you give appropriate credit to the source publications and dataset cited above, indicate any changes made, and do not suggest endorsement by the authors of either work.

---

## Maintainer

Flora of the World Foundation, Boise, ID, USA — <https://floraoftheworld.org>
