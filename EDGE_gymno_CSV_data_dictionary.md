# Data Dictionary — EDGE Gymnosperms GBIF Alignment

Documents the columns of `edge_gymno_taxonomy_complete.csv`, produced by `harmonize_gymno.py` from the 2024 EDGE2 gymnosperm scores (Gumbs et al. 2024, 1,083 species, EDGE2 methodology of Gumbs et al. 2023).

The output schema is intentionally aligned with `edge_taxonomy_complete.csv` from the companion repository [`EDGE-flowering-plants-GBIF-alignment`](https://github.com/Flora-of-the-World/EDGE-flowering-plants-GBIF-alignment), so a single FotW import logic consumes both clades and EDGE scores are directly comparable across both.

---

## Background: EDGE2

**EDGE** (Evolutionarily Distinct and Globally Endangered) is a composite conservation metric. **EDGE2** (Gumbs et al. 2023) is the current protocol, where scores are measured in *millions of years of expected loss of evolutionary history that conservation can avert*. Both this gymnosperm release and the angio release use EDGE2 — the scores are on the same scale and directly comparable across both clades.

The score is built from:
- **ED** (Evolutionary Distinctiveness, Fair Proportion metric, Myr) — how isolated a species sits on the tree of life.
- **TBL** (Terminal Branch Length, Myr) — the unique evolutionary contribution of the species (branch leading directly to it).
- **GE** (an IUCN Red List–derived extinction probability).

Both ED and EDGE are reported as **medians across 100 MCMC posterior draws** of the gymnosperm phylogeny. The `no.above.median` column records statistical robustness (how many of those 100 draws placed the species above the median EDGE for gymnosperms).

---

## Row classes (`record_type`)

| Value | Source | Count |
|---|---|---:|
| `edge_original` | A row from `Gymnosperm_EDGE2_scores_2024.csv`. | 1,083 |
| `gbif_accepted_new` | An accepted-name record inferred from a synonym. The source row has GBIF status SYNONYM, the accepted name is not itself in the 2024 list, so a placeholder row is added with the accepted name's GBIF id. EDGE score columns are blank because that accepted species was not scored. | 7 |

**Total rows: 1,090.** Of those, **282 carry `EDGE.List = "y"`** (priority species).

---

## Administrative columns

| Column | Type | Description |
|---|---|---|
| `record_type` | string | `edge_original` or `gbif_accepted_new`. |
| `clade` | string | Always `gymno`. Lets a consumer concatenate this deliverable with the angio deliverable while still telling the two clades apart. |
| `synonym_edge_keys` | string | For `gbif_accepted_new` rows: semicolon-separated list of source keys (`Genus_epithet`) that resolved to this accepted name. Blank for `edge_original`. |

---

## GBIF block (14 columns — identical schema to `fotw_taxonomy_resolved.csv` and `edge_taxonomy_resolved.csv`)

| Column | Type | Description |
|---|---|---|
| `taxonID` | string | `Genus_epithet` derived from the source binomial. Not a true GBIF UUID — the EDGE dataset has no native taxon UUIDs. |
| `scientificName` | string | Source binomial with a space (e.g. `Ginkgo biloba`). |
| `genus` | string | Genus portion. |
| `specificEpithet` | string | Specific epithet portion. |
| `infraspecificEpithet` | string | Always blank (binomials only). |
| `scientificNameID` | string | Always blank (no source-side URL). |
| `gbif_id` | string | Blank for `edge_original`; for `gbif_accepted_new`, the GBIF key of the accepted name. |
| `lookup_method` | string | `name_match` (source rows) or `inferred_from_synonym` (synonym-derived new accepted rows). |
| `gbif_status` | string | `ACCEPTED`, `SYNONYM`, `HETEROTYPIC_SYNONYM`, etc. |
| `gbif_confidence` | string | GBIF name-match confidence score (0–100). Blank for non name-match rows. |
| `accepted_name` | string | GBIF-accepted binomial (= `scientificName` if already accepted). |
| `accepted_gbif_id` | string | GBIF species key of the accepted name. **This is the join key for FotW integration.** |
| `accepted_gbif_url` | string | `https://gbif.org/species/{accepted_gbif_id}`. |
| `error` | string | Error message if GBIF lookup failed; blank otherwise. |

---

## EDGE block (angio-compatible)

| Column | Type | Source | Description |
|---|---|---|---|
| `Species` | string | derived from 2024 `Species` | `Genus_epithet` with underscore. |
| `EDGE.rank` | integer | computed | Global rank by `edge.med` descending. #1 = highest EDGE score. |
| `Family` | string | from GBIF | Family per GBIF backbone (e.g. `Araucariaceae`). |
| `Order` | string | from GBIF | Order per GBIF backbone (e.g. `Pinales`). |
| `edge.med` | float | 2024 `EDGE.median` | EDGE2 median score (Myr). Range observed: 0.005 (low-priority) to 148.91 (*Ginkgo biloba*). |
| `ed.med` | float | 2024 `ED.median` | Evolutionary Distinctiveness (Myr), median across 100 MCMC draws. |
| `tbl.med` | float | 2024 `TBL.median` | Terminal Branch Length (Myr), median across 100 MCMC draws. |
| `above.med.tot` | integer | derived from 2024 `no.above.median` | Number of MCMC draws (out of 100) in which the species' EDGE score exceeded the overall gymnosperm median EDGE for that draw. |
| `above.med.perc` | float | derived | `above.med.tot / 100`. Proportion of draws above median. |
| `above.med` | string (`y`/`n`) | derived | `y` if `above.med.tot ≥ 95` (above median in ≥95% of draws — robust). One of the two EDGE.List criteria. |
| `threat` | string | 2024 `RL.cat` | IUCN Red List category: `CR`, `EN`, `VU`, `NT`, `LC`, `DD`, `EW`, or `NA` (not assessed). |
| `EDGE.List` | string (`y`/`n`) | derived from 2024 `EDGE.species` | `y` if the species is a 2024 EDGE priority species (threatened AND `above.med = y`). 282 of 1,083 species. |

---

## Comparison with the angio deliverable

The 14-column GBIF block is byte-identical to `edge_taxonomy_complete.csv` (angio). The EDGE block is also identical in column names and units for the shared fields:

| Shared field | Definition (both clades) |
|---|---|
| `Species`, `EDGE.rank`, `Family`, `Order` | Identifiers + taxonomy |
| `edge.med`, `ed.med`, `tbl.med` | EDGE2 score, ED, TBL — all in Myr, all from the same EDGE2 protocol |
| `above.med.tot`, `above.med.perc`, `above.med` | MCMC stability above the clade-specific median EDGE. **Note:** angio uses 200 draws, gymno uses 100, but `above.med.perc` is the proportion and is directly comparable. |
| `threat`, `EDGE.List` | IUCN category and priority flag |

Angio-only columns NOT present in the gymno deliverable (because the angio Forest et al. 2025 dataset publishes them but the gymno source does not): `pext.med`, `RL.ERP`, `thr.or.not`, `in.backbone`, `EDGE.Borderline`, `EDGE.Research`, `EDGE.Watch`, `useful.plant`. The gymno EDGE panel on the FotW taxon page should simply omit these.

---

## Citations

- Gumbs, R., Pipins, S., et al. (2024). EDGE2 scores for gymnosperms. EDGE of Existence Programme, Zoological Society of London.
- Gumbs, R., Gray, C. L., Böhm, M., et al. (2023). The EDGE2 protocol: Advancing the prioritisation of Evolutionarily Distinct and Globally Endangered species for practical conservation action. *PLoS Biology* 21(2): e3001991. <https://doi.org/10.1371/journal.pbio.3001991>
- Isaac, N. J. B., Turvey, S. T., Collen, B., Waterman, C., Baillie, J. E. M. (2007). Mammals on the EDGE: conservation priorities based on threat and phylogeny. *PLoS ONE* 2(3): e296. <https://doi.org/10.1371/journal.pone.0000296>
- Forest, F., Moat, J., Baloch, E., et al. (2018). Gymnosperms on the EDGE. *Scientific Reports* 8: 6053. <https://doi.org/10.1038/s41598-018-24365-4> *(historical precursor)*
