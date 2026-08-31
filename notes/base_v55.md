# The 2025 BASE product, which the pipeline now reads

A second copy of the same AmeriFlux data product, downloaded 2026-08-09. It was
held alongside the 2022 export at first and **is now what the pipeline reads for
both gases.**

The purpose was to test whether the methane series was reprocessed between
releases, which `notes/study.md` recorded as unresolvable, and to obtain the
variables the export lacks. Both questions are now answered, and answering them
is what made the switch safe to make.

**This header used to say the opposite, and it was left standing after the switch
that falsified it.** It read: *kept beside the export the pipeline reads rather
than replacing it. Nothing in `src/ingest` or `src/study` reads anything described
here. The pipeline's inputs are unchanged, and no study result has been recomputed
against this product.* Of those, two are now false and the third is true only on a
reading that misleads:

- **The pipeline's inputs are not unchanged.** `scripts/04_merge_qc_aggregate.py`
  calls `base_v55.load_methane()`, and `scripts/05_build_co2.py` calls
  `base_v55.load_base()`. Carbon dioxide always came from this product, because
  the 2022 workbook carries no carbon dioxide column; methane joined it at commit
  `fbc39d2`. The Excel export is still read, by script 01 alone, to characterise
  the derived `FCH4 Data.csv` subset.
- **Every study result has been recomputed against it.** The switch is why the
  monthly series now reaches 2024 and why `TARGET_END` moved from 2021-12 to
  2024-12.
- **Nothing in `src/ingest` or `src/study` imports `validation.base_v55`**, which
  is literally still true and is not the point: the module lives in
  `src/validation/`, the numbered scripts import it, and what those scripts write
  is what `src/study` reads. The sentence was accurate about imports and wrong
  about provenance, which is the more useful thing for a reader to know.

This is the notes-versus-code drift pattern, and it is the one instance where the
README was right and this record was wrong. The other four ran the other way.

## Provenance

