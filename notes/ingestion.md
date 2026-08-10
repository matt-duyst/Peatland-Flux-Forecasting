# Ingestion layer — findings and judgment calls

Scope: raw AmeriFlux BASE workbook to a merged, provenance-tracked half-hourly
series, then to daily and monthly aggregates. No modeling and no gap-filling.

## Site and data product

Pinned in `src/ingest/site.py`.

| | |
|---|---|
| AmeriFlux site | **US-MBP**, Marcell Bog Lake Peatland |
| Coordinates | 47.505 N, −93.489 W |
| Location | USDA Forest Service Marcell Experimental Forest, Minnesota, USA |
| Data product DOI | **10.17190/AMF/1767835** |
| Data citation | Roman, Kolka, Griffis and Deventer (2022), AmeriFlux BASE US-MBP |
| FCH4 units | **nmol m⁻² s⁻¹** |

**Reference throughout: Deventer, M.J. et al. (2019),
*Agricultural and Forest Meteorology* **278**, 107638,
doi:[10.1016/j.agrformet.2019.107638](https://doi.org/10.1016/j.agrformet.2019.107638)**,
which characterizes the instrumentation at this exact site. Cited below as
*Deventer et al. (2019)*. Every threshold, rule and precedence decision in this
layer traces to it.

## Pipeline

| Stage | Module | Does |
|---|---|---|
| constants | `src/ingest/site.py` | site identity, DOI, units, published thresholds, seed |
| paths | `src/ingest/paths.py` | resolves repo root by marker directories; all paths relative |
| read + clean | `src/ingest/raw.py` | `raws` sheet → half-hourly frame, `-9999` → NaN, parquet cache |
| diagnose | `src/ingest/clean.py` | column coverage and overlap, derived-subset provenance and rule tests |
| identify + validate | `src/ingest/analyzers.py` | analyzer identification, paired differences, distribution fits, regressions |
| merge | `src/ingest/merge.py` | precedence merge with provenance column |
| quality control | `src/ingest/qc.py` | negative-flux diagnostics against the detection limit |
| aggregate (monthly) | `src/ingest/aggregate.py` | monthly mean, n, sd, se direct from half-hourly |
| aggregate (daily) | `src/ingest/daily.py` | coverage-rule daily means, daily→monthly, diurnal test |
| budgets | `src/ingest/budgets.py` | naive annual integration vs published |
| covariates | `src/ingest/covariates.py` | soil temp, air temp, precip, FCO2, WTE from committed CSVs |
| assemble | `src/ingest/assemble.py` | join onto explicit month grid, write outputs |

Cleaning, aggregation, and covariate assembly are separate modules with no
cross-imports except through `paths` and `site`. Scripts in `scripts/`
orchestrate only. `qc.py` reports and never filters.

## The three methane columns

**They are disjoint in time, not redundant and not processing levels of one another.**

| Column | Valid | First | Last |
|---|---|---|---|
| `FCH4` | 44,427 | 2009-04-23 22:00 | 2021-12-28 09:00 |
| `FCH4_1_1_1` | 15,030 | 2015-01-01 03:00 | 2018-07-11 18:00 |
| `FCH4_1_1_2` | 16,534 | 2015-03-17 13:00 | 2018-12-31 23:30 |

`FCH4` has **zero** co-occurring timestamps with either replicate. It carries
2009–2014 and 2019–2021 and is completely empty across 2015–2018, where the two
replicates take over. The replicates overlap each other on 9,045 timestamps,
correlate 0.860, and agree exactly on only 4 of those — two concurrent sensors,
not one series at two processing levels.

In AmeriFlux BASE the `_H_V_R` suffix is a position/replicate qualifier, so the
unqualified `FCH4` is the site-aggregated variable and `_1_1_1`/`_1_1_2` are
replicates at position 1.

### Analyzer identification

`FCH4_1_1_1` = **closed-path TGA-100A**, `FCH4_1_1_2` = **open-path LI-7700**.
Three independent lines of evidence, none of which assumes the answer:

1. **Start dates.** Deventer et al. (2019) report the LI-7700 was not operated
   before March 2015. `FCH4_1_1_2` begins 2015-03-17; `FCH4_1_1_1` begins
   2015-01-01. Only the stated assignment is consistent.
2. **Retained count.** Deventer et al. (2019) report 15,033 retained TGA
   fluxes. `FCH4_1_1_1` holds **15,030** — a discrepancy of 3 in 15,000
   (0.02%). `FCH4_1_1_2` holds 16,534, off by 1,501.
3. **Regression sign.** Deventer et al. (2019) report a geometric slope of 1.08
   for LI-7700 against TGA, i.e. the LI-7700 carries ~8% more spread. The data
   gives sd(`_1_1_2`)/sd(`_1_1_1`) = 1.086 under screening. Had the labels been
   swapped the slope would be its reciprocal, 0.92, and the published value could
   not be recovered in either direction.

The evidence does not point the other way. The workbook still carries no BADM
metadata, so this rests on Deventer et al. (2019) plus the data, not on the file
itself. The BADM metadata of the 2025 product was obtained later and does not
change that: it carries no instrument group at all, so it is silent on the
identification rather than confirming it. Recorded in `notes/base_v55.md`.

## Derived `FCH4 Data.csv` — selection rule not recovered

Every one of its 27,284 values matches a same-day raw value, so it is a strict
subset of this workbook. Column provenance is clean and fully recovered:

- `FCH4` for 2009–2014 and 2019–2021
- `FCH4_1_1_2` for 2015–2018

(`FCH4_1_1_1` is credited 8 values, all of which are ties where the identical
value also exists in `FCH4_1_1_2` the same day — matching artifacts, not
selections. The greedy multiset match is made deterministic by an explicit sort
in `clean.to_long`, not by a seed.)

**The row-level selection rule within those columns is not recoverable.** The
evidence against each candidate rule:

- 2009 and 2010 are retained at 100%; every other year drops to 9–52%.
- Retention is flat across hour of day (34–39% at every hour) and across the
  half-hour offset — not a daytime or hourly-subsample rule.
- 99.9% of discarded values (48,678 of 48,707) fall *inside* the retained value
  range. No absolute threshold or percentile trim can discard those.
- Per-month k-sigma screens classify rows at 36.7–40.5% accuracy against a
  35.9% base rate — no better than chance.
- Within a single day, retained and discarded values interleave with
  overlapping magnitudes (e.g. 2020-07-16 keeps 83.892 while discarding 89.465
  and 71.820).

The most likely explanation is a manual Excel selection, or a filter on a QC
variable that existed in the original AmeriFlux download but was not carried
into the four-column `raws` export. Either way the rule is unrecoverable, and no
approximation of it has been substituted.

## Source files

Seven files in `CSVs/` are primary and are read by the pipeline:

| File | Used for |
|---|---|
| `FCH4 PivotTable 2009_2021 and Raw Ameriflux Data.xlsx` | raw half-hourly methane, the `raws` sheet |
| `FCH4 Data.csv` | the sub-daily subset derived outside this pipeline |
| `MEF_soil_temp_weekly.csv` | soil temperature readings at 10 cm |
| `Monthly Temperature Average.csv` | air temperature |
| `Monthly Precipitation Average .csv` | precipitation |
| `All Combined Variables Monthly.csv` | carbon dioxide flux |
| `Water Table Elevation (1990 - 2021).csv` | water table elevation |

### External reference, not pipeline input

`CSVs/Delwiche_2020_ESSD_Appendix_B.xlsx` is a reference file. **No module reads
it and it is not wired into the pipeline.** It sits in `CSVs/` alongside the
seven primary files above, but it is not one of them.

It is Appendix B of Delwiche et al. (2021), *Earth System Science Data* **13**,
3607-3689, doi:[10.5194/essd-13-3607-2021](https://doi.org/10.5194/essd-13-3607-2021),
holding site metadata and seasonality parameters for FLUXNET-CH4 Version 1.0.
The file itself is archived at
doi:[10.5281/zenodo.4672601](https://doi.org/10.5281/zenodo.4672601) under
CC-BY-4.0. Added 2026-08-08.

Thirteen sheets: seven data tables, B1 through B7, each of B2 to B7 paired with
a column-description sheet. B3 carries 79 sites and 37 metadata fields; B5
carries 189 site-years of seasonality parameters for methane flux, gross primary
productivity, air temperature and soil temperature; B6 carries 366 site-years of
soil temperature parameters across all probes.

Two findings of Delwiche et al. (2021) were recomputed from the file, because
both bear on which temperature predictors are worth fitting later.

The first is that the spring onset of rising methane lags the onset of soil
warming by about a month. Differencing `Start_FCH4_(DOY)` and `Start_TS_(DOY)`
over the 85 site-years holding both gives a mean of **28.1 days**, which
reproduces that figure. The distribution behind it is skewed: the median is
**12.5 days** and the interquartile range runs from **4 to 56 days**. The mean
is therefore not typical of the sites it summarizes, and a one-month lag is not
a value to carry into a model for this site. Any temperature lag is
site-specific and has to be fitted.

The second is that peak methane timing correlates with neither peak temperature
nor peak productivity. Against `Peak_FCH4_(DOY)`:

| Compared with | n | r | p |
|---|---|---|---|
| `Peak_TA_(DOY)`, air temperature | 125 | +0.048 | 0.59 |
| `Peak_TS_(DOY)`, soil temperature | 108 | −0.011 | 0.91 |
| `Peak_GPP_DT_(DOY)`, gross primary productivity | 118 | −0.166 | 0.072 |

None is significant, reproducing the published result. Taken with the spread in
the onset lag, neither the timing nor the offset of a temperature-driven
seasonal cycle transfers across sites, so a predictor built on either must be
estimated from this site's own record.

**US-MBP is not in it.** The workbook names 65 distinct AmeriFlux sites and none
is US-MBP. No cell anywhere contains "MBP", "Marcell" or "Bog Lake", and no site
lies within 100 km of 47.505 N, -93.489 W; the nearest are US-PFa at 300 km and
US-Los at 310 km. The closest analogues are recorded in the report accompanying
this note rather than here, since the choice between them depends on whether
this site is treated as a bog or a fen.

Fifteen further files were removed from the working tree as derived: rescalings,
annual roll-ups, supersets of files that are read, and one byte-identical
duplicate of the water table file. Everything they held is recomputable from the
seven above. They remain in git history.

Two of them should not be reinstated. `All Combined Variables Normalized.csv`
and `FCH4 Monthly Values.csv` hold series rescaled to the unit interval, and the
minimum and maximum used were taken over the whole record, including the period
the original analysis held out for testing. Any model trained on them has seen
its test set through the scaling constants. `Temperature Monthly Values.csv`,
`Temperature Yearly Values.csv`, `WTE Monthly Values.csv`, `WTE Yearly Values.csv`
and `FCH4 Yearly Values.csv` carry the same defect. Rescaling belongs after a
train/test split, computed from the training partition alone.

## Covariates

All reconstructed from the repository's own CSV files and verified against
known values.

| Covariate | Source | Derivation |
|---|---|---|
| `soil_temp_f` | `MEF_soil_temp_weekly.csv` | mean of `depth10cm` by `Month/Year`, ×9/5+32 |
| `atm_temp_f` | `Monthly Temperature Average.csv` | `Cumulative Temperature Mean (F)` |
| `precip_in` | `Monthly Precipitation Average .csv` | `Cumulative Precipitation Mean` |
| `fco2` | `All Combined Variables Monthly.csv` | `FC02_Avg`, paired with `FCO2 Date-Month` |
| `wte_m` | `Water Table Elevation (1990 - 2021).csv` | `Mean(WTE)` |

`soil_temp_n` is retained alongside the soil temperature mean for the same
reason the methane counts are: monthly means there rest on 17–27 readings.

Water table: of the four files, `Water Table Elevation (1990 - 2021).csv` is the
raw monthly series over the full period. `Monthly Water Table Elevation.csv` is
byte-identical to it (same MD5), `WTE Monthly Values.csv` is a min-max
rescaling, and `Yearly Water Table Average.csv` is annual.

`atm_temp_f` is included because air temperature was the second-strongest
predictor in the earlier analysis of this site. Removing it means deleting
`load_atm_temperature` and its entry in `load_all`.

## Output

`data/processed/monthly_bog_lake_fen.{csv,parquet}` — 153 rows × 19 columns,
one row per month from 2009-04 to 2021-12 inclusive, no month omitted.

Methane columns are `{col}_mean`, `{col}_n`, `{col}_sd`, `{col}_se` for each of
the three raw columns. `_n` is 0 where a month has no observations; `_mean`,
`_sd` and `_se` are NaN there. `_sd` and `_se` are NaN for n = 1.

Nothing in the ingestion path is stochastic, so no seed is consumed. A fixed
`site.SEED = 20150317` is defined for downstream use. The one order-dependent
step (legacy subset matching) is pinned by an explicit sort, not a seed.

## Validation against Deventer et al. (2019)

Paired differences on the 9,045 timestamps where both analyzers reported, using
the sign convention of Deventer et al. (2019) **TGA − LI-7700** (reference minus comparison). That
convention is not stated in the published text; it is the only one giving
a positive median *and* positive skewness, matching the published values.

| Statistic | Paper | This rebuild | |
|---|---|---|---|
| median | 0.1 | **0.130** | ✓ |
| IQR | 8.2 | **8.645** | ✓ +5% |
| σ | 8.5 | **8.819** | ✓ +4% |
| skewness | 0.32 | **0.436** (1% trimmed) | ✓ sign and order |

`σ` is the Laplace standard deviation implied by the IQR (`b = IQR/2ln2`,
`σ = b√2`), not the raw second moment. This matters: the raw moment is **15.85**
and the raw skewness is **−1.43**. Both are dominated by a tail far heavier than
Laplace (excess kurtosis 72.3 against Laplace's 3), and the raw skewness even
flips sign. The published σ of 8.5 with IQR 8.2 is internally consistent only
with a robust scale, since a Laplace with σ = 8.5 implies IQR = 8.33. Reading
the published σ as an empirical standard deviation would have produced a spurious
2× disagreement.

**Laplace versus Gaussian — the published leptokurtic finding reproduces
decisively.** MLE fits over all 9,045 differences:

| | log-likelihood | AIC | KS |
|---|---|---|---|
| Laplace | −34,313.5 | 68,631.1 | **0.058** |
| Gaussian | −37,827.7 | 75,659.4 | 0.168 |

ΔAIC = **7,028** in favor of Laplace, with the KS distance cut by a factor of
three. This is load-bearing for the uncertainty work: a Gaussian error model
would misstate the tails badly.

### Regressions — reproduced, with a caveat stated plainly

The despiking applied by Deventer et al. (2019) is not in the BASE product, so
these statistics were run under a **sweep of nine screens** rather than one,
because a single screen chosen to hit the published number would be circular.
Their wind-sector exclusion, by contrast, is carried in the product: no retained
flux value of any species comes from 30° to 200°, measured in
`notes/base_v55.md`.

| Screen | n | GMR slope | GMR intercept | OLS slope (t vs 1) | OLS intercept (t vs 0) |
|---|---|---|---|---|---|
| none | 9,045 | 0.979 | +0.69 | 0.842 (−30.1) | 5.55 (22.7) |
| \|diff\| ≤ q0.95 | 8,592 | 1.065 | −2.04 | 1.018 (5.5) | −0.43 (−2.9) |
| **\|flux\| < 100 & \|diff\| ≤ q0.98** | 8,553 | **1.086** | **−2.61** | **1.007 (1.7 n.s.)** | **−0.05 (−0.3 n.s.)** |
| *paper* | | *1.08 ± 0.02* | *−3.0 ± 0.8* | *≈1, n.s.* | *≈0, n.s.* |

Unscreened, the GMR slope is 0.979 and does **not** match. Under screening it
converges monotonically toward the published value. The screen in bold was
selected post hoc from the sweep — but it is the only one of the nine where all
four published statements hold at once: GMR slope inside ±0.02, GMR intercept
inside ±0.8, and *both* OLS parameters statistically indistinguishable from 1
and 0. Hitting four independent published targets simultaneously is much weaker
evidence of curve-fitting than hitting one.

**Verdict: reproduced.** The distributional core (median, IQR, robust σ, Laplace
dominance) reproduces without any screening at all. The regression parameters
reproduce under a plausible outlier screen and cannot be reproduced without one,
which is expected given that Deventer et al. (2019) applied despiking the BASE product does
not carry.

## Coverage and the budget-bias test

Deventer et al. (2019) note that open-path systems lose data during freezing or
rainy periods, and that snow cover here lasts roughly 120 days, which predicts
systematically lower winter coverage. **In the merged series that prediction
does not hold:**

| | Coverage | Mean flux |
|---|---|---|
| Cold season (Nov–Mar) | **28.7%** | 14.8 |
| Growing season (Jun–Aug) | **29.8%** | 69.8 |

A ratio of 1.036 — essentially flat. Monthly coverage spans only 24.0% (January)
to 33.4% (April), with no seasonal shape.

Coverage of roughly 30% is not 30% of an attainable 100%. The footprint rule of
Deventer et al. (2019) removes 37.6% of all half-hours, and 41.5% of those
carrying a wind direction, before any instrument or
quality consideration applies, and against what it leaves, methane retention is
60.2%. Measured in `notes/base_v55.md` from the wind direction the 2022 export
does not carry.

Per raw column, over each instrument's own active period, the picture is more
interesting and still not the predicted one:

| Column | Analyzer | Winter | Summer | Summer/winter |
|---|---|---|---|---|
| `FCH4` | site-aggregated | 0.199 | 0.195 | 0.98 |
| `FCH4_1_1_1` | TGA-100A (closed) | 0.215 | 0.265 | **1.23** |
| `FCH4_1_1_2` | LI-7700 (open) | 0.291 | 0.201 | **0.69** |

The open-path LI-7700 loses proportionally more data in *summer*, not winter.
That is physically coherent — open-path windows are degraded by rain, dew and
high humidity, and summer is the wet season here — but the replicate deployments
span only 3.5–4 years, so month-of-year coverage is confounded with when each
instrument happened to be deployed and serviced. Treat the direction as
suggestive, not established.

**Consequence for the annual budgets.** Because coverage is not seasonally skewed at the
merged level, the pooled observed mean is not systematically biased, and the
close agreement of the coverage-scaled budgets with published values is not an
artifact of that mechanism. This was tested directly rather than argued:
`budgets.budget_method_comparison` recomputes each year by weighting every
month's mean by its share of the calendar year, so uneven monthly coverage
cannot tilt the annual mean.

| Year | Pooled-scaled | Calendar-weighted | Published | Divergence | Weighted % of published |
|---|---|---|---|---|---|
| 2015 | 14.25 | **14.31** | 14.3 | −0.5% | **100.1%** |
| 2016 | 19.14 | **18.01** | 19.0 | +6.3% | **94.8%** |
| 2017 | 19.06 | **20.13** | 20.0 | −5.3% | **100.6%** |

The two estimators differ by at most 6.3%, and the sign is inconsistent across
years — noise from uneven monthly coverage, not a directional bias. The
calendar-weighted estimate, which is the defensible one, agrees with the
published budgets at least as well as the pooled estimate did, and every
deviation sits inside the published 7–17% uncertainty. **The agreement
survives the correction.**

The diagnostic behaves as it should on the years already known to be thin: 2013
(4 months of data) diverges by −16.6% and 2014 (10 months) by +13.5%. Divergence
between the two methods is therefore a usable per-year data-quality flag.

## Merge

Sanctioned by **Deventer et al. (2019) recommendation 3**, which permits
combining observations from different measurement systems subject to the flux
uncertainty of a single system — a condition the paired-difference result quantifies
(robust σ ≈ 8.8 nmol m⁻² s⁻¹ between systems).

**Precedence: `FCH4` > `FCH4_1_1_1` (TGA) > `FCH4_1_1_2` (LI-7700).**
Values are selected, never averaged, and `merge.py` writes a `source_column`
and `analyzer` column for every retained value.

Rationale for preferring the TGA where both reported:

- It is the closed-path instrument and the one Deventer et al. (2019) treat as
  the reference — their geometric regression is LI-7700 *against* TGA.
- The paired-difference analysis shows the LI-7700 runs ~8% high with a ≈−3 offset. Choosing one system
  consistently keeps that scale difference at the era boundaries instead of
  injecting it as pseudo-variance at every alternation.
- The TGA starts earlier (2015-01-01 vs 2015-03-17), so preferring it maximizes
  continuity across the 2014/2015 handover.

`FCH4` takes top precedence only because it is temporally disjoint from both
replicates; precedence never actually fires between it and them.

**Validation.** `merge_halfhourly` checks that its precedence names at least one
column and that every named column is present. It does *not* reject overlapping
columns: arbitrating overlap is the merge's purpose, and the TGA-100A and
LI-7700 overlap on 9,045 timestamps by design. Disjointness is a property of a
particular dataset, so it is asserted by the caller — `merge.assert_disjoint`,
which `scripts/04_merge_qc_aggregate.py` applies to the site-aggregated series
against each replicate, the pair that genuinely must never coincide.

**Unavoidable consequence:** the TGA stops 2018-07-11 while the LI-7700 runs to
2018-12-31, so 2018-07-12 onward is LI-7700 regardless of precedence. That
single 2,698-half-hour block carries the inter-analyzer offset relative to
everything before it.

## Quality control

Detection limit from Deventer et al. (2019): **~3 ± 2 nmol m⁻² s⁻¹**. Their
conclusion that measured negative net fluxes are questionable rests on ~70% of
negatives exceeding detection limits while only ~1% appeared concurrently in
both systems. Both halves of that reproduce here (84.7% and 3.0%). No filter has
been applied; the decision is the project owner's.

## Aggregation

Daily means are built under the rule of Deventer et al. (2019): **a day is extrapolated only when
at least 8 valid half-hours exist**, with thresholds of 8, 12 and 16 tested as
that study tests 8 to 16. Monthly values are then the mean of daily means, with
day counts and across-day dispersion retained at both levels.

**Per-analyzer fractions travel with every aggregate.** Because the two systems
interleave at half-hourly scale (2,915 switches, median run 2 half-hours) and
differ by ~8% in scale with a −3 offset, a single day can mix them. The daily
and monthly outputs therefore carry `frac_site_aggregated`, `frac_tga100a`,
`frac_li7700`, `n_analyzers`, and — daily — `is_mixed`, so downstream work can
see which records blend instruments without going back to the half-hourly data.
Monthly fractions are weighted by each day's half-hour count, so they describe
the month's observations rather than its days. **475 of 2,714 days (17.5%) mix
analyzers, across 38 of 142 months.**

Monthly aggregation is justified rather than assumed. Deventer et al. (2019)
found only marginal diurnal variation at this site with variability concentrated
on seasonal timescales, and the data agrees: the half-hour-of-day cycle explains
**0.97%** of half-hourly variance against **37.4%** for month-of-year, an
amplitude ratio of **6.0**, and the hourly means show no coherent diurnal shape
(the growing-season maximum falls at 22:00 and the minimum at 19:00, which is
noise, not a cycle).

## Carbon dioxide

Built by `scripts/05_build_co2.py` from `FC` in the 2025 BASE product, under the
same coverage rule as methane: a daily mean only from days holding at least
eight valid half-hours, then a monthly mean of those daily means, with counts
and dispersion retained at both levels. There is one carbon dioxide column and
no replicates, so no analyzer identification or precedence merge arises.

**The source is the 2025 product rather than the 2022 export**, because that
export carries only the three methane columns. The two were shown to hold
identical methane values over every shared half-hour, so drawing one gas from
each is not a change of source in any material sense. `notes/base_v55.md`
records that comparison.

| | |
|---|---|
| Half-hours, 2009 to 2024 | 280,512, of which 98,006 valid, 34.9% |
| Days meeting the coverage rule | 4,046 of 5,844 |
| Months | 192, 2009-01 to 2024-12, none absent |
| Days per month | median 21, minimum 3; eight months rest on fewer than ten |
| Monthly mean | −1.264, range −4.586 to 0.123 µmol m⁻² s⁻¹ |

### The single-column series it replaces is a straight half-hourly mean

The carbon dioxide the study has used until now is `FC02_Avg` in
`All Combined Variables Monthly.csv`, which carried no provenance, no count and
no dispersion. Its rule is now recovered: it is **the unweighted mean of every
valid half-hour in the month**, which reproduces all 156 of its values to three
decimal places. It is not wrong; it is built by a weaker rule than methane's,
and it weights a month by when observations happened to fall rather than by day.

Against the series built here it correlates 0.9946, with a mean difference of
−0.024 and a median of −0.002. The largest disagreements are in months where
observation counts are uneven across days, 2013-09 differing by 0.79.

### The diurnal problem, which methane does not have

Bringing carbon dioxide to methane's standard fixes the weighting of days. It
does not fix the weighting of hours, and for this gas that is the larger
problem.

| | Methane | Carbon dioxide |
|---|---|---|
| Half-hour of day, share of half-hourly variance | **1.5%** | **29.1%** |
| Month of year, share of half-hourly variance | 41.3% | 22.4% |
| Daylight share of retained observations | | **62.1%**, against 50% if even |

For methane the diurnal cycle is negligible, which is why monthly aggregation
was defensible without further argument. For carbon dioxide it is the dominant
term, daylight is when the ecosystem takes carbon up, and daylight is
over-represented in what the instrument retained.

**The consequence is a seasonal artifact, not a constant offset.** Measured
against a monthly mean that weights every half-hour of the day equally, the
daily-rule series reads:

| | |
|---|---|
| Mean difference | −0.576 µmol m⁻² s⁻¹, 46% of the series' typical magnitude |
| In January | +0.016 |
| In August | **−1.849** |
| Seasonal swing of the difference | 1.865, against a seasonal amplitude of 3.028 |

**About 62% of the carbon dioxide seasonal cycle in the daily-rule series is
therefore a property of when the instrument was sampling rather than of the
peatland.** The same measurement on methane gives a seasonal swing worth 4.3% of
its typical magnitude, so the methane series is not affected in this way.

A diurnally balanced monthly series is written alongside, in
`monthly_fco2_diurnally_balanced.csv`, averaging within half-hour of day and
then across those cells. It can only correct a skew where every half-hour of the
day appears somewhere in the month: 186 of 192 months carry all 48 cells and six
carry 45 to 47, so the correction is close to complete but not exactly so.

### What carbon dioxide will not inherit from methane

- **No logarithm.** The series crosses zero, with 3 of 192 months at or above it
  and 62 of 156 within 0.5 of it, so a log target and percentage error are both
  unavailable.
- **Inverse-variance weighting behaves differently.** Dispersion across days does
  not scale with the mean for a quantity that changes sign, so a weight built
  from it does not mean what it means for methane.
- **The Laplace error finding does not transfer.** Deventer et al. (2019)
  established it for methane from paired analyzers. Carbon dioxide has one
  column and no pair, so nothing here tests the distribution of its error.

## The earlier analysis: supporting evidence

Detail behind the README's account of the analysis this work replaced. Every
statement was checked against the five notebooks as committed, read out of git
history at `891f6d3~1`, rather than against their figures or prose.

**That commit, not the tag, is where the original analysis survives.** The
notebooks, the `assets/` directory and the README that referenced them were
removed by `891f6d3`, so its parent holds the last copy of all three. The tag
`pre-squash-ingestion-layer` is a descendant of that removal and contains none of
them: `assets/` is empty there and the README is the rebuilt one. Anyone reaching
for the tag will find nothing and conclude the material is gone.

### The state-space model was fitted but never committed

No committed cell in any of the five notebooks contains `sarimax`, `arima`,
`statespace`, `pmdarima`, `auto_arima` or `seasonal_order`, in code or markdown.
The only `statsmodels.tsa` import anywhere is `seasonal_decompose` and
`plot_acf`, in `Bog_Lake_Fen.ipynb` cell 76. No text output carries a trace.

Two committed figures are nonetheless state-space output.
`assets/Four_Series_Assessment.png` is the four-panel layout `statsmodels`
produces from `MLEResults.plot_diagnostics()`, with the panel titles
*Standardized residual for "F"*, *Histogram plus estimated density* carrying a
Hist/KDE/N(0,1) legend, *Normal Q-Q*, and *Correlogram*. That method exists only
on state-space results objects. `assets/SARIMAX.png` shows a forecast with a
shaded confidence band extending past the observed record, and no committed cell
calls `conf_int`, `get_forecast`, `get_prediction`, `plot_diagnostics` or
`fill_between`. The notebook that produced both was never committed.

### Diagnostics actually invoked

`Bog_Lake_Fen.ipynb` invokes `sms.het_breuschpagan` (cell 73), `normal_ad`
(cell 69), `durbin_watson` (cell 71) and `influence.resid_studentized_internal`
(cell 66). It prints its own failures: "Residuals are not normally distributed"
at cell 69, and "Signs of positive autocorrelation" with "Assumption not
satisfied" at cell 71.

Two further diagnostics are imported but never called: `het_white`, imported at
cells 0 and 73, and `variance_inflation_factor`, imported at cell 0. There is no
Q-Q plot in that notebook; no cell calls `qqplot` or `probplot`. The Q-Q panel
that appears in the figures belongs to the uncommitted state-space diagnostics.

### Leakage in the rescaled target

The Prophet target was rescaled to the unit interval over the whole record. In
the normalized monthly series the minimum, 0.0, falls at 2010-02 and the
maximum, 1.0, falls at **2017-07**. The split assigns every date after 2017-01
to the test partition, so the maximum lies inside it. That series matches the
notebook's own stored output exactly: 2009-04 = 0.071228, 2021-08 = 0.285278,
2021-12 = 0.031888.

### Metrics computed on one or two points

`make_future_dataframe(periods=59)` uses the default daily frequency, so the
future frame holds 325 month-start history dates plus 59 daily dates running
2017-01-02 to 2017-03-01. The notebook demonstrates this itself: cell 39
inner-merges that frame against the monthly data and its printed tail ends at
index 326 with 2017-03-01, giving 327 rows rather than 384.

Cell 29 then slices `[-16:]`, covering 2017-02-14 to 2017-03-01, all daily, and
inner-merges on `ds` against a month-start test index. One row survives,
2017-03-01, so the reported mean absolute error of 0.0817 is a single absolute
error. Cells 35, 42 and 47 slice `[-59:]` and leave two rows. The ratio
0.08166736 / 5.52435843 = 0.014783 is consistent with a single point.

### Percentage error on a series crossing zero

Carbon dioxide flux runs from −4.464104 to 0.086111 in the Prophet notebook's
own summary at cell 7. In `Multivariate Scalecast.ipynb` cell 29, the elastic
net model reports an in-sample percentage error of 3.4565 with a coefficient of
determination of 0.0000.

### Ensemble composition

Cell 30 of `Multivariate Scalecast.ipynb` builds the stack from `mlr`,
`elasticnet` and `xgboost`, with `KNeighborsRegressor` as the final estimator.
Ranking by `LevelTestSetMAPE` from that notebook's own cell 29 output:

| Rank | Methane flux | Carbon dioxide flux |
|---|---|---|
| 1 | xgboost 0.2764 | xgboost 0.3249 |
| 2 | rf 0.3352 | gbt 0.3785 |
| 3 | knn 0.3445 | mlp 0.4291 |
| 4 | gbt 0.3558 | rf 0.4603 |
| 5 | mlr 0.3859 | knn 0.4767 |
| 6 | elasticnet 0.3991 | mlr 0.8575 |
| 7 | mlp 0.5709 | elasticnet 1.2545 |

The three base estimators rank first, fifth and sixth for methane flux, and
first, sixth and seventh for carbon dioxide flux. `results.loc[...].values[0]`
takes the first matching row, which is the methane row, so methane
hyperparameters are applied to both series.

### Stored outputs span more than one version of the inputs

Execution counts are non-monotonic in four of the five notebooks, so cells were
not run in the order they appear. In the Prophet notebook the same path is read
at cell 3, execution count 4, and again at cell 14, execution count 140. The
first output shows six columns including carbon dioxide flux; the second shows
five, without it, in a different order.

The value 4.23 appears in no notebook source or text output. It occurs in the
title of `assets/Real_vs_Predicted.png`, which spans 2018-01 to 2019-12, and in
the removed README's caption. `Bog_Lake_Fen.ipynb` cells 87 and 89 store figures
titled MAE 7.23 and MAE 7.383, both spanning 2017-01 to 2019-12, matching the
`horizon=12*3` holdout defined at cell 86.

## Open question: the ingestion script numbers

The study scripts were renamed to drop their numeric prefixes, because they run
independently and the numbers recorded only the order in which they were built.

The same argument may apply to the ingestion scripts. They are numbered 01 to
04, but each runs standalone: whichever runs first parses the workbook and
caches it, and none reads another's output. Only `04_merge_qc_aggregate.py`
produces anything the study consumes; 01 to 03 are diagnostic and write either
nothing or an interim file nothing else reads.

What the numbers still carry is reading order. Someone meeting the pipeline for
the first time is better served by working through the column investigation
before the merge that depends on understanding it. Whether that is worth a
naming convention which implies a dependency that does not exist is unresolved.
Nothing has been renamed.
