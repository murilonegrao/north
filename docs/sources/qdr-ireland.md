# Source: Irish Register of Qualifications via the EU Qualifications Dataset Register (QDR)

Spike S-7, run on 2026-11-22. Script: `spikes/s7_ie_lists/profile_qdr_ie.py`. Result: `spikes/s7_ie_lists/RESULT.md`.

## What it is

- **IRQ (Irish Register of Qualifications, irq.ie):** QQI's national database of the qualifications on the NFQ and the programmes that lead to them. According to QQI's IRQ page, it also lists TrustEd-authorised English language providers and their programmes. QQI calls it "free to use and ... the most reliable source of information about qualifications and quality assured providers in Ireland".
- **QDR:** QQI uploads IRQ data to the European Commission's Qualifications Dataset Register, as EU law requires (QQI news, 2022). The Commission republishes it as linked open data on data.europa.eu.

The EU file is the only bulk, machine-readable way to get **all** Irish programmes at every NFQ level.

## Why not irq.ie directly

`https://irq.ie/robots.txt` is `User-agent: * / Disallow: /`. The site is an Angular single-page app on top of an API. North must not script it. Use it by hand only, to check a single programme.

## Where and in what format

| Item | Value |
|---|---|
| Dataset | https://data.europa.eu/data/datasets/european-learning-data (API: `https://data.europa.eu/api/hub/search/datasets/european-learning-data`), modified 2026-11-15 |
| Catalogue | https://europa.eu/europass/qdr/open-data/dcat (Turtle, lists per-country files) |
| Ireland, Turtle | `https://europa.eu/europass/qdr/open-data/dcat/download?url=http://data.europa.eu/snb/data/downloadable/country/irl/ttl/irl-ttl_1.zip`: 21,357,472 bytes, 46 `.ttl` files (26 `learning-opportunities-*`, 20 `qualifications-*`), 142 MB unzipped, files dated 2026-11-22 05:59 |
| Ireland, JSON-LD | same pattern with `jsonld/irl-jsonld_1.zip`. **On 2026-11-22 every file in the zip was 0 bytes** (Malta's too). Use Turtle. |
| SPARQL | https://europa.eu/europass/qdr/#/sparql (listed in the dataset; not tested) |
| Licence | Distribution licence `COM_REUSE`: Commission reuse decision 2011/833/EU, free re-use with attribution |
| Model | European Learning Model (ELM): `elm:LearningOpportunity` → `elm:learningAchievementSpecification` → `elm:Qualification` |

## Fields (as found in the Irish dump)

| ELM | Content | North |
|---|---|---|
| LearningOpportunity `dct:title` | programme title | program name |
| LearningOpportunity `elm:status` | `released` 15,072, `Not published anymore` 10,633 | ingest `released` only |
| LearningOpportunity `elm:providedBy` → Organisation `rov:legalName` | provider legal name | institution matching |
| LearningOpportunity `adms:identifier` → `skos:notation` (datatype `https://qqi.ie`) | QQI code + IRQ id, e.g. `PG22907 - [3036]`, `DL_BDENT_R - [6611]` | `program_identifiers(scheme='ie_irq')`. The bracketed number looks like the IRQ internal id; to confirm. |
| Qualification `elm:EQFLevel` | EQF 1–8 | `level`, cross-check |
| Qualification `elm:NQFLevel` | opaque concept URI (`http://data.europa.eu/snb/qdr/c_…`) with **no label in the dump** | NFQ level, from the mapping below |
| Qualification `elm:ISCEDFCode` | **ISCED-F 2013**, 4 digits (19,681 qualifications) or 3 digits (150) | `classifications(scheme='isced_f_2013')`, direct, no crosswalk needed |
| Qualification `elm:awardingOpportunity` → `elm:awardingBody` | awarding body | awarding body |
| `foaf:homepage` | always `https://europa.eu/europass` (placeholder) | not usable |
| `elm:location` → Address | country `IRL` only, never a city (0 full addresses on learning opportunities) | not usable for city |

There is **no** price, start date, duration, mode (full-/part-time), language of instruction beyond `ENG`, programme URL or campus city.

### NFQ concept → NFQ level (inferred)

The concepts have no labels, so the level was inferred from the EQF level and from title words. QQI or the QDR vocabulary should confirm it before production.

| Concept | EQF | Title words (qualifications) | NFQ |
|---|---|---|---|
| `c_ac9adabb` | 8 | doctor 688 | 10 |
| `c_c6ada0f4` | 7 | master 3,795, postgraduate 1,651 | 9 |
| `c_218a7e54` | 6 | honours 2,320, higher diploma 372 | 8 |
| `c_38f52397` | 6 | bachelor 1,339, no "honours" in the top words | 7 |
| `c_670e54c7` | 5 | higher certificate 672, advanced certificate 75 | 6 |
| `c_4053e803` | 4 | certificate | 5 |
| `c_57c9e957`, `c_4c88e501`, `c_060f2f91`, `c_53e465cb` | 3, 2, 1, 1 | certificate | 4, 3, 2/1 |

The EQF levels in the data agree with the official NFQ→EQF referencing: NFQ 6→5, 7 and 8→6, 9→7, 10→8.

## Numbers (dump of 2026-11-22)

- 25,705 learning opportunities, 15,072 `released`. 19,831 qualifications, all with EQF, NFQ and ISCED-F. All dated 2026.
- Released at **NFQ 6–10: 11,705** (9: 4,881; 8: 2,799; 6: 2,218; 7: 1,310; 10: 497) from **152 providers**. 859 of the NFQ 6 rows are ETB further-education courses (Advanced Certificates).
- Released, all levels: 210 providers. Largest: ATU 1,178, SETU 1,074, TU Dublin 969, TCD 758, UCC 748, MTU 719, UCD 695.
- ISCED-F broad field of released programmes: 04 business/law 2,804; 09 health 2,257; 02 arts/humanities 2,118; 07 engineering 1,934; 06 ICT 1,103; 10 services 1,077; 01 education 987; 05 natural sciences 934; 03 social sciences 821; 00 generic 608; 08 agriculture 423.
- Title-only match with the immigration lists: TrustEd HE 2,464 / 6,711; ILEP HE 15 / 78; English language programmes **0 / 1,120**. The EU dump has no English language programmes, although QQI says the IRQ lists them.

## Joins

- No shared identifier with ILEP or TrustEd. The IRQ code is not the `TE…` reference. The only link is provider + normalised title, which gets 37% exact for TrustEd. Better normalisation (award prefix, "(Hons)", campus) will raise that, but some matching will stay manual.
- Provider legal names are clean and stable (e.g. "Trinity College Dublin, University of Dublin"). Use them for an `institution_identifiers(scheme='ie_irq_provider')` link after a manual match.

## Limitations

- It is a register of quality-assured programmes, not a list of what is open for the next intake. `released` does not mean "running in 2027".
- No city, URL or mode of study, so it can't tell whether a programme is full-time (Stamp 2 needs full-time).
- The NFQ concept URIs need an official label table.
- One run had empty JSON-LD files. Check that files are not empty and that counts are close to the previous run before replacing data.

## Update frequency and access

- The dump is regenerated daily (files dated the day of download; dataset `modified` 2026-11-15). How often QQI pushes IRQ updates to the QDR is unknown.
- data.europa.eu and europa.eu answered `curl` with `north-research-spike` (HTTP 200). robots.txt doesn't block these paths. **No blocking.** One 21 MB request per run.