| | |
|---|---|
| Product | AmeriFlux BASE-BADM, US-MBP |
| BASE version | **5-5**, published 2025-03-18 |
| BADM version | **20260527**, published 2026-05-27 |
| DOI | [10.17190/AMF/1767835](https://doi.org/10.17190/AMF/1767835) |
| License | **CC-BY-4.0** |
| Downloaded | 2026-08-09 |
| Archive | **not carried in the repository.** 17,409,071 bytes, MD5 `0467d27993a28716ac6e6debd929e7f7` |
| Held as | `CSVs/AMF_US-MBP_BASE-BADM_5-5/`, the extraction, which is what the code reads |
| `AMF_US-MBP_BASE_HH_5-5.csv` | 69,296,494 bytes, MD5 `6bfad3e00a5dfb7345f87d3ca7a6b80f` |
| `AMF_US-MBP_BIF_20260527.xlsx` | 9,282 bytes, MD5 `3633a0148a87b47a7f76172983d5bc83` |

**The archive was tracked and is not any more.** It sat beside its own extraction,
so the same product was carried twice: 16.6 MB of zip against 66.1 MB of files,
and between them 80% of everything in the repository. Nothing read the zip.
`validation.base_v55.PRODUCT_DIRECTORY` names the extracted directory and always
has, and no module in this project opens an archive at all.

What the archive was for was provenance, and the MD5 above is that provenance.
It is the whole of it: a checksum is what lets a download be verified, and
carrying the bytes the checksum describes adds nothing a reader could not
establish without them. The two extracted files now carry their own checksums as
well, so the copy in the working tree can be verified without reference to the
archive at all.

**To reobtain it.** Request BASE-BADM for US-MBP from
[ameriflux.lbl.gov/data/download-data](https://ameriflux.lbl.gov/data/download-data)
at BASE version 5-5 and BADM version 20260527, which arrives as
`AMF_US-MBP_BASE-BADM_5-5.zip`. Check it against the MD5 above, extract it to
`CSVs/AMF_US-MBP_BASE-BADM_5-5/`, and the pipeline reads it where it stands. The
archive is in `.gitignore` so a re-download cannot be committed by accident.
AmeriFlux may republish a version under the same number; if the MD5 differs, that
is a finding about the product rather than about the download, and it belongs in
these notes rather than being worked around.

Citation, as the product states it in its own metadata:

> Tyler Roman, Andrew C. Hill, Randy Kolka, Timothy Griffis, Julian Deventer
> (2025), AmeriFlux BASE US-MBP Marcell Bog Lake Peatland, Ver. 5-5, AmeriFlux
> AMP, (Dataset). https://doi.org/10.17190/AMF/1767835

The 2022 export the pipeline reads is
`CSVs/FCH4 PivotTable 2009_2021 and Raw Ameriflux Data.xlsx`, sheet `raws`, four
columns and no version stamp. **Any number in `notes/ingestion.md` or
`notes/study.md` comes from that export unless it explicitly says otherwise.**
This file is the only place the 2025 product is described.

The download was requested through the AmeriFlux data API, which logs it and
emails the site principal investigators. R was unavailable, so the request was
made directly to `POST https://amfcdn.lbl.gov/api/v1/data_download` with the
payload `amerifluxr::amf_download_base` constructs, established by reading that
package's source. The API validates the account username and ignores the email.

## The methane values are identical

Every timestamp in the 2022 export is present in the 2025 product, and **every
methane value agrees exactly**.

| Column | Valid, 2022 export | Valid, 2025 product | Identical | Differing | Only in one |
|---|---|---|---|---|---|
| `FCH4` | 44,427 | 44,427 | **44,427** | **0** | 0 |
| `FCH4_1_1_1` | 15,030 | 15,030 | **15,030** | **0** | 0 |
| `FCH4_1_1_2` | 16,534 | 16,534 | **16,534** | **0** | 0 |

All 227,904 half-hours of the export appear in the product, which adds 52,608
more covering 2022 to 2024. There is no year, column or era in which the two
disagree, so no breakdown by year is reported: the difference is nowhere.

**The methane series was not reprocessed between the 2022 export and the 2025
release.** Because a deterministic function of identical inputs returns identical
outputs, every published number in `notes/ingestion.md` stands unchanged, and
this was confirmed by rerunning the pipeline's own functions on the new file
rather than asserted. The paired-difference statistics, the distribution fit and
all nine regression screens reproduce to six decimal places:

| | 2022 export | 2025 product | Published |
|---|---|---|---|
| median | 0.130 | 0.130 | 0.1 |
| IQR | 8.645 | 8.645 | 8.2 |
| sigma, robust | 8.8191 | 8.8191 | 8.5 |
| skewness, trimmed | 0.4356 | 0.4356 | 0.32 |
| Laplace against Gaussian, difference in AIC | 7028.36 | 7028.36 | |
| reduced major axis slope, selected screen | 1.086236 | 1.086236 | 1.08 ± 0.02 |
| reduced major axis intercept | −2.612 | −2.612 | −3.0 ± 0.8 |
| retained TGA-100A half-hours | 15,030 | 15,030 | 15,033 |

**The reproduction holds. It neither weakens nor improves.** The count of 15,030
against a published 15,033 is unchanged, so the second of the three grounds for
the analyzer identification is undisturbed.

### What this settles about the discrepancy against Olson et al.

`notes/study.md` records as unresolvable whether the base methane column was
reprocessed between the access of Olson et al. (2013) and the export used here,
and names the current product as one of the two things that would settle it.

It settles half of it. The 2022 export **is** the current product, value for
value, so the discrepancy is not an artifact of holding a stale or unusual
snapshot, and no reprocessing occurred between 2022 and 2025. What this cannot
rule out is reprocessing between about 2012, when Olson et al. would have drawn
their data, and 2022. Only their original extraction could close that, and it is
not available.

The remaining explanation is unchanged and is now the stronger one: Olson et al.
gap-filled and this pipeline integrates observed months only, and the
discrepancy is largest in the most episodic year.

## The BADM metadata

Read from `AMF_US-MBP_BIF_20260527.xlsx`: 106 records across 23 groups.

**On the analyzers it is silent, exactly as predicted.** `GRP_INST` and
`GRP_INSTPAIR` are both absent, so the file carries no instrument model, no
deployment period, no height, no position, and no mapping from instrument to
variable. It cannot confirm or contradict the identification of `FCH4_1_1_1` as
the closed-path TGA-100A and `FCH4_1_1_2` as the open-path LI-7700. **That
identification continues to rest on Deventer et al. (2019) plus the three
data-side lines of evidence in `notes/ingestion.md`, and on nothing else.**

The prediction was made before the file was opened, from the published BADM
group-availability table showing `GRP_INST` at 0 for this site, and is recorded
here because a prediction that is checked is worth more than one quietly
dropped.

`GRP_FLUX_MEASUREMENTS` is the nearest thing to instrument metadata and does not
reach the question. It holds four entries giving method and start date per flux
variable:

| Variable | Method | Start |
|---|---|---|
| CO2 | Eddy Covariance | 2007-01-01 |
| H | Eddy Covariance | 2007-01-01 |
| H2O | Eddy Covariance | 2007-01-01 |
| CH4 | Eddy Covariance | **2009-04-22** |

There is one methane entry, not two, so the two systems are not distinguished.
The methane start date corroborates the record: the first valid `FCH4` value in
both products is 2009-04-23 22:00, one day later.

### The site

`SITE_DESC`, the data provider's own description, states the classification
directly:

> The study site is a fen within the Marcell Experimental Forest, which has been
> monitored for fluxes and environmental variables at various points in time. In
> 2007 an EC tower was established to monitor CO2/H2O fluxes within the
> peatland. Methane observations were added in 2009 and have been ongoing since.
> This site has also been referred to as Bog Lake Fen in the past.

This is stronger than the pore water pH inference it replaces in
`src/ingest/site.py`, and its last sentence confirms the alias handling. The pH
from Deventer et al. (2019) is kept as corroboration. No soil chemistry group is
present in the file, so the pH itself remains a citation.

| Field | Value | Bears on |
|---|---|---|
| `IGBP` | WET | wetland, but silent on bog against fen |
| `LOCATION_ELEV` | **416 m** | sits above the 412.5 to 413.8 m water table range, corroborating those units |
| `LOCATION_LAT`, `LOCATION_LONG` | 47.5051, −93.4893 | confirms `site.py` |
| `SITE_SNOW_COVER_DAYS` | **120** | the snow cover taken from Deventer et al. (2019) is now data |
| `SURFACE_HOMOGENEITY` | **200 m** | the homogeneous fetch, which is why the footprint filter matters |
| `WIND_DIRECTION` | SSW | prevailing direction, as a site characteristic |
| `TERRAIN`, `ASPECT` | Flat, FLAT | |
| `TOWER_TYPE` | tripod | |
| `UTC_OFFSET` | **−6** | timestamps are local standard time |
| `MAT`, `MAP` | 3.4 °C, 780 mm | |
| `LAND_OWNERSHIP` | public | |

Vegetation, disturbance history and soil are all absent: no `GRP_SPP`, no
`GRP_DOM_DIST_MGMT`, no `GRP_SOIL_CHEM`, `GRP_SOIL_CLASSIFICATION`,
`GRP_SOIL_TEX` or `GRP_SOIL_DEPTH`, no `GRP_HEIGHTC`, `GRP_LAI` or `GRP_SWC`.

`GRP_REFERENCE_PAPER` names Deventer et al. (2019) and Feng et al. (2020) as the
site's reference papers, both already central here. Neither Olson et al. (2013)
nor either Shurpali paper is listed.

## The variable inventory as delivered

34 columns and 280,512 half-hourly rows covering 2009-01-01 to 2024-12-31,
matching the published availability table exactly, with `TIMESTAMP_START` and
`TIMESTAMP_END` and 32 variables.

**The methane columns match ours in name and count.** `FCH4`, `FCH4_1_1_1` and
`FCH4_1_1_2`, with no additional methane flux column, so the analyzer mapping in
`site.py` needs no new entry. Three matching methane mole fraction columns
`CH4`, `CH4_1_1_1` and `CH4_1_1_2` are present, which the mapping does not know
about because they are concentrations rather than fluxes.

The four variables the audit asked after:

| | | Coverage |
|---|---|---|
| Soil temperature | `TS_1_1_1` | 2009 to 2024, **97.0%** complete, native half-hourly. Six further depths `TS_1_2_1` to `TS_1_7_1` from 2022 only, which is outside the study window |
| Wind direction | `WD` | 2009 to 2024, **90.6%** complete |
| Friction velocity | `USTAR` | 2009 to 2024, **90.6%** complete |
| **Quality flags** | **none** | no steady-state or turbulence test column of any kind |

**The absence of quality flags is a property of this site, not of the product.**
182 other AmeriFlux sites publish `FCH4_SSITC_TEST` and related flags in the same
release and US-MBP publishes none. The named candidate explanation for the
unrecoverable selection rule behind `FCH4 Data.csv` is therefore not available
here either, and that question stays closed.

**Precipitation and water table are absent.** No `P`, `WTD` or `SWC`, though 247
other sites publish `P`. Precipitation remains a binding reconstruction covariate
ending 2019-12, so **this product does not recover the twenty-five discarded
methane months and does not extend the study.** It is a validation pass and a
source of wind direction and friction velocity.

### The availability table corroborates the disjointness

The disjointness of the three methane columns was recovered from the export by
inspection, and the merge design, its precedence order and its provenance column
all rest on it. **The product's own published availability table confirms it
independently.** Share of each year holding data:

| | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `FCH4` | 0.3 | 0.4 | 0.3 | 0.3 | 0.05 | 0.2 | **0** | **0** | **0** | **0** | 0.3 | 0.4 | 0.4 |
| `FCH4_1_1_1` | 0 | 0 | 0 | 0 | 0 | 0 | 0.2 | 0.2 | 0.3 | 0.2 | 0 | 0 | 0 |
| `FCH4_1_1_2` | 0 | 0 | 0 | 0 | 0 | 0 | 0.1 | 0.2 | 0.3 | 0.3 | 0 | 0 | 0 |

`FCH4` is empty across 2015 to 2018 and only there, which is exactly where the
two replicates run. This is not a restatement of our own finding by another
route through the same file: it is the data provider's published summary of the
product, generated independently of anything done here, agreeing that the
site-aggregated column and the replicates never coexist. The precedence rule
between `FCH4` and the replicates therefore never fires, as
`notes/ingestion.md` states, and `merge.assert_disjoint` asserts a property the
provider's own metadata also reports.

## The excluded wind sector is already applied

Deventer et al. (2019) state, in section 2.2, that flux data for all sensors were
discarded where wind direction indicated flow distortion from the tower or
footprint contribution from surrounding upland forest, **from 30° to 200°**. That
was previously recorded from the citation. It can now be measured, and the result
is not the expected one.

**The filter is already in the published product.** Of the retained flux values
with a wind direction recorded, the share lying in 30° to 200° is:

| Column | Valid with `WD` | Share inside 30° to 200° |
|---|---|---|
| `FCH4` | 66,972 | **0.00%** |
| `FCH4_1_1_1` | 15,030 | **0.00%** |
| `FCH4_1_1_2` | 16,523 | **0.00%** |
| `FC` | 97,985 | **0.00%** |
| all half-hours | 254,111 | **41.47%** |

Two denominators are in play and both appear here. Of half-hours **carrying a
wind direction**, 41.5% fall in the sector; of **all** half-hours, 37.6% do. The
first is the rule's effect on the population it can act on, and is what the site
figure plots; the second is its cost to the record.

Not one retained flux observation, of any species, comes from the excluded
sector, while 41.5% of the site's wind does. The exclusion is applied upstream of
publication, so it is a property of the data the pipeline already reads rather
than something that could be applied or relaxed here.

A consequence: the fraction of retained flux falling in the sector is zero by
construction, so that quantity cannot be reported and the figure annotation
should not imply it. What can be stated is what the sector removes before
methane is ever considered.

**This reframes the site's coverage.** Over 2009 to 2024:

| | Half-hours | Share |
|---|---|---|
| All | 280,512 | 100% |
| Wind direction recorded | 254,111 | 90.6% |
| Removed by the 30° to 200° sector | **105,387** | 37.6% of all, 41.5% of those with a direction |
| Outside the sector, wind direction present | 148,724 | 53.0% |
| Methane retained | 89,517 | 31.9% of all, **60.2% of what the sector filter leaves** |

The roughly 30% coverage reported throughout `notes/ingestion.md` is not 30% of
an attainable 100%. Well over a third of the record is removed by a footprint
rule before any instrument or quality consideration applies, and against what
that rule leaves, methane retention is 60%. The 200 m surface homogeneity in the
BADM file is the reason the rule is so costly.

The sector filter is applied; the despiking is not. The unscreened reduced major
axis slope is 0.979 and reaches the published 1.08 only under an outlier screen,
so `notes/ingestion.md` is right that the quality control of Deventer et al.
(2019) is not carried in the product. That statement should be read as applying
to despiking rather than to the wind sector filter, which is carried.

## Friction velocity

`USTAR` is present at 90.6%, with a median of 0.162 m s⁻¹ over the record. Of the
methane half-hours carrying a friction velocity, **13.1% fall below 0.10 m s⁻¹
and 46.5% below 0.20 m s⁻¹**, the range in which turbulence thresholds are
usually set for such a site.

This bears on the negative-flux question that `notes/ingestion.md` leaves open.
The standard turbulence filter can now be applied or assessed, which it could not
be before. Nothing here has been filtered, and the decision remains the project
owner's.

## Native soil temperature disagrees with the reconstructed series

`TS_1_1_1` is measured half-hourly at the tower and is 97% complete from 2009.
The pipeline's `soil_temp_f` is a monthly mean of the MEF weekly file. Over the
146 months both cover:

| | |
|---|---|
| Readings per month | native median **1,487**, ours 17 to 33 |
| Correlation | 0.985 |
| Difference, native minus ours | mean **+1.50 °F**, median +1.74 °F, sd 2.24 °F |
| Largest difference | 6.07 °F |
| Months differing by more than 2 °F | **76 of 146** |

The two series track each other closely and **the tower reads systematically
warmer by about 0.84 °C**. The depth of `TS_1_1_1` cannot be confirmed, because
that is exactly what the absent `GRP_INST` would have recorded, so part of the
offset may be a depth difference rather than a calibration one.

**This is an argument for leaving the pipeline alone, not for switching it.** The
native series stops at 2009, and the reconstruction window is 1990 to 2009, where
only the MEF record exists. Fitting on the tower series and reconstructing on the
MEF series would put a 0.84 °C step at exactly the fit-to-reconstruction
boundary. At the fitted Q10 of 2.66 that is a **+8.5%** shift in predicted flux,
and at the published Q10 of 2.9 a **+9.3%** shift, applied to the whole
reconstruction and to nothing else. That is the same order as the bias the study
reports and would be indistinguishable from it.

Using one source throughout, as the pipeline does, keeps the covariate consistent
across the boundary the study is about. The cost is a noisier and warmer-biased
predictor in the fit window; the benefit is that no artificial step is
introduced where the study makes its claim.

## What this product does not change

It supplies nothing before 2009, so the 48.3% of reconstruction months outside
the fitted range, the water table support gap and the study's conclusion are all
untouched. It does not recover the twenty-five discarded methane months, because
precipitation is absent from it. No study result has been recomputed.
