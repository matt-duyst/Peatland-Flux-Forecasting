# Bog Lake Peatland methane flux: ingestion

This repository turns the raw eddy covariance record from a northern Minnesota
peatland into a monthly dataset suitable for analysis, with every processing
step expressed in code. It contains an ingestion pipeline, a test suite, and
notes recording the decisions the pipeline embodies. It does not contain a
model.

## Site and data

Measurements come from AmeriFlux site **US-MBP**, Marcell Bog Lake Peatland, at
47.505 N, −93.489 W, in the USDA Forest Service Marcell Experimental Forest,
Minnesota. The data product is AmeriFlux BASE, DOI
[10.17190/AMF/1767835](https://doi.org/10.17190/AMF/1767835), cited as Roman,
Kolka, Griffis and Deventer (2022). BASE is AmeriFlux's standardised half-hourly
product; its variable names carry a horizontal, vertical and replicate qualifier
suffix, so `FCH4_1_1_1` and `FCH4_1_1_2` are two replicates at one position
while unqualified `FCH4` is the site-aggregated series.

Methane flux is reported throughout in **nanomoles per square metre per second**
(nmol m⁻² s⁻¹). Annual budgets are expressed in grams of methane per square
metre per year (g-CH₄ m⁻² yr⁻¹).

The instrumentation is described by Deventer et al. (2019), *Agricultural and
Forest Meteorology* **278**, 107638, DOI
[10.1016/j.agrformet.2019.107638](https://doi.org/10.1016/j.agrformet.2019.107638).
Every threshold, detection limit and coverage rule in the pipeline traces to
that paper, and the validation below compares the pipeline's output against its
published statistics.

## What the pipeline does

The raw sheet holds 227,904 half-hourly slots spanning 2009-01-01 to
2021-12-31. Of these, 66,946 carry a methane measurement in at least one of the
three methane columns, and 44,427 carry one in the site-aggregated column; the
remainder are marked with the value −9999. The pipeline replaces that sentinel
with a null value, identifies which analyser produced each of the three columns,
merges them into a single series by precedence while recording which instrument
each retained value came from, reports diagnostics on negative fluxes against
the published detection limit, and aggregates to daily and monthly resolution.

Aggregation retains the weight of evidence behind every mean. A month built from
two half-hourly observations is not interchangeable with one built from several
hundred, so each aggregate carries its observation count, standard deviation and
standard error. The monthly grid is explicit: every month in the target span has
a row, including months with no methane data, so the series is regularly spaced
by construction rather than silently collapsed.

Covariates are reconstructed from the primary files in `CSVs/` rather than from
any pre-joined intermediate: soil temperature at 10 cm, air temperature,
precipitation, carbon dioxide flux and water table elevation.

## Validation against Deventer et al. (2019)

Three results are reproduced from the published characterisation of this site.
These are the only figures in this document, and they are here because they are
checks against an external result rather than findings of this work.

**Analyser identification.** The two 2015–2018 methane columns are identified as
`FCH4_1_1_1` = closed-path TGA-100A and `FCH4_1_1_2` = open-path LI-7700, on
three independent grounds. Deventer et al. report that the LI-7700 was not
operated before March 2015; `FCH4_1_1_2` begins 2015-03-17 while `FCH4_1_1_1`
begins 2015-01-01. They report 15,033 retained TGA-100A fluxes; `FCH4_1_1_1`
holds 15,030, a difference of three, while `FCH4_1_1_2` holds 16,534. They
report a reduced major axis slope of 1.08 for the LI-7700 against the TGA-100A,
implying the open-path instrument carries about 8% more spread; the data gives a
ratio of standard deviations of 1.086 under outlier screening, which under the
opposite assignment would have to be its reciprocal.

**Paired differences.** On the 9,045 timestamps where both analysers reported,
taking the difference as TGA-100A minus LI-7700:

| Statistic | Published | This pipeline |
|---|---|---|
| Median | 0.1 | 0.130 |
| Interquartile range | 8.2 | 8.645 |
| Standard deviation | 8.5 | 8.819 |
| Skewness | 0.32 | 0.436 |

The standard deviation here is the one implied by the interquartile range under
a Laplace distribution, not the raw second moment. That distinction is not
cosmetic: the raw second moment of these differences is 15.852 and their raw
skewness is −1.432, both dominated by a tail heavier than Laplace, and the raw
skewness even carries the opposite sign. A Laplace distribution with a standard
deviation of 8.5 implies an interquartile range of 8.33, close to the published
8.2, so the published figures are internally consistent only under the robust
reading.

**Error distribution.** Deventer et al. find that flux errors at this site are
leptokurtic rather than normal. Fitting both distributions to the same 9,045
differences by maximum likelihood:

| Distribution | Log-likelihood | Akaike information criterion | Kolmogorov–Smirnov distance |
|---|---|---|---|
| Laplace | −34,313.5 | 68,631.1 | 0.058 |
| Gaussian | −37,827.7 | 75,659.4 | 0.168 |

The difference in the Akaike information criterion is 7,028 in favour of
Laplace, and the Kolmogorov–Smirnov distance is smaller by a factor of three.
The excess kurtosis of the differences is 72.3, against 0 for a Gaussian and 3
for a Laplace, so the tail is heavier than either.

## What is not implemented

There is no model here, and no gap-filling. That bounds what can be said about
annual totals. Summing only the half-hours that were actually measured recovers
25.1%, 29.1% and 36.1% of the published annual budget for 2015, 2016 and 2017
respectively, against a published total uncertainty of 7 to 17%. Between 64 and
75 percent of an annual budget at this site therefore rests on inference about
unobserved periods rather than on measurement. Any gap-filling method chosen
later will determine most of the answer, and is not a refinement of it.

## Installation

Requires Python 3.11. Dependencies are pinned exactly in `requirements.txt`.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running the pipeline

Requires Python 3.11 and the pinned dependencies above.

The ingestion scripts are numbered because they are meant to be read in that
order, not because each depends on the last. Any one of them runs on its own;
whichever runs first parses the Excel workbook, which takes a few seconds, and
caches the parsed frame under `data/interim/` for every later run.

```
.venv/bin/python scripts/01_investigate_raw.py
.venv/bin/python scripts/02_build_monthly.py
.venv/bin/python scripts/03_verify_analyzers.py
.venv/bin/python scripts/04_merge_qc_aggregate.py
```

`01_investigate_raw.py` reports how many valid observations each of the three
methane columns holds, their temporal coverage and overlap, and which column
supplied each value in the derived `CSVs/FCH4 Data.csv`. It also tests whether
any threshold or dispersion rule reproduces that file's row selection. It writes
`data/interim/derived_labelled.parquet`.

`02_build_monthly.py` verifies each reconstructed covariate against known
values, reports coverage against the target span, and writes the monthly dataset
of methane aggregates and covariates to
`data/processed/monthly_bog_lake_fen.{csv,parquet}`.

`03_verify_analyzers.py` produces the identification evidence and the
distributional comparisons in the validation section above. It prints only and
writes nothing.

`04_merge_qc_aggregate.py` merges the three methane columns with per-value
provenance, reports negative-flux and coverage diagnostics, aggregates to daily
and monthly resolution, and integrates annual budgets from observed half-hours.
It writes `data/processed/halfhourly_merged.{csv,parquet}`,
`data/processed/daily_fch4.{csv,parquet}` and
`data/processed/monthly_fch4_from_daily.{csv,parquet}`.

The merged half-hourly output is not tracked, being large and regenerable; the
daily and monthly outputs are.

## Running the study

The study scripts are unnumbered because they do not form a sequence. Each is
independent of the others and can be run alone, in any order. All four read
`data/processed/monthly_fch4_from_daily.csv`, so `04_merge_qc_aggregate.py` must
have run at least once first; nothing else is required.

```
.venv/bin/python scripts/prepare_study.py
.venv/bin/python scripts/holdout_experiments.py
.venv/bin/python scripts/bias_and_validation.py
.venv/bin/python scripts/reconstruct.py
```

`prepare_study.py` establishes the window a model can be fitted on and the
window it would have to answer for, and reports how far the second lies outside
the range of the first.

`holdout_experiments.py` withholds four blocks of the fit window in turn, each
chosen to resemble the reconstruction problem, and reports error, interval
coverage and covariate distance from the training set for each.

`bias_and_validation.py` states the sign convention for error, reports the
direction each holdout errs in, and compares withheld predictions for 2009 to
2011 against Olson et al. (2013).

`reconstruct.py` projects the fitted model back to 1990. It also runs the
coefficient stability test, whose result determines how the projection can be
read; that test has no separate entry point.

None of the study scripts writes to `data/`.

## Tests

```
.venv/bin/python -m pytest tests
```

The suite runs entirely on synthetic frames built in memory. No test reads the
workbook, any file in `CSVs/`, or anything under `data/`, and expected values
are derivable by hand rather than taken from previous output. It covers the code
paths a production run never exercises, such as a single-column merge precedence
or a series containing no negative fluxes, together with the contracts the
pipeline depends on: that provenance fractions sum to one, that merged values
are selected from one instrument rather than averaged across two, and that no
timestamp appears twice.

## Layout

```
CSVs/               seven primary source files, including the Excel workbook,
                    and one external reference the pipeline does not read
Project_Write-Up/   report from the earlier analysis of this data
data/processed/     pipeline output
data/interim/       cached intermediates, not tracked
notes/              decisions, judgment calls, and what could not be recovered
scripts/            runnable entry points: ingestion numbered, study not
src/ingest/         the ingestion pipeline
src/study/          the analysis built on it
tests/              offline test suite
```

`notes/ingestion.md` is the substantive record. It documents the merge
precedence and its rationale, the quality-control diagnostics, the reasoning
behind the aggregation rules, and the parts of the original processing that
could not be reconstructed.

## Earlier analysis in this repository

This repository previously held a different analysis of the same site: five
Jupyter notebooks, a set of figures, and a README describing the results. That
work was removed from the working tree and remains in git history.

Parts of it are sound. `Bog_Lake_Fen.ipynb` fits an ordinary least squares
regression of methane flux on its covariates, then tests the assumptions that
regression rests on with Breusch-Pagan, Anderson-Darling and Durbin-Watson
tests and internally studentized residuals, and prints the results against
itself: the residuals are not normally distributed and the errors are
positively autocorrelated. `Multivariate Scalecast.ipynb` is built on a
defensible forecasting design, checking stationarity with an Augmented
Dickey-Fuller test, inspecting the autocorrelation and partial autocorrelation
functions, splitting the series temporally with a separate validation partition
for tuning, and using autoregressive lags of the target as predictors.

Its deepest problem is leakage. The Facebook Prophet target was rescaled to the
unit interval using the minimum and maximum of the whole record, and the
maximum falls at 2017-07, inside the held-out test period, so a test observation
sets a constant applied to the training target. Beyond that, most of the models
estimate flux from soil temperature, air temperature, carbon dioxide flux and
precipitation measured at the same timestamp as the flux itself, which is a
different task from forecasting flux that has not yet occurred, though the
earlier README presents them as forecasts. Smaller errors compound this. The
mean absolute percentage error was misread by a factor of one hundred, since
scikit-learn returns a ratio and 5.5243 was reported as 5.5 percent when it
means 552 percent. Model selection in the Scalecast notebook used test-set
performance after tuning. And percentage error is not interpretable for the
carbon dioxide flux series, which crosses zero.

Some reported figures cannot be traced to committed code. The earlier README
describes a seasonal autoregressive integrated moving average model with
exogenous regressors, abbreviated SARIMAX. No such code was committed, though
two of the figures are output only a state-space model produces, so it was
fitted in a notebook that never reached the repository. The mean absolute error
of 4.23 attributed to it appears only as a chart title, where the committed
notebooks give 7.23 and 7.383 from a gradient boosting model. The described
ensemble of the three lowest-error models in fact combines those ranked first,
fifth and sixth of seven. Stored outputs cannot settle these questions, because
execution counts are non-monotonic in four of the five notebooks and the Prophet
notebook reads one file twice with different columns, so the outputs span more
than one version of the inputs. The notebooks also read from absolute filesystem
paths on a personal machine, and of the thirteen filenames they load only
`All Combined Variables Monthly.csv` exists here under that name, with different
columns. That work is preserved in history as a record. It is not runnable, its
numbers should not be cited, and `notes/ingestion.md` records the evidence
behind each finding above.
