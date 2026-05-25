# Data Dictionary — EDGE Gymnosperms GBIF Alignment

This dictionary documents the columns of `edge_gymno_taxonomy_complete.csv`, the harmonized deliverable produced by `harmonize_gymno.py`. The file integrates two source datasets:

- **2018 paper:** Forest et al. (2018), *Scientific Reports* — full ranked list of 1,090 gymnosperm species, EDGE methodology of Isaac et al. (2007) and IUCN50.
- **2024 EDGE list:** Zoological Society of London / EDGE of Existence — the 258 gymnosperm species classified as EDGE2 priority species (threatened *and* robustly above median EDGE2 for the gymnosperm clade), using the EDGE2 methodology of Gumbs et al. (2023, *PLoS Biology*).

The output schema is intentionally aligned with `edge_taxonomy_complete.csv` from the companion repository [`EDGE-flowering-plants-GBIF-alignment`](https://github.com/Flora-of-the-World/EDGE-flowering-plants-GBIF-alignment), so a single FotW import logic can consume both clades.

---

## Background: EDGE and EDGE2

**EDGE** (Evolutionarily Distinct and Globally Endangered) is a composite conservation metric. The original EDGE (Isaac et al. 2007) is defined as:

```
EDGE = ln(1 + ED) + GE × ln(2)
```

where `ED` is the species' Evolutionary Distinctiveness (Fair Proportion metric — branch lengths divided equally among descendants) and `GE` is a Red List–derived extinction probability term.

**EDGE2** (Gumbs et al. 2023) replaces this with a metric whose units are *millions of years of expected loss of evolutionary history that conservation can avert*. EDGE2 scores are larger than the original EDGE scores (the gymnosperm top species score ~150 in EDGE2 vs. ~5 under the original transformation) and are more directly interpretable.

The 2018 paper used the original EDGE (under two extinction-probability transformations: ISAAC and IUCN50). The 2024 EDGE list uses EDGE2. **The harmonized deliverable preserves all three** so users can choose by methodology.

---

## Row classes (`record_type`)

| Value | Source | Count |
|---|---|---:|
| `edge_original` | A row from the 2018 paper. EDGE.rank, edge.med, ed.med, etc. reflect 2018 methodology. | 1,090 |
| `gbif_accepted_new` | An accepted-name record inferred from a 2018 synonym. The 2018 row has GBIF status SYNONYM, the accepted name is not itself a 2018 EDGE species, so a placeholder row is added with the accepted name's GBIF id. 2018 score columns are blank; 2024 fields populated if the accepted name is on the 2024 EDGE list. | 5 |
| `gbif_accepted_new` *(override)* | Synthetic row added for a known genus-split between 2018 and 2024 taxonomy (e.g. *Cupressus* → *Xanthocyparis*/*Hesperocyparis*). Lets FotW lookup find EDGE.List = y under either taxonomy. `lookup_method = "manual_override_to_2024"`. | 3 |

**Total rows: 1,098**, **rows with `EDGE.List = y`: 266** (= 258 unique 2024 priority taxa + 5 GBIF synonym duplicates + 3 override-pair duplicates).

---

## Administrative columns

| Column | Type | Description |
|---|---|---|
| `record_type` | string | `edge_original` or `gbif_accepted_new`. |
| `clade` | string | Always `gymno`. Enables clean concatenation with the angio deliverable for clade-aware FotW logic. |
| `synonym_edge_keys` | string | For `gbif_accepted_new` rows: semicolon-separated list of EDGE keys (`Genus_epithet`) that resolved to this accepted name. Blank for `edge_original`. |

---

## GBIF block (14 columns — identical schema to `fotw_taxonomy_resolved.csv` and `edge_taxonomy_resolved.csv`)

| Column | Type | Description |
|---|---|---|
| `taxonID` | string | `Genus_epithet` derived from the source binomial. Not a true GBIF UUID — the EDGE dataset has no native taxon UUIDs, so this is constructed from the name. |
| `scientificName` | string | Binomial with a space (e.g. `Ginkgo biloba`). |
| `genus` | string | Genus portion of `scientificName`. |
| `specificEpithet` | string | Specific epithet portion. |
| `infraspecificEpithet` | string | Always blank (the 2018 paper is binomials only). |
| `scientificNameID` | string | Always blank (no source-side URL). |
| `gbif_id` | string | Always blank for `edge_original` rows; for `gbif_accepted_new` rows, the GBIF key of the accepted name. |
| `lookup_method` | string | `name_match` (most rows), `inferred_from_synonym` (synonym-derived new accepted rows), or `manual_override_to_2024` (the 3 *Cupressus*/*Hesperocyparis*/*Xanthocyparis* overrides). |
| `gbif_status` | string | `ACCEPTED`, `SYNONYM`, `HETEROTYPIC_SYNONYM`, etc. |
| `gbif_confidence` | string | GBIF name-match confidence score (0–100). Blank for non name-match rows. |
| `accepted_name` | string | GBIF-accepted binomial (= `scientificName` if already accepted). |
| `accepted_gbif_id` | string | GBIF species key of the accepted name. **This is the join key for FotW integration.** |
| `accepted_gbif_url` | string | `https://gbif.org/species/{accepted_gbif_id}`. |
| `error` | string | Error message if GBIF lookup failed; blank otherwise. |

---

## Angio-compatible EDGE block

These column names match `edge_taxonomy_complete.csv` (angio) so FotW import logic can be shared across clades. Values are the **2018-paper IUCN50 EDGE quantities** (the closest analogue to the angio columns).

| Column | Type | Source | Description |
|---|---|---|---|
| `Species` | string | derived from 2018 `Taxon` | `Genus_epithet` with underscore. |
| `EDGE.rank` | integer | 2018 `Rank EDGE IUCN50` | Global EDGE rank among the 1,090 gymnosperms by EDGE-IUCN50 score (1 = highest priority). |
| `Family` | string | 2024 list | APG / Christenhusz et al. family. Filled only when the species is on the 2024 EDGE list (the 2018 paper did not carry family/order). |
| `Order` | string | 2024 list | Order. Same coverage caveat as `Family`. |
| `edge.med` | float | 2018 `EDGE IUCN50 scores` | Median EDGE score under the IUCN50 extinction-probability transformation. **Not directly comparable in magnitude with `edge.med` from the angio deliverable** — the angio Forest et al. 2025 paper uses a similar but not identical EDGE formula and a different ED-distribution. Use `EDGE.rank` for cross-clade comparison instead. |
| `ed.med` | float | 2018 `Median ED scores` | Median Evolutionary Distinctiveness (millions of years) across 100 trees. *Ginkgo biloba* has the maximum at 315 Myr. |
| `tbl.med` | float | 2024 list | Median terminal branch length (millions of years) from the EDGE2 model. **Populated only for the 258 priority species** (the 2018 paper did not publish TBL). |
| `threat` | string | 2018 `IUCN categories` | IUCN category from the 2018 paper: `CR`, `EN`, `VU`, `NT`, `LC`, `DD`, `NE`, or `EW`. May differ from the current IUCN assessment — see `threat_2024`. |
| `EDGE.List` | string (`y`/`n`) | derived | `y` if the row's `accepted_gbif_id` (or its 2018 binomial under one of the three manual overrides) appears on the 2024 EDGE list. Mirrors `EDGE.List` in the angio deliverable. |

---

## Gymno-specific columns from the 2018 paper

The 2018 paper publishes both Isaac et al. (2007) **ISAAC** and **IUCN50** transformations. The angio-compatible block above carries IUCN50; the ISAAC variant is preserved here for completeness.

| Column | Source | Description |
|---|---|---|
| `ED.SD` | 2018 `ED SD` | Standard deviation of ED across 100 trees. |
| `ED.rank` | 2018 `Rank ED` | Rank by ED score (independent of extinction probability). |
| `EDGE.ISAAC` | 2018 `EDGE ISAAC scores` | EDGE score under the ISAAC extinction-probability transformation. |
| `EDGE.ISAAC.rank` | 2018 `Rank EDGE ISAAC` | Global EDGE rank under ISAAC. |

---

## Columns from the 2024 EDGE list (priority species only)

Populated only when `EDGE.List = y` (i.e., the row corresponds to one of the 258 species on the 2024 EDGE list, or a synonym/override pointing to one). Blank for the other 832 rows.

| Column | Source | Description |
|---|---|---|
| `Class` | 2024 list | Higher rank (`GINKGOOPSIDA`, `PINOPSIDA`, `CYCADOPSIDA`). |
| `common_name` | 2024 `Common.name` | Vernacular name (English-leaning, occasionally French/Spanish). May be empty. |
| `ed2.med` | 2024 `ED.median` | Evolutionary Distinctiveness (Fair Proportion, median, Myr) **recomputed under the EDGE2 phylogeny.** Same metric definition as the 2018 `ed.med` but different underlying tree. **Almost never equal to `ed.med`** — see "ED.median values" comparison below. |
| `edge2.med` | 2024 `EDGE.median` | EDGE2 median score (Gumbs et al. 2023). Units: millions of years of potential evolutionary history lost. *Ginkgo biloba* has the maximum at 151.02 Myr. **Different formula from `edge.med`** (which is 2018 IUCN50). |
| `EDGE2.rank` | 2024 `EDGE.Rank` | Global EDGE2 rank among gymnosperms (1 = highest priority under EDGE2). |
| `threat_2024` | 2024 `RL.category` | Current IUCN Red List category used in the 2024 list. Always one of `CR`, `EN`, `VU`, `EW` (the 2024 list only includes threatened species). May differ from `threat` for species whose IUCN status changed since 2018. |
| `distribution_code` | 2024 `Distribution.code` | ISO 3166-1 alpha-2 country code(s), comma-separated for multi-country ranges. |
| `distribution_name` | 2024 `Distribution.name` | Full country name(s), comma-separated. |
| `red_list_id` | 2024 `RL.ID` | Numeric IUCN Red List taxon ID. Links to https://www.iucnredlist.org/species/{red_list_id}/{version}. |

> ### ⚠️ Two ED columns, two EDGE columns, and blank ≠ zero
>
> The deliverable preserves both the 2018 and 2024 quantities side-by-side. Do not confuse or substitute them.
>
> - **`ed.med` (2018) vs `ed2.med` (2024)** — same definition (Fair Proportion ED in Myr), different phylogeny. Comparing the 255 species present in both: only 1 has identical values (*Ginkgo biloba*, by coincidence — its ED is bounded by tree height); mean diff ~6 Myr, max diff 40.9 Myr.
> - **`edge.med` (2018) vs `edge2.med` (2024)** — entirely different formulas. 2018 IUCN50: `ln(1+ED) + GE·ln(2)`, range ~0.7–4.9. 2024 EDGE2 (Gumbs et al. 2023): Myr-of-history-at-risk, range ~5–151. **Do not combine, subtract, or rank-correlate them.**
> - **Blank ≠ zero.** For the 832 species not on the 2024 priority list, `ed2.med`, `edge2.med`, `tbl.med`, `EDGE2.rank`, `threat_2024`, `Class`, `Family`, `Order`, `common_name`, `distribution_code`, `distribution_name`, `red_list_id` are all blank because the 2024 list did not publish them. Statistical or display code must treat blank as missing — substituting zero will misrank the dataset.

### ED.median values: 2018 vs 2024 (sample)

| Species | `ed.med` (2018) | `ed2.med` (2024) | Identical? |
|---|---:|---:|---|
| *Ginkgo biloba* | 315.00 | 315.00 | yes (coincidence) |
| *Wollemia nobilis* | 139.59 | 136.10 | no |
| *Parasitaxus usta* | 109.34 | 101.58 | no |
| *Araucaria angustifolia* | 67.71 | 41.54 | no |
| *Araucaria araucana* | 67.71 | 56.13 | no |

---

## Cross-source comparison: 2018 vs 2024 rankings (top 10)

Illustrates that EDGE2 (2024) and EDGE-IUCN50 (2018) can disagree substantially — both methodologically and because the 2024 list reflects updated IUCN assessments.

| Species | 2018 IUCN50 rank | 2024 EDGE2 rank | 2018 IUCN | 2024 IUCN |
|---|---:|---:|:--:|:--:|
| *Ginkgo biloba* | 2 | **1** | EN | EN |
| *Wollemia nobilis* | 1 | 2 | CR | CR |
| *Araucaria angustifolia* | 3 | 3 | CR | CR |
| *Acmopyle sahniana* | 5 | 4 | CR | CR |
| *Microcycas calocoma* | 7 | 5 | CR | CR |
| *Araucaria araucana* | 17 | 6 | NE / EN | EN |
| *Parasitaxus ustus/usta* | 139 | **7** | VU | VU |
| *Sequoiadendron giganteum* | 19 | 8 | NE / EN | EN |
| *Metasequoia glyptostroboides* | 11 | 9 | EN | EN |
| *Sequoia sempervirens* | 15 | 10 | EN | EN |

---

## Key relationships

```
EDGE.List = "y"
    ↔ row's accepted_gbif_id (or 2018 binomial under override) is in the 2024 list
    ↔ species is threatened (current IUCN: CR / EN / VU / EW)
      AND robustly above median EDGE2 for the gymnosperm clade

threat        — 2018 paper IUCN category (historical)
threat_2024   — current IUCN category (priority species only)
edge.med      — 2018 EDGE under IUCN50 (small values, 4–8 range top)
edge2.med     — 2024 EDGE2 (Myr-of-history units, up to 151 top)
EDGE.rank     — 2018 IUCN50 rank, all 1,090 species
EDGE2.rank    — 2024 EDGE2 rank, priority 258 species only
```

---

## Citations

- Forest, F., Moat, J., Baloch, E., Brummitt, N. A., Bachman, S. P., Ickert-Bond, S., Hollingsworth, P. M., Liston, A., Little, D. P., Mathews, S., Rai, H., Rydin, C., Stevenson, D. W., Thomas, P., **Buerki, S.** (2018). Gymnosperms on the EDGE. *Scientific Reports* 8: 6053. <https://doi.org/10.1038/s41598-018-24365-4>
- Gumbs, R., Gray, C. L., Böhm, M., Burfield, I. J., Couchman, O. R., Faith, D. P., Forest, F., Hoffmann, M., Isaac, N. J. B., Jetz, W., Mace, G. M., Mooers, A. O., Safi, K., Scott, O., Steel, M., Tucker, C. M., Pearse, W. D., Owen, N. R., Rosindell, J. (2023). The EDGE2 protocol: Advancing the prioritisation of Evolutionarily Distinct and Globally Endangered species for practical conservation action. *PLoS Biology* 21(2): e3001991. <https://doi.org/10.1371/journal.pbio.3001991>
- Isaac, N. J. B., Turvey, S. T., Collen, B., Waterman, C., Baillie, J. E. M. (2007). Mammals on the EDGE: conservation priorities based on threat and phylogeny. *PLoS ONE* 2(3): e296. <https://doi.org/10.1371/journal.pone.0000296>
