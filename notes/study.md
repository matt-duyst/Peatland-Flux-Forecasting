# The study: temporal generalisation at US-MBP

The counterpart to `notes/ingestion.md`. That document records how the monthly
dataset was built; this one records what was asked of it, what the answers rest
on, and what could not be resolved.

Quantities described as published come from the sources cited here. Those papers
are not held in this repository, so statements about their contents rest on the
project owner's reading of them rather than on anything checkable in the tree.
Quantities described as produced here come from this pipeline, and the script or
module that produces each is named.

## The question

How much methane did this peatland emit before flux measurements began in 2009,
and how well does a model fitted on the observed record answer for a period it
has never seen. The second clause is the study. A reconstruction that cannot be
tested is an assertion; the question is whether the relationship fitted on
2009-2019 transfers backward at all.

The precedent is Olson, D. M., Griffis, T. J., Noormets, A., Kolka, R., and
Chen, J. (2013), *Interannual, seasonal, and retrospective analysis of the
methane and carbon dioxide budgets of a temperate peatland*, Journal of
Geophysical Research: Biogeosciences **118**, 226-238,
doi:[10.1002/jgrg.20031](https://doi.org/10.1002/jgrg.20031). Working from three
years of eddy covariance at this site, Olson et al. reconstructed 1991 to 2011
by fitting functional relationships to the short flux record and applying them to
long-term hydrometeorological records, reporting +7.8 to +15.2 ± 2.7 g C m⁻²
yr⁻¹. This study uses the same approach over a decade more flux data, which
makes agreement with it method agreement rather than confirmation.

Olson et al. report carbon mass; the other site reference reports methane mass.
One gram of methane carries 0.74868 g of carbon, and one gram of carbon carried
as methane is 1.33569 g of methane, by the ratio of molar masses 12.011 and
16.043. Both conventions appear below and each figure states which it uses.
The conversion is implemented in `src/study/targets.py`.

## Windows

The fit window is every month carrying both a methane observation and a complete
covariate set. The reconstruction window is every complete-covariate month
before the flux record begins. Both are built by `src/study/windows.py` and
reported by `scripts/prepare_study.py`.

**The fit window is 115 months.** Two months of 2019 are excluded as instrument
artifacts, for the reasons set out under support below; the study was first run
on all 117 and both configurations are reported where they differ.

| Window | Months | Span | Absent from span |
|---|---|---|---|
| Fit | **115** | 2009-04 to 2019-12 (129) | 12, plus 2 excluded |
| Reconstruction | **230** | 1990-01 to 2009-03 (231) | 1 |

Covariate coverage over the full record:

| Covariate | First | Last | Months | Interior gaps |
|---|---|---|---|---|
| Soil temperature at 10 cm | 1989-07 | 2021-06 | 383 | 2011-02 |
| Air temperature | 1990-01 | 2019-12 | 360 | none |
| Precipitation | 1990-01 | 2019-12 | 360 | none |
| Water table elevation | 1990-01 | 2021-01 | 371 | 1995-02, 2020-02 |
| Carbon dioxide flux | 2009-01 | 2021-12 | 156 | none |

The window is bounded by the weakest covariate, not the strongest. Air
temperature and precipitation both end 2019-12, and that boundary **discards
twenty-five months of methane record** the ingestion layer recovered: all of
2020 and 2021, plus 2011-02, which lacks soil temperature. A fifth of the
usable flux record cannot enter a model that needs those two covariates.

Carbon dioxide flux is excluded from the reconstruction covariates. It begins in
2009-01 alongside the methane record and holds no earlier values, so including
it would leave a reconstruction window of zero months. It remains available for
a contemporaneous model, but not for this question.

## Support

A model interpolates only where the period it is applied to falls inside the
range it was fitted on. Comparison is in `src/study/support.py`.

| Covariate | Fit range | Reconstruction range | Months outside |
|---|---|---|---|
| Soil temperature | 26.75 to 65.04 | 23.29 to 62.89 | 2 (0.9%) |
| Air temperature | −2.37 to 70.36 | −6.09 to 68.96 | 3 (1.3%) |
| Precipitation | 0.020 to 0.730 | 0.010 to 0.890 | 5 (2.2%) |
| **Water table** | **413.13 to 413.46** | **413.07 to 413.75** | **113 (49.1%)** |

**117 of 230 reconstruction months, 50.9%, hold at least one covariate outside
the fitted range**, and water table accounts for almost all of it: 107 above the
maximum and 6 below the minimum. On the nominal 117-month window the water table
fit range reads 412.51 to 413.46 with 107 months outside, and 111 of 230, 48.3%,
outside on any covariate; `scripts/prepare_study.py` now emits the adopted
figures and reports both window sizes above them. Temperature
and precipitation excursions are isolated single months of negligible size; the
largest precipitation excess is 0.005 on a range 0.71 wide.

The water table excursions are not scattered. They form long consecutive runs:
1995-03 to 1998-10 is 44 months, 1999-04 to 2001-01 is 22, and 2001-05 to
2003-01 is 21. The maximum excess is 0.29 m above a fitted range itself only
0.95 m wide.

The joint picture identifies a partly different set than the univariate one.
In covariate space standardized on the fit window, fit months sit a median 0.409
from their nearest neighbor with a 95th percentile of 0.791. Reconstruction
months sit a median 0.714 from the nearest fit month, and **110 of 230 lie
beyond that 95th percentile**, reaching 2.874. Roughly the same fraction fails
on both measures, but not the same months: falling inside every covariate's
range separately does not place a month inside the region the fit window
actually occupies.

Water table also differs between the periods in distribution, not only in range.
Tested in `src/study/stationarity.py`, the reconstruction period is wetter by
0.140 m, a standardized difference of 0.902 with Cliff's delta 0.471 and
Mann-Whitney p below 0.0001, and the result holds on anomalies from the
month-of-year mean, so it is not an artifact of month composition. Air
temperature shows no raw difference but is 1.59 °F cooler once deseasonalised
(p = 0.0009). Soil temperature and precipitation show no difference either way.

The reason is visible in the annual means. Water table sits near 413.5 to 413.6
through the 1990s and declines steadily to 413.14 to 413.18 by 2007 to 2009.
**The fit window opens in 2009, after the decline.** The model never sees the
hydrological state that prevailed through most of the period it is asked to
reconstruct. Restricting to the contrast Olson et al. (2013) drew, 1991-1999
against 2007-2011, water table falls 0.275 m with p below 0.0001, while soil
temperature, air temperature and precipitation show no significant difference.

### The fitted range is far narrower than its bounds suggest

The fitted water table range of 412.51 to 413.46 m is 0.95 m wide, but **115 of
the 117 months then in the window occupy only 0.33 m**, from 413.13 to 413.46. The whole
lower half of the nominal range rests on two months, 2019-06 and 2019-09.

**Those two months are not credible as water table.** The evidence, from
`covariates.load_all` and the monthly record:

| | |
|---|---|
| Size of the excursions | −0.83 m in 2019-06 and −0.84 m in 2019-09 |
| Rank among 358 monthly changes to 2019-12 | the four largest are these two drops and their two recoveries |
| In standard deviations of monthly change | ±8.3 to ±8.6 |
| Recovery | +0.82 m the following month, then +0.85 m the following month, each returning to within 0.01 m of the prior level |
| Against the same calendar month, 1990 to 2019 | 2019-06 is the lowest June by 0.58 m; 2019-09 is the lowest September by 0.58 m |
| Precipitation in those months | 2019-06 at the 13th percentile for June, **2019-09 at the 83rd percentile for September** |

A peatland water table does not fall 0.84 m in a month and return within the next
one, twice in a season, by nearly identical amounts. The second excursion falls
in a wetter-than-usual September, where a drawdown of that size has no driver at
all. Both are more consistent with an instrument or transcription fault than with
hydrology. Adding exactly 1.00 m to each turns both into ordinary months, which
suggests the specific fault, but that is a hypothesis and is not adopted: it
would raise the fitted maximum to 413.58 and cut the months outside support from
111 to 59, which is the direction that flatters the model. **The two months are
treated as missing rather than corrected**, which assumes nothing.

**Recomputing support on the effective range tightens the finding.** Dropping the
two months moves no other covariate's range:

| | Nominal | Effective |
|---|---|---|
| Fitted water table range | 412.51 to 413.46 | **413.13 to 413.46** |
| Reconstruction months above the maximum | 107 | **107** |
| Reconstruction months below the minimum | 0 | **6** |
| Months outside on any covariate | 111 of 230, 48.3% | **117 of 230, 50.9%** |
| Years wholly inside support | 6 of 20 | **4 of 20** |

The upper bound does not move, so the headline excursion is untouched: 107
months, reaching 0.29 m past anything fitted. Six months of 2007 to 2009 fall
below the narrowed minimum, all by 0.06 m or less, and they carry **2008 and
2009 from inside support to outside**. Those two verdicts turn on margins of 0.01
to 0.06 m and should be read as marginal rather than as a change of kind.

**The study was refitted on the 115 months and the effective window adopted.**
Fitting on values established as instrument error is fitting on instrument error,
and the two months carried 22.3% of the design's leverage in the water table
dimension on 1.7% of the rows. Both configurations are set out below, because two
claims the study previously made turn out to have depended on the artifacts.

| | Nominal, 117 | Effective, 115 |
|---|---|---|
| Soil temperature slope, unweighted | 0.09781 | 0.09418 |
| Soil temperature slope, weighted | 0.08883 | 0.08806 |
| **Q10, unweighted** | **2.66** | **2.56** |
| **Q10, weighted** | **2.43** | **2.41** |
| Water table coefficient, unweighted | 1.826 | **2.385**, +30.6% |
| Water table coefficient, weighted | 2.564 | **2.704**, +5.5% |
| Clamp bounds | 412.51 to 413.46 | **413.13 to 413.46** |

Every Q10 stays inside the published interval of 1.9 to 4.3, under both
estimators and across all sixteen holdout fits, whose range on the adopted window
is **2.36 to 3.10**. The eight fits carrying the water table term, which is the
model the study uses, range **2.36 to 2.65**; the eight without it reach 3.10. Two
earlier versions of this line were wrong in different ways: one gave 2.33 to 2.72
for all sixteen, which was the with-water-table subset mislabeled, and the
correction to that used the nominal window's values, 2.33 to 3.10 and 2.33 to
2.72. The
water table coefficient steepens, and it steepens six times more without
weighting than with it, because inverse-variance weighting had already discounted
the two months to 0.28% of total weight against a 1.71% equal share.

**The 115-month configuration was not produced by any committed script, and that
was a defect.** `src/study/windows.py` had no exclusion parameter, so
`prepare_study.py`, `reconstruct.py`, `holdout_experiments.py` and
`bias_and_validation.py` all built their window from `build_windows` and all ran
on the nominal 117. The two artifact months were named only in
`src/study/figures.py` and applied only by `make_figures.py`, so **the figures
described the adopted window while every table beside them described a different
one**, and the adopted numbers existed only in prose here.

This is the same class of defect the rebuild was undertaken to fix. The original
analysis was untrustworthy in part because a filtering step lived outside the
repository and could not be rerun; an adopted window that lives only in prose is
a smaller instance of the same thing.

**It is now closed.** `WATER_TABLE_ARTIFACTS` lives in `study.windows`, which is
the single source; `build_windows` takes an `exclude` parameter defaulting to it
and returns `fit`, `fit_nominal` and `excluded` so both configurations are
available without rebuilding; `study.figures` re-exports the constant rather than
declaring its own, and a test asserts the two are the same object; and every
script prints which window it used before any number. Passing `exclude=()`
recovers the nominal window. Two further literals were removed at the same time:
`scripts/reconstruct.py` pinned the wettest-band bias at 0.148 and the
backward-transfer coverages at 84.4% and 62.5%, all three of which described the
nominal window, and all three are now computed from the window in use.

**A fourth instance, found later.** `ingest.assemble.TARGET_END` was the literal
`"2021-12"`, the last month of the 2022 workbook export. When methane moved to
the 2025 BASE product it would have left `monthly_bog_lake_fen.csv` ending three
years short of every other methane output, and nothing would have failed: the
grid would simply have stopped, regularly spaced and wrong. It is now `"2024-12"`
with the reason at the constant. **This is the same class as the three above** —
the window exclusion living in the figure module, the pinned wettest-band bias,
the pinned backward-transfer coverages — a value that describes the data sitting
as a constant rather than being derived from it. Four instances is enough to call
it a pattern in this repository rather than three accidents. A fifth followed,
and the class turned out to be wider than a pinned value: see **The pattern:
reimplemented beside itself** below, which collects all five.

**Everything below is the adopted window as the committed scripts now produce it.
Numbers that moved when the pipeline caught up with the prose are noted where
they appear.**

**The reconstruction does not move materially.** Every year rises by 1.2 to 4.1%,
the largest absolute change being 0.69 g C m⁻² yr⁻¹, and the mean over twenty
years goes from 13.78 to 14.24. All of that sits far inside the sensitivity
spans, whose median is 44%. The years carrying the pending independent check,
1991 and 1992, remain inside support under both windows.

## Model form

Built in `src/study/features.py`, fitted in `src/study/fitting.py`.

The target is the logarithm of the monthly mean flux. Soil temperature enters as
degrees Celsius, linear on that scale, which makes the response a first-order
exponential and its slope a Q10. That form is taken from Deventer, M. J.,
Griffis, T. J., Roman, D. T., Kolka, R. K., Wood, J. D., Erickson, M., Baker,
J. M., and Millet, D. B. (2019), *Error characterization of methane fluxes and
budgets derived from a long-term comparison of open- and closed-path eddy
covariance systems*, Agricultural and Forest Meteorology **278**, 107638,
doi:[10.1016/j.agrformet.2019.107638](https://doi.org/10.1016/j.agrformet.2019.107638),
who fitted a first-order exponential of daily flux to soil temperature at 10 cm
at this site. Choosing a measured form rather than a flexible one matters
because extrapolation behavior, not in-sample fit, is what this study tests.

That paper states the response function and its estimator in section 2.5, page
5, as F(Tsoil) = a·exp(b·Tsoil) with Q10 = exp(10b), the coefficients obtained
by least absolute residual optimisation.

**The estimator used here is the published one.** Least absolute deviations was
chosen from that paper's finding that flux errors at this site are Laplace, of
which it is the maximum likelihood estimator, and not from any knowledge of how
the paper fitted its own curve, which was established only when the figures were
examined. Arriving independently at both the response function and the
estimator that the only published fit at this site used is the strongest
independent check the model form has. It is a check on form, not on values: the
same estimator applied to a different aggregation of the same site can still
disagree, and the Q10 comparison below is what tests that.

The paper reports three Q10 figures that do not at first agree, and it is worth
recording where each comes from because the model form here is checked against
them.

| Value | Location | Basis |
|---|---|---|
| 2.9, 95% interval 1.9 to 4.3 | section 3.4.1, page 9 | stated with R² 0.88 and RMSE 9.5 |
| 3.00, bounds 2.72 to 3.00 | figure 9 caption, page 10 | exponent b = 0.11 with 90% prediction bounds [0.10, 0.11] |
| 2.3 to about 3.1 | page 10 | per-year values, 2015 lowest |

The three are reconcilable. The figure prints b to two decimal places, and
b = 0.106, which is ln(2.9)/10, rounds to 0.11; its bounds are the parameter
bounds of a single pooled fit and are correspondingly tight. The wider interval
of 1.9 to 4.3 is quoted for the same fit statistics but is far too wide to be
that fit's parameter uncertainty, and section 2.5 describes total uncertainty
for this approach as the range across fifty separate extrapolations, each with
its own soil temperature regression. The wider interval is therefore consistent
with variation across those replicates and across years rather than with the
standard error of one fit, though the paper does not say so explicitly and this
reconciliation is inference rather than something stated.

**The value used for comparison here is 2.9 with an interval of 1.9 to 4.3**,
as the paper's headline figure. Fitted on the 115 months, the Q10 is **2.56**
unweighted, from a soil temperature slope of 0.09418, and 2.41 weighted. Across
the sixteen holdout fits it ranges **2.36 to 3.10**, and across the eight that
carry the water table term **2.36 to 2.65**. On the nominal 117 it was 2.66
unweighted and 2.43 weighted, with holdout ranges of 2.33 to 3.10 and 2.33 to
2.72.

**Every one of those values falls inside the published interval of 1.9 to 4.3**,
under both estimators and across all four holdouts, and the whole holdout range
also sits inside the 2.3 to 3.1 the paper reports across its own years. The
agreement therefore does not depend on which estimator is used or on which block
of the record is withheld. Q10 is the coefficient in this model that behaves most
nearly as a property of the site rather than of the sample, which is the contrast
the water table result below draws. Most nearly rather than entirely: narrowing
the fitted range moves it 16% under weighting, against the water table's 51%.

Water table enters clamped to the range seen in training: beyond that range the
term holds at its edge value. Deventer et al. (2019) report that the water table
response at this site is more complex than the soil temperature response and
follows neither a linear nor a log-linear form, so no functional form is
available to extrapolate with. Clamping asserts no trend where there is no
evidence, which is the conservative choice and the only one that states its
assumption legibly.

The estimator is least absolute deviations, which is maximum likelihood under
Laplace errors. Deventer et al. (2019) established that flux errors at this site
follow a Laplace rather than a Gaussian distribution. Their figure 4, page 8,
separates the two kinds of quantity across its two panels. Panel a annotates the
sample statistics of the paired differences, median 0.1, kurtosis 7.8 and
skewness 0.32, over a histogram with a fitted Laplace density overlaid. Panel b
gives the cumulative form, and its legend reads Laplace with mu = 0.05 and
sigma = 8.5, against a normal distribution drawn for comparison. **The 8.5 is
therefore a parameter of the fitted Laplace distribution and not the sample
standard deviation of the differences**, which the figure states rather than
leaves to be inferred from the text. The caption of the following figure names
sigma the standard deviation of the fitted Laplace, which is how the constant is
described in the ingestion layer. That layer reproduced the distributional
finding independently, with a difference in the Akaike information criterion of
7,028 in favor of Laplace.
Intervals are the empirical quantiles of the training residuals, which assume no
distributional form at all, with a Laplace variant widened by each month's own
standard error.

The fit is solved as a linear program, so nothing in the estimator is
stochastic. The only stochastic step in the study is the bootstrap in
`src/study/stability.py`, whose seed is fixed at 20110801 and reported with its
results.

Weighting is by inverse variance, using the standard errors the ingestion layer
carries on each monthly mean. It is not a neutral choice: it reduces effective
sample size from 115 to 42.11 and gives July and August 1.8% and 1.3% of total
weight against an equal share of 8.3%, because high-flux months are variable
months. It was adopted because it was the most consistent configuration across
all four holdout experiments, not on principle.

## Held-out experiments

Four blocks of the fit window are withheld in turn by `src/study/holdout.py`,
each chosen to resemble the reconstruction problem. Weighted full model, 90%
nominal intervals:

| Withheld | MedAE (log) | MAPE | Coverage |
|---|---|---|---|
| Wettest decile | 0.204 | 24.6% | 0.750 |
| Coldest decile | 0.240 | 25.8% | 0.833 |
| Earliest three years | 0.242 | 30.8% | 0.875 |
| Latest three years | 0.164 | 18.9% | 0.941 |

On the nominal 117 these read 0.188/20.2%/0.833, 0.246/25.8%/0.917,
0.232/31.5%/0.844 and 0.174/20.5%/0.889. The wettest-decile coverage falls from
0.833 to 0.750 on the adopted window, which is the one place narrowing the window
makes a holdout look worse. **That drop is one month.** The wettest decile is
twelve test months, so 0.833 is ten of twelve covered and 0.750 is nine of
twelve; a single month changed side. It should not be read as a trend, and no
quantity in this study turns on it.

Unweighted backward transfer was reported as 50.2% MAPE at 62.5% coverage on the
nominal window, and that number was **substantially an artifact of the two
excluded months**. On the 115-month window the same experiment gives **30.1% MAPE
at 87.5% coverage**, which is not a failure. The striking figure did not survive
the check, and establishing that here is what the check existed for.

The wettest-decile test is the closest available analogue of the reconstruction
problem and the model passes it. That result is weaker than it sounds. A holdout
drawn from inside the record can only reach the record's edge: the wettest
decile extrapolates 0.05 m past its training range, against the 0.29 m the
reconstruction demands, so it covers **17% of the required extrapolation**.
Passing it rules out the cheapest failure mode and nothing more.

### The wettest-decile holdout is unstable under ties

Moving to the 115-month window appeared to worsen the wettest-decile holdout,
weighted mean absolute percentage error rising 20.2 to 24.6 and coverage falling
0.833 to 0.750. **That is neither a harder test nor a loss of skill. It is a
different set of months.**

Ten fit months share a water table of exactly 413.41 m. The decile takes twelve
months, and the twelfth and thirteenth wettest are both 413.41, so the cut falls
inside the tie and which months enter the holdout is settled by sort order rather
than by water table. Removing two months from the frame changes that order:
the nominal window holds out 2014-09 and 2019-05, the effective window holds out
2016-05 and 2017-08, and all four sit at 413.41.

Nothing about the model differs. The water table coefficient is 2.721 in both,
the clamp is 413.41 in both, the reach beyond the training maximum is 0.050 m in
both, and the ten shared months receive predictions identical to the cent. The
whole difference comes from the swapped pair: the two months unique to the
nominal window err by 11.8% and 33.5%, the two unique to the effective window by
74.9% and 22.7%.

The training range does narrow at the dry end, 0.900 m to 0.280 m, which lifts
that same 0.050 m reach from 5.6% to 17.9% of the range. It had no effect on the
predictions, because the clamp ceiling and the coefficient are unchanged and no
held-out month lies near the lower bound.

**The consequence is that the wettest-decile figures are not determinate.** They
depend on an arbitrary tie-break, and the same is true of any decile cut landing
inside a tie in this record. `holdout.wettest_decile` has not been changed, since
altering the selection rule would move published numbers again; the instability
is recorded here so the figures are read as approximate.

## Coefficient stability

Whether a coefficient can be projected beyond its observed range is testable
without leaving the record: refit on progressively drier subsets and watch it as
its supporting range narrows. A coefficient that is a property of the system
holds; one that is a property of the sample moves.

Water table coefficient, 500 bootstrap resamples per step, seed 20110801:

| Wettest months dropped | Unweighted | 95% interval | Weighted | 95% interval |
|---|---|---|---|---|
| none | 1.826 | −0.016 to 2.912 | 2.564 | 2.064 to 4.245 |
| 10% | 1.995 | −0.048 to 3.004 | 2.721 | 2.151 to 4.452 |
| 20% | 1.953 | −0.073 to 3.325 | 2.864 | 2.265 to 4.973 |
| 30% | 1.833 | −0.223 to 3.289 | 3.303 | 2.504 to 5.461 |
| 40% | 0.867 | −0.363 to 3.742 | **4.077** | 2.462 to 6.716 |

Both configurations fail, and they failed on the nominal window for different
reasons. Unweighted, the coefficient was not distinguishable from zero at any
step and drifted 62% downward; **that too was partly an artifact**. On the
115-month window the unweighted path never spans zero at any step and climbs
2.385 to 3.299, a 38% rise, so the second of the two claims does not survive
either. Weighted, the coefficient climbs 2.704 to 4.077 on the effective window
against 2.564 to 4.077 on the nominal, a 51% rise with a rank correlation against
the share removed of +1.00 at p below 0.0001.

**The verdict is unchanged on both windows and under both weightings**: the
coefficient drifts by more than a quarter of its full-range value and trends
monotonically as the range narrows.

**The Q10 along the same path is a contrast of degree under weighting and of kind
only without it, and this note previously said it stays stable across every
path.** Weighted, it runs 2.412, 2.438, 2.656, 2.757, 2.785 across the five
steps: monotone like the water table, a **16%** rise on the coefficient scale
against the water table's 51%, and a final value that sits **above the upper
bound of its own full-range interval**, 2.785 against 2.700. Unweighted it is
genuinely flat, running 2.565 to 2.580 with a 2.1% spread and no monotone trend.
So the control does its job — a third of the movement, and none at all under the
plainer estimator — but "stable across every path" overstated it, and the
coefficient stability figure is drawn and captioned as 51 against 16 rather than
as movement against none.

A criterion requiring only that each step stay inside the full-range interval
and keep its sign does not discriminate here. That interval spans 2.064 to 4.245
weighted, so containment is nearly guaranteed and the criterion is blind to
exactly the drift it exists to detect. The criterion applied in
`stability.verdict` therefore also requires that the coefficient move by less
than a quarter of its full-range value and show no monotone trend against the
share removed. Under it, both configurations fail.

**Consequence.** A linear continuation of the water table term beyond the fitted
range is not a defensible bound. The three-variant spread reported with the
reconstruction is a **sensitivity range**, not a confidence interval, and it
demonstrates how much the answer depends on an assumption the data reject rather
than bounding the answer.

## A diagnostic designed and discarded

The original plan measured hydrological extrapolation uncertainty as the gap
between the model including water table and the model omitting it. That cannot
work. Across the 107 reconstruction months above the fitted maximum the clamped
term is constant, so the full model reduces to soil temperature plus a fixed
offset, which is structurally what the reduced model already is. **The two
converge precisely where extrapolation is worst**, and the diagnostic would have
reported its smallest value where uncertainty is greatest.

It is still reported, because the convergence is worth showing. It is not the
measure of hydrological uncertainty. The replacement is the three-way spread
across clamped, unclamped and reduced variants, qualified by the stability
result above.

A smooth saturating form, such as a logistic or a spline with flat
extrapolation, was rejected for the same class of reason: it produces
confident-looking values beyond the data whose shape is chosen by the analyst
rather than measured.

## Bias

Every residual and bias in `src/study` is **observed minus predicted**. A
positive value means the observation exceeded the prediction, so the model
predicted too low; a negative value means it predicted too high. On the
logarithmic scale the model fits, a bias converts to a multiplicative factor
rather than an additive offset. The convention is fixed in
`fitting.BIAS_CONVENTION` and asserted by a test.

| Withheld | Weighting | Bias | Prediction over observation | Direction |
|---|---|---|---|---|
| Wettest decile | unweighted | −0.020 | 1.020 | predicts high 2.0% |
| Wettest decile | weighted | +0.076 | 0.927 | predicts low 7.3% |
| Earliest three years | unweighted | +0.022 | 0.979 | predicts low 2.2% |
| Earliest three years | weighted | +0.030 | 0.970 | predicts low 3.0% |

**These moved substantially when the pipeline caught up with the adopted window.**
On the nominal 117 they read +0.143, +0.126, −0.214 and +0.017, so the wettest
decile unweighted and the earliest three years unweighted both change sign. Two
months carrying 22.3% of the design's leverage in the water table dimension were
doing much of the work in these holdouts, which is the same finding as the
coefficient instability arriving by another route.

The reconstruction period is both earlier and wetter, so the two effects apply
together, and the question is whether they can be added.

**They cannot, and the reason is that the two axes are not independent inside the
fit window.** The correlation between calendar time and water table is **+0.393
at p below 0.001**. Adding a time effect to a water table effect assumes each can
be varied while the other is held fixed, and here they move together, so the sum
double-counts whatever the two share. Combining them anyway gives +0.002
unweighted and +0.106 weighted.

*Two earlier arguments in this section have been retracted and should not be
reused.* The first was that the two effects combine to opposite signs, which was
true on the nominal window and is not true here: they now agree in direction. The
second was the opposite of the argument above — that the axes were
*near-independent*, at +0.098 with p = 0.291, with the objection to additivity
resting entirely on the non-uniformity below. Both were properties of the nominal
window. The two excluded months sat at the late, low extreme of both axes, where
a handful of points has enormous leverage on a time correlation, and removing
them reversed the independence result. **The conclusion that the effects cannot
be summed is unchanged; what changed is that it now rests on the correlation
between the axes, and the non-uniformity below corroborates it rather than
carrying it alone.**

The earliest three years remain slightly drier than the rest, at 413.243 against
413.327, rather than wetter. Splitting the backward-transfer holdout by water
table shows the bias is also not uniform:

| Water table band | Mean | Unweighted | Weighted |
|---|---|---|---|
| Driest | 413.16 | −0.103 (high 10.8%) | −0.110 (high 11.7%) |
| Middle | 413.22 | +0.077 (low 7.5%) | +0.078 (low 7.5%) |
| **Wettest** | **413.35** | **+0.112 (low 10.6%)** | **+0.145 (low 13.5%)** |

The backward-transfer bias depends on water table, so the two effects interact,
which is the second reason they cannot be summed. The band matching the reconstruction is the wettest, and
it gives a consistent answer under both weightings: **the model is expected to
predict low by roughly 11% unweighted and 13% weighted.** `bias.wet_end_bias`
computes this from the window in use, and `scripts/reconstruct.py` calls it
rather than carrying the old 0.148 as a literal.

**No correction is applied.** The supporting band has a mean water table of
413.35 and the reconstruction period sits above it, so applying the correction
would require extrapolating the correction itself, which is the class of error
this study exists to expose. It rests on eleven months in a single band. It is
carried as a stated directional expectation attached to each reconstructed year,
computed by `src/study/bias.py`.

## 2011

The model misses 2011 by 10 to 11 g C in every configuration. Two independent
lines converge on the reason, and it is not the one the covariates suggest.

**2011 is not covariate-anomalous in this record.** Against the rest of the fit
window, standardized differences are +0.15 for soil temperature, +0.07 for air
temperature, −0.10 for precipitation and +0.23 for water table. Its water table
maximum of 413.410 is below the fitted maximum of 413.460. Olson et al. (2013)
characterize 2011 as 1.3 °C warmer and 40 mm wetter than the 30-year average
with the greatest radiative forcing of their three study years, but relative to
the 2009-2019 fit window it is unremarkable, because that window is itself a
warm, wet decade against a longer baseline.

**The shortfall is concentrated, not seasonal.** Analysis in
`src/study/residuals.py`, which had no caller until `scripts/reconstruct.py` was
given one; these numbers could not previously be regenerated by running the
repository. This is the third of five instances collected under **The pattern:
reimplemented beside itself**. On the adopted window and the primary weighted model, the eleven
observed months of 2011 carry a total shortfall of 4.23 g C m⁻², of which
**September 2011 alone carries 51.8% and September with August carries 96.8%**.
Seven of eleven months are under-predicted. Against the same calendar month in
other years, September 2011 stands at **+5.67 standard deviations**, November at
+3.44 and August at +3.43.

The previously recorded 46.7% and 91.2% **could not be reproduced under any of
the four configurations tested** — weighted or unweighted, nominal or effective —
the closest being 49.2% and 92.6% weighted on the nominal window. They predate
some earlier state of the pipeline and should not be cited. September's
standardized value moves from +6.07 to +5.67 for a reason that is fully
explained: 2019-09 leaves the reference set when the artifact months are
excluded, so September's reference mean and spread both change, while November
and August are untouched.

Fluxes of that size with unremarkable covariates are the signature described by
Irvin, J., Zhou, S., McNicol, G., et al., with Jackson, R. B. as senior author
(2021), *Gap-filling eddy covariance methane fluxes: comparison of machine
learning model predictions and uncertainties at FLUXNET-CH4 wetlands*,
Agricultural and Forest Meteorology **308-309**, 108528,
doi:[10.1016/j.agrformet.2021.108528](https://doi.org/10.1016/j.agrformet.2021.108528),
who report that episodic fluxes, possibly from ebullition, are often not
captured by gap-filling models and are instead filled with averages for
comparable conditions. This site is not among their seventeen.

**The headline gap decomposes into two unequal parts.** Over the eleven observed
months of 2011:

| | g C m⁻² |
|---|---|
| Observed monthly means, this pipeline | 18.59 |
| Model, months withheld | 13.53 |
| Olson et al. (2013) | 24.90 |

Model against observations is **−5.06 g C, −27%**, which is model failure.
Observations against Olson et al. is **−6.31 g C, −25%**, which is a difference
between records and not a model error at all. The absent February contributes
about 0.33 g C, so it explains little of the second part.

The implication for the reconstruction is the more serious one. The episodic
component is invisible to the covariates, so its frequency before 2009 is
unobservable and unconstrained by anything in this data. If episodes like
August and September 2011 occurred in the 1990s, the reconstruction
under-predicts by an amount nothing here can bound, and that failure does not
shrink with better covariate modeling.

## The discrepancy against Olson et al.

Applying one estimator, monthly means integrated over available months
respecting month lengths, to both published comparisons:

| Year | Months | This pipeline | Published | Units | Ratio |
|---|---|---|---|---|---|
| 2009 | 9 | 9.92 | 11.8 | g C | 0.840 |
| 2010 | 12 | 9.88 | 12.2 | g C | 0.810 |
| 2011 | 12 | 18.81 | 24.9 | g C | 0.756 |
| 2015 | 12 | 14.19 | 14.3 | g CH₄ | **0.992** |
| 2016 | 12 | 17.79 | 19.0 | g CH₄ | **0.936** |
| 2017 | 12 | 20.14 | 20.0 | g CH₄ | **1.007** |

The 2015-2017 published values are the annual budgets of Deventer et al. (2019),
14.3, 19.0 and 19.9 to 20.1 g-CH₄ m⁻² yr⁻¹ with a total uncertainty of 7 to 17%.
The same pipeline agrees with one published source to within 0.8 to 6.4% and
falls 16 to 24% short of the other, at the same site.

Stated as recovery of the published totals, the ratio column spans **75.6% to
100.7% across the six comparable years**, the extremes being 2011 at 0.756 and
2017 at 1.007. That is the form the README uses, and it is written here so the
range is recorded rather than derived afresh from the two statements above.

What can be established. It is **not a uniform scaling**: the ratios differ by
0.084 and decline monotonically. It is **not a coverage artifact**: half-hourly
coverage is comparable across both eras at 25.5%, 36.3% and 34.9% for 2009-2011
against 25.2%, 28.8% and 37.8% for 2015-2017, which sits inside the 25 to 40%
typical of methane records after filtering reported by Irvin et al. (2021).
It leaves **no fingerprint in the values**: all three methane columns share an
identical decimal-precision profile and comparable quantisation.

**The discrepancy aligns exactly with a change of source column.** 2009-2011 is
served entirely by the unqualified FCH4 column; 2015-2017 entirely by the two
replicate columns. The era agreeing with Deventer et al. and the era
disagreeing with Olson et al. draw on different columns. That is circumstantial
but it is the sharpest structure in the data.

Two of three years sit inside Olson's own stated uncertainty: 2009 differs by
−1.88 against ±3.1 and 2010 by −2.32 against ±3.0, while 2011 falls outside by
−6.09 against ±5.6. The 2009 total covers only April to December; completing it
with climatological January to March gives 11.00 against 11.8, a ratio of 0.932.
The discrepancy is largest in the most episodic year, which is consistent with a
gap-filling difference rather than a data difference, since Olson et al.
gap-filled and this pipeline integrates observed months only.

**What the 2025 product settles, and what it does not.** The open question was
whether the base methane column was reprocessed between Olson's access and the
2022 export used here. That product has since been obtained and held alongside
the export rather than substituted for it, and **every methane value in the two
is identical**: 44,427 site-aggregated and 31,564 replicate half-hours, with no
value differing and none present in one and absent from the other. Recorded in
`notes/base_v55.md`.

So the export is not a stale or unusual snapshot, and no reprocessing occurred
between 2022 and 2025. What that cannot rule out is reprocessing between about
2012, when Olson et al. would have drawn their data, and 2022; only their
original extraction could close that, and it is not available. The remaining
explanation is the one already preferred, that Olson et al. gap-filled where
this pipeline integrates observed months only, and it is now the stronger of the
two because the alternative has been narrowed rather than merely doubted. Olson
et al. should still be treated as a weak comparison rather than a benchmark.

## The hysteresis null

Feng, X., Deventer, M. J., Lonchar, R., Ng, G. H. C., Sebestyen, S. D., Roman,
D. T., Griffis, T. J., Millet, D. B., and Kolka, R. K. (2020), *Climate
sensitivity of peatland methane emissions mediated by seasonal hydrologic
dynamics*, Geophysical Research Letters **47**(17), e2020GL088875,
doi:[10.1029/2020GL088875](https://doi.org/10.1029/2020GL088875), established
hysteresis in the methane response to soil temperature at this site: the
response differs between the warming and cooling limbs of the annual cycle,
delineated by t_rise, the early-spring day when soil temperature sharply rises
at the inflection where the second derivative turns positive, and t_mid, the
midsummer day when soil temperature is maximized after 30-day smoothing. The
same work concludes that shifting seasonal water availability from winter to
summer increases annual emissions even under identical soil temperature
trajectories.

Tested here as a limb indicator with a temperature interaction, the limb taken
from the sign of the month-over-month change in soil temperature. The
classification behaves sensibly, marking 100% of April to July as warming and
0% of September to January, 48% overall.

| Withheld | MedAE without | with | MAPE without | with |
|---|---|---|---|---|
| Wettest decile | 0.188 | 0.275 | 20.2% | 24.1% |
| Coldest decile | 0.246 | 0.253 | 25.8% | 25.7% |
| Earliest three years | 0.232 | 0.240 | 31.5% | 30.6% |
| Latest three years | 0.174 | 0.175 | 20.5% | 24.3% |

**It does not improve holdout performance and is not included.** On backward
transfer, training error improves markedly from 0.198 to 0.170 while holdout
median error slightly worsens, which is the signature of parameters fitting
training structure rather than transferable structure. Two of four holdouts get
clearly worse.

This is a null for a monthly proxy, not a refutation of Feng et al. (2020).
Their delineation is defined on daily soil temperature with a 30-day smoothing,
and hysteresis operating at sub-monthly scale would be largely destroyed by
monthly aggregation. A monthly test cannot refute a sub-monthly finding.

## Absence from FLUXNET-CH4

This site does not appear in FLUXNET-CH4 Version 1.0, so no community
gap-filled product exists for it. Established by searching the appendix of
Delwiche, K. B., Knox, S. H., Malhotra, A., et al., with Jackson, R. B. as
senior author (2021), *FLUXNET-CH4: a global, multi-ecosystem dataset and
analysis of methane seasonality from freshwater wetlands*, Earth System Science
Data **13**, 3607-3689,
doi:[10.5194/essd-13-3607-2021](https://doi.org/10.5194/essd-13-3607-2021), with
the appendix archived at
doi:[10.5281/zenodo.4672601](https://doi.org/10.5281/zenodo.4672601) under
CC-BY-4.0. The workbook is a synthesis rather than a network: its own
`ORIGINAL_DATA_SOURCE` column credits AmeriFlux for 45 of the 79 sites in the
metadata sheet, EuroFlux for 28, AsiaFlux for 5 and OzFlux for 1. None of the
45 is US-MBP, which is itself an AmeriFlux site: the product this study reads
is `AMF_US-MBP_BASE-BADM_5-5`. So the site belongs to the network that supplied
the plurality of FLUXNET-CH4 and was not gathered into the synthesis, which is a
different statement from not belonging to the network, and the figure must not
conflate them. (An earlier version of this note said the workbook names 65
AmeriFlux sites. No count in it is 65: the metadata sheet holds 79 sites, the
annual-values sheet 81, and the Americas prefixes total 45.) No cell
contains "MBP", "Marcell" or "Bog Lake"; and no site lies within 100 km of
47.505 N, −93.489 W. The nearest are US-PFa at 300 km, classified upland, and
US-Los at 310 km, a fen in the same climate zone and the closest usable
analogue.

Recomputing two of that paper's network-scale findings from the appendix gives a
mean onset lag between rising methane and soil warming of 28.1 days over 85
site-years, reproducing the reported month, but a median of 12.5 with an
interquartile range of 4 to 56. The published figure is a mean unrepresentative
of a skewed distribution. Peak methane timing correlates with neither peak air
temperature (r = +0.048, p = 0.59), peak soil temperature (r = −0.011, p = 0.91)
nor peak gross primary productivity (r = −0.166, p = 0.072). Neither the timing
nor the offset of a temperature-driven seasonal cycle transfers across sites, so
a predictor built on either must be estimated from this site's own record rather
than adopted from the literature.

## The reconstruction

Produced by `src/study/reconstruct.py` and `scripts/reconstruct.py`, weighted
full model primary. Every year carries its support verdict, its sensitivity
range and its directional bias expectation in the same row as its estimate.

**Four of twenty years lie inside the fitted support.** Sixteen require
extrapolation, almost always on water table. Representative rows, g C m⁻² yr⁻¹,
on the adopted window as `scripts/reconstruct.py` now produces it:

| Year | Support | Months outside | Estimate | Interval | Sensitivity span |
|---|---|---|---|---|---|
| 1991 | **inside** | 0 | 11.95 | 7.51 to 18.92 | **5%** |
| 1992 | **inside** | 0 | 11.23 | 7.06 to 17.78 | **6%** |
| 1994 | outside | 9 | 17.68 | 11.11 to 27.99 | 72% |
| 1997 | outside | 12 | 17.42 | 10.94 to 27.58 | **115%** |
| 1999 | outside | 9 | 17.98 | 11.30 to 28.47 | 106% |
| 2004 | **inside** | 0 | 11.42 | 7.17 to 18.07 | 11% |
| 2008 | outside | 3 | 8.22 | 5.17 to 13.02 | 14% |

On the nominal 117 these read 11.77, 11.05, 17.02, 16.74, 17.30, 11.20 and 8.08,
with spans of 2%, 2%, 66%, 107%, 98%, 8% and 17%, and six years inside support
rather than four. 2008 crosses from inside to outside on the narrowed range, by
margins of 0.01 to 0.06 m, and should be read as marginal rather than as a change
of kind.

The sensitivity span reaches 115% of the estimate in 1997: the three water table
variants disagree by more than the estimate itself. Inside-support years span 5
to 11%. The span tracks support closely, which is the demonstration working:
where the model has evidence it is nearly indifferent to the assumption, and
where it does not the assumption determines the answer.

**Two years of the reconstruction window are not full years.** 1995 holds eleven
months, the water table record having no value for 1995-02, and 2009 holds three,
the window ending at 2009-03 where the flux record begins. 1995 is kept: eleven
months of twelve integrate to an annual total without distortion worth naming.
2009 is not, and it is omitted from the reconstruction figure rather than shown:
its three months total 0.83 g C m⁻², which beside full years of eight to eighteen
would read as a collapse in emission rather than as a quarter of a year. Both are
facts about how the series was assembled rather than about the peatland, which is
why they are recorded here and not on the figure.

Empirical coverage against a 90% nominal level is **89.6% in sample** over the
115 fit months, and **87.5% on held-out backward transfer under both weightings**.
On the nominal 117 the backward-transfer figures were 84.4% weighted and 62.5%
unweighted, so narrowing the window brought the unweighted case from far below
nominal to close to it. An earlier version of this line paired the nominal
weighted figure with the effective unweighted one.
**No empirical coverage can be computed over the reconstruction period**,
because nothing was observed there. The held-out figures are the only evidence
about how these intervals behave away from the fit window. Irvin et al. (2021)
report that raw machine learning ensemble uncertainties are underestimated and
require calibration, which is consistent with the direction seen here.

Against the retrospective range of Olson et al. (2013), +7.8 to +15.2 ± 2.7 g C
m⁻² yr⁻¹ for 1991 to 2011, this reconstruction gives **7.90 to 17.98 across
eighteen complete years with a mean of 14.88**, against 7.78 to 17.30 and a mean
of 14.40 on the nominal window. Both were produced by fitting a
short flux record and projecting backward, so this is method agreement and not
independent confirmation.

## The strip's key, and a measurement that was wrong twice

The strip's marks belong in the strip. Folding them into the panel's key put an
entry for hatched bars on a panel that carries none, so a reader looking there
would not find them. They are keyed where they appear.

Getting them there took two attempts because the first measurement compared the
wrong things. A probe labelled "heading as a blank-handle row" in fact carried no
heading at all, so its 54.4 px was two entries, and setting that against a
titled legend's 77.2 px produced a 23 px saving that does not exist. Measured
properly, on the same three rows, a blank-handle heading costs 81.2 px and a
title 77.2: the row is 4 px *more*, not 23 less. The conclusion drawn from it,
that the strip's height was never really the constraint, was wrong. It is.

What actually fits, at 8.2 pt with a heading, on a strip an eighth of the block:

| arrangement | height | % of strip | clears the 2007 bar by |
|---|---|---|---|
| heading row, stacked | 81.2 | 63.5% | −4.0 |
| title, stacked | 77.2 | 60.4% | −0.7 |
| heading row, three columns | 35.7 | 27.9% | −32.6, it reaches a 100% bar |
| **title, two columns** | **58.4** | **45.7%** | **+15.2** |

The heading names the marks rather than where they sit. "In the strip below"
was right while these entries lived in the panel's key and pointed downward;
from inside the strip it tells a reader only what they can already see. "What
each bar shows" would have been the obvious replacement and is not honest: one
of the two marks is a flat tick for a year with no months outside, which is a
bar of no height and does not read as one, which is why it is drawn flat and in
the panel's blue rather than as a hairline orange bar. "What each mark shows"
covers both, and is the set's wording for exactly this case, heading the keys on
the prediction error and residual figures where unlike marks are grouped. The
set holds one near-duplicate, "What the marks show" on the flux figure, which
should be brought into line when the pass reaches it.

Only the last one clears, so the strip's key is one row of two under a title.
Stacking is what costs the height, not the heading, and laying the entries
across is what buys it back. The title is the site figure's device, so this is
the set's other heading rather than a new one, and it is set in the same
mathtext bold at the same size and ruled by the same line, so the three headings
on this figure are one device in two placements.

The alternatives were a taller strip, 0.17 to 0.22 of the block, which fits the
stacked form at 6.3% of the main panel; and the gap above the strip, which needs
81 px against the 41 there and costs 6.9%. Both pay panel height for a placement
a reader does not benefit from.

`test_the_strip_legend_fits_inside_the_frame_without_covering_a_bar` holds the
clearance, because +15.2 is a property of the last years' bars being short
rather than of the layout. Its fixture was widened from five plotted years to
nineteen at the same time: at five, the x axis is compressed enough that the key
spans half the panel instead of a quarter, which is a different layout from the
one being checked.

## The strike, and why length is not what tells it from a bar

An empty cell on the measurements figure carries a strike rather than a word.
Two reasons a cell is empty were written into it, "does not apply" on the date
column and "not available" on a horizon column, which is ten italic annotations
and 1,070 px of text for cells that hold nothing. The description carries both
reasons in one sentence and the panel carries one mark.

**Length does not separate a strike from a short bar and cannot be made to.** At
8.0 on the panel's 0 to 124 scale it renders 16.6 px, against 19.6 px for a 9%
bar, and this figure draws bars at 9% and 10%. They end within 3 px of each
other. Lengthening or shortening the strike only moves which bar it collides
with.

Two things do separate them:

- **Thickness.** 2.9 px against a bar's 39.4, which is 7%. Nothing on the panel
  is a thin bar, so the strike is a different kind of object rather than a small
  one, and that reads at any length.
- **The labelling rule.** 50 bars, 50 numbers, 10 strikes, no number on any of
  them. Every bar carries its value including a "0" where the value is a measured
  zero, and no strike carries one. A reader who has looked at two cells has the
  grammar.

Both are held by a test, because a change to bar height or to the number rule
would remove the distinction without touching the strike or its constant.

The strike starts where a bar starts. It began 1.0 in, which at this scale is 2
px: too little for a reader to register as "not measured from the axis", and
enough to invite them to look for meaning in the gap where there is none.

**The explanation arrives last and that is correct.** A reader meets ten strikes
before the sentence explaining them, which sits at the end of a five-line block
at its cap. The mark does not depend on that sentence: it has to say "there is no
number here and that is deliberate", which position and the missing number do on
their own. What the sentence adds is which of two reasons applies, and that is
caption material. The failure mode worth guarding is the opposite one, a reader
inferring a wrong meaning before reaching the caption, and the only wrong reading
available is "a very short bar", which the two separations above block.

## For after the pass: the wrap under-fills every description

`_wrap_width` divides the drawable width by a character-width estimate of 0.545
em, and the estimate is generous, so every description stops short of the width
it is allowed:

| figure | drawable | widest line renders | uses |
|---|---|---|---|
| seasonal cycle | 2152 px | 1990.5 | 92.5% |
| measurements used | 1652 px | 1538.0 | 93.1% |
| water table | 1652 px | 1593.9 | 96.5% |

Roughly 7% of the width is unavailable across eleven figures, and that is why
several blocks ran to an extra line during the visual pass when they sat near a
boundary. Recovering it would give several of them a line back.

**Not corrected now.** Changing the estimate reflows every description in the
set, and doing that mid-pass would invalidate every line count already agreed. It
is a decision for the set once the pass finishes, and it should be made by
measuring rendered width rather than by tuning the constant until the counts look
right.

## Where the prose sits on a figure, not just how much

The measurements figure reads as the wordiest in the set and is not. On the three
text blocks it holds 1,249 characters against the forecast figure's 1,401, and it
now holds 1,075.

What makes it read heavy is distribution rather than volume. Its text is spread
across two column headings with their units, four horizon sub-headings, two axis
labels repeating those units, six row labels and two in-panel marks, so a reader
meets prose in eight places before the caption. The forecast figure concentrates
more characters in three blocks a reader can skip past in one movement.

Worth holding when a figure feels wordy: count where the text sits, not only how
much there is.

## For the README pass: what the unpredictable quantity is worth globally

Bousquet et al. (2006) attribute **70% of global methane emission anomalies
between 1984 and 2003 to interannual variability in wetland emissions**. The
quantity this study finds unpredictable at this site, the size of each season
rather than its shape, is the one that dominates global methane variability.

Bousquet, P., et al. (2006), *Contribution of anthropogenic and natural sources
to atmospheric methane variability*, Nature **443**, 439-443.

**This entry read "Meng et al." until 2026-08-30, and the attribution was
wrong.** Meng et al. (2015) quote the finding in their introduction and name its
source: *"Using inverse methods, Bousquet et al. (2006) suggests that 70 % of the
global emission anomalies CH4 for the period 1984-2003 are due to the
interannual variability in wetland emissions."* Meng's own analysis period is
1993 to 2004, and 1984-2003 appears nowhere in that paper except inside the
sentence quoting Bousquet. Recorded in the drift table below.

That is context beyond anything the figure set draws, so it belongs in the README
above the figures rather than in a caption. Recorded here so the README pass
picks it up rather than rediscovering it.

## The pattern: corrected where it was noticed

The sibling of the entry below, and the same class of failure running the other
way. There, something that existed was not found and was written again. Here,
something that existed in two places was changed in one. Which of the two places
is the correct one varies, and the table says which for each. Two shapes recur:
the figure or the code moved and the record did not, or the record moved and the
figure did not. Two rows are neither. In one both places agreed and both were
wrong, because the error entered from outside the repository; in another the
inventory was split across two notes, each of which stayed true about its own
half while their union stopped being true.

The rows are numbered and the prose below does not count them, deliberately.
An earlier version of this paragraph enumerated *the first three*, *the fourth*
and *the fifth*, and the sentence beside it in `notes/base_v55.md` said *the
other four*. Appending a row falsified both, in the section whose whole subject
is a claim in two places updated in one.

| | what changed | where it was applied | where it was not |
|---|---|---|---|
| 1 | the adopted window, 117 months to 115 | `study/figures.py` | every script, which kept building the nominal window |
| 2 | the 2011 shortfall shares | prose in these notes | nothing computed them, so nothing could disagree |
| 3 | the v5-5 correction to the seasonal numbers | the figure's description | these notes, which kept 0.54 and p = 0.119 |
| 4 | the 2015 month-size correction | these notes, which say **middle** third | the figure's description, which went on saying *all small ones* |
| 5 | nothing: the 70% anomaly finding was attributed to Meng et al. (2015) here and in the README draft taken from here | both places, identically | the source, which names Bousquet et al. (2006) |
| 6 | the Delwiche appendix gained a reader, and the pipeline's inputs gained the 2025 BASE product | `study/sitemap.py` and scripts 04 and 05 | `notes/ingestion.md`, which went on saying no module read the appendix and that seven files were the whole input set |

The third is the one that prompted this entry. Cutting six precise figures out of
the seasonal description meant checking they were recorded, and four were not:
the spread ratio and the amplitude trend p were **stale**, having been updated in
the figure and not here, and the carbon dioxide trend p and both variance shares
had **never been written down**. Removing them without checking would have lost
two outright and left two contradicting the figure.

**The fix is a test, and it is named so it is found.**
`test_the_amplitudes_and_their_trend_tests_are_recorded` reads these notes and
asserts every number that left the block is present in them. It is the only kind
of guard that works here, because prose cannot be type-checked and a number
living in two files will drift the moment one is edited alone.

**The fourth runs the other way, and it is the worst of the four.** Here the
notes were right and the figure was wrong. `Facet the prediction error figure by
year` wrote the note that 2015's months sit in the **middle** third of methane's
size distribution, not the smallest, precisely because an earlier pass had
credited the whole 2015 difference to which months the year contains. The very
next commit, `State both halves of the 2015 claim`, then put *its months are all
small ones* into the description. A note written to prevent a claim was
contradicted by the next commit to touch the claim, and the contradiction sat
there through every regeneration since, because regenerating a figure checks that
it draws without error and never that its prose agrees with the record.

Nothing would have caught it but reading the description back against the notes
line by line. A draft of the same description reproduced the error a second time,
which is what finally surfaced it.

**The fifth is a different shape again, and it is the one no check here could
have caught.** The first four are a claim held in two places and updated in one.
This one was never inconsistent: the 70% anomaly finding was attributed to Meng
et al. (2015) in these notes, the README draft took the attribution from here,
and the two agreed with each other perfectly. What they disagreed with was the
paper. Meng quotes the finding and names Bousquet et al. (2006) as its source in
the same sentence, so the error was visible only to someone who opened the
source.

**The error was in an attribution rather than in a number**, and that is what
makes it distinct. Every guard this project has built watches numbers: the
recorded-numbers test, the grep-before-changing rule, the reproduce-the-basis
rule. All of them would have passed this, because there was no number to check
and nothing computed disagrees with anything. A regenerated figure would have
passed it. A spot check of the bibliography would also have passed it, since the
citation is real, correctly formatted, and does contain the sentence: the volume,
the pages and the year are all right, and only the names in front of it are
wrong. That is the version of a citation error that survives every check short of
reading the source.

Two circumstantial signals were available without the source and were not used:
Meng's own analysis period is 1993 to 2004, which does not contain 1984 to 2003,
and a modeling paper is an unlikely home for an inversion result. Either should
have prompted the check that a single fetch then settled.

**What to check first, next time:** a claim carrying someone's name is two
claims, and the citation being real does not make the attribution right. Before
publishing an attributed finding, open the source and find the sentence. Where
the finding turns out to be quoted rather than made there, cite what the source
cites.

**The sixth is the `base_v55.md` shape again**, and it is the plainest form the
pattern takes: a note that was true when it was written, falsified by a later
commit that did not touch it. `notes/ingestion.md` said the Delwiche appendix was
a reference file that no module read, which was true at `14d5efb`. The site
figure arrived at `2d0747e`, later, and reads sheet B3 of that appendix for the
FLUXNET-CH4 coordinates. Nothing connected the two: the commit that added the
reader had no reason to look at an ingestion note, and the note had no test that
could notice a new import.

The same section drifted a second way at the same time. It listed seven files as
the pipeline's inputs, and the switch to the 2025 BASE product added two more
without amending it, because the switch was recorded in `base_v55.md` instead.
Neither note was wrong about its own half. The inventory was wrong because it
was split, and each half was maintained by whoever was working on that half.

**The fix is one inventory rather than two.** `notes/ingestion.md` now lists every
file in `CSVs/` with what reads it, including the BASE product documented at
length elsewhere. A split inventory has no owner for the whole, which is the
condition under which each half stays locally true and the union stops being.

**The primary-versus-reference division went with it.** It was the thing that
made the split feel natural, and it had quietly stopped meaning anything: the
appendix was "reference" because nothing read it, which changed, and the 2022
workbook was "primary" while the live source was the 2025 product. The division
that survives is which files a fresh clone must fetch, which is one file, and
which are carried, which is the rest.

**What to check first, next time:** before removing a number from a figure,
confirm it is recorded somewhere a test can see. Before *changing* one, grep for
it across the repository rather than editing the place you are looking at. And in
both directions, at every text block: **any number or claim leaving a text block
must be verified against these notes, and any claim entering one must be verified
against the outputs.** The third instance is the first half of that rule failing,
the fourth is the second half.

## The pattern: reimplemented beside itself

Five times now, something that already existed was not found and was written
again next to itself. Recording them together because the fifth was predictable
from the fourth, and the sixth will be predictable from these.

| | what existed | what was written instead | what it cost |
|---|---|---|---|
| 1 | the adopted 115-month window, named in `study/figures.py` | every script built its own from `build_windows` on the nominal 117 | the figures described one window and every table beside them another |
| 2 | the wettest-band bias and the backward-transfer coverages, computable | `scripts/reconstruct.py` pinned 0.148, 84.4% and 62.5% as literals | three numbers describing a window the script no longer used |
| 3 | `src/study/residuals.py`, a whole module | nothing called it; its numbers lived only in prose here | the 2011 concentration figures could not be regenerated by running the repository |
| 4 | the end of the record, derivable | `ingest.assemble.TARGET_END` pinned `"2021-12"` | on the BASE v5-5 switch the grid would have stopped three years short, regularly spaced and wrong, with nothing failing |
| 5 | `plotstyle.even_year_ticks`, already drawing annual minors | a second date locator written into `_draw_flux_panel` | two places setting ticks on one axis, the later silently overriding the earlier |
| 6 | `TRAINING_LABEL`, a label written for the lead on a forecast row | nothing: no caller anywhere | the mark was drawn and never keyed, so a reader met it with no entry for it |

The sixth is the smallest shape it takes. A constant was written, named exactly
for the mark it describes, and never wired to the legend that would have used it,
so it sat at line 1565 with no caller while the mark it names went unkeyed on the
panel. Nothing failed, because an unused constant is not an error and an unkeyed
mark still renders. Six instances now, in five shapes: a window exclusion in the
wrong module, pinned literals, an orphaned module, a hardcoded end date, a
duplicate tick locator, and a label with no caller.

The first four were recorded as one class, a value that describes the data
sitting as a constant rather than being derived from it. That framing is true of
four of them and false of the fifth: a tick locator is not a value. The class
they actually share is **something that already exists, is not found, and gets
reimplemented beside itself.** Under that description all five belong, and so
does the audit that could not see the flux figure's green, which is the same
failure in the reading direction rather than the writing one.

**What to check first, next time:** whether the thing you are about to write
already exists one call away. In four of the five it did, within the same module
or the one being imported three lines up. Number 5 was written four lines above
the call to the helper that already did it.

Two of these are recorded in more detail where they were found, and those notes
stay: the window exclusion and `TARGET_END` above, and the orphaned residuals
module in the 2011 section. Someone arriving at either should find this table
from there.

## Never state a count of a list beside the list

The general form, and it earned its own entry by happening inside the table that
records it.

The drift table above grew two rows. The prose beside it read *in the first three
the figure was right and the record stale, in the fourth the record was right and
the figure stale*, and continued *the fifth breaks the shape*. The sentence in
`notes/base_v55.md` that points at the same table said *the other four ran the
other way*. Appending row 5 falsified both. Appending row 6 falsified them again.

**Those were counts of a list, held somewhere other than the list.** That is the
same object as every row in the table: one fact in two places, updated in one.
The list is authoritative about its own length and nothing else can be, so any
sentence that restates the length has taken a copy that only stays true until the
next append, and appending is the one thing a growing list is for. It cost
nothing here because the entry is prose. In a figure description it is what the
adopted-window row records.

**The rule.** A list carries its own count. Prose beside a list names shapes,
kinds and directions, never how many. *Two shapes recur* survives an append;
*the first three* does not. Where a number really must appear beside a list, it
belongs in a test that reads the list, which is what
`test_the_amplitudes_and_their_trend_tests_are_recorded` does for the seasonal
figures. The same applies to ordinals: *the fourth* is a count wearing a
different hat, and it goes stale the moment a row is inserted rather than
appended.

Both sentences are now count-free, and the rows carry the numbers.

**It happened a third time, in the report that proposed this rule.** Asked what
merging the working branch would involve, the survey said `main` was *eleven
commits behind*. It was 132. Nothing was counted; the number was supplied from
an impression of the log and then repeated back by the reader, who had no reason
to doubt it. `git rev-list --count main..<branch>` is one command and takes no
judgment, and it was not run until the next round asked a question the wrong
answer would have made unanswerable.

Three instances, in one session, in the same class: the enumerations beside this
table, the "eighth" taken across two tables, and this. **All three were counts of
something countable, asserted rather than counted.** None was caught by care;
each was caught by eventually running the count. The rule is not to be more
careful with numbers of this kind, because that has now failed three times. The
rule is that a count of a list is a computation, not a recollection, and prose
that states one without running it is unsupported no matter how obvious the
number seems.

**A second-order instance, recorded because it is the same failure at one
remove.** The survey that found the `CSVs/` drift called it *the eighth*
instance. It is the sixth row of this table, and the seventh of the family
counting the one recorded in `base_v55.md` that is not tabulated here. The
"eighth" came from counting across two different tables at once, this one and the
reimplemented-beside-itself list below, which is a count of a list taken from
memory rather than from the list. It reached a report before it was checked. The
correction is recorded rather than quietly fixed, because the instructive part is
that the same failure appeared twice in one round, once in the notes and once in
the prose describing them, and neither instance was noticed by writing more
carefully. Both were caught by going back to the list and counting it.

## A history rewrite was attempted, measured, and abandoned

Twelve commits near the tip carry a `Co-Authored-By` trailer. Removing them was
proposed, estimated, attempted on 2026-08-31, and reverted. **A later pass seeing
those trailers should not try again**, and this entry exists so the cost does not
have to be rediscovered by paying it.

**The estimate was that twelve commits would be rehashed and 152 would keep their
SHAs.** The measurement was that all 164 changed and none were kept. The estimate
was not wrong by degree; it was wrong in kind, and it was wrong for a reason no
amount of care about the trailers would have surfaced.

**The initial commit carries a GPG signature, and rewriting strips it.** A
signature covers the content it signs, so a rewritten commit cannot carry the old
one and `filter-repo` drops it. That changes the root, which changes its child,
and the cascade runs the whole length of the history. There is no flag for this
and no way around it: keeping a signature and rewriting the commit it signs are
mutually exclusive.

**Twenty-seven Verified badges would be lost permanently.** All 27 signed commits
are the ones made through the GitHub web interface, signed by GitHub's key. They
are the only cryptographic evidence that those commits are the author's, and on a
public repository they are the part of the history that carries the most weight
per byte. Trading them for twelve lines of trailer is a poor exchange on its own
terms, and it works against the presentation the removal was meant to improve.

**The decisive cost is that the rewrite orphans this repository's own audit
trail.** These notes cite five commits by hash: `072e739`, `14d5efb`, `2d0747e`,
`891f6d3` and `fbc39d2`. All five predate the twelve, so the pre-flight check
said they were safe. **That was the wrong check.** It asked whether they were
among the commits being edited, when what mattered was whether they survive a
full-history rehash, and under a root-cascade rewrite nothing survives. After a
garbage collection those five would resolve nowhere, in a repository whose whole
argument is that its claims can be traced to what produced them. A visible
blemish would have been traded for a broken provenance chain.

**The benefit was already partial before any of this.** The repository went
public roughly an hour before the rewrite was proposed. Force-pushing makes old
commits unreachable, not absent: they stay fetchable by direct URL until GitHub
garbage-collects, which is not on a published schedule. Genuine removal now needs
a request to GitHub Support. Rewriting before publication would have avoided that
window, and the ordering was proposed but overtaken by events.

**Running it is what settled it.** The rewrite was executed on the real history
with a backup tag in place, measured, and reverted before anything was pushed.
That is the reason the entry can state 164 and 27 rather than estimate them. The
attempt was not waste; it converted a prediction into a measurement, and the
measurement reversed the decision. Where a change is cheap to try and expensive
to guess at, trying it on a backup **is** the analysis.

## The fourth instance: a scope estimate stated as a fact

This belongs with the counts and the remote, and it is the same shape. A fact one
command away was asserted from inference. The inference was that `filter-repo`
rehashes only what it changes, which is true. The premise it missed is that
stripping a signature changes the commit that carries it, and the commit that
carried it was the root.

The three earlier instances were counts: rows in a table, instances across two
tables, commits on a branch. This one is a blast radius, which does not look like
a count and is one. **The guard is the same.** The scope of a rewrite is a
computation, not a prediction, and the way to run it is to run the rewrite on a
backup and diff the ref lists. That takes a minute and returns an exact answer,
against an estimate that was off by a factor of thirteen and silent about the
thing that actually mattered.

**What to check first, next time:** before quoting the blast radius of any
history operation, do it on a copy and count. And before calling a referenced
object safe, ask whether it survives the operation, not whether it is among the
operation's targets.

## A licence file is a claim about everything a reader can see

Recorded because the reasoning generalises past this repository and is easy to
get wrong in the safe-looking direction.

Adding `LICENSE` at the root looked like pure gain: no licence means all rights
reserved, which would have shipped CC-BY-4.0 data inside a container nobody may
reuse, in a repository whose argument is that work should be checkable. That much
is right. What it misses is that the file is not only a grant, it is a
**statement about scope**, and a bare one takes the widest scope available.

**Two things make a root licence overclaim.** GitHub renders a badge in the
sidebar that names the licence and nothing else, and a reader takes it as
covering what they can see. Here what they can see is 72 MB of third-party data
under different terms, most of the repository by weight. And MIT cannot grant
what the author does not hold: the AmeriFlux product is not this project's to
license, so an unqualified file at the root makes a claim about `CSVs/` that is
not the author's to make. Neither failure is visible from the licence file, which
is correct in isolation; both come from where it sits.

**The fix is a boundary, not a different licence.** The README says what the
licence does not cover before saying anything else about it, then states what
each outside source actually carries. The MIT file stays exactly as it is.

**And the honest form of an unknown is a gap, not a grant.** The Marcell station
records carry no licence statement this repository can point to. The tempting
moves are to leave them unmentioned, which lets the root badge cover them by
implication, or to describe them as open, which is unsupported. Recording that
nothing states their terms is the only claim the evidence carries, and it also
tells a later reader what to go and find out.

**What to check first, next time:** before adding a licence to a repository that
carries data, ask what the badge will appear to cover rather than what the file
grants. Any repository holding material it did not produce needs the boundary
written down, and the check is to list what a reader sees at the root and ask, of
each item, whether the author holds the right to license it.

## No references.bib, and what to do if a writeup ever needs one

Considered and declined. The case for one is real: twelve works are cited across
the README and these notes, the papers live outside the repository, and a
bibliography would give each citation one canonical form. The case against is
that it would be a fourth place a reference could drift from, beside the README's
Sources section, these notes, and the prose around them.

**What settles it is that a `.bib` would not have caught the only citation error
this project has had.** The Meng-to-Bousquet misattribution had flawless
bibliographic detail: author, year, title, journal, volume 12, pages 4029-4049,
every field correct and verifiable. What was wrong was whose finding it was. A
`.bib` file has a field for everything that was already right and no field at all
for the thing that was wrong, so it would have stored the error faithfully and
added a fourth copy of it. Against that, the failure it introduces is exactly the
one this section of the notes exists to record: a value living in several places
and updated in one.

**Sources is already the project bibliography, not the README's references.**
Five of its twelve entries, Irvin, Knox, Li and Makridakis by name and Roman by
bare DOI, are never cited in the README's body at all; they are cited here. So a
`.bib` would not serve a purpose Sources does not already serve. It would
duplicate it wholesale.

**If a writeup outside this repository ever needs one, generate it rather than
keep it.** Make the README's Sources section canonical, emit the `.bib` from it,
and have a test assert the two agree, which is the instrument
`test_the_amplitudes_and_their_trend_tests_are_recorded` already uses on the
seasonal numbers. A derived artifact regenerated from one source cannot drift. A
maintained one standing beside three others will, and this project now has six
recorded instances of precisely that.

## The pattern: two right answers mistaken for one

The climatology reduction against `seasonal naive` on methane is **23 to 28% in
scaled error and 24 to 29% in mean absolute error**, on the same shared-target
basis and the same four horizons. Per horizon, MASE gives 28.4, 27.9, 25.9 and
23.0; MAE gives 28.6, 28.2, 26.5 and 23.9. Neither is a drifted version of the
other. They are two valid computations of one relationship, and the difference
between them is the measure, not the basis, not the months, and not the data.

**A correction was made in the wrong direction on this, and it was neither a
right answer nor a wrong one.** The README carried 23 to 28. A verification pass
reported the relationship as 23.0 to 28.4 without saying it had computed in
scaled error, the number was read as stale, and it was corrected to 24 to 29 --
which is exactly right in mean absolute error. A correct value was replaced by a
differently correct value, and both sides of the exchange believed they were
reconciling one quantity.

**This is a distinct failure from the four substitutions above and needs a
different guard.** There the danger was a stale number replaced by a current one,
and the check was to reproduce the basis the record was computed on. Here the
basis was never in question and reproducing it would have changed nothing: both
figures come off the same 243 shared horizon-target pairs. What was missing was
the name of the measure. **The check that catches this is stating the measure
alongside the number**, in the notes and in any report of them, so that two
numbers can be seen to answer different questions rather than to disagree.

**The document and the figure do not use the same measure, and this is not
reconciled.** The README commits to scaled error within a gas, in its own terms:
scaled error is used within each gas and not across them, because methane's
scaling denominator is twice the difficulty of the period being scored while
carbon dioxide's matches its test period closely. The forecast figure beside that
paragraph is drawn in mean absolute error, in nanomoles and micromoles, because
`forecast_panel` computes MAE and the significance band is in the same units.
**A reader checking the paragraph's 23 to 28 against the figure will not recover
it**, and will read 24 to 29 off the panel instead.

That is deliberate and should stay deliberate. The paragraph is a comparison
within one gas, where scaled error is the committed measure; the figure is a
picture of error in the units the gas is measured in, where a scaled axis would
be unreadable. **A later pass must not silently reconcile them.** Changing the
paragraph to MAE breaks the document's stated rule, and changing the figure to
MASE costs the units. If the gap is ever closed it should be closed by naming
both measures where they meet, not by making one of them disappear.

## The pattern: assuming the record is the side that moved

A verification that finds a recorded number disagreeing with a fresh computation
has established a disagreement and nothing more. It has not established which
side is wrong. Both defaults are available and only one of them was taken.

Checking the prediction-error description turned up six recorded values that a
reimplementation did not reproduce, and all six were reported as **v5-5 drift**:
numbers correct when written and stale since the switch. That reading was adopted
and acted on, and the instruction that followed was to overwrite four of them
with the recomputed values. It was wrong on every count that mattered:

| recorded | reimplementation | what was actually true |
|---|---|---|
| 4 bins, 1.93 | 1.84 | record correct; bin edges taken from the months, not the rows |
| 5 bins, 1.99 | 2.02 | record correct; bin edges taken from the rows, not the months |
| carbon dioxide 2014, 1.18 | 1.200 | record correct; it is what `year_ratio` returns |
| leave-one-out, 2.23 | 2.36 | near miss, and still unreproduced |
| worst month dropped, 1.62 | 1.20 | unreproduced under eight readings |
| continuous log-log, 2.08 | 2.31 to 3.55 | unreproduced; recorded value is outside the range of its own named computation |

Three of the four substitutions would have replaced a correct value with a wrong
one **while claiming to correct the record**, and the notes would have carried the
error with a verification pass standing behind it. That is worse than the drift
they were meant to fix, because a number nobody has checked is merely unverified
where a number wrongly corrected is now attested.

**What settled it was reproducing the record's own basis rather than a
reasonable one.** `year_ratio` takes its bin edges from the 57 monthly
measurements and then cuts the 456 method-rows with them, which is neither of the
two obvious implementations. Matching that recovered three rows exactly. Two rows
still do not come back, and the difference between *unreproduced* and *moved* is
the whole finding: an unreproduced number may be right, wrong, or computed some
fourth way, and substituting the current value for it asserts one of those three
without evidence.

**The data had not moved at all.** That was checkable and was not checked before
the drift was asserted. The forecast files grew at the switch, but the exogenous
family still ends at 2020-12, so `shared_targets` intersects to the same 456 rows.
Reading the pre-switch files out of the commit that wrote the table and running
every control on both gives identical values to three decimals.

**What to check first, next time:** before concluding a record drifted,
reproduce the basis the record was computed on, and check whether the inputs
moved at all. Where the inputs are versioned this is a `git show` and one run,
and it is the difference between correcting the record and corrupting it. Where
the original computation was never committed, as here, say so and record the
number as unreproduced rather than replacing it.

## An audit that could not see the thing it was for

The palette note recorded green as four meanings across five figures. It is five
across six: the flux figure uses `FITTED` for its model range and was missed.

The mechanism is worth more than the correction. The sweep grepped for
`ps.FITTED` and filtered out lines containing `FITTED_FILL_ALPHA`, to drop the
alpha constant's own definition. That figure writes its fill as

    facecolor=ps.FITTED, alpha=ps.FITTED_FILL_ALPHA,

so the filter removed the line. The one green use with no recorded
justification was invisible to the audit that existed to find unrecorded uses,
and an audit written the same way would miss it again. Grep for the name and
read every hit; a filter that removes noise removes signal shaped like noise.

Its justification is now recorded: grey is already doing three jobs on that
panel, the uncertainty band, the seasonal average's line and the span marking
where forecasts exist, so a fourth grey for the model range would be
indistinguishable from the band it has to be read against.

### Hatching the evaluated-years span, tried and rejected

IPCC AR5 11.25a hatches a region with a particular status, which is texture
rather than hue and would free one of those three greys without adding a colour.
Rendered, it adds ink. The diagonals run through the whole series rather than
behind it, and on carbon dioxide they cross the uncertainty band into noise. The
IPCC case works because the hatched region is otherwise empty; here it contains
the data. The flat span recedes and the hatch does not. It also frees nothing,
since the hatch is drawn in the same grey.

### The 2015 pair, moved off the figure

The description said the seasonal average predicted 94 nanomoles for July 2015
and the tower measured 40. Both are correct. A single month's pair of values is
an illustration rather than a sample size, and cannot be read off a panel at
this scale, which is the standard already applied to the Shurpali point
estimates on the reconstruction figure. The counts stay: 12 of 57 and 9 of those
are the evaluated n, which a caption is meant to carry.

## Drawn geometry, checked against a fresh recomputation

A check that reads the artifact confirms what was drawn. A check on the numbers
confirms the arithmetic. While the two never run in one process, the first
faithfully confirms whatever the second regressed to, which is the gap these
tests close: each builds its figure through the production path and compares
geometry read off the artists against values recomputed in the same process.

Covered, on the rule that it is worth doing where drawn values are an
estimator's output rather than a redrawing of an input:

| figure | what is recomputed |
|---|---|
| forecast error by horizon | shared targets, both benchmarks' mean absolute error, the eight-model envelope, the Diebold-Mariano margin with its own Bartlett variance and Harvey correction |
| prediction error by year | the median of eight predictions per month, pivoted on family and method |
| reconstruction series | annual totals for all three water table variants |
| coefficient stability | every refit's coefficient and bootstrap interval |
| residual distribution check | the residuals refitted, and their quantiles against both distributions |

Not covered, deliberately: the water table figure and the availability figure
draw a series and its extent rather than an estimate, and their existing tests
already hold what they draw.

**The limit, which matters as much as the coverage.** This proves two
implementations agree. It does not prove the definition is right. The
shared-target logic in these tests was written from the same understanding as
`fully_scored`, so if that understanding is wrong both are wrong together and
every assertion passes. Independence of implementation is what this buys, and
nothing more. A definitional error needs a different instrument: a worked
example computed by hand, or a second person.

The forecast test was checked against the bug it exists for. Collapsing the
pivot back to method alone fails both parametrisations. On this data that
pivot would give between 0.49 and 0.93 of the envelope's true width on methane
and 0.60 to 0.88 on carbon dioxide, so it is live geometry rather than a
historical curiosity.

## The clearance test read series at their vertices

`_raise_top_until_furniture_clears` grows a panel until its key clears the
series running under it. It found the highest series by reading `ax.lines` at
their plotted x values and taking the maximum of those inside the key's span.

Between two vertices a line is straight, so a series that starts low inside the
span and climbs steeply past its right edge is invisible to that test. The
forecast figure is the sharp case, four positions across a panel: methane's
envelope runs 9.98, 11.13, 9.37, 15.06, and a key whose right edge falls at 2.9
sees 11.13 where the series actually reaches 14.49, an error of 3.36 in the
quantity the layout is deciding on.

`_highest_between` replaces the vertex reading and is exact rather than sampled.
The maximum of a piecewise-linear series over an interval is attained at a
vertex inside it or at one of the two edges, so reading the interior vertices
and interpolating the two edges is the whole answer.

**It costs nothing on the figures that use it.** Both users were checked:

| figure | vertex reading | exact | missed |
|---|---|---|---|
| forecast, methane | 15.0593 | 15.0593 | 0 |
| forecast, carbon dioxide | 0.2695 | 0.2695 | 0 |

The forecast key's right edge sits exactly on the last horizon, so the vertex
there was already inside the span and the interpolated edge equals it. The flux
figure samples monthly, so its edges fall at most one month from a vertex and
the reading barely moves. No panel top changed and no figure was redrawn
differently.

That is the point worth recording: the defect was latent, not active. It was
found by checking a placement by hand and would not have been found by looking
at the output, because the output was correct by luck. A key edge landing a
tenth of a category further left, or a data change moving where the envelope
turns, would have put a series under a key with nothing failing.

## Which benchmarks the forecast figure draws, and why not the other two

The subtitle says four benchmarks are compared and the panel draws two. A
proposed sentence would have explained the omission as the other two losing so
heavily at longer horizons that plotting them would compress everything else.
That is true of one of them and false of the other, so it was not written.

Mean absolute error, every benchmark, both gases:

| horizon | climatology | seasonal naive | naive | seasonal naive with drift |
|---|---|---|---|---|
| methane 1 | 8.11 | 11.35 | 12.21 | 11.38 |
| methane 3 | 7.91 | 11.02 | **29.23** | 11.13 |
| methane 6 | 6.91 | 9.40 | **41.42** | 9.57 |
| methane 12 | 8.00 | 10.52 | 10.52 | 10.65 |
| carbon dioxide 1 | 0.2202 | 0.2587 | 0.2998 | **0.2586** |
| carbon dioxide 3 | 0.2211 | 0.2576 | 0.6184 | 0.2587 |
| carbon dioxide 6 | 0.2169 | 0.2540 | 0.7970 | 0.2573 |
| carbon dioxide 12 | 0.2239 | 0.2357 | 0.2357 | 0.2448 |

**The drawn pair is not the two most accurate at every horizon**, and it fails
in two different ways. At twelve months `naive` ties `seasonal naive` exactly on
both gases, because forecasting twelve months ahead from the last observation
uses the value twelve months before the target, which is the same month last
year: the two are the same prediction by construction and the tie is not a
coincidence. And at one month on carbon dioxide, `seasonal naive with drift`
beats `seasonal naive` by 0.0001, which is a tie in everything but sorting.

**The two omissions have different reasons.** `naive` does lose heavily, but in
the middle rather than at the end: 29.2 and 41.4 against a climatology of 7.9
and 6.9 on methane, 0.618 and 0.797 against 0.221 and 0.217 on carbon dioxide,
then back to a tie at twelve. Drawing it would compress the comparison, and
"at longer horizons" is the wrong description of when. `seasonal naive with
drift` is omitted for the opposite reason: it never leaves `seasonal naive`,
differing by at most 0.2 on methane and 0.009 on carbon dioxide, so drawing it
would add a line no reader could separate from one already there.

Any sentence explaining the omission has to carry both reasons or name neither.

## Three errors the reconstruction figure carried

**The subtitle said the three assumptions give 10 to 30 g C per square meter.**
Across the nineteen plotted years they run 7.77 to 30.46: held flat 7.90 to
17.98, continued linearly 7.77 to 30.46, term absent 9.27 to 11.74. The floor
was wrong by more than two grams. The 10 is close to the absent variant's own
floor of 9.27, which suggests it was once read off that line rather than off all
three. It now says 8 to 30.

**It said eighteen of twenty years have nothing to compare against.** The figure
plots nineteen years, 1990 to 2008 inclusive, and two carry a published
measurement, so it is seventeen of nineteen. Twenty is the reconstruction
window's calendar span, 1990 to 2009, which is not what the figure draws.

**It said measurement did not resume until 2007.** For methane it resumed in
2009: the monthly index opens 2009-04, and the Shurpali seasons are recorded
here as seventeen years before the flux record begins, which is 1992 plus
seventeen. 2007 is the carbon dioxide start, and this is a methane figure.

The Shurpali point estimates left the description. They were 9.29 and 8.49 g C
for May to October, which are correct and are already recorded above with their
sensitivity spans, so the figure was carrying the weaker copy of something the
notes hold better. The description keeps the status, that no published total has
been obtained, because that is what the two circled years mean.

One thing the wording must keep refusing: the fan is not an uncertainty range.
The literature convention describes scenario spreads as spanning a conservative
uncertainty range, and this study rejects that reading. The spread is what the
choice of assumption buys, and the record cannot test the choice. That is why
the three are drawn as named lines and never as a band, and why the subtitle
says the term has to be assumed rather than estimated.

## The pending independent validation

Shurpali, N. J., Verma, S. B., Clement, R. J., and Billesbach, D. P. (1993),
*Seasonal distribution of methane flux in a Minnesota peatland measured by eddy
correlation*, Journal of Geophysical Research **98**, 20,649-20,655; and
Shurpali, N. J., and Verma, S. B. (1998), *Micrometeorological measurements of
methane flux in a Minnesota peatland during two growing seasons*,
Biogeochemistry **40**, 1-15. These measured the 1991 and 1992 growing seasons
at this site, seventeen years before the flux record used here begins, and are
the only genuinely independent out-of-sample validation available.

This reconstruction gives, for May to October: **1991, 9.29 g C m⁻² (5.84 to
14.71); 1992, 8.49 g C m⁻² (5.33 to 13.44)**, computed on the adopted 115-month
window. On the nominal 117-month window the same figures were 9.16 (5.87 to
15.08) and 8.36 (5.35 to 13.75).

### The published totals, and a consistency check that is not a validation

The seasonal totals remain unobtained. The abstracts give midday flux: about
1.5 mg CH₄ m⁻² h⁻¹ in late May of both years, 2.5 to 5.5 through early June to
early July, a peak of 6.5 in mid-July 1991 and of 8.0 three weeks later in 1992,
with 1992 the wetter and cooler year and a sustained water table drop from late
July to late August 1991 that may have reduced emission.

Averaging those crudely at roughly 3.5 mg CH₄ m⁻² h⁻¹ across a May to October
season of 4,416 hours gives about 15.5 g CH₄ m⁻², or **11.6 g C m⁻²**, against
predictions of 9.29 and 8.49. That is the model reading low by 20% for 1991 and
27% for 1992.

**This is a consistency check and must not be recorded as a validation.** It
takes midday values from an abstract and averages them over a season in which
flux varies by a factor of five, so the arithmetic is indicative at best. What
can be said is that the direction matches: the bias bands expect the model to
read low by roughly 13%, and this crude comparison points the same way at a
similar order. One point cuts in its favour and is worth stating, since it is
measured rather than assumed: the diurnal cycle at this site explains 0.97% of
half-hourly variance, so midday flux is a far better stand-in for a daily mean
here than it would be at most sites.

**Olson et al. (2013) is now the highest-value paper still to obtain.** Its
Table 2 compares its own budgets against Shurpali and Verma (1998) and Shurpali
et al. (1995), so obtaining it would yield Shurpali's figures second-hand with a
citation trail, and it is newer and more accessible than either 1990s paper.
That is a better route than continuing to chase the originals.

**Shurpali et al. (1995) reports this site emitted 71 g C m⁻² in 1991 and
absorbed 32 g C m⁻² in 1992.** That is carbon dioxide, not methane, so it
validates nothing here. It does confirm the two years differed sharply, which
bears on how informative the pending methane check will be: two years that
differ in carbon balance by more than a hundred grams are a stronger test of a
model than two similar ones would be.

The comparison is prepared and pending. The published values have not been
supplied to this analysis and are not invented here. What makes the pending
check unusually informative is that **1991 and 1992 are among the best-supported
years in the entire reconstruction**, at zero months outside range and 2%
sensitivity spans. The two years carrying independent validation are two of the
few the model is well placed to answer for.

## A defect in the joint-distance measure

The joint-distance measure standardizes each covariate by its standard deviation
over the fit window. A covariate that does not vary there gives a standard
deviation of zero, and dividing by it produced undefined distances. Because a
comparison against a threshold is false when either side is undefined, the
measure then reported **every month as supported**.

No published number changes, because no real covariate is constant over the fit
window. It is recorded because it is the same class of thing this study is
about: a diagnostic failing quietly toward the reassuring answer. Both
`support.joint_support` and `reconstruct._joint_distance_by_month` now drop
non-varying dimensions and raise if none remain, and tests cover both paths.

## What the source figures establish

Statements here come from the figures themselves, retrieved and viewed, rather
than from captions read in isolation. Deventer et al. (2019) was retrieved from
the USDA Northern Research Station copy at
`fs.usda.gov/nrs/pubs/jrnl/2019/nrs_2019_deventer_001.pdf`. Irvin et al. (2021)
was retrieved from the NSF Public Access Repository at
`par.nsf.gov/servlets/purl/10293991`. Feng et al. (2020) was not retrievable
from the publisher, but its seasonal-responses figure is reproduced, credited to
that paper, in a Department of Energy final report at
`osti.gov/servlets/purl/2047108`.

**Deventer figure 8 is a three-dimensional surface, not a contour plot.** Its
panels a and b plot mean flux against half hour of the day and month of the
year as a surface, with contours projected onto the base plane beneath it.
Panels c and d are separate two-dimensional contour plots of the coefficient of
variation over the same two axes. A description of it as a binned contour with a
coefficient-of-variation panel conflates the two halves. The version produced
here is a two-dimensional contour in all cases, because a surface obscures the
values it plots, but the source should not be misdescribed on that account.

**Deventer figure 9 uses 90% prediction bounds** on its soil temperature fit,
which is the same nominal level chosen independently for the intervals here.

**Deventer figure 10 shows uncertainty around a series as a band around the
line it belongs to**, with the range across gap-filling approaches drawn that
way and an inset carrying annual totals with error bars. That is the convention
followed for the reconstruction figure here.

**Irvin figure 9 pairs coverage with sharpness**, plots both against a dashed
line at the nominal level, and separates model identity from calibration state
by giving each its own visual channel and its own legend. That is the form the
calibration figure here follows. The same paper reports coverage of 56.6% and
28.4% against a nominal 95% before calibration, which is the same class of
failure as the 62.5% against a nominal 90% that this study found on its nominal
window, before that number proved to rest on two months of instrument error.

**Olson et al. (2013) could not be retrieved by any route attempted**: the
publisher returned 403 for both the full-text and direct-PDF paths, the USDA
Northern Research Station has no copy at the expected path, the Office of
Scientific and Technical Information returned 404, and ResearchGate returned
403. Its figures have therefore not been seen. Because it is the methodological
precedent, the figure it would most have informed is the reconstruction with its
uncertainty, and that figure instead follows the convention used elsewhere at
this site, in Deventer figure 10. This is a record of what was available, not a
qualification of the result.

## The figure set: sizing and separation, measured

Drawing decisions live in `src/study/plotstyle.py` and are shared by every
figure. Two of them were verified rather than assumed, and the verification is
reproducible through `scripts/verify_palette.py`.

### Separation

Hue carries exactly one distinction across the whole set: whether a month falls
inside the range the model was fitted on. Every other distinction is carried by
line style, marker shape, hatching or lightness, so no figure depends on hue
being seen at all.

Separation was measured, not asserted. Each pair was converted to sRGB, simulated
under the three dichromacies by the method of Viénot, Brettel and Mollon (1999),
and compared in CIE L\*a\*b\* as a Euclidean distance, which is the CIE 1976
color difference. A difference of about 2.3 is the threshold of noticeability.

| Pair | Normal | Deuteranopia | Protanopia | Tritanopia | Grayscale luminance gap |
|---|---|---|---|---|---|
| inside against outside | 114.6 | 111.7 | **93.3** | 166.9 | 0.069 |
| clamped against unclamped | 40.4 | 40.4 | 40.4 | 40.4 | 0.171 |
| clamped against reduced | 62.6 | 62.6 | 62.6 | 62.6 | 0.424 |
| unclamped against reduced | 22.2 | 22.2 | 22.2 | 22.2 | 0.253 |

The support pair stays above 93 under every deficiency. The variant values do not
change across the three columns because those marks are achromatic, which is the
point of making them so.

**Two assignments were rejected on these measurements.** Assigning the support
inside hue to the clamped variant as well would have given one hue two meanings
on the one figure that carries both, the reconstruction. Separately, the support
outside hue and one of the variant hues first proposed measured a difference of
**0.9** under deuteranopia, which is indistinguishable, and those two also
co-occur on that figure. Every three-hue variant set tried measured worse than
achromatic: the best reached 12.5 against 22.2, and all separated less well in
grayscale. Reserving hue for support status resolved both problems at once.

Text contrast against white is 17.4 to 1 for the main ink and 7.0 to 1 for the
muted ink used in descriptions, against a 4.5 to 1 threshold for body text.

Sequential quantities use cividis. It is perceptually uniform, monotonic in
lightness so it survives grayscale, and ships with matplotlib. The alternative
considered, batlow, is comparable on all three counts but arrives through a
further package, and at most one or two figures in the set encode a continuous
quantity by color. The dependency was not worth the difference.

### Sizing

Figures are written as portable network graphics at 1800 pixels wide, or 1200 for
square panels. A GitHub README renders its content column at roughly 900 pixels,
so the figures are drawn at about twice display size and stay sharp on
high-density screens and when opened alone.

Pixel dimensions are the quantity that matters here, and dots per inch only
converts between pixels and the inch-and-point units the drawing library works
in. Nominal resolution is set to 150 so that ordinary point sizes for type land
at comfortable on-screen sizes. Any other pairing of resolution and canvas size
that multiplies to the same pixel count produces a byte-identical image, so the
figure quoted for resolution carries no information on its own.

Vector output is not produced. These are read in a README, which will not display
one, and every figure is regenerable from its function if a document ever needs
one.

## The drawing block sits evenly between its two text blocks

Setting the description from the floor of its block evened the canvas margins
and moved the slack to where the eye meets it next: between the axis label and
the caption. On the water table figure that gap read 95.5 px against 35.1 px
above the panel.

The obvious fix and the previous one are in exact opposition. Moving the
description up by the 60.4 px that would equalise puts its last line 86.4 px
from the canvas bottom, which is the uneven margin just removed, one pixel for
one pixel. Nothing is gained by trading them.

The panel is the third term, and it is the one with room. Growing the drawing
block downward into the rows the description does not use closes the gap without
moving the description at all: both gaps are now 35.06 px, the bottom margin
stays 26, and the panel gains 60.4 px, 451.6 to 512.0.

`balance_drawing_block` measures both gaps after everything is drawn and expands
the block into whichever is larger, so the panel only ever grows. This does not
weaken what the fixed block protects. The block is still 156 px. The case it
exists for, a description filling all five lines, is left exactly as it was, and
no figure loses drawing area to text. What changes is that rows the text does
not use stop being a reservation to defend.

The imbalance runs both ways across the set, which is why the helper expands
rather than shifts. A three-line description leaves 70 px of its block unused
and the panel floats high above its own axis label; a five-line one leaves 12 px
and the below gap falls to about 22 px against 35 above, so the block grows
upward instead and the subtitle clearance closes to about 22 px. Applied to the
water table figure only so far, since each remaining figure should be looked at
as the pass reaches it.

## The description sets from the floor of its block

Every figure looked unevenly bounded: 26 px of air above the title and between
92 and 108 below the description. The four pixels between `MARGIN_PX["top"]` and
`MARGIN_PX["bottom"]` were not the cause. The cause was that the description
block is a fixed 156 px, five lines, and no description in the set uses five on
its own canvas: two use three and four use four, so between 12 and 70 px of
unused rows fell out as white space at the canvas edge.

The fix is where the text anchors, not how big the block is. Setting it from the
floor of the block rather than the ceiling leaves the block the same fixed
height, so `axes_bottom` is unchanged and no panel moves on any figure. Only the
slack relocates, from below the last line to above the first, where it sits
between the axis label and the text and reads as air inside the figure rather
than a broken margin. `MARGIN_PX["bottom"]` went to 26 to match the top exactly.
All eleven figures now measure 26 px of ink to the edge at both ends.

The trade is real and worth naming. Before, the gap between the axis label and
the description was constant at 74 px and the bottom margin varied. Now the
bottom margin is constant and that gap varies, from about 12 px on a five-line
description to about 70 px on a three-line one. The canvas edge is the stronger
reference: an uneven margin there reads as a mistake, while uneven air between
two elements inside the figure reads as spacing.

## The palette convention, and the two collisions that produced it

Recorded in `src/study/plotstyle.py`. Three hues carry meaning across the set and
each carries exactly one:

| | | |
|---|---|---|
| `INSIDE` | `#0072B2` | inside, or retained |
| `OUTSIDE` | `#D55E00` | outside, or discarded |
| `FITTED` | `#009E73` | the range across the eight fitted models |
| `SITE` | `#F0E442` | the site, and the tower on it |

The first two are the support encoding, and they are the strongest separation in
the set: 111.7 apart under deuteranopia and 93.3 under protanopia. `FITTED` is
scoped to the two forecast figures, and exists because the study's halves ask
different questions. `SITE` is the site map only.

The mapped wetland boundary is cartography rather than an encoding: heavy white
over a dark casing, separating from its 48 thin white neighbors by weight. Yellow
was measured as a fallback at 68.8 from its nearest scene tone and was not needed.

**None of these is available for reuse without checking what it already means,
and that check has failed twice.** Sky blue was introduced for the fitted range
beside a blue that already meant retained. The support orange was borrowed for
the wetland boundary beside a wind rose where orange meant discarded, and it also
marked the site in the network panel, so one hue was doing three jobs on one
figure. Both were caught after the figure was built.

**What the contrast checks established.** The imagery was sampled rather than
assumed: the scene is uniformly dark, six dominant tones from `#2D3939` to
`#8A8B6F`, median luminance 0.114 and only 0.02% of pixels above 0.5. Against the
ground beside the tower, which runs from 0.04 under the forest to 0.54 on bare
peat, yellow measures 41.3 from the light peat and 101.5 from the dark forest
under the worst simulated deficiency. It is cased dark in both panels, because on
the network panel it sits 0.161 in luminance from the pale state fill and a white
casing would be 0.095 from it, effectively invisible.

Emphasis was also moved. The boundary had been loud and the tower quiet, which
had it backwards: the tower is one point and the subject of the panel, the
boundary is context.

## Data caveats beyond the study windows

**The water table series steps by about 2 m at 2020-01 and never returns.** Every
month from 1990 to 2019-12 sits between 413.07 and 413.75; every month from
2020-01 to the end of the record in 2021-01 sits between 411.08 and 411.22. The
transition is a single step of −2.25 m between 2019-12 and 2020-01, with no
intervening values, and the series afterwards is as smooth as it was before.
That is the signature of a change of datum or of gauge, not of hydrology.

**This paragraph used to say that nothing in the study touched it. That was
true of the reconstruction half and false of the forecasting half.** The fit
window ends 2019-12 and the reconstruction ends 2009-03, so no fitted
coefficient, holdout or reconstructed year draws on a post-2019 value. The
forecasting half runs to 2021, and `forecast_models.load_covariates` read the
water table column straight through the step until this was caught.

**What it reached, and what it did not.** The models were untouched. Air
temperature and precipitation are absent for every month from 2020-01, so every
design row needing them was already dropped, and rerunning both gases end to end
after the cut reproduced all six forecast files byte for byte. What the step did
reach was every quantity computed from the water table column on its own, where
nothing else forced those months out: the share of the water table the calendar
accounts for, which read **0.5% with the step and 3.8% to 6.0% without it**, and the
partial correlations, which changed sign. Both are corrected above and in the
figure. Twelve months in 141, all at one end of the record and all two meters
out, moved a headline number by a factor of ten.

**The cut is now in the code rather than in a caveat.**
`ingest.covariates.before_datum_break` masks the water table from 2020-01 onward,
and the forecasting half and the figure that reports calendar shares both apply
it. The reconstruction half is unaffected either way, since no month after the
break carries a complete covariate set. It is still worth knowing for anyone
extending this study: the 2020 and 2021 methane months cannot be added without
resolving the datum first, and a naive extension would read the step as a
two-meter drawdown.

The same series carries the two 2019 months described under support, which are
treated as missing there.

## The geospatial layers, and what the wetland inventory says

Four layers under `geodata/` carry the site figure. All were retrieved on
2026-08-09 and each is credited inside the panel that uses it.

| Layer | Source | Detail |
|---|---|---|
| Aerial imagery | USDA National Agriculture Imagery Program, via Microsoft Planetary Computer | scene `mn_m_4709329_sw_15_060_20210831`, 2021-08-31, 0.6 m |
| Wetland polygons | US Fish and Wildlife Service, National Wetlands Inventory | 49 polygons over the panel |
| State outlines | US Census Bureau cartographic boundaries, 2022 | 1:20,000,000, lower states |
| Wind direction | AmeriFlux BASE version 5-5, this site | 172,639 half-hours carrying a direction, 2009 to 2019 |

The imagery covers 47.497 to 47.515 N and −93.500 to −93.478 W. The southern
edge is 47.497 rather than the 47.495 first wanted because the quarter-quad
holding the tower begins there, and a second scene for 220 m would have added a
seam and a second acquisition to attribute.

### Subtitles are balanced, not justified

Nine of the eleven subtitles run to more than one line, and every one of them
was setting as a filled block with a short last line. The worst were the
residual check, whose fourth line was 16 characters against a first of 147, and
the coefficient stability figure at 63 against 147.

Justification was considered and rejected as the wrong instrument twice over. A
justified block never stretches its last line, so a two-line subtitle would end
up flush above ragged, which is the same complaint in a new place. And
stretching word spaces to reach a fixed measure is what body text set in a
column needs; a centred heading is not that. Implementing it would also have
meant drawing each line as its own artist with computed word positions, which
breaks the mathtext bold runs `emphasize` inserts, since a bold term can span a
word boundary.

What a ragged centred block wants is lines of similar length. `_balance` binary
searches for the narrowest measure that does not spill into another line, which
holds the line count and so moves nothing below the subtitle. All nine now set
within about ten characters across their lines. The cost is one function and no
layout change anywhere.

### The three panels now all present a rectangle

Panels a and b are bounded by their own spines at 0.8 weight. Panel c is polar,
so its spine is a circle, and it was the only panel floating on the page.

Three treatments were rendered and compared. A rectangle round each panel
double-frames a and b, which already have one, and reads as ink rather than
structure. A single rectangle round all three mostly outlines the white space
between the columns. A rectangle round panel c alone, on panel b's width and at
the same 0.8 weight, is the one that works: the right column becomes two
stacked boxes on one measure, and the set reads as three framed panels instead
of two boxes and a circle. The ring note stays outside the frame, where panel
a's coordinate labels are.

### Even air above and below, and why 50 was not available

The gap a reader sees is not the one the rectangles describe. Above the panels
it is clear to the subtitle; below it is filled by panel a's coordinate labels
and panel c's ring note, both of which hang outside their boxes. Measured to the
boxes the gaps were 85 and 92, which says the figure is already even and looks
wrong. Measured to the ink they were 85 and 50, which is what the eye was
reporting. The ink measure is the one to hold.

The block is rigid between two text blocks that cannot move, so the two gaps
trade one for one: every pixel taken off the top is added to the bottom. Closing
the top to 50 would have opened the bottom to 85 and moved the imbalance rather
than removing it. Halving the difference is the only setting that leaves them
equal, and both are now 67.8.

Fifty on both sides was available, at a price that was not worth paying. Taking
the 36 px inset off the top gives the drawing area back to the layout, which
widens panels b and c by 16 px and lands both gaps at 48.9. But `ROSE_FLOOR_PX`
was tuned against the narrower panel: a rose 16 px taller hangs 35 px below
panel a's floor, so the frame no longer closes on panel a's bottom and the line
the two columns share is lost. Restoring it means raising the floor to about 83,
which leaves the circle at 355 px against the 374 it has now. So the choice was
even gaps at 68 with the columns aligned and the rose at 374, or even gaps at 49
with the alignment broken, or even gaps at 49 with a 5% smaller rose. The first
was taken: the shared line is structure a reader can see, and the difference
between 49 px of air and 68 is not.

The inset survives, but not for the reason it was added. It no longer clears the
subtitle, which the balance now does. It holds panels b and c at the size the
rose floor was tuned against, and the comment at its definition says so.

### Panel c's floor, and what it cost

The rose carries its legend above the circle and its ring note below, so its ink
runs past its rectangle at both ends. The note was landing 15 px above the
description against panel a's 63.

Raising the rose's floor rather than lowering its ceiling keeps the legend where
it is, so panel b's clearance is untouched; the gaps are now 63 for panel a and
68 for panel c. Because the polar circle's diameter is the panel's height, this
is paid for in the rose's size: 422 px to 374, about 11%. That was accepted over
the alternatives, which were shrinking the gap between panels b and c to under
10 px or moving the legend inside the circle, where the widest dead corner is
165 px against a legend needing about 200.

### The peatland's geomorphology, and what the figure may say about it

The Marcell Experimental Forest's peatlands sit in ice-block depressions left by
the retreating Wisconsin ice sheet, and the Forest Service describes the forest's
six research watersheds that way as a group. Whether that origin applies to this
particular basin cannot be established from anything in this repository or from
the site's own metadata. The Forest Service's own discriminator between the
forest's bogs and its fens is peat depth, and this site's peat depth appears
nowhere in the repository: not in the BADM, not in `geodata/`, not in any
derived table. So the general statement is well sourced and the specific one is
an inference the repository cannot carry, which is why the site figure's
description says nothing about glacial origin.

The rule this settled, in the form it should be kept:

> A figure carries only what it draws or derives from what it draws.

That is stricter than "no uncited claims" and easier to apply. It admits the
subtitle's coordinates, which are the tower the star marks. It admits the 40%
exclusion, which panel c draws. It excludes an ice-block origin, which no layer
on the figure shows, no matter how well cited the claim would be in prose. It is
also why the figure carries no citation: a figure that only says what it draws
has nothing to cite.

### The sector is wider than the upland, and has two stated reasons

The site figure's subtitle attributes the excluded sector to upland forest. Two
things qualify that, both verified here rather than assumed.

Ray-testing the NWI polygons outward from the tower on sixteen compass points,
at 5 m sampling to 400 m, the directions with no wetland at all are NE through
SSE, about 45° to 160°. Due east is as devoid of wetland as southeast. The
subtitle therefore reads "to the east and southeast"; "to the southeast" alone
would be a third of the upland block.

The excluded sector is wider than that block on the clockwise side. SSW, inside
the sector, carries 260 m of continuous wetland from the tower, and S carries 55
m. The sector's definition in `validation/base_v55.py` gives two reasons, tower
flow distortion and upland forest in the flux footprint, and the geometry is
consistent with that: the upland accounts for the sector's middle, not its
edges. "Because upland forest lies to the east and southeast" states the reason
that is visible on panel a and does not claim it is the only one.

### Why the tower coordinates are rounded in two places

`ingest/site.py` holds 47.505 and −93.489. The BADM holds 47.5051 and −93.4893.
The difference is about 11 m north-south and 22 m east-west, invisible on a
two-kilometre panel, so nothing projected from the constants is wrong. But it is
a second source of truth for one number, and the site figure's subtitle quotes
the BADM values to a reader, so the two now differ in the same figure.

They should be left rounded. Widening them changes the projection origin of
every panel that uses them, which moves the star, the 200 m circle and the
imagery window by a fraction of a pixel each, with no gain a reader could see,
and requires re-checking every layout that was measured against the current
extent. The constants are the drawing origin; the BADM is the citable location.
The comment at the definition now says so, which is the fix that was actually
needed: the risk was never the 22 m, it was that the discrepancy was silent.

### Why the wind rose stops at 2019

**The rose is restricted to 2009 to 2019**, the months the model was fitted on,
although the product carries wind direction to 2024 and the sector rule is a
property of the site's protocol rather than of the study window. The restriction
is deliberate and rests on two things.

Every other quantity in this study is computed on the fit window. A wind
climatology running five years past it would be the only panel in the set
describing a different population, and a reader comparing panels would have no
way to know that from the figure.

The shares quoted in the subtitle and description were recomputed on the fit
window for the same reason. Had the rose covered 2009 to 2024 while those
numbers stood, the panel would have plotted one population and quoted another.

| | 2009 to 2019, plotted | 2009 to 2024, full product |
|---|---|---|
| Half-hours | 192,816 | 280,512 |
| Carrying a wind direction | 172,639 | 254,111 |
| In the discarded sector | 77,245 | 105,387 |
| Share of those with a direction | **44.7%** | 41.5% |
| Share of the whole record | **40.1%** | 37.6% |

The rule does not change between the two periods; its cost does, by about three
points, because the wind distribution differs. That is a fact about the weather
of those years and not about the protocol, which is a further reason to quote
the window the study actually uses rather than a longer one.

**The share is quoted against half-hours that carry a wind direction**, 172,639
of 192,816. That is the population a direction rule can act on, and the one
whose shares sum to a hundred in the panel. Quoting the rule against the whole
record is also true and is stated alongside, but it does not match what the
panel plots. Both figures are written into the figure as text, and a test
asserts they still agree with the stored shares, so regenerating that file over
a different period cannot leave the words behind.

**The inventory maps the tower on a polygon of 88.2 acres, 35.7 ha, coded
`PSS3Dg`.** Read out, that is palustrine, scrub-shrub, broad-leaved evergreen,
continuously saturated, on organic soil. It confirms peatland from a third
independent direction: organic soil and a substrate saturated at or near the
surface throughout the year.

**It does not settle bog against fen, and cannot.** The Cowardin system the
inventory uses classifies by vegetation structure, water regime and soil, not by
trophic status, which is the property separating the two. The service's own
definition of the organic modifier groups them, reading "sometimes used to
indicate peatlands, fens, and bogs". So the inventory joins the land cover class
of WET in being consistent with the fen designation while not testing it. The
designation still rests on the site description supplied with the data product,
corroborated by the pore water pH of Deventer et al. (2019).

No layer anywhere gives a bog or fen boundary as such. The polygon drawn in the
figure is the inventory's wetland extent, which is what exists.

## Forecasting: the benchmarks, before any model

The reconstruction asked whether a model fitted on 2009 to 2019 answers for the
1990s. This asks the forward question the 2022 work asked: whether statistical or
machine learning methods forecast monthly flux better at this site. Benchmarks
are built and scored first, because a method that cannot beat a naive rule on a
seasonal series has shown nothing.

Four benchmarks, scored by rolling origin with a sixty-month minimum expanding
training window at horizons of one, three, six and twelve months. The scaled
error's denominator is the seasonal naive error on the training window alone.
`scripts/benchmark_forecasts.py` produces all of it.

### Month-of-year climatology wins at every horizon, on both gases

| Gas | Horizon | Climatology | Seasonal naive | Naive |
|---|---|---|---|---|
| Methane | 1 | **0.435** | 0.549 | 0.573 |
| Methane | 12 | **0.376** | 0.473 | 0.473 |
| Carbon dioxide | 1 | **0.888** | 1.043 | 1.063 |
| Carbon dioxide | 12 | **0.890** | 1.071 | 1.071 |

Mean absolute scaled error. Climatology beats seasonal naive by 19 to 21% on
methane and 15 to 17% on carbon dioxide, at every horizon tested.

**The more telling result is that climatology does not decay with horizon.** Its
error at twelve months is no worse than at one, on either gas, because it uses no
recent information at all. Persistence behaves as expected and falls apart,
methane's scaled error running 0.573 at one month and 1.872 at six. So the recent
past carries something for one month and nothing by six, while the seasonal mean
carries the same amount however far ahead you ask.

**That is close to being the study's finding rather than its baseline.** If these
series are predictable from their month-of-year mean and little else, a model
comparison measures how well each method recovers a seasonal average. Nothing has
been fitted yet, and this is the bar to clear.

### What the numbers rest on

For methane, 82 origins and 82 distinct target months carry 1,240 scored
forecasts; for carbon dioxide, 132 origins and 132 months carry 2,040. **The
forecasts overlap heavily and the effective sample is far smaller than the
count.** Distributions are reported with quartiles rather than as single numbers
for that reason, and the spread is wide: methane's climatology has a median
scaled error of 0.19 against a mean of 0.44.

No percentage error is reported for either gas. It is undefined for carbon
dioxide, which crosses zero, and dominated by near-zero months for methane.

At a twelve-month horizon seasonal naive and naive are identical by construction,
since the last observed value and the value twelve months before the target are
the same month.

### The result survives the window it was measured through

The sixty-month minimum puts methane's earliest scorable month at 2015-03, so the
two highest summers of the record, 2011 at 132.3 and 2012 at 115.3 against an
all-record July to September mean of 76.1, are training data for every origin
while the two lowest, 2015 at 46.3 and 2021 at 35.4, are the ones scored.
Climatology's mean is therefore lifted by years it can never be tested on and
then over-predicts the low years it can. Both its skill and its failures could be
artifacts of where that minimum falls, so the benchmarks were rerun across four
window lengths before anything was fitted.

Climatology's error as a ratio to seasonal naive on the same months:

| Minimum | Methane, h=1 | h=6 | h=12 | Carbon dioxide, h=1 | h=6 | h=12 |
|---|---|---|---|---|---|---|
| 36 | **0.732** | 0.675 | 0.720 | **0.803** | 0.800 | 0.815 |
| 48 | **0.753** | 0.753 | 0.768 | **0.814** | 0.816 | 0.847 |
| 60 | **0.777** | 0.793 | 0.773 | **0.846** | 0.852 | 0.831 |
| 72 | **0.778** | 0.785 | 0.829 | **0.829** | 0.834 | 0.850 |

**The conclusion holds at every window.** Climatology beats seasonal naive by **17
to 33% on methane and 15 to 20% on carbon dioxide**, across every horizon and
minimum in the table. The lower bound was previously given as 22%, which omitted
the weakest cell, methane at twelve months on a seventy-two month minimum, where
the ratio is 0.829. Note that these are **ratios of mean absolute error**, while
the percentages in the benchmark section above are ratios of *scaled* error; the
two measures are not interchangeable and the sections should be read as reporting
different quantities. The advantage is *largest* at the shortest window, so the
sixty-month choice understates it rather than manufacturing it. At a thirty-six
month minimum the evaluation window admits 2012, a summer 51% above the record
mean, and climatology still wins by more than at sixty. Including a high year
does not overturn the result, which is what the confound would have predicted.

**Forty-eight months is adopted**, not because it maximizes the advantage, which
thirty-six does, but because of what enters the evaluation window:

| Minimum | Summers scored, above vs below the record mean | Observations per month of year at the first origin |
|---|---|---|
| 36 | 4 above, 5 below | 3.0 |
| **48** | **3 above, 5 below** | **4.0** |
| 60 | 2 above, 5 below | 5.0 |
| 72 | 2 above, 4 below | 6.0 |

Sixty and seventy-two leave only two above-average summers against four or five
below, which is the imbalance that raised the question. Thirty-six fixes the
balance but estimates each month-of-year mean from three observations, which is
too thin to defend as a seasonal average. Forty-eight admits 2014 at 97.3,
carries four observations per month, and yields ninety-four scorable months
against eighty-two. The trade is a slightly noisier seasonal estimate for an
evaluation window that spans both directions.

### The scaled error did not deliver the comparability it was chosen for

Mean absolute scaled error was chosen so the two gases could be compared on one
footing. Between these two series it does not do that.

| | Methane | Carbon dioxide |
|---|---|---|
| Denominator, seasonal naive on the training window | 20.328 | 0.290 |
| First origin to last | 25.342 to 16.540, a 35% fall | 0.311 to 0.304 |
| The same benchmark on the months actually scored | **10.575** | **0.303** |
| Ratio, scored to training | **0.520** | **1.045** |

Methane's denominator is **twice the difficulty of the period being scored**,
because the early record is much noisier than the later one, and it falls 35%
across origins as the training window accumulates better years. Carbon dioxide's
matches its test period. Every methane scaled error is therefore depressed by
roughly a factor of two relative to carbon dioxide's, and the apparent gap
between 0.4 and 0.9 is mostly that rather than a difference in predictability.

**Mean absolute scaled error is kept for comparison within a gas**, where the
denominator is common to every method. **Cross-gas statements use the error as a
ratio to seasonal naive measured on the same scored months**, which shares no
training-period term and does travel between series.

### The framing for the model comparison

Climatology already extracts the entire month-of-year signal, and it does so
without decaying at horizon: its error at twelve months is no worse than at one,
on either gas. Persistence carries something for about a month and nothing by
six. So deseasonalizing before fitting is not a preprocessing convenience. It is
the question. **What the models are being asked is whether anything predicts what
the seasonal mean leaves over.**

The diagnostics say what that residual is made of. Methane's seasonal amplitude
varies **4.5-fold**, from 33.7 in 2021 to 150.6 in 2011, a coefficient of
variation of 43%, with **no trend detected** (p = 0.215). It is not drifting;
it varies without direction. The two lowest-amplitude years are exactly the two
years climatology fails on. A time-varying climatology cannot help, because there
is no trend for it to track.

**So the proposition under test is that methane at this site is predictable in
shape and not in magnitude**: the seasonal pattern repeats, the size of the
season does not, and nothing in the seasonal structure anticipates it. The
lagged-covariate family exists to test whether anything outside that structure
does. If nothing reaches it, that is the finding, and it is a more useful one
than a ranking of methods against each other.

Deseasonalizing is applied to both gases, whose lag-12 autocorrelation is
significant at z = 3.32 and 4.11 against a Bartlett standard error. **Detrending
is not applied to either**, because neither shows a trend approaching
significance, raw or deseasonalized, and following Makridakis et al. (2018) means
applying each step where its diagnostic fires rather than applying the whole
protocol regardless.

### The easier-case framing was wrong, and is retracted

Carbon dioxide was described as the easier case with stronger seasonality, on a
lag-12 autocorrelation of 0.83 against methane's 0.62. **That comparison used the
unbalanced series and was substantially an artifact of diurnal sampling.** On the
balanced series, over the era both share:

| | Methane | Carbon dioxide, unbalanced | Carbon dioxide, balanced |
|---|---|---|---|
| Autocorrelation at the annual lag | 0.617 | 0.829 | **0.692** |
| Variance explained by month-of-year means | 70.9% | 85.6% | **70.3%** |
| Seasonal naive against naive, error ratio | 0.985 | 0.709 | **0.916** |

The gap in the annual autocorrelation narrows from 0.21 to 0.08, and on the
variance measure it **inverts**: methane is fractionally the more seasonally
explained of the two. Carbon dioxide keeps a real advantage in that its annual
cycle beats persistence more clearly, 0.916 against 0.985, but it is not the
easier case in the sense claimed. Neither gas should be framed as the easier one.

### Whether the artifact reached the reconstruction

It did not, and this was checked rather than assumed. The legacy `FC02_Avg`
column is an unweighted mean of every half-hour and carries the same diurnal
skew. It is read by `covariates.load_fco2`, named in `windows.CONTEMPORANEOUS_ONLY`
as excluded from the reconstruction covariates, and appears in the covariate
coverage table. It reaches **no fitted model, no holdout experiment, no
reconstruction and no figure**: no module under `src/study` that fits or predicts
references it, and neither does any figure. The exclusion that kept it out was
made because it has no pre-2009 record, not because of the artifact, but it had
the effect of keeping the artifact out of every result.

### An open question, not a decision

Methane has not been diurnally balanced. Its diurnal cycle explains 1.5% of
half-hourly variance against carbon dioxide's 29.1%, and balancing would move its
monthly means by about 4.3% of their typical magnitude, so the effect is small.
It is left alone because every number in the reconstruction rests on the current
series, and that work is committed and written up. **This is recorded as
considered rather than settled.** If the forecasting work later needs both gases
on an identical footing, balancing methane is the change to make, and the cost is
recomputing the reconstruction rather than any difficulty in the aggregation.

## Forecasting: the models

Two families were fitted, kept apart throughout. The **autoregressive** family
sees only the flux's own past and the calendar, so a twelve-month forecast is a
genuine twelve-month forecast. The **exogenous** family adds lagged soil and air
temperature, precipitation and water table depth. Pooling them would put a method
that can see the weather against one that cannot, which measures information
rather than method.

Every forecast is direct: a separate model per horizon, all of whose predictors
are lagged by at least the horizon. Nothing contemporaneous appears anywhere. The
month-of-year means, the predictor screening and the fit all happen inside the
fold, on months up to the origin.

### The comparison had to be put on shared months before it meant anything

The families reach different distances into the record. On methane the benchmarks
score 94 target months, the autoregressive family 80, and the exogenous family 57,
because the four covariates are all present in only 117 of 153 months and the
lags eat further into the start. Scoring each family on whatever it could reach
and then dividing produced a table in which models appeared to beat climatology at
three horizons out of four. On the 57 months every method could score, that
becomes one horizon out of four. **The apparent win was the month set, not the
method.** `evaluation.shared_targets` and `evaluation.restrict` exist to prevent
this, and every number below is on shared months.

### Climatology is beaten at two horizons of eight, tied at a third, and not significantly

On shared months, the best method against the best benchmark, as a ratio of mean
absolute error where below one means the model wins:

| horizon | methane | best method | carbon dioxide | best method |
|---|---|---|---|---|
| 1 | **0.887** | autoregressive ridge | **0.935** | autoregressive gradient boosting |
| 3 | 1.073 | autoregressive gradient boosting | 1.012 | exogenous ridge |
| 6 | 0.999 | exogenous gradient boosting | 1.034 | autoregressive ridge |
| 12 | 1.095 | autoregressive ridge | 1.060 | autoregressive gradient boosting |

Month-of-year climatology is the best benchmark at every horizon on both gases.
Models beat it at one month on both gases and tie it at six months on methane,
so it is beaten at two of eight and tied at a third; everywhere else the
climatology is better. Corrected for serial correlation with
a Diebold-Mariano test, Bartlett-weighted at the larger of the horizon minus one
and the automatic Newey-West lag, and with the Harvey, Leybourne and Newbold
small-sample factor, **no horizon on either gas separates the best method from
climatology**:

| gas | horizon | best method | n | effective n | DM t | DM p | sign-test p |
|---|---|---|---|---|---|---|---|
| methane | 1 | autoregressive ridge | 57 | 35.6 | −0.67 | 0.503 | 0.185 |
| methane | 3 | autoregressive gradient boosting | 60 | 31.4 | +1.41 | 0.163 | 0.245 |
| methane | 6 | exogenous gradient boosting | 61 | 68.8 | −0.09 | 0.928 | 0.443 |
| methane | 12 | exogenous gradient boosting | 65 | 39.3 | +1.51 | 0.136 | 0.082 |
| carbon dioxide | 1 | autoregressive gradient boosting | 85 | 80.4 | −1.37 | 0.175 | 0.386 |
| carbon dioxide | 3 | exogenous ridge | 85 | 79.3 | +0.28 | 0.779 | 0.828 |
| carbon dioxide | 6 | exogenous ridge | 85 | 80.1 | +0.62 | 0.539 | 0.386 |
| carbon dioxide | 12 | autoregressive gradient boosting | 85 | 32.4 | +0.98 | 0.331 | 0.128 |

A negative statistic means the model beat climatology. **The overlap correction
matters:** methane at one month is worth 35.6 independent comparisons rather than
57, at three months 31.4 of 60, and carbon dioxide at twelve months 32.4 of 85.
The earlier sign-test values were optimistic as flagged, and nothing changes
direction, but methane at one month moves from p = 0.185 to p = 0.503, which is
the difference between a number worth mentioning and one that is not.

Effective n above n appears in several of the method-group comparisons below.
That is not an error: it means the loss differential alternates rather than
persists, which mildly increases precision.

### The methane one-month advantage is one year, and a simpler method has it too

Ridge's lower mean absolute error at one month is real but it is not spread over
the record. It is **almost entirely 2015**:

| year | months scored | nmol saved against climatology | that summer as a share of normal |
|---|---|---|---|
| 2015 | 8 | **+85.2** | 0.62 |
| 2016 | 12 | +0.7 | 0.94 |
| 2017 | 12 | +19.8 | 1.02 |
| 2018 | 12 | −33.4 | 1.12 |
| 2019 | 12 | −8.0 | 1.01 |
| 2020 | 1 | −1.5 | 1.07 |

The expectation was that the gains would be in low-amplitude years where
climatology over-predicts, and that is confirmed. 2015 is the weakest summer in
the scored window at 0.62 of the average year's June-to-September mean, and the
second weakest in the whole record after 2021. Excluding it, ridge is **worse** than
climatology by 22.4 nmol over the remaining 49 months. Splitting the same way
with a Diebold-Mariano test: all months t = −0.67, p = 0.503; excluding 2015
t = +0.52, p = 0.606; 2015 alone t = −1.35, p = 0.218 on eight months.

**But the advantage is persistence, not detection, and it belongs to a one-line
benchmark.** In 2015 alone, naive-1, which is last month's value carried forward
with no seasonal structure at all, saves 117.3 nmol against climatology, against
ridge's 85.2. The mechanism is visible in the coefficients: fitted at July 2015
on the deseasonalized series, ridge puts **+1.034 on the one-month lag**, which
is unit weight on last month's departure from its seasonal mean. Ridge is a
seasonal mean plus last month's anomaly carried forward, shrunk enough not to pay
naive's cost in ordinary years, where naive loses 233.7 nmol overall.

So the honest statement is narrower than "a model detects an anomalous year one
month ahead". The 2015 anomaly was detectable one month ahead, the information
was in the previous month's flux and nowhere else, and what the model contributed
was knowing how much to weight it. **No covariate the tower measures was
involved.** The anomaly is visible in the record from May 2015, when the flux
fell to 0.75 of its month-of-year mean, and reached 0.50 by July.

### Statistical against machine learning, which was the original question

Mean scaled error by method group on shared months, with the difference in the
last column, where positive means the machine learning group did worse:

| family | horizon | methane ML − stat | carbon dioxide ML − stat |
|---|---|---|---|
| autoregressive | 1 | +0.092 | −0.002 |
| autoregressive | 3 | +0.044 | +0.023 |
| autoregressive | 6 | +0.030 | +0.024 |
| autoregressive | 12 | +0.054 | −0.001 |
| exogenous | 1 | +0.039 | +0.001 |
| exogenous | 3 | +0.023 | +0.047 |
| exogenous | 6 | −0.017 | +0.033 |
| exogenous | 12 | −0.113 | −0.019 |

Ordinary least squares and ridge are ahead of the random forest and gradient
boosting in twelve of sixteen comparisons, and the margins are small everywhere
except the two exogenous methane cases at six and twelve months, where gradient
boosting is genuinely ahead. This reproduces the direction Makridakis et al.
(2018) found on M3 and that Li et al. (2026) found on flux data: **on a series
this short, the extra flexibility does not pay for itself.** Ridge and ordinary
least squares are within 0.002 of each other throughout, which says the design is
not collinear enough for the penalty to matter.

### What the screening kept: a finding, not a diagnostic

Boruta was rerun in every fold, with the seasonal terms retained without being
judged. Share of folds in which each predictor survived, exogenous family:

| predictor | methane h=1 | h=3 | h=6 | h=12 | CO2 h=1 | h=3 | h=6 | h=12 |
|---|---|---|---|---|---|---|---|---|
| seasonal terms (three) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| annual flux lag | 0.66 | 0.25 | 0.55 | 0.17 | 1.00 | **1.00** | 1.00 | 1.00 |
| one-month flux lag | 1.00 | — | — | — | 1.00 | — | — | — |
| soil temperature | 0.93 | 0.00 | 1.00 | 0.85 | 0.00 | **0.00** | 0.15 | 0.93 |
| air temperature | 1.00 | 0.00 | 0.89 | 0.72 | 0.01 | **0.00** | 0.76 | 0.42 |
| precipitation | 0.20 | 0.00 | 0.03 | 0.54 | 0.09 | **0.00** | 0.14 | 0.33 |
| water table | 0.29 | 0.10 | 0.00 | 0.00 | 0.15 | **0.00** | 0.00 | 0.48 |

**Carbon dioxide at three months is the sharpest result in the table.** The
annual flux lag survives in every fold; not one covariate survives in any fold,
at any point in the record. Soil temperature, air temperature, precipitation and
water table depth carry nothing about carbon dioxide three months out that the
seasonal terms and last year's value do not already hold. Carbon dioxide never
uses water table at three or six months and only reaches for it at twelve, where
lagging by a year makes it a seasonal quantity again.

Methane is less extreme but points the same way. Its covariates matter at one
month, vanish entirely at three, and return at six and twelve as temperature.

### The surviving temperatures are the season restated

Where a covariate does survive it is usually soil or air temperature, which the
earlier note described as the season arriving by another route. That is now
established rather than asserted. A phase-shifted annual cycle is a linear
combination of the same sine and cosine, so lagging a seasonal driver does not
stop the seasonal terms from restating it. Regressing each surviving covariate
lag on the three seasonal terms:

| gas | predictor | explained by the calendar | partial r with the flux | p |
|---|---|---|---|---|
| methane | soil temperature, lag 1 | 0.947 | **0.268** | 0.0017 |
| methane | air temperature, lag 1 | 0.950 | 0.118 | 0.202 |
| methane | soil temperature, lag 6 | 0.947 | 0.024 | 0.784 |
| methane | air temperature, lag 6 | 0.947 | −0.004 | 0.964 |
| methane | soil temperature, lag 12 | 0.954 | 0.174 | 0.049 |
| methane | air temperature, lag 12 | 0.954 | 0.032 | 0.729 |
| methane | precipitation, lag 12 | 0.397 | 0.152 | 0.100 |
| methane | water table, lag 1 | 0.042 | **0.245** | 0.0075 |
| methane | water table, lag 2 | 0.044 | 0.220 | 0.017 |
| carbon dioxide | air temperature, lag 6 | 0.950 | **0.277** | 0.0015 |
| carbon dioxide | soil temperature, lag 12 | 0.953 | 0.099 | 0.236 |
| carbon dioxide | air temperature, lag 12 | 0.950 | 0.139 | 0.115 |
| carbon dioxide | water table, lag 12 | 0.045 | **0.250** | 0.0042 |
| carbon dioxide | precipitation, lag 12 | 0.382 | −0.038 | 0.667 |

**Every temperature lag that survived screening is between 94.7% and 95.4%
explained by the calendar alone**, at every lag, on both gases. The lag is
irrelevant to this: a six-month lag inverts the phase and a twelve-month lag
restores it, and both are recoverable from a sine and a cosine of the same
frequency. What is left over is small. Two of the seventeen partial correlations
clear a Bonferroni threshold of p = 0.0029 — methane against soil temperature at
lag 1 (r = 0.268) and carbon dioxide against air temperature at lag 6 (r = 0.277)
— so there is a genuine non-seasonal temperature signal, but it accounts for
about 7% of the flux's non-seasonal variance in the two cases where it exists at
all, and none elsewhere.

Water table is the one covariate the calendar cannot explain, at **4.2% for
methane at lag 1** and **4.5% for carbon dioxide at lag 12**, against 95% for
temperature, so it is genuinely non-seasonal information.

**The screening result is a methane result that carbon dioxide follows only at
the top of the ranking.** Ranking the four measurements by mean share of rebuilds
across the four horizons, against the share of each the calendar explains:

| | calendar | methane chosen | carbon dioxide chosen |
|---|---|---|---|
| soil temperature | 95% | 69% | 27% |
| air temperature | 95% | 65% | 30% |
| precipitation | 38 to 40% | 19% | **14%, the lowest** |
| water table | 4 to 6% | **10%, the lowest** | 16% |

The rank correlation between what the calendar explains and what the models chose
is **+0.80 on methane and +0.60 on carbon dioxide**, and on carbon dioxide the
bottom two invert: precipitation, which the calendar explains 38% of, is chosen
less often than the water table, which it explains 6% of. Neither correlation is
significant at four points (p = 0.20 and 0.40), which is the honest reading of a
four-item ranking and a reason not to lean on the correlation itself.

So "the models reached for what the date already predicts and left alone what it
does not" holds on methane and holds only for the temperatures on carbon dioxide.
The figure's description says "choosing temperature most and the water table
least **on methane**" for this reason.

**Two places state it more broadly than that supports, and neither is edited
here.** The README says of the water table: "It is also the measurement the
models chose least often." That is true on methane and false on carbon dioxide,
where precipitation is lower at 14% against 16%. And the section above concludes
from the temperature and water table shares alone, which is where the claim is
strongest; it does not mention that precipitation breaks the pattern on one gas.
The fix in both cases is one qualifier, not a retraction: the ordering by
calendar share is right at the top and wrong at the bottom on one of two gases.

**These water table figures are corrections, and they change what this section
concludes.** The values published here before were 0.2% and 0.5% for the calendar
share and r = 0.006 and −0.157 for the partial correlation, and all four were
artifacts of the 2020 datum step described under data caveats: twelve months
sitting two meters below the rest of the record, read as hydrology. Cut at the
break, the water table's partial correlation with the deseasonalized flux is
**+0.245 for methane at lag 1 (p = 0.0075)** and **+0.250 for carbon dioxide at
lag 12 (p = 0.0042)** — the same sign, and very nearly the same size, as the two
temperature terms that do clear the threshold. Neither water table term clears
the Bonferroni threshold of 0.0029, so neither is claimed as established; but the
earlier statement that **the covariate carrying independent information carries no
usable signal is withdrawn.** It carried a signal of ordinary size and a fitted
error was hiding it.

What survives, and it is the sharper claim, is this. The water table is not
disqualified by an absence of correlation. It is disqualified by the coefficient
stability result: the term does carry signal inside the fitted range, and its
coefficient still moves by half its own value as that range narrows, so it cannot
be projected past the range's edge. Correlation was never the obstacle. Support
was.

Two cautions on reading the survival counts. Boruta is all-relevant rather than
minimal-optimal, so two predictors carrying the same information both survive and
the size of a kept set is not a count of independent information. And the
binomial threshold is the published rule rather than a calibrated error rate:
only the shadow is redrawn between repeats, so the repeats are not independent.
Measured on synthetic null data, between four and eight percent of irrelevant
candidates survived.

### The same result at twenty-three other wetlands, and a limit of monthly data

This is replication rather than a standalone result, and it belongs here because
it says what condition makes this site behave the way it does. Knox et al. (2021),
*Global Change Biology* **27**, 3582-3604, identified the dominant environmental
predictors of freshwater wetland methane flux across 23 sites and found
temperature dominant wherever seasonal water table variation was small.

**Their condition is testable, not qualitative.** Sites where the water table
dominates tend to have a greater ratio in the variation of the water table
relative to the variation in air temperature. This site sits at the other end of
that ratio. Over the whole clean record, 1990-01 to 2019-12 less the two months
established as instrument error, the water table's month-of-year means span
**0.135 m** and the three seasonal terms fitted to it span **0.101 m**, against a
full observed span of **0.680 m**, from 413.07 to 413.75. Air temperature's
month-of-year means span **32.65 °C** against a full span of 42.47 °C. Put as each
variable's seasonal swing relative to its own full span, the water table is
**0.199** and air temperature **0.769**, a ratio of about one to four. The water
table here moves, and most of that movement is not seasonal, which is the same
fact as its small calendar share seen in meters rather than as a variance share.
**This is the regime their synthesis predicts temperature dominance in**, so the
finding that the models reach for temperature and not for the water table is what
the multi-site work expects of a site like this one, not an anomaly of this
record.

**An earlier version of this paragraph was wrong twice over, and both errors are
worth keeping visible.** It reported a full observed range of **2.380 m**, which
is the 2020 datum step described under data caveats: the series was read across a
change of gauge, and two meters of instrument became two meters of hydrology. It
then reported a month-of-year span of **0.333 m**, computed on the same
contaminated series. Neither figure survives. The conclusion does, at 0.199
against 0.769 rather than 0.140 against 0.813, which is the useful part: the
ratio is robust to the error that produced it, and that is luck rather than
method.

### Three water table spans, and which is which

Three different quantities in these notes are the "range" of the water table, two
of them printed **0.33** at some point, and they have been used interchangeably.
They are not the same thing and no argument should move between them.

| quantity | value | what it is |
|---|---|---|
| Full observed span | **0.680 m** | 413.07 to 413.75, 1990-2019, less the two instrument-artifact months. The site's whole hydrological range. |
| Seasonal swing | **0.135 m** | The span of the month-of-year means. What the calendar accounts for. |
| Fitted seasonal cycle | **0.101 m** | The span of the three seasonal terms fitted to it. The same idea, estimated rather than binned. |
| Fit window span | **0.330 m** | 413.13 to 413.46 over the 115 months the model was fitted on. The evidence the water table coefficient rests on. |

The **0.33 m cited throughout as "the fitted water table range" is the fourth
row**, the span of the fit window, and it is the right number for any statement
about extrapolation or coefficient support. The **0.333 m** that appeared in the
Knox paragraph was the second row computed on the contaminated series; corrected,
that row is 0.135 m and the resemblance disappears. Two quantities printing the
same digits is why the conflation went unnoticed.

**How much any single driver carries, for scale.** At site level they report a
top predictor generally explaining between 10 and 50 percent of variance. That is
the range a dominant driver occupies in this literature, and it is worth holding
beside the 7% of non-seasonal flux variance the two significant temperature
partial correlations account for here.

**Consistent, not identical, and the difference matters.** Their result ranks
which drivers matter. This one shows that the driver that matters is collinear
with the seasonal cycle — 94.7% to 95.4% of every surviving temperature lag is
recoverable from three seasonal terms. A ranking cannot say that, because a
driver can rank first while being a restatement of the calendar, and it can rank
first while being independent of it. The two results agree on which variable comes
out on top and answer different questions about what that means. Nothing here
should be written as reproducing their finding.

**A limit of this study's resolution, stated as such.** A 2024 synthesis reports
seasonal methane flux changes lagging the water table by about 17 days across 23
sites. Seventeen days is sub-monthly, so a monthly aggregation cannot represent
it: a lag shorter than the sampling interval is aliased onto zero or onto one
whole month, and neither is the truth. Nothing here rules out a water table
effect operating at that lag; the monthly series simply cannot see it. This is a
statement about the resolution of this study, not about the site. The citation is
not yet pinned to a volume and page, and must be before any writeup carries it.

### The figure, and the palette measurement behind it

`figures/forecast_error_by_horizon.png`, built by
`study.figures.forecast_error_by_horizon`
from the scored forecasts rather than by refitting.

The subtitle carries the method definitions, the benchmark count and what the band
means, so the description carries only what it does not: that the two panels are in
different units whose heights are not comparable, and where the fitted range crosses
the seasonal average. `plotstyle.wrap_subtitle` sizes the title block from the
wrapped subtitle rather than fixing it, so a figure whose subtitle has to define its
terms is given the room instead of being compressed into it; every other block stays
fixed.

**Mean absolute error against horizon, one panel per gas, in each gas's own
units, on linear vertical scales and a categorical horizontal one.** Scaled error
does not appear at all. It was chosen so the gases could be
compared on one footing and does not deliver that, so removing the measure
removes the axis a reader could misuse, which is stronger than labeling it.

**What sets the band's width, which is not what a reader first assumes.** The
half-width at each horizon is a critical value times the long-run standard
deviation of the loss differential, divided by the root of the sample size. The
sample size varies modestly across horizons; the standard deviation of the
differential varies enormously, and it dominates:

| gas | horizon | sd of the month-to-month difference in absolute error | effective n | band half-width |
|---|---|---|---|---|
| methane | 1 | **9.744** | 35.6 | **3.273** |
| methane | 3 | 2.160 | 31.4 | 0.798 |
| methane | 6 | 1.449 | 68.8 | 0.381 |
| methane | 12 | 3.064 | 39.3 | 1.177 |
| carbon dioxide | 1 | 0.091 | 80.4 | 0.020 |
| carbon dioxide | 3 | 0.095 | 79.3 | 0.022 |
| carbon dioxide | 6 | 0.101 | 80.1 | 0.024 |
| carbon dioxide | 12 | 0.073 | 32.4 | 0.029 |

The methane band is a wedge, reaching from 8.1 down to 4.8 at one month and
narrowing to a sliver by six. **That is not a statement that short horizons are
uncertain.** At one month the closest method is ridge, which puts near-unit weight
on last month's departure from the seasonal mean, so its errors differ from
climatology's erratically month to month: the standard deviation of that
difference is 9.744, larger than climatology's own mean absolute error of 8.106.
A method whose advantage is concentrated in a few months, which is exactly what
the 2015 examination found, produces a high-variance loss differential and
therefore a wide band. At six months the closest method is a gradient boosting
fit that tracks climatology closely, the differential has a standard deviation of
1.449, and a much smaller gap would be detectable.

So the band answers "how large a difference would be needed here", and the answer
depends on how erratically the two methods being compared disagree, not on how
well the seasonal average is known. The description says so, because a reader
would otherwise read the wedge as uncertainty and draw the opposite conclusion
from the one the study reached.

**The pale band is an inverted Diebold-Mariano test.** `evaluation.significance_margin`
returns the difference in mean absolute error that would have reached p = 0.05
given the observed noise in the loss differential, so a method inside the band is
not distinguishable from climatology and a reader checks that directly instead of
taking a caption's word. Its width uses the long-run variance and the Harvey
correction, so it reflects effective sample size: 35.6 rather than 57 at methane's
one-month horizon. **The best fitted method is inside the band at every horizon on
both gases**, which is the figure's whole claim, drawn rather than asserted.

**The fitted models are a range, not eight curves.** Four of the sixteen method
comparisons reach nominal significance and none survives correction, so drawing an
order would assert a ranking the evidence cannot support. The envelope's lower
edge dips below climatology at one month on both gases and at six on methane, in
each case without leaving the band. Its upper edge does leave the band at three,
six and twelve months, which is a real finding in the other direction: some fitted
methods are distinguishably *worse* than a seasonal average.

**Persistence is drawn to six months only.** At twelve, carrying the last value
forward reaches the same month the seasonal benchmark uses, so the two coincide by
construction and the curve would appear to recover from 41.4 back to 10.5.
Drawing that would be true and misleading at once.

**Carrying last month's value forward is scored but not drawn, and two earlier
attempts to draw it were both wrong.** It loses at every horizon past one month
and nobody would use it, so it is not a contender; what it establishes is that
recent information decays with horizon, which reads as a sentence and now sits in
the subtitle.

The first attempt let it leave the top of a linear panel with its value
annotated. That failed because **the annotated number was unreachable from the
axis**: a reader saw a line exit the frame and a figure with no relationship to
any scale, and the visible stub read as apparatus rather than as a series. The
second attempt put the vertical scale on a logarithm, which did make it reachable
and did preserve flatness, but **it was scaling the figure for the benchmark that
loses badly**. Compressing everything else into the lower half of the axis costs
most on carbon dioxide, where climatology's 15% margin over the seasonal
benchmark is real and looks like nothing on an axis running to 1.0. Dropping the
series fixed both at once, and with it the mixed logarithmic tick labels, the
empty band left by a legend pad, an unexplained terminal marker, and an
annotation that crossed the curve.

Each panel now spans what its drawn series occupy: 4.8 to 15.1 on methane and
0.193 to 0.270 on carbon dioxide, plus headroom for the legend.

**The horizontal scale is categorical.** At their true numeric positions the step
from six months to twelve is twice the step from three to six, which stretches the
curves for a reason that has nothing to do with the forecasts. No tick is drawn at
nine, because nothing was evaluated there.

**The subtitle ends on the band; the panel notes sit at the bottom.** The
persistence fact was briefly put in the subtitle, where it fell between the
finding and the explanation of the band and pushed that block to six lines. It
belongs with the other panel notes in the description, and a test checks that the
figures it quotes are the ones the data holds.

**The legend is two columns, one group each, centered above the curves.** Each
heading sits over its own entries and is underlined by a drawn rule, because
matplotlib's mathtext has no underline. The rules are added to the figure rather
than to the axes, so they do not appear in `ax.lines`, where the checks that keep
the furniture off the data would otherwise count them as series.

**The band's legend entry names the band, not what is true inside it.** "Too
close to the average to tell apart" described the methods that fall in the band
rather than the region itself, which is why it read oddly as a key entry. It now
reads "Margin needed to differ from the average", which is what the region is.

**The subtitle is set at the description's size.** It carries the finding and is
read first, but it is near-black against the description's muted gray, and that
difference carries the hierarchy without a difference in size as well. Set on the
shared constant, so the whole figure set matches; two intermediate sizes were
rendered and compared before choosing. On this figure the subtitle rewraps from
five lines to four and the panels gain the room.

**The description names the units rather than saying they differ.** "The two
panels are in different units" leaves a reader to work out which and why it
matters; the panel now says methane is in nanomoles and carbon dioxide in
micromoles, so the two cannot be compared by eye. The persistence sentence was
cut from the figure entirely: it described a series the panel does not draw, and
these notes carry it.

**The headroom is measured rather than fixed, and for every piece of furniture.**
How much room is needed depends on the furniture's rendered size and on how high
the series run beneath it, which differ between the gases: a pad chosen by hand
gave methane visible empty space and still left carbon dioxide overlapping its
seasonal line by a thousandth of a unit. Correcting the legend alone then moved
the collision onto the annotation rather than removing it, so
`_raise_top_until_furniture_clears` grows the axis until the legend keeps a fixed
pixel gap above the nearest series and the annotation's target sits at a fixed
share of the panel height, which is what gives its arrow length.

**Two things about that loop are worth recording, because both diverged first.**
The clearance was initially a share of the data range, so each enlargement raised
the requirement that had prompted it and the axis ran away. It is a pixel
quantity now. The arrow length was initially measured from the annotation's own
window extent, which for an `Annotation` **covers the arrow as well as the text**,
so sizing the arrow from it is circular; both panels stayed at ten pixels while
the axis grew fourfold. The target's position is set rather than measured.

Carbon dioxide's benchmark line runs high in its panel, so the legend clearance
is what separates them, and it is the binding constraint there rather than the
annotation. Matching methane's much larger gap exactly would compress the carbon
dioxide comparison into half its panel, so the clearance is set to sixty pixels
rather than to whatever methane happens to have.

**The panels are stacked rather than side by side, and the legend forced it.**
Naming the benchmarks by what they do rather than by their jargon makes the
longest label thirty-eight characters, and a half-width panel cannot hold that
legend without putting it over the data. Stacking gives each panel the full canvas
width. Both groups appear on both panels, in one two-column legend with bold
headings, so either panel can be read alone.

**Hue is rescoped, and the comment in `plotstyle` was amended in the same commit.**
Hue carried support status because that was the distinction the reconstruction
figures are about. This panel has no such distinction, so hue marks the benchmark
against fitted contrast instead. The alternative, an entirely achromatic panel,
was rejected because it carries two filled regions and a gray envelope beside a
gray inferential band would be the one genuine confusion on it.

| candidate | pure hue, worst separation under deficiency | against |
|---|---|---|
| **Bluish green `#009E73`** | **20.9** | `INSIDE`, deuteranopia |
| Sky blue `#56B4E9` | 25.0 | `INSIDE`, deuteranopia |
| Orange `#E69F00` | 14.9 | `OUTSIDE`, tritanopia |
| Reddish purple `#CC79A7` | **0.9** | `OUTSIDE`, tritanopia |

Two colors become distinguishable at about 2.3. **Reddish purple would be
invisible against the support orange for a tritanope**, which is the same failure
as the tab10 orange against green in Irvin et al. (2021) figure 9, measured here
at 5.6 under protanopia. The band edges and the legend patch are drawn in the
pure hue, so that collision would be on the page rather than hypothetical.

**Sky blue was used first and was replaced.** It measured well against the greys
in the abstract, but blue at `INSIDE` already means inside or retained across the
water table figure, the site map and the reconstruction, and a second blue meaning
something unrelated is the collision these rules exist to prevent. Re-measured
against what is actually on these two panels rather than against a generic
palette, it also failed in grayscale where it had not been checked: its fill sat
**0.014 in relative luminance from the grid and 0.006 from the window edge**, all
but invisible without color. Bluish green clears every gray on the panel by 12.1
and by 0.197 in luminance, at a heavier fill weight of 0.55 chosen for that
reason.

The two filled regions also had to separate without hue. A test asserts the gap
and its direction on the forecast figure, and on the flux figure the observed
uncertainty band was lightened from 0.28 to 0.16 so the black series reads through
it on carbon dioxide: the two fills then separate by **0.215 in relative luminance
and 12.7 under the worst deficiency**, and their overlap is distinct from each of
them. The band's width was not touched, since carbon dioxide is genuinely measured
less precisely relative to its range.

### The measurements-used figure, and the heatmap it replaced

`figures/measurements_used_across_forecast_horizons.png`, built by
`study.figures.measurements_used`. The file was first named `predictor_usage`,
which used on disk the vocabulary that had just been taken off the panel; the
name now says what the figure shows.

**The first version was a heatmap and it was wrong.** Six rows against four
horizons in two blocks of shaded cells, every cell printing its value. It failed
on four counts. It asked a reader to decode a shading scale to find a pattern
that is an ordering. Its row labels carried the calendar share inside them, which
compressed them to the point of unreadability. Its struck cells, where the
one-month flux lag does not exist, read as missing data rather than as a
predictor that was never offered. And its single annotation pointed at one of
those compressed labels. The form was replaced, not restyled.

**Ranked horizontal bars in small multiples.** One panel per horizon, four
horizons across, the two gases as the two rows of panels. Rows sit in the same
order on every panel, so the eye compares along a row across horizons and down a
column between gases. Length carries the share, and the ordering carries the
finding without needing to be read off a scale.

**The title names the site, as the other five figures do.** An earlier title
described the figure's two halves in a comma construction and named no place; the
horizon is now parenthetical and the site is in the title proper.

**The subtitle defines a forecast horizon.** This may be the first figure of the
set a reader meets, and every panel is a horizon. An earlier six-sentence version
carried two definitions and the finding, and spent a sentence explaining that
July is warm and January cold — which the grey bars and the column heading
already carry between them. Cut to four sentences: what a horizon is, what the
green bars are, what the grey bars are, and what reading the two together shows.

**Rows are ordered by mean use across both gases and all four horizons.** The
resulting order is the flux a month before, the flux a year before, soil
temperature, air temperature, precipitation, water table. The description states
the sort basis, because a sorted figure that does not say what it sorted on
invites the reader to assume the wrong quantity.

**Two kinds of empty cell, drawn differently.** A blank meant two things at once
in the first build. On the date column the two flux rows are empty because the
question does not apply: the flux's own past is not a measurement taken at the
site. On the horizon columns the one-month row is empty at three, six and twelve
months because a model forecasting that far ahead cannot have last month's flux.
The first is marked *does not apply* and the second *not available*, both in the
cell. Left blank they read alike, and both read as data that went missing. **The
description explains them in its second, third and fourth sentences, before any
finding**: a reader meeting a marked cell should not have to reach the end of the
block to learn what it means. The two are given a sentence each rather than one
clause, since they are two different situations.

**Each column group names its unit twice: once above and once under the ticks.**
"Predictable from the date (% of variation)" over the leading column and "Chosen
by the models (% of rebuilds)" over the four horizons, each broken before its
parenthetical so the pair reads in the same register, with "% of variation" and
"% of rebuilds" under the bottom row of panels. The heading sits a full figure
height above the numbers it belongs to, so a reader at the tick marks would
otherwise have to travel back up to learn what they are. An earlier build used
"Percent" for both and a build before that had no axis name at all; the unit is
now the group's own words in both places. Per group rather than per column, since
the unit is a property of the question rather than of a horizon, and five copies
would repeat two facts. Ticks read 0, 50, 100 on the bottom row of panels only.

**No units beside the row labels.** They would name what the bars are not. The
bars carry two percentages, and precipitation in millimeters or temperature in
degrees appears nowhere on this panel, so "(mm)" beside a row would read as the
quantity the bar measures. A test pins their absence.

**"Chosen" rather than "kept" or "retained".** The literal description is that a
selection step retained a candidate. Two things decided against it. "Kept"
presupposes a pool the reader has not been shown, and naming that pool is the
screening vocabulary returning by another route, where "chosen" needs no
antecedent. And the subtitle says "chose" three times; a heading that said "kept"
would describe the same act with a second verb and read as a second operation.
The anthropomorphism is real and is the price paid.

**The gases are named in the same bordered box as the other figures**, seated
above each panel rather than in its corner: the corner holds the first row, which
here is a marked cell rather than the empty space the box needs. `panel_name`
took an `x` override for this rather than the box being redrawn a second way.

**The description was cut to four lines, and three parts moved to the writeup.**
It reached eight lines, longer than any other figure in the set, and needed a
`description_px` override on `wrap_description` and `canvas_area` to hold it.
Cut, it fits the shared allocation, and the override has been removed from
`plotstyle` rather than left behind unused. What stays is what a reader needs
while looking at the panel: the two blank-cell meanings, which are marks on the
panel; the 95% and 5%, which are what the grey bars mean; and the carbon
dioxide three-month result, which is the panel's most visible feature. A test
asserts it fits the block every other figure has.

**Three things moved out of the description and into the writeup.** All three are
established results and none is lost; they are recorded here so the writeup picks
them up.

1. **The sort basis.** Rows are ordered by how often the models chose each
   measurement, averaged across both gases and all four horizons, and the date
   column was not sorted yet falls in the same order. That matters for verifying
   the figure and not for reading it, and it is the mechanism behind the ordering
   rather than something the ordering shows.
2. **That the water table explains almost nothing left in the flux once the
   seasonal cycle is removed.** Cut from the description because the panel does
   not display it and a description asserting it asks the reader to take a second
   analysis on trust. **It then turned out to be false**: on the corrected series
   the partial correlations are +0.245 and +0.250, and the claim is withdrawn in
   the section above rather than carried into the writeup. Cutting it from the
   panel for a presentational reason is the only thing that kept it off a figure.
3. **That the same pattern appears at other wetland sites.** Knox et al. (2021),
   recorded above with the ratio that makes this site fit. It is context for what
   the figure means in the field, which is the writeup's job.

**The calendar share is a fifth column, not a row label.** Drawn as a leading
column of bars to the left, separated by a gap: soil temperature 95%, air
temperature 95%, precipitation 40% and 38%, water table 3.8% for methane and 6.0%
for carbon dioxide. That column happens to fall in the same order as the usage column, which
is the figure's whole argument put in one glance — the measurements the models
chose are the ones the date already predicts. It is a coincidence of the usage
sort rather than its cause, and the description says so. These are the unlagged
covariates over each gas's evaluated index, so the two gas rows differ slightly;
the per-lag values in the table above are the ones to quote for a specific lag.
**The water table figures here were 0.5% on both rows until the datum step was
cut out.** The argument is unchanged, 95 against 5 saying what 95 against 0.5
said, but the number a reader takes away is ten times different.

**The date column nearly repeats between the two gas panels, and that was left
alone.** Its four values are properties of the measurements rather than of either
gas, and differ between the rows only because each gas is evaluated over a
different set of months: four bars carrying two facts. Drawing it once was
considered and rejected. A single column would have to sit in the gutter between
the two panels, aligned with neither one's rows, and the alignment is the whole
point — the reader compares the grey bar against the green bars on its own line.
The only layout that removes the repetition is a single six-row grid with the two
gases as paired bars inside each row, which collapses the four horizon panels
into one and gives up the small multiples. The repetition is cheap, achromatic,
and lets the carbon dioxide ranking be read against the date without travelling
back up the figure.

**Two hues, and the grey was measured rather than guessed.** Green `FITTED` for
usage, achromatic `DATE_SHARE` for the calendar share, because the latter is a
property of the measurement rather than a result of this study. `#A9A9A9` was
chosen over three candidates: it sits **16.7 ΔE from the green under the worst
simulated deficiency and 0.140 apart in relative luminance**, against 11.7 and
0.076 for `#767676`, and 10.3 and 0.005 for `#8C8C8C`, which would be
indistinguishable from the green in grayscale. `#BFBFBF` separates from the green
better still (23.7, 0.264) but sits only 9.4 from the gridlines, where a short
bar could merge with one. The green's relative luminance is 0.257.

**No legend.** The two column headings name the two quantities in the place a
reader is already looking, so a key repeating them would add a lookup and say
nothing new.

**No annotation.** One was planned for the water table row and held in reserve.
Built, the row reads on its own: it is last in the order, its calendar bar is the
only one at zero, and the subtitle names it. The heatmap needed the annotation
because absence reads as unremarkable in a grid of pale cells; a bar chart makes
the shortest bar the most conspicuous row on the panel.

**Two rows for the flux, ruled off from the four measurements.** "The flux a
month before" and "the flux a year before" are different claims, and it is the
annual lag that carries the carbon dioxide result. They are kept so the carbon
dioxide three-month panel is not empty — that panel is the sharpest result in the
study, and an empty panel would read as a figure that failed rather than as a
finding. A light rule separates them from the four site measurements, since the
flux's own past is not something measured at the site alongside the others.

**A rounding rule was added and then removed.** Shares below one percent were
printed to one decimal, so the water table's 0.5% would not round to "0". With
the datum step cut out the smallest share on the panel is 1.2%, the rule became
unreachable, and it went along with its test rather than sitting in the module
against a case that no longer arises.

**No internal vocabulary anywhere on the figure.** Not Boruta, not fold, not
survival, not lag, not screening, not covariate. A test asserts their absence
from the title, subtitle and description. "How often the models used it" is what
a survival share is in plain terms, and the flux rows are named in words rather
than as lags.

**No citations on the figure.** The last sentence of the description says the
same pattern has been found across other wetland sites without naming Knox et al.
(2021); the reference is in these notes and belongs in the writeup. A figure
states what its data shows.

**What was left out.** The autoregressive family, whose rows would be flux lags
only. Individual lags, collapsed to each covariate's best-surviving one. The
three seasonal terms, kept in every fit by construction and therefore a row of
ones. The partial correlations against the deseasonalized flux, which are the
quantitative backing for the description's claim that the water table correlates
with nothing left in the flux once the season is taken out — r = 0.006 for
methane at lag 1 and −0.157 for carbon dioxide at lag 12, neither significant —
and which stay in these notes. Significance marks, since the binomial threshold
is the published rule rather than a calibrated error rate and stars would imply
otherwise. A colorbar, since every bar prints its value.

### The prediction-error figure

`figures/prediction_error_by_year.png`, built by
`study.figures.prediction_error_by_year` from `study.figures.agreement_panel`,
whose columns `study.figures.agreement_errors` turns into errors.

**Why it exists.** The forecast comparison summarizes error by horizon and the
observed-and-predicted figure shows when the predictions fail. Neither shows how
much a prediction missed by against the month it missed on, which is where the
arrangement of the misses is visible.

**Three forms, and the third is the one that is kept.**

1. **Predicted against measured**, a pooled one-to-one scatter with 2015 ringed.
   The ring asserted a grouping the panel did not show: those months are
   scattered across the axis rather than clustered. Cut.
2. **Error against measured**, a pooled residual panel. The residual form was
   right and is kept: it exaggerates the vertical deviations relative to the
   scatter they came from, and a one-to-one panel puts the finding at a distance
   from a diagonal that a reader has to infer while the diagonal's own range
   compresses it. What it showed was spread without direction, and no year in it.
3. **Small multiples by year**, this one. Six years told apart by hue would
   overlap into one cloud; a panel per year separates them. Faceting was chosen
   over color for exactly that reason.

**What was given up in the move to facets.** The pooled residual build drew a
three-step band showing the average miss in each third of the months by size,
which made the widening visible rather than only stated. It is not drawn here:
the band is the same in every panel, so sixteen copies of it spend ink on
something that does not vary across the facets, which is the one thing a small
multiple is for. The widening is now a number in these notes and nowhere on the
figure. If the year figure is cut, the band goes back.

**No precedent, and this one was searched for rather than assumed.** The notes
above hold Deventer figures 8, 9 and 10 and Irvin figure 9; none is a residual
or a predicted-against-measured plot, and no paper in this study's grounding
carries one. Designed from first principles and recorded as such.

**Three findings this figure carries that no other does.**

1. The eight fitted methods **bracket the measurement in 56% of methane months
   and 16% of carbon dioxide months**. They agree closely with each other and are
   wrong together: the non-separation result arriving from a third direction,
   after the shared-months correction and the Diebold-Mariano margins.
2. They **miss in the same direction as the seasonal average in 81% and 87% of
   months**, at error correlations of 0.79 and 0.90. They fail on the same
   months, which is stronger than either failing alone and is why the seasonal
   average is drawn beside them rather than left to the forecast figure.
3. The errors **widen with the size of the month**. Pooled over all eight
   methods, mean absolute error runs **3.1 in methane's smallest third of months
   against 13.2 in its largest**, and **0.12 against 0.33** on carbon dioxide,
   with Spearman correlations between miss size and month size of 0.49 and 0.44
   (p = 5e-29 and 3e-33). The seasonal average's own miss widens with it, 1.4 to
   15.3 and 0.13 to 0.34. This is what the residual panel made visible and the
   one-to-one panel did not.

**What a widening residual cloud licenses, and what it does not. This was got
wrong once and the wrong version was published in the figure.** The first
residual build's description said a non-random arrangement of residuals means the
model is **under-specified** — a missing variable or an unspecified curve — and
concluded that what the methods lack is whatever sets the size of a season. That
is not what a widening cloud shows. **The under-specification diagnostic is a
pattern in the mean of the residuals**: a slope, or a curve, in where they sit.
Non-constant spread around a flat mean is a different diagnostic with a different
name and different consequences. The claim rested on a slope, and the same
description reported, three sentences later, that there is no slope: −0.08 and
+0.06, neither separable from flat. It contradicted itself and the stronger half
was the unsupported one. The wording is corrected and a test now refuses the term
anywhere in the figure's words.

**What the widening does mean, on its own terms.** The size of the miss scales
with the size of the month while its direction stays centred on zero. Regressing
log absolute error on log absolute measurement gives an exponent of **0.81 on
methane (95% CI 0.66 to 0.97) and 0.75 on carbon dioxide (0.63 to 0.87)** — close
to proportional, a little below it. Three consequences, none of which is a claim
about a missing variable:

1. **A pooled error figure describes no month.** Methane's 8.3 is an average over
   a regime running 3.1 and one running 13.2. Quoting it alone overstates the
   accuracy on big months and understates it on small ones.
2. **The methods are about equally wrong in relative terms everywhere.** Mean
   absolute error over mean measurement runs 0.25, 0.28 and 0.21 across methane's
   thirds. They are not doing disproportionately badly on the large seasons; the
   absolute misses simply follow the size of the month. This is the sentence that
   most directly kills the earlier reading — if something specific to big seasons
   were missing, the relative miss would climb, and it does not.
3. **Constant-width uncertainty would be wrong at both ends.** Anything this
   study reports as a single interval is too wide for small months and too narrow
   for large ones.

Carbon dioxide's relative miss is not quotable in the smallest third: those
months sit near zero flux, so the ratio blows up (1.56 against 0.33 and 0.26).
That is an artifact of the denominator and not a finding, and it is why the
relative-miss argument above is made on methane.

**A premise corrected three times.** Each correction cut a claim the figure could
not carry: the first cut a pooled direction claim, the second cut the tilt, the
third cut the year-level direction claim and the three-times factor with it. The
first, made before the one-to-one figure was designed: the claim
that the largest misses are over-predictions does not survive pooling, at 31 of
57 methane months and 41 of 85 carbon dioxide, and 6 of 10 and 3 of 10 among the
ten largest. The residual form forced the second. Redrawn against zero, **there
is no tilt**: the slope of error against measurement is **−0.08 on methane
(p = 0.24) and +0.06 on carbon dioxide (p = 0.27)**, both confidence intervals
straddling zero and the two signs opposite each other. So the pattern a reader is
taught to look for on a residual plot — negative residuals at small values and
positive at large — **is not present here in either gas**, and the description
says so rather than leaving its absence to be discovered. The old description's
"too much predicted in the weak months and too little in the strong" was a
reading of a handful of bars and is gone; it was also inconsistent with the same
description's slope of 1.07, which says the opposite.

**The year-level structure, measured again on the corrected panel.** Pooled over
all eight methods, methane's mean absolute error by year runs **16.5 in 2015,
5.9, 10.1, 7.7 and 4.6 in 2016 to 2019**, and 2.9 on the single scored month of
2020. So 2015 is the worst year by a clear margin, but **not by the factor this
study has been quoting**: 16.5 against the mean of 7.1 across the other years is
**2.3 times**, not three. The three-times figure compared 2015 against the *best*
other year rather than against their average, and it was computed on the
middle-of-four the pivot bug produced. Against the best year, 2019 at 4.6, it is
3.5 times. The honest statement is a range and it is quoted as 2.3 here.

**The direction half of the year claim does not survive at all.** "2015 is missed
mostly from above" is true of the eight methods pooled, at 64% of its 64
predictions. It is **not** true of the points the figure draws, which are one
median per month: **5 of 2015's 8 months fall below the line, against 9 of 2016's
12.** By that measure 2016 is the more over-predicted year. Singling 2015 out for
direction is therefore not something any form of this figure has shown, and the
description no longer says it. Carbon dioxide's yearly mean errors run −0.12 to
+0.13 and its below-the-line counts run 3 of 12 to 9 of 12 with no order to them.

**What 2015 separates on, and the reading that replaced the earlier one.** An
earlier build of this description said 2015 "separates, and it separates
sideways", quoting that its months span **36% of methane's evaluated range against
76% to 98% for the other years**. The span figures are right and are kept, but
the framing was wrong twice over. It was a rhetorical construction rather than a
statement, and more importantly **it is a fact about which months occurred, not
about prediction quality at all**: a weak season contains no large months, so of
course its points sit in one part of the axis. Read as a finding about the
methods it says nothing. It is now stated as what it is, a property of that
year's data, and the prediction claim is made separately.

**The prediction claim, controlled for the widening.** A raw yearly miss cannot
separate a year that was predicted badly from one that happened to hold large
months, because the miss grows with the size of the month. Dividing each year's
miss by what months of that size are missed by across the record does separate
them. `agreement_panel` computes it as `year_ratio`:

| gas | year | ratio |
|---|---|---|
| methane | **2015** | **1.68** |
| methane | 2017 | 1.16 |
| methane | 2018 | 0.97 |
| methane | 2020 (one month) | 0.96 |
| methane | 2016 | 0.71 |
| methane | 2019 | 0.59 |
| carbon dioxide | widest, 2020 (one month) | 1.23 |
| carbon dioxide | widest full year, 2014 | 1.18 |

2015's months sit in the **middle** third of methane's size distribution, not the
smallest: 6 of its 8 fall between 17 and 44 and 2 above 44, none below 17. Months
of that size are missed by **9.8** across the record and 2015's by **16.5**, so
it is missed **1.7 times worse than its own months' size accounts for** while no
other methane year passes 1.16. That is the claim the description makes, and it
is the one claim about 2015 that survives every correction: it is not about
direction, not about the raw yearly average, and not about where its months sit.

**2015 differs on two counts, and the description states both.** A pass of the
description credited the whole difference to which months the year contains, on
the reasoning that a weak season holds no large months. That is true and it is
half the story. Stated alone it **denies the prediction claim, which the data
supports**, and it is the exact mirror of the earlier overcorrection in the other
direction, where the figure claimed 2015 was predicted worse without controlling
for the size of its months. Both are true and independent:

1. **Which months it holds.** Its eight months run 17 to 52 where methane's
   evaluated record runs 10 to 104, so its points sit entirely in the lower half
   of the axis. A property of the year.
2. **How well they were predicted.** Controlling for size, it is missed about
   **1.7 times** as badly as months of its size are across the record. A property
   of the predictions.

**The size-controlled ratio was checked six ways before it went on the figure**,
because a ratio built on binned means can be an artifact of where the bin edges
fall or of one bad month. Methane's 2015 against every other methane year:

| control | 2015 | next highest | reproduced |
|---|---|---|---|
| 3 size bins, mean (the reported figure) | **1.68** | 1.16 (2017) | yes, and it is what `year_ratio` returns |
| 4 size bins, mean | 1.93 | 1.10 (2017) | yes, edges from the 57 months |
| 5 size bins, mean | 1.99 | 1.13 (2017) | yes, edges from the 456 method-rows |
| 3 size bins, median | 1.37 | **1.37 (2017)** | yes |
| 3 bins, each year's worst month dropped | 1.62 | 1.18 (2017) | **no**, nearest reached is 1.59 / 1.12 |
| continuous log-log fit, no bins at all | 2.08 | 1.16 (2017) | **no**, every log-log form gives 2.3 or more |

It holds under every control that reproduces. The one measure where 2015 does not
stand alone is the median, where it ties 2017 at 1.37; a median over eight months
is a coarse instrument and it is recorded rather than hidden. The description
quotes **1.7**, the lowest of the mean-based figures, and the range across the
four controls that reproduce is **1.4 to 2.0**.

**Two rows of that table cannot be reproduced, and that is a different problem
from a number that moved.** No script was ever committed for these controls, so
the only record of them is the table itself. A reimplementation recovers four
rows exactly and cannot reach the other two under any variant tried:

- **Worst month dropped, recorded 1.62 / 1.18.** Eight readings of "drop each
  year's worst month" were tried: dropping the year's largest single method-miss
  (1.59 / 1.12), aggregating each month over methods and dropping the year's
  largest (1.20 / 0.96), dropping from the numerator only (1.22 / 0.91), dropping
  from numerator and baseline together (1.42 / 1.01), taking the mean of
  per-month ratios (1.15 / 1.04), the median form (1.11 / 0.75), and dropping the
  worst month from 2015 alone (1.20 / 1.16). None gives 1.62.
- **Continuous log-log fit, recorded 2.08 / 1.16.** Every genuine log-log fit
  gives 2.31 at the lowest and 3.55 at the highest, depending on whether the fit
  is over months or method-rows and whether the year's ratio is a ratio of means,
  a mean of ratios, or a median. The recorded 2.08 is only approached by fits
  that are **not** log-log: a linear fit gives 2.14 / 1.13 and a proportional one
  2.01 / 1.15. The recorded value is outside the range of the computation its own
  label names.

**The conclusion those two rows were carrying still stands; the numbers do not.**
The point of dropping each year's worst month was that the finding is not the
single July 2015 miss carrying it, and under every one of the eight readings above
2015 is still the highest year. The margin is thinner than 1.62 against 1.18
suggests: on the most natural reading, aggregating each month over the methods and
dropping the year's largest, it is **1.20 against 0.96**. The claim survives, the
figure quoted for it does not.

**The research behind the panel labels and the key.** Wilke, *Fundamentals of
Data Visualization*, establishes that small multiples need no alphabetical panel
labels: the faceting variable identifies each panel, and an added *a, b, c* names
a panel that already has a name. This figure follows it. Each panel carries its
year in bold above it and nothing else, and the two rows carry a boxed gas name
rather than a row letter. Nothing in the figure or in either text block refers to
a panel by position.

The Caltech data-visualization handout gives the rule that settled the key: with
**three or fewer groups**, either a caption naming the marks or a legend works,
and the choice is between them rather than a licence for both. Three marks is
exactly what this figure has, and it took the legend. That is what makes the
restatement a fault rather than a redundancy worth keeping: the subtitle carried
*The grey points are the months of every other year, repeated behind every panel*
while the key's second entry read *The months of every other year*. One of the
two had to go, and the key is where a reader looks for what a mark means. The
sentence went.

**The four rows that reproduce were not computed under one rule.** The 4-bin row
comes back only with bin edges taken from the 57 monthly measurements, and the
5-bin row only with edges taken from the 456 method-rows. `year_ratio` itself
mixes the two, taking edges from the months and cutting the rows. No single basis
returns both 1.93 and 1.99, which is why a fresh reimplementation appears to
disagree with the table until each row is matched to its own basis. That is a
defect in the table, not in the finding.

**None of this is v5-5 drift, and an earlier pass of this section wrongly said it
was.** The forecast files did grow at the switch, from 1284 to 1860 rows on
methane's autoregressive family, but the exogenous family still ends at 2020-12,
so `shared_targets` intersects to the same 456 rows over 2015-03 to 2020-01 that
it did before. Reading the pre-switch files out of the commit that added this
table and running the controls on both gives **identical values to three decimals
on every row**. The switch did not reach this figure at all.

**The baseline includes the year it is measuring, which understates the ratio.**
`year_ratio` divides a year's mean absolute error by what months of its size are
missed by **across the whole record**, 2015 included. Since 2015's own large
misses inflate the bin means it is compared against, the comparison is
conservative. Leaving each year out of its own baseline gives methane
**2015: 2.23**, 2016: 0.66, 2017: 1.22, 2018: 0.98, 2019: 0.54. A reimplementation
gets 2.28, 0.66, 1.14, 1.02, 0.53, which is the same result reached a slightly
different way rather than a match; like the two rows above it, the exact form was
never committed. The figure quotes **1.7**, the conservative form, and the
description says *months of the same size across the record* rather than
*elsewhere in the record* for that reason: the second phrasing would describe the
leave-one-out baseline and would go with 2.2, not 1.7. Both are recorded; the
smaller claim is the one drawn.

**Carbon dioxide has nothing of the kind.** Its widest ratio on a full year is
1.18 in 2014, and 2015 sits at 1.07. No carbon dioxide year separates on either
count, which is why the description names only methane.

**The deepest single error on the panel is 2015's**, 49 too much predicted where
40 was measured, in July 2015. Kept in these notes; it is one point and the
description no longer spends a clause on it.

**Regressing the four full methane years' mean error on their amplitude gives
p = 0.33 on four points**, which is not a result and is not quoted anywhere on
the figure.

**The balance, and the two things it needed that no earlier figure did.** This
figure had the worst split in the set, **85 px of air under the subtitle against
163 px over the description**. `balance_drawing_block` closed it to **35.6 px at
both ends**, the panel block growing from 782 to 860 px. Getting there took two
additions to the helper, both of which are about the same thing: this is the first
figure whose drawing block is not made only of axes.

- **`extra`,** artists measured as the block's edges though they are not axes.
  The top of this block is a boxed gas label, which stands above the year labels
  rather than on a panel, and the bottom of it is the key wherever the key falls
  back to a band under the rows. A balance measuring the panels alone drives the
  first into the subtitle and lets the panels walk through the second.
- **`reflow`,** a callback run after every resize. Moving an axes does not move a
  figure text placed against it, and this figure has six such texts and a key.
  Left behind they slide out from under the block, which is the fault the
  seasonal figure hit and fixed by converting one text to an axis label. That
  will not work here, so instead every piece of furniture is built by one
  function and the balancer calls it. The measurement is stale without this: the
  next round measures against where the label used to be.

Both default to doing nothing, so the other nine callers are unchanged.

**The gap under the block was reported as 35.6 px and was 1.5 px.** The row axis
names are figure text, so they were outside the balance entirely: it equalised to
the carbon dioxide **tick labels** and left the axis name hanging 34 px below
them, which put it 1.5 px clear of the description. The figure looked balanced in
the numbers and was nearly touching on the canvas. This is the same class as the
gas label at the other end, and it is why `extra` exists; the axis names simply
were not put in it. Both ends of this block are furniture rather than panels, and
neither was measured until it was looked for.

**Three things had to be settled before the axis names could be enlarged**, since
enlarging ink that was never measured drives it straight through the description.
They are separate decisions and are recorded separately.

1. **The axis names are measured.** They are now the block's floor, which is what
   the description is set against.
2. **`edges`,** a third parameter on the balancer: the two references to
   equalise, given as a callable rather than taken from the ink. The default is
   still the ink and the other nine callers are unchanged. It exists because *what
   should look symmetric* and *what must not collide* are different questions on
   this figure, and answering them with one measurement answers neither. The
   balance runs against named references; the clearance check that follows still
   runs against every piece of ink.
3. **The references are the nearest ink at each end**, which is the balancer's
   default: the boxed gas name above the top row, and the carbon dioxide axis
   name below the bottom one. Both gaps come to **35.56 px**, equal to 0.000.

**The pairing that was tried first, and why it was dropped.** Balancing the
methane panel's **top border** against the carbon dioxide axis name was built and
rendered. It equalises at 111.1 px and is wrong, because the two references are
not comparable: the top gap **contains the gas label**, 75.5 px of its 111.1,
leaving 35.6 px of air, while the bottom gap is 111.1 px of nothing. The figure
measured symmetric and read bottom-heavy, with a band of white under the last row
about three times the air under the subtitle. It also cost panel height, **232.9
px against 260.1**, because the block has to shrink to find the top gap room the
gas label does not leave it.

Ink to ink is right here for a reason worth keeping: **both ends of this block are
furniture rather than panel.** A boxed gas name stands above the top row and the
row's axis name hangs below the bottom one, each an object in the margin at its
own end. Treating the two alike is what makes the white space alike. The panel
border is not the edge of anything a reader sees at the top, because the gas label
is drawn above it.

Against the 273.8 px the panels had before any of this, the cost of measuring the
axis names at all is **13.7 px**. That is the price of the 1.5 px gap being real.

**The axis names are 10.5 pt, up from 9.0.** At 9.0 they were the same size as the
bold year label over every panel, and two bold labels at one size in one figure
compete: a reader has nothing but position to tell a panel's name from the row's
quantity. The ladder is now **7.5 tick labels, 9.0 year labels, 10.5 axis names,
11.1 gas names**, which steps at every level and keeps the boxed gas names largest
because they name the row. 10.5 rather than 11.0 for that reason; at 11.0 the
competition moves to the gas names instead of being removed.

**The key's left margin is measured, not written down.** It sits on the
**description's first word at x = 108.0**, exact to 0.00 px. It was set on the
carbon dioxide axis name at x = 139.2 instead, which lined it up with the nearest
thing rather than with the page. Centering the key on that name was tried first
and is not available at all: the key is **577 px wide against a 25 px axis name**,
and a shared center line carries its left edge to **x = −136**, off the canvas.
The edge is read off the drawn text each time the furniture is placed rather than
stored as an offset, because both the grid and the key's own width have moved
during this figure's life and an offset records the answer to a question rather
than the question.

**What the key's size costs, and what the move bought back.** At 8.2 pt with
`labelspacing` and `borderpad` at 1.0 it is 577 × 157 px, against 525 × 106
before. Aligned to the axis name its right edge landed at 716.2 with the methane
row's own axis name beginning at 726.3, a clearance of **10.1 px**, the tightest
horizontal gap on the figure and the binding constraint on the key. Moving it to
the description's margin took it 31.2 px left, and the clearance is now **39.5
px**. The two changes were asked for separately and the second is what makes the
first safe.

**`borderaxespad` had to be taken to zero.** With `loc="center left"` matplotlib
insets the box from its anchor by half a font size, 8.6 px here, which put the key
almost but not quite on the axis name's edge. Almost-aligned reads as a mistake
where unaligned reads as a margin.

**The gas labels stand 64 px above their panels**, up from 56. At 56 the frame's
lower edge sat on the year labels and the two read as one stack rather than as a
name over a row of years.

**Why the 2020 column holds one month, checked rather than assumed.** Both 2020
panels show a single point and it is correct. The panel takes only the months
**every family scored**, and the three families reach very different distances:

| gas | benchmarks | autoregressive | exogenous |
|---|---|---|---|
| methane | to 2021-12 | to 2021-12 | **to 2020-01** |
| carbon dioxide | to 2024-12 | to 2024-12 | **to 2020-01** |

The exogenous family stops at **2020-01** on both gases because the drivers it
needs stop before it: `atm_temp_f` and `precip_in` in
`data/processed/monthly_bog_lake_fen.csv` run 2009-04 to **2019-12**. At a
one-month horizon the last target reachable from a 2019-12 origin is 2020-01, so
that is the last month the driver-using models can score and therefore the last
month every family shares. The shared set runs 2015-03 to 2020-01 on methane and
2013-01 to 2020-01 on carbon dioxide, giving **{2015: 8, 2016: 12, 2017: 12,
2018: 12, 2019: 12, 2020: 1}** and **{2013: 12 ... 2019: 12, 2020: 1}**. Not a
defect. It does mean a full grid column carries two months out of 142, and
dropping or folding 2020 is available if the column is judged not to earn its
width; it is kept because a thin panel is a true statement about where the record
ends.

**January 2020 was scorable and is omitted, with the reason.** It is the last
month all three families could reach. The benchmarks and the autoregressive
family run to 2021-12 on methane and 2024-12 on carbon dioxide, but the exogenous
family needs air temperature and precipitation, and both stop at **2019-12** in
`data/processed/monthly_bog_lake_fen.csv`. At a one-month horizon the last target
reachable from a 2019-12 origin is 2020-01, so that is the last month the
driver-using models can score and the last the three families share. It is a real
scored month and it was dropped anyway: **one month out of 142 on each row would
have occupied a full grid column for a single point.**

**What dropping it bought.** The grid went from eight columns to seven and the
panels from **243.6 px wide to 280.3 px**, a gain of 36.7 px or **15%** on every
one of the twelve, at no cost in height. The rule is a constant rather than a
hardcoded year: `YEAR_MIN_MONTHS = 3`, so a year needs a quarter of itself before
it earns a column.

**It is dropped from the background as well, and the title follows the columns.**
An earlier pass kept January 2020 in the grey behind every panel and titled the
figure *(2013 to 2020)* on the set's convention that the parenthesis gives the
span of the record drawn. That was defensible but it named a year no column
carried, and a reader counting columns would have looked for a panel that is not
there. The month is now out of the figure entirely, foreground and background,
and the title reads **(2013 to 2019)**, which is the span of everything drawn.
The scored set behind the figure is unchanged: `agreement_panel` still returns 57
methane months and 85 carbon dioxide months, and every pooled figure in these
notes is computed over those.

**The description was cut from six lines to two.** Under twelve small panels,
six lines of text put the words over more of the canvas than the data, which
fails the whitespace test from the other side. What went is everything precise
that **cannot be checked against a panel**: the pooled error measures, the 1.7
ratio, the 16.5 against 9.8 comparison, the bracketing and same-side shares, and
the January 2020 explanation. All of it is in these notes.

**And then rewritten, because two lines can still say nothing.** The first cut
read *"The panels look alike: the methods fail in much the same way in every
year"*, which states that the panels resemble each other without saying what the
resemblance means. What it means is that **nothing about a particular year makes
the methods better or worse at predicting it**, and that is the finding. The
description now says it: they miss by similar amounts and in similar directions
regardless of which year they are predicting.

**The gap under the last row was half again the gap over the first.** Measured on
the built canvas, the subtitle-to-first-row gap was 43.6 px and the last-row-to-
description gap 88.5 px. The excess is `XAXIS_BLOCK_PX`, the 74 px `canvas_area`
reserves under the drawing area for tick labels and an axis name. This figure
does not use it: each row carries its own axis name inside its own band. Taking
**45 px** of it back levels the two gaps at 43.6 and 43.5, and the canvas came
down from 1230 to **1185 px** by the same amount, so the panels kept their height
at 280.3 by 229.8 px.

**The description block is a fixed allocation, so cutting the text leaves the
space empty rather than giving it to the panels.** `DESCRIPTION_BLOCK_PX` is 156
across the set so that figures keep the same proportions whatever they say, and a
two-line description uses about 58 of it. The remaining 98 px reads as bottom
margin. Sizing the block to its contents would recover it and would break the
proportions rule this set holds everywhere else, so it was not done.

**Ecological context, added here and missing everywhere else in the set.** No
figure in this set said **why carbon dioxide runs negative and methane runs
positive**. A reader meets one axis below zero and one above with nothing to tell
them that is the ecosystem doing two different things rather than a plotting
convention. The subtitle now says it: carbon dioxide runs negative because the
peatland takes up more carbon than it releases, and methane runs positive because
peatlands emit it.

**The same context is missing from two other figures and was not added to them.**
`figures/seasonal_cycle.png` draws both gases' cycles with carbon dioxide's
inverted against methane's and never says why. `figures/observed_and_predicted.png`
does the same on a time axis. Either they each carry the clause, or the README
carries it once above the figure set and the individual figures rely on it. The
second is probably right, since it is a fact about the site rather than about any
one figure. **Not changed now**; recorded so it is not lost.

**Prediction error is defined on the figure rather than assumed.** The title
names it and nothing said what it was, which left a reader meeting an axis called
"Error" to work out what it was the error of. The subtitle now defines it before
giving the sign convention: how far a prediction fell from what was measured,
taken as the measurement minus the prediction.

**One horizon, at one month**, matching the observed-and-predicted figure for the
same reason: it is the horizon most favorable to the fitted methods, so falling
short of the seasonal average there says more than doing so a year out.

**A key, added after the first build.** That build had none: a reader met green
bars and black dashes with nothing on the panel to read them by, and had to go to
the subtitle to learn what they were. A figure that must be read before it can be
looked at has failed. **The zero line had been left out of it** for two builds,
which was the worst of the omissions: it is the reference every panel is read
against, and the subtitle explaining the sign convention is not the same thing as
naming the line.

**The key is held right of and below the middle of its region.** Centered
exactly, it sat at the same height as the row's rotated axis name, which is also
centered on the row, and two blocks at one height read as a single band however
far apart they are. Dropping the key below that line is what separates them;
moving it right of center keeps it in the empty columns rather than against the
canvas edge.

**The key moved into the gap the methane row leaves.** It sat in a band under
both rows, which cost 96 px of height for a block of three entries. Methane has
no forecasts before 2015, so the two columns at the left of its row are blank
anyway, and the key standing in them costs nothing. That height went to the
panels, and the canvas came down from 1350 to 1230 px at the same time. The key
also now sits where a reader meets it before the panels rather than past them.
Two things had to be got right: it stops 84 px short of the methane row's rotated
axis name, which stands in the gutter beside the first panel and was otherwise
drawn straight through the frame, and its font is two points below the set's
legend size, since it has two grid columns to fit in rather than the whole canvas.

**The key does not depend on that gap existing.** Methane happening to start two
years after carbon dioxide is what leaves the columns free, and a figure whose key
existed only because of an accident of the record would lose it the moment the
record changed. The layout decides where the key goes **before** it computes the
row height: if some row leaves `YEAR_KEY_COLUMNS` columns empty at its left the
key takes them, and otherwise a band under the rows is reserved and the rows are
made shorter to pay for it. A test covers both paths.

**The heading is a label and it is centered.** It reads `What each mark shows`.
It was "What each mark is" for a build, a sentence fragment doing a label's job,
then `Marks`, a placeholder rather than a label, then "What each point shows",
which is plain but not exact: one of the three entries is a line rather than a
point. The current wording is both. Centering needed a change to `_underline_legend_headings`:
matplotlib left-aligns every legend label including a heading, which puts the
heading off to one side of the column it heads and makes it read as another
entry. The helper now recovers the columns from the drawn artists, since
matplotlib does not expose which entry went into which column, and moves each
heading to the middle of its own before ruling it.

**One column, after a build with two.** The key was split between `Points` and
`Reference`, which put the zero line on its own away from the two kinds of point.
That division is one a reader cannot see on the panel and does not need: all
three are simply what is drawn. Three entries under one heading is shorter to
read than two lists with a rule to work out between them. The zero line's gloss
is parenthesized rather than set off by a comma, since the comma made the entry
read as two things named rather than one thing and what it means.

**Both rows carry year labels, and the columns really do align.** For one build
only the top row was labeled. The rows are drawn on one eight-column grid indexed
by year, so 2015 sits at the same x in both, but with the lower row unlabeled a
reader has nothing to check that against and will reasonably assume the rows are
offset, since methane's first panel is 2015 and carbon dioxide's is 2013. Every
panel in both rows is labeled now and a test asserts the alignment holds.

**Nothing is drawn in methane's 2013 and 2014 columns.** An earlier build put a
"no forecasts before 2015" note in them. It stood where every other column
carries a year label, so it read as a third kind of mark rather than as an
absence. The columns are empty and the fact moved to the description, where it is
a statement about the record: methane has no forecasts before 2015, when its
record first reached the sixty months a forecast needs.

**The gas names are framed, as they are across the set.** They were plain rotated
text in the gutter for one build, which matched nothing else and did not read as
a row heading. Each row now carries the bordered bold label the gas panels take
elsewhere, centered over that row's own panels. The rotated axis name stays in
the gutter and is now one line rather than two, since it no longer has to carry
the gas name as well.

**The background points were too heavy.** At `#D3D3D3` and 3.0 pt against a
foreground at 4.6 pt they competed with the year they exist to give context for,
which is most visible on the carbon dioxide row where 12 foreground months sit
among 73 background ones. They are `#DEDEDE` at 2.6 pt now and the foreground is
5.0 pt.

**Panel size: eight columns kept, height raised instead.** The panels were 244 px
wide and **191 px tall**, and the complaint that they were narrow was really that
they were short: these are residual panels and vertical position is what is read
off them. Fewer columns buys width, not height. Measured, at this canvas width:

| layout | panel width | canvas height for square panels | panel area |
|---|---|---|---|
| **8 columns, 2 rows** | 244 px | 1296 px | 59k px² |
| 4 columns, 4 rows | 500 px | 3153 px | 250k px² |
| 3 columns, 6 rows | 671 px | 5524 px | 451k px² |

Four columns would give **4.2 times the panel area** but needs a canvas **2.4
times taller** than the one in use, well past the 1900 px of the tallest figure
in this set, and it would split each gas into its own grid so the two could no
longer be compared column by column. Raising the canvas from 1250 to 1350 px
instead brings the panels to **244 by 241 px**, square, for an 8% increase in
height. If the points are still judged too crowded, four columns is the next
move and the cost is recorded here.

**No method is identifiable, and at this size no method is drawn.** The pooled
builds drew each month as a vertical bar spanning all eight fitted errors; the
median spread is 0.37 of the observed standard deviation on methane and 0.22 on
carbon dioxide, so the bars were short, which was itself the finding. Here each
month is **one point at the middle of the eight**. Two reasons, and the first is
decisive: the background-context device repeats every other year behind each
panel, so a panel carries about 140 background months, and drawn as segments that
is a grey wash the foreground year cannot be picked out of. Second, at a 263 px
panel against the 642 px of the pooled build, segments shrink by a factor of
0.41: the median falls from 28.6 px to about 11.7 px and the shortest from 5.2 px
to about 2.1 px, below the 2.9 px the line is drawn wide, so the shortest few
would stop encoding their own length. What the segments carried is a pooled
statement about method agreement, and the description makes it in numbers.

**The seasonal average is not drawn here either.** It was one of the two marks on
the pooled panel and it earned its place there. At this size a third mark type
doubles the foreground ink in exactly the place the year signal has to be legible,
and the comparison it carries — the eight fall the same side of zero as the
seasonal average in 81% and 87% of months — is pooled rather than year-level, so
repeating it in sixteen panels shows nothing that varies across them. It is a
number in the description.

**A bug in what the bar spanned, found by asking why some dashes looked
unaccompanied.** `agreement_panel` built the range with
`pivot_table(index="target", columns="method", values="forecast")`. Both fitted
families run **the same four method names**, so the pivot's default `aggfunc` of
`mean` silently averaged each method's autoregressive and exogenous prediction
and left a range over **four numbers where the figure said eight**. Nothing
errored and nothing looked wrong; the bar was simply shorter than it should have
been. What it cost:

| | drawn before | correct |
|---|---|---|
| median bar, methane | 5.58 | **9.06** (×1.57) |
| median bar, carbon dioxide | 0.082 | **0.118** (×1.22) |
| brackets the measurement, methane | 30% | **56%** |
| brackets the measurement, carbon dioxide | 11% | **16%** |
| same side as the seasonal average, methane | 75% | **81%** |
| median bar / observed sd, methane | 0.23 | **0.37** |

The fix pivots on `["family", "method"]`. The pooled error measures were never
affected — they are taken from the raw scored rows, so 8.3, 13.3, 0.21 and 0.28
stand, as do the tercile misses. **The bracketing share published in the earlier
figure was wrong by roughly a factor of two on methane** and every place it
appeared has been corrected. A test now asserts the range reaches the extremes of
all eight predictions, and a second asserts that the collapsing pivot would
shrink both the bar and the bracketing share, so the mistake cannot return
quietly. The two other pivots on `method` in the codebase were checked and are
both safe: `evaluation.per_origin` pivots inside one family, and
`model_examinations.errors_at` pivots per family and prefixes the columns.

**Why the black dashes looked unaccompanied, which is what started the check.**
Neither of the two explanations offered was right. No segment is too short to
draw — the shortest renders at 5.2 px against a 2.9 px line width, and none is
sub-pixel — and no month carries a seasonal average without eight fitted
predictions behind it. The dash sits at **the same horizontal position as its
bar** but often far from it vertically: 34 of 57 methane dashes and 57 of 85
carbon dioxide dashes fall outside their bar's span, 16 and 36 of them by more
than 10 px, up to 100 px. The dash is also drawn **five times wider** than the bar
(7 pt against 1.4 pt, 14.6 px against 2.9 px), so a separated dash reads as a
standalone mark with nothing beside it. It is a consequence of the finding rather
than a defect: the seasonal average and the fitted methods disagree, which is why
both are drawn.

**No year is set apart, and the mark that did it is gone.** An earlier build gave
every month of 2015 an open ring and a heavier bar. Checked against the panel,
those months sit at measured values from 12 to 52 rather than clustered, so the
ring grouped points the panel shows as ungrouped. On the residual panel the
year-level structure would have to arrive as a slope to be readable, and it does
not arrive at all — see the tilt above. Nothing was added back in its place.

**No numbers on the panel at all.** The one-to-one build carried two lines in each
panel, the pooled mean absolute error and root mean square error, on the argument
that a magnitude is worth having in front of the marks. The residual form retires
that argument: the vertical axis **is** the error, in the gas's own units, so a
magnitude is now read off a position and a corner block would restate the axis a
reader is already looking at. Both lines moved to the description. The zero
returned is deliberate — the question asked was whether one number should come
back, and on this form none should.

**What the numbers cost to move.** The description block holds five lines and it
is full. The sentence explaining why both error measures are quoted — the root
mean square weights large misses more heavily, so the gap between 8.3 and 13.3
(ratio 1.60) and between 0.21 and 0.28 (1.32) says a few big errors carry the
total — did not fit alongside the widening, the absent tilt, the two shares and
the magnitudes themselves. It was cut rather than the panel being given a
number back. The ratios are recorded here, and the widening sentence now carries
the same point in a form a reader can act on: the big errors are the big months.

**No coefficient of determination.** It inflates on a strongly seasonal series:
predicting the seasonal mean alone would score well while adding nothing, which
is the exact confusion this study exists to avoid.

**The tilt is a clause in the description, not a number on the panel.** At −0.08
and +0.06 it is a statement about shape that no error measure makes, and it is
reported because it is **absent**: a reader who has been told the errors are
patterned will look for a slope first, since that is the pattern the diagnostic
is usually taught with. On the panel it would have read as a score.

**The widening was drawn on the pooled build and is not drawn here.** That build
carried three flat levels per panel, each the average miss inside one third of the
months by size, mirrored above and below zero and stepped across the axis, drawn
from the same numbers the description quoted: 3.1, 8.7, 13.2 on methane and 0.12,
0.18, 0.33 on carbon dioxide. A step and not a fitted envelope, because a smooth
curve would assert a functional form for how the miss grows with the month and
the log-log exponent's confidence interval runs 0.66 to 0.97 on methane, wide
enough to admit several. It is recorded here in full because it is the one device
this figure has lost to the facets, and because it is what should return if the
year figure is cut.

**The zero line is named rather than called a target.** It replaces the diagonal
and inherits its style, light and dashed, for the same reason: the seasonal
average does not sit on it either, and a figure that framed it as the thing to
hit would be asserting what this study denies.

**The sign convention is stated in both directions.** Error is the measurement
minus the prediction, so above the line the prediction was too low and below it
too high, and the subtitle says both halves. One half stated leaves the other to
be inferred, and that inference is the thing a reader gets wrong. The axis name
carried it too on the pooled build, as "Error, measured − predicted"; at this
panel size the name has to sit beside a 263 px panel, so it is now "Error" and
the subtitle does the work alone. A test checks the drawn values against the
panel they come from rather than trusting the labels: drawn the other way round,
every reading inverts.

**Two rows aligned by year, not two blocks.** Methane has six evaluated years and
carbon dioxide eight, so the grid is eight columns wide and methane's first two
cells are empty. The alternative, a block per gas each starting at its own first
year, would have avoided the empty cells but would have made the two rows'
columns mean different years and their panels different widths. Aligning by year
buys a reader the vertical comparison — was 2016 a bad year for both gases — and
the empty cells state a true fact about the record, which one note across them
gives in words: methane has no forecasts before 2015, when its record first
reached the sixty months a forecast needs. Nothing is drawn in those cells, since
a panel with axes and grey context but no year in it reads as a year that was
forecast and missed everywhere.

**Shared axes within a row and not across rows.** The two gases are in different
units, so one scale through all sixteen panels is not available. Within a row
every panel shares both axes, which is what makes the columns comparable and is
the whole point of the form; a test holds it. The vertical axis is centered on
zero in every row, so the line meaning no error sits at the middle.

**Two labeled ticks per panel was not enough to place a point against.** A
three-bin locator left methane showing only 40 and 80 and carbon dioxide only
-1.5 and 0.0, so a reader had nothing between them but the panel edges. Raised to
seven bins with the step set constrained to 1, 2, 5 and 10, which is what keeps
the values round: left to itself the locator offered carbon dioxide -2.4, -1.6
and -0.8. Methane now carries 0, 20, 40, 60, 80, 100 and carbon dioxide -2.5
through 0.0 in halves. Measured on the built panel, the tightest gap between
adjacent carbon dioxide labels is **7.9 px** and methane's is 25.3 px, so the
carbon dioxide row is close but clear.

**Methane's axis is carried to zero.** Its flux never crosses zero, so the axis
would otherwise begin at whatever its smallest evaluated month happens to be,
which is 9.7 and is nothing in particular. Carrying it to zero costs about 2% of
the row's width and is what puts a labeled tick at 0 rather than one at 25 or 30
inside the data. Carbon dioxide already crosses zero and is left alone; the rule
is written as *extend to zero when the flux does not cross it* rather than as a
special case for one gas.

**One axis name per row rather than one per panel.** Eight copies of
"Measured (nmol m⁻² s⁻¹)" would say eight times over what the shared scale
already says once. Tick labels are kept on every panel, at three across and four
up, because a panel a reader is looking at should be readable without counting
columns back to the left edge. The row name and the axis name are set together at
the left of each row, against that row's own first panel rather than the grid's
left edge, which is two empty columns away on the methane row.

### Which variable goes on which axis, and the dispute about it

Measured on the x-axis, error on the y. Measured stayed on the horizontal through
the redraw, and the disagreement it belongs to is about the vertical it used to
carry. Piñeiro, G., Perelman, S., Guerschman, J. P. and Paruelo, J. M. (2008),
*How to evaluate models: observed vs. predicted or predicted vs. observed?*,
**Ecological Modelling** 216, 316-322, argue that regressing observed on predicted
is the correct arrangement and that the reverse produces erroneous slope and
intercept estimates. A 2019 rebuttal in the same journal argues their result is an
artifact of how their simulation was set up and defends observations on the
horizontal axis.

**The dispute concerns slope and intercept estimated from a fitted regression,
and no regression line is drawn here.** The one slope this study quotes, the tilt
at −0.08 and +0.06, is reported in the description as a shape diagnostic and is
computed once, not read off the panel. So the disagreement does not bite on this
figure. The choice was made knowingly and both sides are named, so a reader who
holds the other position can see that it was considered rather than missed.

**Plotting residuals against the observation rather than against the fitted value
is the arrangement the diagnostic is described in**, and it is what makes the
widening readable here: the horizontal axis is the size of the month, which is the
variable the errors are being asked to be independent of. Against the fitted value
the same cloud would answer a question about the model's own output instead.

### Three things from the grounding literature that bear on this figure

**Irvin et al. (2021) report gap-filled methane fluxes reaching a mean
coefficient of determination of 0.68 and a mean root mean square error of
6 nmol m⁻² s⁻¹ across sites.** That is the closest published performance figure
in this study's grounding, and it is **not directly comparable**: it is
half-hourly gap-filling inside a record, where the model interpolates between
observed neighbours, against monthly forecasting beyond the origin here. The
numbers are recorded so nobody reads this study's 8.3 against their 6 as a like
comparison.

**They also found decision tree algorithms performing best in cross-validation.**
That is the same family as the gradient boosting and random forest which, here,
do not separate from a seasonal average. The contrast is the point: filling a gap
inside a record is a different problem from forecasting past its end, and a method
family that wins the first need not win the second.

**Knox et al. (2021) found soil and air temperature the strongest predictors of
annual flux across wetland sites globally, with water table correlating only where
sites were not consistently inundated.** That is this study's screening result at
network scale, and it is recorded here as well as in the screening section because
this figure is where the fitted methods' failure is most visible.

### The residual distribution check figure

`figures/residual_distribution_check.png`, built by
`study.figures.residual_distribution_check` from
`study.residuals.quantile_comparison`, `study.residuals.local_level` and
`study.residuals.distribution_comparison`.

**Why it exists.** The estimator is least absolute deviations, which is maximum
likelihood under Laplace error, and it was chosen because Deventer et al. (2019)
established that flux errors at this site are Laplace. **Nothing had tested
whether the model's own residuals follow that distribution.** The published
result concerns paired differences between two analyzers; the estimator
assumption concerns model error. Those are different quantities and this study
has conflated them before.

**No precedent for the form, and the notes said otherwise.** This figure was
briefed as following Deventer's own, and it does not. Deventer figure 4 is a
histogram with a fitted Laplace density (panel a) and a cumulative comparison
against a normal (panel b). Neither is a quantile plot. The only quantile plots
anywhere in these notes come from the superseded analysis, and `ingestion.md`
records that no cell in that notebook ever called `qqplot` or `probplot`. **The
comparison and the site follow Deventer; the form is from first principles.**
The histogram and cumulative views were considered as companions and cut: three
views of one assumption over four fits is twelve panels for a question the
quantile plot answers alone, and it is the form most sensitive in the tails,
which is where Laplace and Gaussian differ.

**Which residuals, and why not the others.** The reconstruction fit only. It is
the fit that minimizes absolute deviations, so it is the one the assumption
belongs to. The forecast methods minimize squared error or carry no likelihood at
all, so the assumption was never theirs. **The residuals are on the log scale**,
because `features.log_target` is what the model fits: the assumption the
estimator encodes is Laplace error in log flux, and a quantile plot of
flux-scale residuals would test a different claim.

**Methane only, and the reason is doubled.** Carbon dioxide was never fitted this
way — `log_target` requires strictly positive values and the series crosses zero,
so no fit of this kind exists for it anywhere in `reconstruct.py`, `holdout.py`
or `stability.py`. And the assumption was never established for it: Deventer's
finding came from paired analyzers, and `ingestion.md` records that carbon
dioxide has one column and no pair, so nothing tests the distribution of its
error. A carbon dioxide panel would test an assumption nobody made using an
estimator nobody used.

**Both weightings, and the weighted row is scaled.** Weighted least absolute
deviations minimizes the weighted sum of absolute errors, which is maximum
likelihood under Laplace with a scale of `b / w` for each month. So under the
weighted fit it is `w * residual` that should be Laplace, not the residual
itself, and that is what the upper row draws. The stability figure already sets
the convention of drawing both weightings when weighting matters.

**Three residuals are exactly zero and that is the estimator, not the data.** A
least-absolute-deviation fit with `k` parameters interpolates `k` observations
exactly. The clamped design has three columns, so three of the 115 residuals are
zero by construction. It is 2.6% of the sample and it shows as a flat step
through the middle of each panel.

**These are in-sample residuals and they are shrunk by fitting.** They are not
draws from the error distribution. At 115 months against three parameters the
effect is small, but the figure is a diagnostic rather than a formal test and
nothing here claims more than that.

### The band, and why it is not drawn point by point

**A band drawn point by point is the wrong instrument and the error is large.**
Bounds that each hold 95% of their own order statistic are escaped somewhere by
**56.8% of samples that follow the distribution exactly** at n = 115. A reader
shown such a band and told it is a 95% band would read ordinary sampling noise as
a failed assumption, more often than not.

**The band is the equal local levels construction** of Weine, McPeek and Abney
(2023), *Journal of Statistical Software* 106(10), implemented in R as `qqconf`.

**The term is "simultaneous testing band", and a writeup should use it.** That
paper and its package use it and "global testing band" throughout, and the
distinction from a *confidence* band is deliberate: this is a hypothesis test on
the whole sample rather than an interval around an estimate, which is why one
point outside it is decisive and why the pointwise level is 0.002079 rather than
0.05. The figure stays in plain language — the key says *95% band (covering all
115 points at once)*, whose parenthetical is the property that separates a
simultaneous band from a pointwise one — but the term belongs in prose.
Every order statistic is tested at one common level chosen so that the chance of
*any* point escaping is the level asked for the whole figure. At n = 115 and a
5% global level that local level is **0.002079**: each point is held about
twenty-four times tighter than the band as a whole.

**It is computed exactly rather than simulated.** `residuals._all_inside` follows
the counting process — the number of draws at or below a point — forward through
the sorted bounds. Between two bounds the count gains a binomial number of the
draws not yet placed; at a bound the counts that would violate it are dropped.
The solve is a bisection on the local level, about 55 lines and **3.6 s at
n = 115**, and it introduces no stochastic step: the study's only one remains the
seeded bootstrap in `stability.py`. It was checked against 40,000 simulated
samples, which escaped the solved bounds 5.09% of the time against the 5.00% the
recursion reports.

**Cost of the alternatives, for the record.** Calibrating the local level by
Monte Carlo would have been shorter but would have added a second seeded step for
a quantity that has a closed recursion. Building no band at all was the fallback
if the exact route proved substantial; at 3.6 s and 55 lines it did not.

### The words, which took two passes

**Everything the figure says was written twice.** The first pass leaned on the
word *shape* — in the title, both axis names, the key and the description — where
*distribution* was the word that already existed. A reader outside the study
could not tell whether it meant a curve, a pattern or a probability
distribution, and the file was named `residual_shape.png` after the same vague
word. Renamed to `residual_distribution_check.png`, which says what it tests.

**The title now names the test.** It read *Model error against the shapes it
might follow*, which is passive and names nothing that happens. It reads
*Whether the model's errors follow the distribution its estimator assumes*.

**The axis names are the quantities rather than the reading.** They read *Error
the shape expects* and *Error the model made*, the first of which is not a
quantity anyone would recognize. A quantile plot compares two sets of values rank
by rank, so the axes are **Distribution's value at that rank** and **Model's
error at that rank**, both in log flux. Naming an axis for what it is "expected"
to show describes the conclusion rather than the number underneath it.

**The key entries were circular or oblique.** *Where a point falls if the errors
follow that distribution* describes the dashed line by the conclusion it exists
to support; it is the **1:1 line, where the two sets of values are equal**. *Where
every point falls together, 19 times in 20* is closer but leaves the reader to
work out what kind of band it is; it is a **95% band, meaning all 115 points fall
inside it 95% of the time if the distribution holds**.

**Weighting is explained rather than named.** The subtitle said the upper row
*scales each month by how well it was measured (which is what the weighted fit
assumes about it)*, a parenthesis that names the fit instead of saying what it
does. It now says the weighted fit **counts a month resting on many measurements
more heavily than one resting on few**, and that the study runs both throughout.

**The title calls it a diagnostic, which is what sets the expectation.** Three
titles were tried. *Model error against the shapes it might follow* is passive
and names nothing that happens. *Whether the model's errors follow the
distribution its estimator assumes* names the test but reads as though a finding
follows. **Diagnostic check on the model's errors** says what the figure is for:
it checks an assumption and reports a null, and a diagnostic is the thing that
is allowed to do that.

**The subtitle says what a quantile plot is before using one.** A reader who has
not met the form has no way to work out why sorted errors are being paired with
predicted values, and every earlier subtitle described the marks without naming
the construction. It now opens by naming it, says the errors are sorted smallest
to largest, and says what pairing rank with rank means.

**The axis names went back to the conventional pair.** They passed through *Error
the shape expects* and *Distribution's value at that rank* before settling on
**Theoretical quantiles** and **Sample quantiles**, both in log flux. The long
forms were attempts to avoid a term; once the subtitle defines the plot, the
short conventional names are the clearest thing on the axis and leave room beside
a 453 px panel. The key's middle entry lost its trailing clause for the same
reason: the subtitle defines the 1:1 line, so **The 1:1 line** is enough.

**The subtitle went to three sentences, and what went was construction detail.**
At seven lines over four small panels it put more canvas under text than under
data. The sentences cut explained that the errors are sorted smallest to largest
and paired by position, which is **how a quantile plot is built**: a reader who
knows the form does not need it, and one who does not is not helped by it. What
stayed is the naming of the form, what falling on the line means, what the band
covers, and what weighting does.

**The panels are sized by the width and the canvas height follows.** They sat at
453 px square with 156 px of empty margin either side of the pair, because the
height was chosen first and squareness then took whichever direction ran out
sooner. Setting the height to whatever squares the panels at the full available
width gives **609 px square**, and the panels went from **28.6% to 45.2% of the
canvas**. Two rows of square panels under a text stack is taller than it is wide,
so this is the one portrait size in the set, at 1560 by 2102.

**The block is centered, not the panels.** `MARGIN_PX` keeps 108 px at the left
against 40 at the right, which is there to hold y-axis names on figures that have
no gutter of their own. This one has a gutter, so that margin was doubling up and
the whole block sat 52 px right of centre. `_centering_shift` measures what the
panels and their axis names actually occupy after drawing — the room set aside
for a name is not the room it uses — and slides every panel and the key by the
difference. Margins are 92 px either side now and a test holds them equal.

**The text blocks are measured rather than allotted, for this figure only.**
`canvas_area` reserves the subtitle a share of the *title's* height, so the air
under a title doubles when the title wraps to two lines. Every other figure in
the set has a one-line title and never met it; this one wraps, and sat under 53 px
of air with another 40 px below the subtitle. `canvas_area` now takes
`measured_text`, off by default, which places the subtitle one `TEXT_GAP_PX`
under what the title actually occupies and the drawing area one gap under the
subtitle. Both gaps are 26 px, and no figure that does not ask for it moves.

**The key sits below the middle of its band.** It is taller than the 92 px band
it stands in, so centering it puts its top edge against the axis names of the row
above. At an anchor of 0.30 it clears them by 41 px and the description below by
41 px. The canvas height was tuned alongside it: the tighter text freed 40 px
that the square constraint could not spend, since the panel side is set by the
width, so the canvas came down rather than leaving the gap above the key to grow.

**The title fits one line, by dropping two words rather than a dash.** It read
*Diagnostic check on the model's errors at Marcell Bog Lake Peatland (2009 to
2019)* and wrapped with *2019)* alone on the second line. The wrap budget is a
character count taken from an average glyph width, which said 82; measured as
ink, the limit at this canvas is **76 characters**. Dropping the possessive gives
*Diagnostic check on model errors...* at 76 characters and 1388 px of the 1412
available. An en-dash in the year range was the other option and was not taken:
every other title in the set reads *(1990 to 2019)* or *(2013 to 2019)*, and
changing one of them would be the only figure spelling it differently. A test
holds the title to one line at this width, since a character budget that is 6
characters optimistic will not catch the next one.

**The one-line title freed 37 px, which the canvas gave back.** It came from
2102 to **2065**. The panel side is set by the width, so height the square
constraint cannot spend only opens a gap above the key: the same reclaim as when
the subtitle was shortened.

**The 1:1 line was tried in color and left achromatic.** The band was considered
for color first and rejected — blue at `#0072B2` means inside or retained across
the whole set, and a blue fill would be a fourth blue meaning something unrelated
— so the line was the next candidate, being a reference mark rather than a filled
region. Rendered against the achromatic version at panel size, it does not help:

- **Blue dashed** competes with the points on a panel whose points are the
  finding, and blue sits close enough to the green that the line and the points
  read as related when one is data and the other is apparatus.
- **Blue solid** reads as a **fitted line**, which is the one reading this figure
  has to refuse. Both distributions are fitted to these errors by maximum
  likelihood, so agreement is the line of equality and nothing here is regressed.
- **Achromatic** keeps the hierarchy the set uses everywhere: apparatus in gray,
  data in color, one colored element per panel.

The panels were not reading as flat, which was the condition for trying it. A
test now holds the line gray and dashed.

**The description bounds the null rather than leaving it open.** Every earlier
version stated the negative result and stopped, which leaves a reader working out
what a failed assumption breaks. The last sentence answers it: least absolute
deviations stays robust whether or not the errors are Laplace, and the study's
intervals are the empirical quantiles of the training residuals rather than
anything distributional, so nothing downstream moves. **What the null costs is
the argument for the estimator, not the estimator.**

**The description leads with the finding and carries no loose numbers.** The
counts, the gap of 96, the factor of 554 and the differences in the Akaike
information criterion are all precise and **none of them can be checked against a
panel**, so they are in the table below and nowhere on the canvas. What the
description carries instead is the finding, which row to read and why, and the
conflation that is the takeaway.

**Which row to read, which the figure could not say for itself.** The two rows
disagree and nothing on the panel says which fit is primary. The unweighted row
is the one to read for the distribution: the weighted row tests the weights as
well as the errors, and it is the weights that fail there.

**The block is balanced by translation, not by growth.** This was the only figure
in the set calling neither `balance_drawing_block` nor the site figure's
`_balance_gaps`, and it sat **28.0 px** under the subtitle against **75.4 px** over
the description. It is now **51.7 px** at both ends.

It could not use the balancer as the other nine do. That one grows the block into
the larger gap, and these four panels are **square in pixels** because the
reference they carry is a line of equality: stretched vertically to fill 47 px the
1:1 line would no longer be at 45 degrees, which is the one thing these panels have
to be. `balance_drawing_block` gained a `grow=False` mode that slides the block by
half the difference and leaves its size alone, and the four panels measure
609.00 x 609.00 after it.

Adding the balance also moved the heading rule, which now has to be drawn after
it. This figure had been escaping the rule-position fault by luck: it did not
balance, and `_underline_legend_headings` was the last call in the last helper.
`_distribution_key` now returns its axes and the caller rules it once the block has
settled.

**The key is centred in the band below the panels, and the balance settles with
it.** It had sat 36.8 px under the panels and 64.6 px over the description, which
is the wrong way round for an object a reader meets on the way down. Centring it
is not independent of the balance: the key is the block's floor, so moving it
moves what the balance measures. The two are solved together — `seat_key` centres
the key in the band on every round and the balancer equalises the outer gaps —
and they converge on **three gaps of one number, 55.33 px**: under the subtitle,
between the panels and the key, and between the key and the description.

**The key's drawn extent is not its axes.** The legend is 120.3 px tall in a 92.0
px band and overflows downward by **32.6 px**, which is deliberate and explained at
`_distribution_key`. Both the seating and the balance measure the legend rather
than the axes it sits in, and the legend goes into `extra` for the same reason.
Measured from the axes the lower gap reads 87.9 px where it is 55.3.

**Two questions the description rewrite left open**, recorded because neither is
settled by measurement alone.

*It carries 554, which a reader cannot check.* Every other precise number on this
figure went to these notes under the rule that a figure's text carries only what a
panel can be checked against, and the weights are drawn nowhere. It earns its place
only if *these weights do not track how the errors vary* needs a magnitude to be a
claim rather than an assertion.

*It dropped the conflation sentence to make room.* The published Laplace result
came from comparing two instruments against each other and was a different
quantity: 7,028 on 36,000-odd analyzer differences against −0.31 on 115 model
residuals. That sentence and the weighted-row account will not both fit, since the
description's allocation is five lines and holds about 643 characters. The
weighted row won because it is **drawn** and the conflation is not: two of four
panels were rejecting decisively with no account anywhere on the canvas.

**"Quantile" and "residual" are allowed.** The rule against terms a reader would
have to decode is about this study's own vocabulary — Boruta, fold, survival,
lag, screening, covariate — and not about standard statistics. On a quantile plot
those two words name the quantities exactly, and the earlier text avoided them at
the cost of saying nothing precise.

### What the figure found, which is not what was assumed

| fit | months outside the Laplace band | outside the Gaussian band | gap in fit |
|---|---|---|---|
| unweighted | **0 of 115** | 1 of 115 | **−0.31** |
| weighted (scaled) | 11 of 115 | 61 of 115 | **+95.84** |

**The unweighted residuals do not distinguish the two shapes.** A gap of 0.31 in
the Akaike information criterion is nothing: 2 is the conventional floor for
remarking on a difference at all. Laplace passes the band test and Gaussian fails
it by a single point, which at a 5% global level is the coin-flip end of the
scale. **The model's own error carries no Laplace signature.**

**The weighted row looks strongly Laplace and it is an artifact.** The
inverse-variance weights span a factor of **554**, and multiplying residuals of
one constant size by weights that variable produces a scale mixture, which any
heavy-tailed shape fits better. Simulated against the actual weights, 400 draws
each:

| what the errors really are | gap the scaled residuals produce |
|---|---|
| Gaussian, scale ∝ 1/w (weights right) | −11.9 [−20.0, −1.9] |
| Laplace, scale ∝ 1/w (weights right) | +15.8 [+0.2, +35.2] |
| **Gaussian, one constant scale (weights wrong)** | **+97.9 [+65.7, +133.3]** |
| Laplace, one constant scale (weights wrong) | +114.6 [+77.5, +167.9] |

The observed **+95.84** sits on top of the third row and far outside the second. It
also sits inside the fourth, so it separates wrong weights from right weights and
says nothing about which distribution the errors have.

**This table reproduces, and that is worth recording.** Re-derived from the setup
described above, 400 draws against the real weights, all four means land within 1
to 3 units: −11.2, +15.2, +98.8, +117.3. Set that beside the coefficient stability
figure's six controls, where two could not be recovered under any variant tried
and the recorded value for one of them lay outside the range of the computation
its own label named. Both tables were written the same way, from a script that was
never committed; only one of them survives re-derivation. Which it is cannot be
known without trying, and the entry on **assuming the record is the side that
moved** is about what happens when that is not tried.

**The 554-fold span does not imply unequal spread, and a draft of the description
said it did.** If the weights were right, scale proportional to 1/w, then
multiplying residuals by w would make the scaled residuals **homoscedastic** —
that is the entire purpose of inverse-variance weighting, and the top two rows of
the table show it, at gaps of −11 and +15 with no artifact. The spread is unequal
because the weights are **wrong**: the errors carry roughly one constant scale
while the weights vary 554-fold, so scaling manufactures the variability instead
of removing it. The conclusion the draft drew, that the weighted row tests the
weights rather than the errors, is right and is what the simulation licenses. The
reason it gave was the inverse of the mechanism.
So the weighted row is evidence that **the weights do not match the dispersion of
the errors**, not that the errors are Laplace. Both shapes fail its band test,
which says the same thing.

### The conflation this figure was built to establish

**This is the finding, and it now lives only here.** The ingestion layer
reproduced Deventer's result at **ΔAIC = 7,028 in favor of Laplace**, on
36,000-odd paired analyzer differences. This figure finds **ΔAIC = −0.31** on 115
model residuals. The two numbers are the same statistic on different quantities:
measurement disagreement between two instruments against the error of a fitted
model, and **the first was never evidence for the second**. The study chose least
absolute deviations because it is maximum likelihood under Laplace error, on a
published Laplace result that turns out to be about something else.

It is recorded here rather than on the canvas because the figure's own text was
distilled to what a reader needs while looking, and none of this can be read off a
panel. Three things left the description together and all three are in these
notes: why the estimator was chosen, that the published result measured a
different quantity, and that the estimator stays robust either way. A test asserts
each of them is still written down, on the pattern the seasonal figure set when
six numbers were cut from its block and four turned out to be stale or missing.

**It is also the second conflation of this kind this project has caught.** The
first was the wet-end directional expectation carried as a literal after the study
had adopted a different window; both are a number that was true of one quantity
being used for another without the substitution being noticed.

**What does not follow from the negative result.** Least absolute deviations
stays consistent and robust whether or not the errors are Laplace; it stops being
maximum likelihood, which is a claim about efficiency and not about validity. The
study's primary prediction intervals are the **empirical quantiles** of the
training residuals, which assume no shape at all, so they are untouched. What is
touched is the **Laplace interval variant** in `fitting.laplace_interval`, which
should now be read as a convenience rather than as a fitted distribution, and the
inverse-variance weighting, which this figure gives independent reason to
distrust — it already reduces effective sample size from 115 to 42.11, and now
the residuals say its weights do not describe their spread.

### One parenthetical went and one stayed, which looks inconsistent until stated

*Months with both flux and drivers* lost its `(used to fit the model)`. *Months
with drivers but no flux* kept its `(estimated by the model)`. The asymmetry is
deliberate.

The first restated twice over. The heading above it reads **Which months the
model used**, so "used to fit the model" says the heading again, and the row name
already says the months hold both flux and drivers, which is what makes them
fittable. The second does not restate: the heading covers both rows, and the two
rows mean opposite things, one being where the model learned and the other where
it predicted. Without the parenthetical a reader has no way to tell which is
which, because "used" in the heading is true of both.

The upper block's parentheticals are a different device and are not affected.
They carry units, one per row, and no heading can hold six of them.

### The key splits as the panel does

Four entries in one unheaded row read as one list of marks. They are two groups,
and the division is the figure's own: *months covered* and *a month missing* say
what the record holds, *set aside by the study* and *the range the model was
fitted on* say what the study decided about it, which is the upper block against
the lower. Headed in the set's device it is also narrower, 670 px against 1095,
at the cost of 58 px of height.

### Defaults nobody chose, swept across the set

Two spacings in this pass turned out to be matplotlib defaults that had never
been decided: `borderaxespad` at half a font unit on the forecast key, which left
it 8.85 px short of the series end it was meant to align with, and this figure's
`bbox_to_anchor` at 1.012, worth more than every geometry lever combined. Both
were binding constraints nobody had picked.

Swept, without changing anything. Five of the twelve keys in the set still sit at
one default or both:

| figure | anchor | inset |
|---|---|---|
| water table | default | 0.68, chosen |
| flux, per panel | **default** | **default** |
| site figure, network panel | **default** | **default** |
| reconstruction, panel and strip | chosen | **default** |
| coefficient stability | chosen | **default** |
| prediction error, residual check, site panels a and c, availability | chosen | chosen or zero |

Rendered insets from the corner each is anchored to: water table 11.3 px, site
network 8.8, reconstruction panel 33.3 and 20.3, reconstruction strip 16.8 and
12.4, flux 32.5 and 20.2, coefficient stability 12.2, prediction error 20.3 and
24.3.

The spread runs 8.8 to 33.3 px for the same relationship, a key sitting in a
panel corner, and nothing chose any of it. Whether that matters is a question for
after the pass, and the answer is probably that the four keys inset by more than
20 px are giving away panel area for nothing. Recorded rather than acted on,
because changing five keys at once at the end of a pass is how a consistent set
becomes an inconsistent one.

### The four elements step down evenly now

Measured before: title to subtitle 30.38, subtitle to key 18.06, key to panel
11.74, panel to caption 18.00. The key's clearance was the odd one, and it was
odd because two things set it: the anchor, and `borderaxespad` at its default.

`borderaxespad` is zero now, so the anchor is the whole of the distance, and the
anchor is computed after the block settles from `MIN_BLOCK_GAP_PX` and the
panel's final height. The three gaps around the key are then the same number by
construction rather than by tuning: **18.72, 17.74, 18.01**.

**The floor is a chosen value, not a hard constraint**, and only this figure
reaches it. Every other figure balances above it, from 23.8 px on the seasonal
split to 102.3 on the measurements figure, so lowering it would change this
figure alone. It was not lowered: 18 px is what the block already keeps from the
caption, and the point was to make the four elements agree rather than to make
them smaller.

**The title gap was the remaining outlier at 30.38 px, and it closed without a
set-wide change.** `canvas_area` already carries `measured_text`, an opt-in that
seats the subtitle one `TEXT_GAP_PX` under what the title actually occupies
rather than under the share allotted to it. The allotment gives a title 1.9 times
its own point size, 59.4 px for 29 px of ink, so the gap a reader sees below a
one-line title is the leftover rather than a chosen distance. Measured, it is 26
px, and the 4.4 px difference goes to the block where the key needs it.

The four gaps are now **26.00, 18.90, 17.55, 18.01**. The title gap is the widest
and should be: it separates the two blocks a reader reads before the panel, where
the other three separate elements inside one reading.

**26 px is `TEXT_GAP_PX`, and it was chosen rather than inherited** — the
constant exists precisely so that a measured gap does not double when a title
wraps. It is the floor here in the sense that nothing moves the subtitle closer
without changing it, and changing it would move the residual check, which is the
only other figure asking to be measured.

**What this does not settle.** Nine figures still take the allotment, so their
subtitles still sit under a gap that is the leftover of a share rather than a
decision. Turning `measured_text` on across the set is worth about 4 px each and
would make one rule govern all eleven, but it moves every subtitle, so it belongs
with the wrap conservatism and the default legend insets as a decision for after
the pass.

### The key's five entries, and what the levers were worth

The lead on a forecast row, a thin rule marking the months a model had to
accumulate before it could forecast, was drawn and never keyed. It is the fifth
entry, under **What the study decided**, since it is a requirement the study
imposed rather than something the record holds.

**Five entries will not go in one row.** They measure 1897 px against 1652 of
drawable width. Nothing closes that: the shortest defensible label reaches 1774,
shortening both headings 1778, and 7.5 pt reaches 1673 and is still over, on top
of being a point below the set's floor. So the key is two rows, one group to a
row, each headed at its left. The boundary between the groups is then a line
break rather than a reader noticing which item carries no marker, which is what
the inline arrangement would have asked of them.

**What each lever bought, measured rather than guessed:**

| lever | key size | height saved |
|---|---|---|
| as first laid out, handle 1.8, pad 0.5, rows 0.30 | 1238.7 x 64.8 | — |
| handle length 1.8 to 1.2 | 1196.2 x 64.8 | none, width only |
| handle-to-text pad 0.5 to 0.4 | 1231.6 x 64.8 | none, width only |
| row gap 0.30 to 0.22 | 1238.7 x 63.4 | 1.4 px |
| row gap 0.30 to 0.15 | 1238.7 x 62.1 | 2.7 px |
| border pad 0.55 to 0.35 | 1231.6 x 57.7 | 7.1 px |
| all together | 1182.0 x 55.1 | 9.7 px |

**The key's own geometry is worth about 10 px of height and no more**, because
handle length and text pad move width alone and the row gap is one gap between
two rows. Border pad is the only one of the three worth taking, and it is worth
7 of the 10.

**The gap to its neighbours was the larger cost and the cheaper fix.** The key
sat 17.3 px above the panel on a 1.012 anchor, for no reason beyond the default.
At 1.004 it clears by 11.7 px, which is about the width of its own frame line,
and that single number is worth more than every geometry lever together. The gap
above it is the balancer's floor and is not available.

Final: **1231.6 x 56.3 px**, 18.1 px below the subtitle and 11.7 px above the
panel, against 95.2 px tall and two stacked columns when the grouping was
introduced.

**The anchor had to be blended.** Centred at 0.5 in axes fractions the key hung
off the right edge of the canvas, because the row labels take a wide left gutter
and the axes occupies only the right two thirds, while the key is wider than the
axes. It now takes x from the figure and y from the axes, so it centres on the
canvas and still rides the panel when the block is rebalanced.

### `balance_drawing_block` can shrink, and this figure is why

Those 58 px were not available. The block, key and axis name included, came to
964 px between a subtitle and a description 894 px apart, so equalising the gaps
only shared the 70 px overlap out: both came to **−35 px**, equal and both wrong.

The helper only grew, on the reasoning that rows the description does not use are
not a reservation to defend. That is right when there is slack and says nothing
about the case where there is none. It now shrinks the block to
`MIN_BLOCK_GAP_PX` when equalising leaves the gaps under it, and both ends here
come to 19.3 and 18.0 px.

**Growing stays the preferred case and shrinking is the exception**, because
shrinking takes drawing area to pay for furniture. A figure that reaches it is
saying its furniture has outgrown its layout, which is worth noticing rather than
absorbing silently.

**One bug found on the way.** The equalising loop `return`ed when the two gaps
agreed, which is exactly the state the shrink step exists to inspect, so the step
never ran. It breaks now.

### The availability figure's row ordering, after methane reached 2024

**The rows sort by where each record ends, latest first, and that rule was chosen
to make one relationship visible: the study's boundaries fall where the shortest
records end.** With methane extended to 2024 the right edges run **2024-12,
2024-12, 2021-06, 2021-01, 2019-12, 2019-12** — steps of 0, **42 months**, 5, 13
and 0.

**It is not a staircase and it never was.** Before the extension the steps were
36, 6, 5, 13 and 0: one row alone at the top, five clustered below. The extension
moved the top group from one row to two and the drop from 36 months to 42. Four
of the six rows still end within eighteen months of each other, so most of the
visible descent is a single cliff.

**The cliff is the finding, so the shape encodes the constraint rather than
hiding it.** Flux runs to 2024 and the drivers stop in 2019; that gap is what
bounds the fit window, and it is what the drop between the second and third rows
draws. Recorded so a future reader does not re-derive this, or mistake the shape
for a defect and change the ordering rule to something that reads more evenly.
The rule is doing its job. What confirms it is the alignment rather than the
descent: air temperature and precipitation are now the bottom two rows of the
measurement block, and the blue fitted-range bar sits directly beneath them with
its right edge level at 2019-12, so the relationship the ordering exists for now
happens between adjacent rows rather than across a gap.

**The block splits at both ends, and the left edge is the sharper half.** Both
gases begin in 2009 while all four environmental records begin in 1990. The right
edges say where the fit window had to stop; **the left edges say why a
reconstruction is possible at all** — nineteen years of drivers standing before
any flux was measured is the entire opportunity the reconstruction half of this
study exploits. That is the figure's second true message rather than a defect in
the grouping, and nothing on the figure currently states it.

### The seasonal split figure

`figures/seasonal_cycle.png`, built by `study.figures.seasonal_cycle` from
`study.figures.seasonal_parts`, which reads the observed monthly series alone.

**Why it exists.** The study concludes that flux here is predictable in shape and
not in magnitude. Every other figure states that or supports it sideways. This one
draws it: the middle row is the shape, which repeats reliably enough that a
month-of-year average beats every fitted model, and the bottom row is the
magnitude, which varies 4.5-fold without direction and which nothing the tower
measures reaches.

**The span is the whole observed record, and the amplitude claim settles it.**
Methane's weakest season is **2021 at 33.7**, which falls outside the fitting
window. Decomposing on that window drops the year that makes the point and cuts
the range from 4.5-fold to 4.1; on the months forecasts were checked on it is
narrower still, and describes what the models were graded on rather than what the
site does. Carbon dioxide would lose a third of its record for nothing. The figure
fits nothing and scores nothing, so there is no window to protect.

| span | methane range | carbon dioxide range |
|---|---|---|
| **whole observed record** | **4.5×** (33.7 to 150.6) | **3.0×** (0.8 to 2.4) |
| fitting window | 4.1× | 2.5× |

**One shape, and the figure says which.** The middle row is the twelve
month-of-year averages, the same twelve in every year, which is the study's own
benchmark. A method that lets the shape evolve would answer a question the
benchmark does not ask, so none is used and none is named: the subtitle says *one
average shape for the whole record (the same twelve values repeated every year)*.
A test asserts the drawn shape takes twelve distinct values and no more.

**The caveat that is easy to skip and expensive to omit.** This shape is fitted on
every observed month. The forecast benchmark is not: inside each fold it is
rebuilt from the months up to the origin. Same idea, different operation, and a
reader who took one for the other would misread both figures.

It was the last sentence of the description and is now here. It is a statement
about how two figures relate rather than about what this one draws, and a reader
looking at the panel does not need it to read the panel. A test holds it in these
notes instead, so cutting it from the block could not lose it.

**No trend row.** Neither gas trends anywhere near significance — methane
p = 0.668 on the level, carbon dioxide p = 0.530 — and nothing was detrended
anywhere in this study. A row flat by construction would take height from the
bottom row while implying a component that is not there. One clause of the
description instead.

**Two figure artists had to become axes artists when the block was balanced.**
The row labels are placed in the gutter at fixed figure fractions and the time
axis name was too, so balancing the block moved the panels out from under both:
the labels named the wrong rows and the axis name ended up inside the bottom
panel. Placing the axis name after the balance did not fix it either, because a
figure artist is not in the extent the block is balanced against, so it landed on
the description instead. The name is now an axis label and is measured with
everything else; the row labels are still figure text but are placed after the
balance, from where each row ends up rather than from where it was allocated.

**The rule, which is general and worth holding.** Anything positioned in figure
fractions has to be placed *after* `balance_drawing_block`, and anything that has
to be *measured* by it has to belong to an axes. Neither failure announces
itself: a label naming the wrong row still renders, and a label sitting on the
description still renders, so both survive a build and a test suite that does not
look at where things landed. The helper measures `ax.get_tightbbox`, which is the
whole of what it can see.

**The row labels sit 9.5 px above their row centres, and this is pre-existing.**
Each is two lines drawn about one point, the name with `va="bottom"` and the
parenthetical with `va="top"`, so the point is the split between them rather than
the centre of the block. The bold line is the taller, so the block hangs high.
Recorded as known rather than fixed, and recorded so a later pass does not read
it as something the balancing introduced: it predates every change made here and
is identical on every row.

**The six numbers the description used to carry, now that it carries three.**
Recomputed from the current record with `AMPLITUDE_MIN_MONTHS = 10`, which is the
threshold the figure itself uses:

| | methane | carbon dioxide |
|---|---|---|
| share of variance the repeating shape explains | 74.2% | 71.5% |
| what it leaves, as a share of the measurements' spread | 0.508 | 0.534 |
| seasonal swing | 33.7 to 150.6, 4.5x | 0.81 to 2.40, 3.0x |
| trend in that swing | p = 0.215 | p = 0.505 |
| trend in the level | p = 0.668 | p = 0.530 |

Two of these were wrong here and two were absent. The v5-5 correction moved the
spread ratio from 0.54 to 0.51 and the amplitude-trend p from 0.119 to 0.215 in
the figure and not in these notes, and the carbon dioxide trend p and both
variance shares had never been written down at all. This is the reimplemented-
beside-itself pattern in its other direction: one value, two homes, one updated.

**On the wording of the trend.** The description said "neither of them trending"
and now says "neither showing a trend". At p = 0.215 and 0.505 nothing was
detected; that is not the same as nothing being there, and with fourteen and
sixteen annual points the test has little power to find a small one.

**The bottom row is the tallest**, at 1.5 against 1.0 and 0.8. It is where the
finding is, and the row above it is twelve numbers repeated.

**Scale bars: three rounds, and then cut.** Cleveland, Cleveland, McRae and
Terpenning (1990) put a bar of fixed data length at the right of each panel so
component magnitudes can be compared, and R's `plot.stl` and fabletools carry it
still. Three builds went into making one work here. The first drew the same data
length in each row and got three different heights, which says the rows are on
different scales — the confusion the bar exists to remove. The second put one
scale through the column so the bars came out identical. The third moved the label
off the top row, where it read as that row's own.

**They were cut anyway, and the argument is about the label.** The bar's meaning
has to be written somewhere, there is nowhere to write it but the narrow strip the
bar stands in, and that forces the text to be rotated. A 2024 figure-design
checklist recommends keeping every label horizontal, since every degree of
rotation slows reading. And the thing the bars existed to show is already one
sentence of the description, stated exactly: what the average year leaves is
**0.51 of the measurements' spread on methane and 0.53 on carbon dioxide**. A
number in words beats two grey rectangles a reader has to measure.

**The one scale through the column stayed.** It was introduced for the bars but it
is worth having without them: the rows are on one scale and their heights are the
flux each covers, so the middle row is visibly the shortest because the average
year covers the least. That is the comparison the bars were for, now built into
the geometry rather than annotated onto it.

**The season marks were cut with them.** They named an amplitude — the swing of
the measurements across a year — and for two builds pointed at a departure from a
calendar-month average, which is a different quantity whose extremes run the other
way for an uptake. Moved to the measurements row they were finally correct, and
still redundant: the description gives the range they illustrated, 33.7 to 150.6
on methane and 0.8 to 2.4 on carbon dioxide. Two marks that had been wrong twice
were not worth a third defence.

**The axis names are seated by measurement, then corrected.** Left to matplotlib
each sits off the widest tick label on its axis, whichever one that is, which gave
gaps running from −4 to 8 px across the six panels. They are now a uniform 5 px
from the nearest tick label. It takes two passes: a rotated label's extent is not
settled until it has been drawn where it will sit, and `set_position` does not
hold on an axis label, which recomputes its own place on every draw.

**The description is left of the panels, and that is inherent.** It begins 624 px
left of them, because the row labels need that gutter, and ends 162 px short of
their right edge. Relative to the drawing block it genuinely is shifted; relative
to the canvas, which is what the title and subtitle are centred on, it sits
exactly on the text margin at 108 px, which is where a left-set block belongs.

It also reads as narrower than it is because its last line is 93 characters
against 197 and stops over half the drawable width short. That is the ragged edge
of a left-set block and not a placement error. Centring it to match the panels
would trade a correct margin for an accidental one, and is not to be attempted on
a later pass.

**No legend, and the decision is deliberate.** The three row labels are the key:
each is set in the colour of the series it names, beside the row it names, so a
legend would repeat three labels a reader is already reading. Hyndman and
Athanasopoulos section 6.1, which is the reference for this figure type, carries
panel labels and no key on its decomposition figures, which is this structure
exactly. The set keys marks that share an axis and tell each other apart by
colour; here each series has a row to itself.

**Units are rotated at the left of each panel, which is the one place rotation is
expected.** Set above the panel instead they read as belonging to the row beneath
them, which is worse than the rotation costs. Every panel carries one, including
the top row, whose gas label carries it too — a unit on an axis is where a reader
looks for it, and the header is a column identity rather than an axis name.

**The canvas is wider, not taller.** The panels were cramped and there was no room
for both an axis name and a row name in the gutter, so `triple` went from 1800 to
**2300 px wide**, holding 1900 px of height. The gutter is 624 px: the widest row
name is 470, the axis name and its tick labels take about 90, and the frame needs
to clear both. Panels occupy **42.6%** of the canvas, against 39.6% before.

**The row names are written in their rows' own ink** — near-black, blue, green —
which ties each name to its line without six legend boxes repeating six labels.
The line beneath each stays muted, so the hierarchy inside the frame holds.

### The palette on the seasonal split, and the hue that carries two meanings

**Three rows, three kinds of thing, and the ink and weight say so.** The
measurements are neutral and heaviest at 1.7, since they are the record. The
average year takes `INSIDE`, at 1.1: it is the study's own benchmark, the
month-of-year average that beat every fitted model, and blue means retained across
the set, which fits a benchmark better than it fits a raw measurement. What that
leaves takes `FITTED` and is **filled to zero** rather than drawn as a line, which
gives the row the mass its finding deserves and shows each month's departure as an
area rather than as a position.

**Orange is used nowhere here.** It means outside or discarded across the set, and
the average year is neither.

**`FITTED` now carries two scoped meanings, and that is a deliberate exception.**
On the two forecast figures it is the range across the eight fitted models; here it
is what the average year leaves. They never appear on one panel and the figures are
not adjacent. The alternative was a fifth hue in the set for one row of one figure,
and reddish purple was tried for exactly that before this: it measured **9.0 against
the light gray it sat beside**, which is two rows a deuteranope would read as the
same tone, and **0.9 from `OUTSIDE` under tritanopia**. The palette note carries
the exception so it reads as a decision rather than as drift.

**Measured on this panel.** Blue clears the near-black measurements row by 56.8
under the worst simulated deficiency and the gridlines by 56.3; bluish green clears
the measurements row by 47.6 and the gridlines by 32.2; the two hues clear each
other by 20.9, on rows that never touch.

**The scale bar is named once per column, centered on the column.** Beside the top
row it read as the top row's own; beside the middle row, as the middle row's. It
now sits in the strip the bars stand in, centered on all three, and reads *each bar
is 50 nmol m⁻² s⁻¹*.

**The scale bar says what it is.** A gray rectangle with a number beside it was
the one mark on the panel nothing accounted for. Each column's topmost bar now
carries a rotated label reading *50 nmol m⁻² s⁻¹ in every row*, and the bars hang
from one height in all three rows rather than being centered in each, so they are
compared by their lower ends rather than by their middles.

**What the bars actually show, which is not quite what was expected of them.** By
range, what the average year leaves is **larger** than the average year's own
swing: 123 units against 71 on methane. By standard deviation it is smaller: 16.4
against 25.6. Both are true and they are not in conflict — a few extreme months
overshoot far while the typical month does not. The bars show range because that
is what a panel shows; the description gives the standard deviation. Neither the
panel nor the words claim the leftover is small.

**The marks were on the wrong row, and two attempts at the month proved it.** The
year is chosen from the measured swing, which is what a season's size means. The
bottom row does not show that: it shows each month's departure from its
calendar-month average. Marking a departure and labelling it with an amplitude
conflates two quantities, and no choice of month fixes it — the first rule picked
months near zero on carbon dioxide, and the second, which took the largest
departure either way, put *weakest season* on the largest positive excursion and
*strongest season* on the largest negative one. Both readings are inverted because
the label names one quantity and points at another.

**They are now on the measurements row**, at each year's own seasonal extreme: the
month furthest from that year's mean, in whichever direction the gas runs. Methane
peaks and carbon dioxide troughs, and the rule finds either. A reader sees 2011's
peak at 158 against 2021's at 46, which is the amplitude claim drawn rather than
asserted. A test builds an uptake by flipping the sign of a synthetic series and
requires the mark to follow.

**An earlier attempt at the month, kept for the record.** The year
comes from the measured swing, which is what a season's size means. Within that
year the month marked was the *maximum* departure for the strong year and the
*minimum* for the weak one — a rule that assumes the flux is positive. Carbon
dioxide is an uptake: its strongest season is its deepest negative and its
weakest a high positive. So the 2014 mark landed on +0.20 and the 2021 mark on
−0.37, both months near zero that meant nothing, while the year's real extremes
(−0.97 and +1.31) sat unmarked a few months away. The rule is now the largest
departure in either direction, which gives methane the same months it had and
carbon dioxide the right ones. A test builds an uptake by flipping the sign of a
synthetic series and asserts the mark follows.

**The leaders are arrows.** They had been plain stubs, and the methane 2011 stub
was a short diagonal that did not clearly reach its target.

**Two years are marked, lightly.** The strongest and weakest seasons on each gas,
at annotation weight in italic muted, with their values left to the description.
The finding is that the size varies *without direction*, so the marks have to read
as two labeled points in a scattered field rather than two events against a quiet
background. Anything heavier would have said the opposite of the panel.

**The row names are literal, and each says how its row was built.** Three
versions were tried. The first described rather than named. The second used
*shape* metaphorically for a row that holds twelve numbers, one per calendar
month, and left *from it* pointing two rows away. They now read:

- *Monthly flux measured at the tower (each month averaged from its half-hourly
  readings)*
- *The average flux for each calendar month (twelve values, repeated every year)*
- *Each month compared to a typical year (the measurement minus that month's
  average)*

Each parenthetical carries what the name cannot: how a monthly value is built,
that the middle row is one fixed set rather than something recomputed, and what
the subtraction actually is.

**The names sit in the gutter, on two lines.** Over the row they competed with the
gas labels directly above them and crowded the panels. On one line in the gutter
they needed **517 px**; split, with the name bold above and how the row was built
beneath it in smaller regular weight, the widest line is **470 px** — and that is
the bold line, not the parenthetical, on every row. **So the parentheticals are
free**: dropping them to the subtitle would not have bought back a pixel. The
gutter is 512 px and the frame is the one the gas labels take, drawn behind both
lines once their extents are known. A test asserts every frame clears the panels.

**The canvas is taller** — 1900 px against the 1500 the two-row figures use — which
is where the extra panel height came from.

**Units moved to the column headers.** The row names span both columns and cannot
carry two units. The six per-row axis names went with the move, since the header
now says it and nothing else on the panel needed it twice.

**Each column names its own unit on its own axis**, since the two are in different
units, and the time axis is named once beneath both. The gas labels are centered
over their columns and carry the gas alone now that the unit has a place.

**The title names the middle row and the subtitle carries the finding.** That is
the division used across the set: the title orients, the subtitle argues.

**The subtitle's last clause was overstated and is corrected.** It had read *it is
the part nothing in this study predicts*, set bold — the only bold clause in any
subtitle in the set, and a claim wider than the evidence. What is true is narrower
and is now what it says: **nothing tested here predicted it: eight fitted models,
four benchmarks and four measured drivers.** The bold is gone with it.

**What was left out.** A trend row. Any evolving-shape decomposition. Confidence
bands on the shape, which would make an average look like a result. A per-year
amplitude row, which is a different quantity in different units. Model predictions,
which are the forecast figures' job. The reconstruction period, where there is no
flux to split. The observed uncertainty band, which is on the flux figure and
would compete with the bottom row here. And the Delwiche network context, which
belongs to the writeup.

**On precedent.** Delwiche et al. (2021) decompose methane seasonality across 79
sites, and the notes above hold what its appendix gives. It carries nothing on how
to draw a components view for one site, so this was designed from first principles.
One thing from it does bear on the design and is worth repeating here: peak methane
timing there correlates with neither air temperature, soil temperature nor gross
primary productivity across sites, so the shape has to be estimated from this
record rather than borrowed from the literature, which is what the middle row does.

### The in-canvas text is a repository choice, and publication would undo it

Every figure in this set carries its title, subtitle and description inside the
canvas. That is deliberate and it is a choice about **where the figures are read**:
in a repository on GitHub, a figure travels alone, is opened on its own, and has
to explain itself with no caption anywhere near it.

Publication is the goal at the end of this work, and journals set captions outside
the figure, in the venue's register, which is technical rather than plain. **A
publication pass would therefore strip the in-canvas text from every figure and
rewrite it as captions.** That is not a rebuild: every figure function already
takes prepared data and returns a `Figure`, and every block of text lives in a
`FigureText` beside its function rather than inside the drawing code. The work is
a mode in `plotstyle` — one that lays out the same rectangle without the title,
subtitle and description blocks — plus a caption written per figure in the
journal's voice.

Recorded here as a known task rather than an oversight. Two things follow from it
for the work still to come: the text blocks should stay in `FigureText` and out of
the drawing functions, and the plain-language standard is a property of the
repository audience rather than of the figures themselves.

### The availability figure

`figures/covariate_availability.png`, built by `study.figures.covariate_availability`
from every source the study reads.

**Why it exists.** The study's boundaries were stated in prose across three
figures and drawn nowhere: the fitting window ends 2019-12 because air
temperature and precipitation do, the forecast cannot begin until 48 months have
accumulated, 2021 was never compared, the water table is cut at the 2020 datum
break, two months of 2019 are excluded as instrument error, and the
reconstruction covers the years where drivers exist and flux does not. All six
are one alignment problem, and one timeline shows them together.

**No standard form exists for this.** Dataset papers describe gap-filling rather
than drawing where the gaps are. The one adjacent convention is the fingerprint
plot, an hour-of-day against day-of-year grid, which Deventer et al. (2019) use
in the same form; it suits one series at high resolution, not eight across 426
months. Delwiche et al. (2021) was checked and carries nothing on the question.
Designed from first principles.

**Two blocks, not one panel with bands.** The upper block is what was measured,
one row per series; the lower is what each piece of work used. Shading the
windows across the series would have drawn them as a property of the data, and
they are choices made from what was available. As rows with their own names they
read as choices, and the largest ink on the panel never gets drawn.

**Row names carry their units, and no row name carries a term the panel does not
explain.** Each row is a monthly mean, said once in the block heading rather than
six times in the rows. "Reconstruction", "fitting window" and "scored over" are
gone, and the verb phrases that replaced them are gone too: the lower rows are now
noun phrases matching the upper block, *learned from* and *estimated backward*
under **months the model used**, and *methane forecasts* and *carbon dioxide
forecasts* under **months the forecasts were checked on**.

**The two model rows say what their span is rather than naming it.** They read
*months with both flux and drivers (used to fit the model)* and *months with
drivers but no flux (estimated by the model)*. The names they replaced, *learned
from* and *estimated backward*, assumed a reader who already knew the study's
structure, which is the fault being removed everywhere else in this set. The new
names also make the *(no flux to check against)* note redundant, so the note and
its leader are gone.

**Every row name was measured against the gutter rather than assumed**, and where
they did not fit the gutter was widened rather than the names cut. It now holds
580 px against the 565 the longer of the two needs. The cost is the timeline:
2.4 px per month instead of 2.9. That is a trade the notch ticks were already
there to survive, and a name a reader has to already know is worse than a
narrower axis. *Methane forecasts checked against measurements* was the one name
shortened instead, at 503 px, with its shared part moved into the block heading.

**The forecast rows were left alone.** *Methane forecasts* and *carbon dioxide
forecasts* under a heading reading **forecasts checked on** name their subject
under a heading that says what was done to it, and assume nothing. The model rows
needed rewriting because they named an operation without saying what distinguished
the two spans.

**Why there is no flux before 2009 is drawn rather than said.** The row now says
*no flux*, and the upper block shows the methane and carbon dioxide bars beginning
exactly where that span ends. A clause making it explicit would cost the
description a sixth line, which the block does not have without dropping something
else; if it is ever wanted, the sentence to trade is the one about the seasonal
benchmarks reaching 2021 and 2024.

**Where each series is measured, and why the heading does not say.** The heading
over the upper block was going to read *what was measured at the site*, and that
overstates it. Only methane and carbon dioxide come from the tower. Soil
temperature is `MEF_soil_temp_weekly.csv`, the experimental forest's weekly record
at 10 cm; air temperature is a cumulative mean over the forest's stations; and
precipitation is the **average of a north and a south gauge**, which
`covariates.load_precipitation` says in its own docstring. The water table is a
gauge reading in elevation. So the heading reads *what was measured (monthly
means)* and makes no claim about where. This is worth recording on its own
account: three of the four drivers are forest-scale records rather than
measurements at the peatland, which is a limit on how local any driver
relationship in this study can be.

**The three headings were put in one register.** They had been a past participle,
a noun phrase and a passive construction; they now read *what was measured
(monthly means)*, *which months the model used* and *which months the forecasts
were checked on*. The last two name months, which every row in the figure is, and
match the question in the title.

**Each heading is seated over the names it heads.** Left-aligned at the margin
they floated: the widest block set the gutter at 580 px, so the other two headings
sat far from their own rows. Each is now centered on the horizontal extent of its
own block's names, measured after drawing rather than placed. Where a heading is
wider than the names it heads — the first is 422 px against 305 — true centering
would push its frame into the plot, so it is shifted left until the frame clears
by 8 px. Off center by a little beats a frame over the bars.

**The block headings are framed, and the argument against it did not hold.** The
case for leaving them bare was that the bordered box exists to separate a name
from the data behind it, and these sit in the gutter on white. That is true and it
is not decisive: the frame also marks a level in the hierarchy, and the row names
share that gutter, so the set's own treatment does useful work here. Framing them
cost 30 px of timeline. Two headings were too wide to hold a frame clear of the
plot — *What was measured, as monthly means* measures 454 px and *Months the
forecasts were checked on* 431, against a 360 px gutter less 17 px of padding —
so both were shortened rather than the gutter widened further. They now measure
306, 262 and 240 px, and a test asserts every frame's right edge falls left of the
plot. Commas in the headings became parentheses at the same time.

**The key is framed and centered**, as every other legend in the set is. It had
been running from the middle of the panel to its right edge with no frame at all.

**The time axis is named and the row axis is not.** Direction is plain from the
year labels, but an axis with no name is an axis a reader has to infer. The other
one carries six names already, and a title over them would repeat all six.

**Both text blocks were broken into shorter sentences.** The subtitle had said
*longest record at the top* while the rows were sorted by end date, which put soil
temperature, the longest at 383 months, third; and it still called the lower block
three pieces of work after it had become four rows in two groups. Both were
corrected. The description's second sentence had carried four clauses across
three separate facts and is now three sentences. A test holds every sentence in
either block to two clauses.

**The water table row says elevation.** Its values run 413.07 to 413.75 m above
sea level, and a reader who works on peatlands meets "water table" expecting a
depth below the surface. The row reads *water table elevation (m)*: the unit was
right and the word was missing.

**Four kinds of month, three marks.** Measured is a filled bar. Missing from an
otherwise unbroken run is a hole in the bar, with a tick under it because one
month is under four pixels across thirty-five years and a hole alone reads as
nothing. Set aside by a decision is drawn hollow, with the reason written beside
it: *instrument error* on 2019-06 and 2019-09, *gauge change* from 2020-01. Never
covered is nothing at all. Because the two hollow cases carry their reasons in
words, the key holds three marks and no reasons, which is what keeps six kinds of
absence from becoming six keys.

**Rows ordered by where each record ends, latest first.** This is the change that
made three others unnecessary. Ordered that way the right edges step inward —
2024-12, 2021-12, 2021-06, 2021-01, 2019-12, 2019-12 — and the last step is the
month the fitting window stops at, so the study's central constraint is a shape
rather than a sentence. Ordering by span length was tried first and does not do
it: carbon dioxide has the second-shortest span and the latest end, so it lands
mid-block and breaks the descent.

**What the ordering does not do.** Three of the six records end within twelve
months of one another, so the middle of the descent is a slope of fifteen to
twenty pixels per step rather than a stair. The alignment that carries the
argument — the lowest step meeting the fitted bar at 2019-12 — reads; the shape
as a whole is gentler than the word staircase suggests.

**Three things the reorder made redundant, all cut.** The three full-height
guides, which existed for the alignment the ordering now carries. The column of
month counts, which a reader does not need while looking at bars whose lengths
already carry relative magnitude; the exact figures are in the table above. And
the two analyzer rows, which describe how the methane series was built rather
than where the study's boundaries fall, and which have the analyzer-mixing figure
of their own. Eight rows became six and the panel lost its right-hand column.

**The lower block keeps its two groups, and the two changes do not fight.** The
reorder is a rule about records; the groups are a rule about roles. They sit in
different blocks and neither constrains the other. The lower rows are ordered
within their groups by what they do rather than by span, which is right: fitting
comes before projecting because one produces the other.

**One tick per break, not per month.** The first build drew a tick under every
missing month, and the eight months missing across 2013 and 2014 came out as an
indistinct smear rather than as anything countable. A run of adjacent missing
months is one break in the record; the count of months belongs in these notes.
The tick is also heavier and in the same ink as the bars, since it is part of one
rather than a mark on top of one.

### The palette question on this figure, and what it should be

The figure was first drawn in black and gray alone, which left it the only one of
eight with no connection to the palette the rest of the set uses. Four decisions
came out of looking at that.

**The measured bars stay neutral.** They are a record of what exists rather than
a result, and the upper block's distinction is exists, missing, discarded — not
retained against discarded. `INSIDE` for existence would claim a decision was
made where none was. This is the same reasoning that made the date share
achromatic on the measurements-used figure.

**Neutral, but not black.** Near-black made rows that are context the loudest
thing on the page. Three versions were built and compared at full size — black,
reddish purple, and a mid gray — and the gray was chosen, at `#4D4D4D`. It clears
the discard orange, which is drawn on top of these bars, by **54.5 under the
worst simulated deficiency and 0.147 in relative luminance**. Reddish purple was
measured and set aside twice over: Okabe-Ito's `#CC79A7` sits **0.9 from that
orange under tritanopia**, where the outlines would vanish, and the darker plum
that cleared it (`#7B3F5E`, 34.3) added a fifth hue to the set for rows that are
context rather than subject. With gray, the only colored marks on the panel are
the two that carry meaning.

**The set-aside marks take `OUTSIDE`.** That hue already means *outside, or
discarded* across the reconstruction figures and the site map, and these are the
only months on the panel that a decision discarded. The mapping is exact rather
than analogical. Measured against the white they sit on, the edge clears it by
**74.5 ΔE under the worst simulated deficiency and 0.778 in relative luminance**,
so the mark reads with or without color.

**The fitting window takes `INSIDE`; the reconstruction does not take `OUTSIDE`.**
The fitting window is the range that defines what *inside the fitted range* means
everywhere else in the study, drawn in time rather than in water table, so blue is
the same statement in a different projection. The reconstruction is not its
opposite: **117 of its 230 months lie outside the fitted range and 113 inside**,
so a uniformly orange bar would assert a verdict this study measured as mixed and
would contradict the reconstruction figures, where those months are split between
the two hues month by month. It stays neutral, and that asymmetry is the honest
one.

**What the hue is not carrying.** `INSIDE` sits **41.3 ΔE** from the neutral
window fill under the worst deficiency but only **0.029 apart in relative
luminance**, so in grayscale the blue bar and the gray bars are near enough to
identical. The distinction a reader needs is carried by the row name and the
group heading, and the hue is a tie to the rest of the set rather than the thing
that makes the row legible. `FITTED` was not considered: the convention scopes it
to the two forecast figures, and a scoring window is not a range across models.

**One neutral for every bar that is not the fitted range.** The lower block was
briefly drawn in a second, lighter gray. Nothing distinguished those two grays
except that they were drawn at different times, and the blocks are already
separated by position and heading, so the second gray went. Hatching was
considered for the same purpose and rejected: at this bar height across 35 years
it aliases, which is why it was turned down on the reconstruction strip.

**The key covers every mark from one place.** It carried three marks in the upper
block and nothing in the lower, where a reader met a blue bar and two gray ones
with no key at all. It now runs four entries across one line, and the first is
worded *months covered* rather than *months measured* so it serves both blocks;
what each block's bars are is said by its heading. The blue's convention — that it
marks the range the model was fitted on, here and across the set — is a sentence
rather than a label, so it sits in the description, which is on the canvas.

**The lower block is two groups, not four rows of one thing.** Reconstruction and
fitting window are spans of months the study drew on; the two forecast rows are
spans it scored predictions over. Drawn as four identical bars they read as four
instances of one kind. They are now grouped under two headings, which marks the
distinction without a fourth mark in the key, and it shortened the row names to
one line each — the two forecast rows had been wrapping to two while every other
row sat on one.

**The 48-month rule is a weight, not a fourth symbol.** Each comparison row runs
as a thin line from where its flux record starts to where the comparison begins,
then as a full bar. Methane's lead is **62 calendar months for 48 observations**,
because of the 2013 and 2014 gaps, which is worth stating: the rule counts data
rather than time.

**Three guides, added after the build rather than designed in.** The alignments
are the figure's whole argument and they have to be read vertically across the
rule between blocks. At 426 months wide that did not hold by eye, so verticals
were added at the three boundaries that carry a claim: where the flux record
starts and the reconstruction ends, where the shortest measurements stop and the
fitting window with them, and where the comparison ends while methane carries on
for another year. Nothing else is guided. Drawn first in the gridline gray and
under the gridlines, they were invisible at the rendered size; they are now dashed
in the apparatus gray the set rules its range boundaries with, and drawn above the
gridlines. A guide that reads as a gridline is not a guide.

**The month counts sit beside each bar rather than in a column**, which would
read as a table set next to a figure. All twelve are bare numbers: naming the unit
on the first row alone was meant as a heading and read as an inconsistency, and
the subtitle already says the bars cover months.

**What the alignments show without a word of annotation.** The fitting bar stops
exactly where air temperature and precipitation stop, while methane runs 24
months further: those are the 25 discarded months. The reconstruction bar covers
precisely the span where drivers exist and no flux row has begun. Methane reaches
2021-12 and its comparison bar ends 2020-12, which is 2021 never being evaluated.

**What was left out.** Half-hourly and daily coverage, which is the fingerprint
question. The day counts behind each monthly mean, which is quality rather than
availability. Per-horizon evaluation windows, eight rows to show a few months of
difference. Gap-filling, since none was done. Any shading across the panel. And
the benchmark-only tail — methane compared to 2021-12 and carbon dioxide to
2024-12 where no measurement is needed — which is one clause of the description
rather than a fourth mark.

**Both reasons are labeled from below, one to each side of its own mark.** They
were first stacked to the right of the row, which ran two leaders back across the
water table bar to reach marks six months apart. Each label now sits under the
row on its own side, and neither leader crosses anything.

**Nothing is pinned.** Spans, gaps and counts are computed from the committed
sources; the two exclusions come from `windows.WATER_TABLE_ARTIFACTS` and
`covariates.WATER_TABLE_DATUM_BREAK`, so changing either constant moves the
figure.

### The coefficient stability figure

`figures/coefficient_stability.png`, built by `study.figures.coefficient_stability`
from `data/processed/coefficient_stability.csv`, which `scripts/reconstruct.py`
now writes for both treatments.

**There is no standard figure for this experiment.** A search found none. The
sensitivity analysis literature varies model inputs to see how outputs respond,
which is a different question; the extrapolation literature concerns prediction
accuracy beyond the training range rather than coefficient stability within it.
The design is from first principles, with one device adopted: Bartley et al.
(2019), *PLOS One*, shade regions of extrapolation in darker grey beside
prediction intervals, using leverage to set the boundary. That device was adopted
and has since been dropped: what the reconstruction requires the coefficient to
hold across is drawn as an **arrow**, not as a shaded region, and the ground the
fill used to cover is where the key now sits. Four sentences in this section were
still describing the fill after it was removed and are corrected here.

**The axis is the water table, not the experiment.** Metres from the wettest
month in the full fit, so zero is the wet edge of the evidence and the five
refits fall at 0.00, −0.05, −0.07, −0.10 and −0.12. That one decision is what
makes the qualification visible rather than asserted: every refit occupies
**0.12 m** on the left, and the region the reconstruction needs runs **0.29 m**
to the right of everything, **2.4 times** wider than the whole experiment, with
nothing drawn inside it. The share dropped is no longer annotated anywhere: it was
the old top row and it went when that row became a proper axis, as the paragraph
on the two directions below records.

**One key for both panels, in the ground the fill used to cover.** The first
build named the two treatments and nothing else, leaving five unexplained marks
and panel b with no key at all; the second put the key below the axis, which
nothing else in this set does. It now sits in the upper right of the water table
panel, in the two-column ruled-heading form: the treatments in one column, and in
the other the interval bars, the carried-across starting value, the rule at the
edge of the fitted range and the bracket.

**Both panel names moved off the data** to the upper right, for the same reason
and into the same freed space.

**The two axes were reading in opposite directions.** The row above the panels ran
40%, 30%, 20%, 10%, none from left to right while the axis below ran negative to
positive. Reversing either would have put the extrapolation on the left, where it
reads as the past. The row is now a proper top axis carrying the **months left in
the fit** — 69, 81, 92, 103, 115 — which increases in the same direction as the
axis, sits with the fits it describes, and adds the sample size each point rests
on. The percentages are gone rather than doubled up: two rows of numbers running
opposite ways is the thing being fixed.

**The control panel says plainly what it is for**: the control, the same
experiment on a coefficient that barely moves. The earlier wording named the
mechanism instead of the role and was opaque.

**The band beneath the panels now carries one thing**, the 0.05 m the wettest
months held out actually reached, with its label beside it rather than over it.
Everything else it held has moved to where it belongs.

**Both panel names are centred over their panels**, and centred on the axes
frame rather than on the tight bounding box. The distinction matters here: the
rotated axis name and the tick labels stand outside the axes, so the tight box
reaches 79.8 px further left than the frame and centring on it would pull each
name 39.9 px off the middle of the panel a reader sees. An axes fraction of 0.5
is the frame's middle by definition, which is why this one is expressed as a
fraction and not measured.

They had been right-aligned at 0.984, which put them **722.7 px and 688.8 px off
centre**, reading as notes in a corner rather than as the names of the rows. Two
other figures in the set already centre their panel names at `x=0.5`, so this
brings the third into line rather than inventing a third treatment.

**A fraction is not always the thing that drifts.** The key on this figure and the
heading rules across three all drifted because they were seated against another
object's measured position before the balance moved it. These names are not that
case: `balance_drawing_block` rescales panels vertically and leaves x untouched, so
a horizontal fraction cannot drift, and the vertical fraction rides the panel it
names. What the shared fraction does produce is an inconsistency of a different
kind: 0.952 of a 710.8 px panel and of a 245.6 px one puts the two names **34.1 px
and 11.8 px** below their own spines. Both clear, and it is recorded rather than
changed.

**The months axis name was 528 px from anything it named.** It was centred on the
axes, which is 1652 px wide, while the five fits it counts occupy the leftmost 466
of them; the name sat over the empty ground the arrow crosses. It is now seated on
its own numbers, offset 0.00 px, and 10 px above them. Two traps in that:
`set_label_coords` reads its pair in axes fractions and 1.0 is the top of the axes
rather than the top of the tick labels, which stand outside it, so the first
attempt dropped the name into the row of numbers. And seating it after the balance
made it the block's top ink at a height the balance had never measured, leaving the
two gaps disagreeing; it is seated inside the reflow instead.

**The month counts are bold and nothing new is boxed.** They are the sample size
every point rests on, which is a reading rather than apparatus, and the
percentages at the other end of each path were already bold. Boxing them was
considered and refused: this set borders panel names and nothing else, so a second
kind of box on one panel costs the border the one meaning it carries.

**The key drew marks the figure does not contain, twice over, and both faults
were structural rather than careless.**

*Open markers drawn solid.* The two paths are drawn with `markerfacecolor="white"`
and `markeredgewidth=1.4`, so the panel shows hollow rings. Those two settings were
added at the `errorbar` call, and the key does not go through that call: it builds
its handles from the `TREATMENTS` style dict, which did not carry them. The panel
drew open marks and the key drew solid ones for as long as this figure has had a
key. Both settings now live in the dict, so the key and the panel read one source.
Correcting the instance would have left the mechanism; moving the properties
removes it.

*Three ticks where the panel draws one.* A legend lays every handle on three
sample points and draws the marker at each of them. Two entries were markers on a
line, so *Where the coefficient landed in 500 resamples* rendered as **three**
ticks in a row where the panel draws one capped interval, and the bracket rendered
with a **third tick in its middle** where the strip has two at its ends. Neither
had been noticed, and neither reads as an error: at this size three ticks in a row
read as one thick mark. Both are now drawn by handlers, `_IntervalHandler` and
`_BracketHandler`, which draw the pieces the panel and the strip actually draw.

`test_the_key_draws_the_marks_the_panel_draws` holds both: every marker property
the panel sets is read back off the key's own handles, and the bracket's ticks are
asserted to be at its ends.

**The four percentages said nothing about what they measured.** Each is
`100 × (y[-1] / y[0] − 1)`, that coefficient's total change from the 115-month fit
to the 69-month one. They had been cut from the description on the reasoning that
the panel labels them directly, which was wrong: the panel shows the numbers
without saying they are totals across the whole experiment. The clause is back in
the description rather than in the key, because the mark is text and would need a
blank handle in a bordered key where every other row has one. It cost nothing: the
block stays at three lines and its last line grows from **36 characters to 121**,
settling the widow the rewrite had left.

**`set_bbox_to_anchor` reads a bare pair as axes fractions.** Handed display
pixels it multiplies them by `transAxes` again. Seating the key over the annotation
that way put it at x 1,905,754 on an 1800 px canvas. Convert with
`ax.transAxes.inverted()` first.

**The block is balanced, and both ends of it are furniture.** It sat **34.0 px**
under the subtitle and **146.8 px** over the description, the widest split left in
the set once the year figure was fixed. `balance_drawing_block` closes it to
**33.98 px** at both ends, and because the balancer grows into the larger gap
rather than recentring, the drawing block gains all **112.8 px**: its ink runs
1099.4 px against 986.6, **11.4% taller**. Nothing was traded for it.

Two things had to be handed in. The x-axis name below the strip is figure text and
the panel names, the percentages and the key are axes text, so none of them
reaches the balancer through `get_tightbbox`; they are passed as `extra`. Only the
axis name needs a `reflow`, since every other one is placed against the panel or
strip it belongs to and moves with it.

**The key's outer inset was the default and is now zero.** The anchor
`(0.998, 0.90)` was chosen and `borderpad` was already taken to 0.0, so the only
thing left standing between the key and the corner it names was `borderaxespad`
at matplotlib's default half a font size: **8.85 px** at 150 dpi, putting the box
**12.2 px** inside the axes where 3.3 px was asked for. Both numbers appear in the
legend-anchor sweep table and they are the same inset measured from two
references, the chosen anchor and the axes corner.

**A heading rule does not move with the heading, and two figures had drifted
apart from theirs.** `_underline_legend_headings` draws each rule as a figure
artist at fixed figure coordinates. `balance_drawing_block` moves the axes its
legend rides on. Rule first and the line stays where the heading used to be.

Balancing this figure put the rule 5.6 px above the bottom of its own text, which
is through the lower third of a bold capital. Auditing the rest turned up two more,
both older than this session:

| figure | fault | how long |
|---|---|---|
| reconstruction series | ruled at line 323, balanced at 325; both headings struck through | since the figure was first balanced |
| observed and predicted | ruled before *and* after the balance; two artists per heading, the first stale | same |
| coefficient stability | introduced by this session's balance | one build |

The seasonal figure already carried a comment saying to balance before ruling, so
the rule was known and had been applied in one place and not the other two. That
is the *corrected where it was noticed* pattern again, and it is the fifth
instance.

**The fix is a test.** `test_every_ruled_legend_heading_is_ruled_under_its_own_text`
asserts one rule per heading and every rule below its own text box. It reads as a
strike at this size rather than as an error, which is why three builds of three
figures went out with it: nobody looking at the figure would call it a bug, and
only measuring the two boxes against each other says so.

**The axis names are seated by measurement.** One panel's ticks read 7 and the
other's 0.12, so a fixed inset either collided with the second or stranded the
first far to the left. `_seat_axis_names` measures the widest tick label across
both panels and sets both names just clear of it.

**The holdout bracket sits against the arrow.** The wettest-decile test
trained to 413.41 and reached 413.46, so it demonstrated transfer over 0.05 m
against the 0.29 m required. Drawn as two lengths on one axis, the 17% is a thing
a reader measures by eye rather than a number to be taken on trust.

**Each panel carries its own coefficient in its own units, and the comparison is
kept by the geometry rather than by the axis.** The first build indexed both
panels to 100 at the full-range value, which made the two drifts directly
comparable and put a translation step on the figure's central quantity: a reader
seeing 100 rising to 150 had to remember that 100 meant 2.704. The axes now read
in the coefficient's own units, each path's starting value is carried across as a
dotted rule, and the total change is labeled at the dry end. What replaces the
shared axis is a shared scale: **the panels are given heights in proportion to
the proportional range each has to cover, so a percent of change is the same
number of pixels on both.** A control panel scaled to its own data would draw a
16% climb exactly like a 51% one; this one cannot. It also solves the empty
space, since the soil temperature panel is now a third the height rather than
two thirds empty. A test measures pixels per unit of proportion on both panels
and requires them equal.

**Soil temperature is drawn as the fitted slope, not as its Q10.** A Q10 is an
exponential of the slope, so the same experiment reports a different drift on it:
15.5% against the slope's 16.3%, and the description quotes 16%. `stability.
coefficient_path` now emits `soil_temp_coef` beside `q10` so the figure reads the
comparable quantity and the holdout tables keep the one this literature quotes.

**Two treatments, achromatic, separated by line style.** They are one analysis run
twice and the finding is that neither survives, so hue would have made them read
as two methods with a winner. The description says so in as many words.

**The criterion is not on the panel.** It takes four clauses to state, and a
figure carrying it would imply the verdict was obvious. The description says
instead that every step's interval overlaps the first, so no single step is
decisive and the evidence is that the coefficient climbs at all four steps and
never once falls. A test asserts that none of the criterion's vocabulary reaches
the figure.

**What was left out.** The rank correlation of +1.00 at p = 1.4 × 10⁻²⁴, which is
a correlation on five points and would read as more than it is. The month counts
per step, 115 down to 69. The three reconstruction variants. Knox et al. (2021)
and the nuclear verification study. The wettest-decile tie instability. And any
curve drawn along the arrow, which is the one thing the figure exists to
refuse.

**A shortened axis name.** "Coefficient, as a percentage of its value on the
whole range" was doing the work the subtitle should do. The axes now read "Per meter of
water table" and "Per °C of soil temperature", and what a coefficient is belongs
to the subtitle.

**The title was distilled with the rest.** Every title in the set now reads as one
clause naming what is plotted and the site: this one became *The water table
coefficient refitted on drier months at Marcell Bog Lake Peatland*, and the site
figure's became *The flux tower and the wind directions it measures at Marcell Bog
Lake Peatland*, with ", Minnesota" moving into its subtitle. All eight fit on one
line.

**A title that outran the canvas.** This is the longest title in the set and it
overflowed the drawing area. `plotstyle.wrap_title` now wraps a title and sizes
the block from what it wraps to, as the subtitle block already did. No other
figure's title wraps, so nothing else changed shape.

**Independent support for the general case.** A nuclear verification study runs
structurally the same experiment, retraining on deliberately narrowed parameter
ranges and finding that models trained on narrow ranges struggle beyond them
while wider ranges do not diverge. Their conclusion, that this favours broader
training ranges, is this study's finding in the general case. Recorded as evidence
that the result is not peculiar to this site; the citation is not pinned and must
be before a writeup carries it.

### Observed against predicted, and two results that came out of drawing it

`figures/observed_and_predicted.png`, built by
`study.figures.observed_and_predicted` from the scored forecasts and the observed
monthly series.

**A time series, not a scatter against a one-to-one line.** A scatter shows how
far predictions miss by and destroys when they miss. The finding is about which
months, so the axis has to be time.

**The whole record is drawn, with the evaluated months shaded.** Predictions
exist for **40% of the methane record and 44% of the carbon dioxide record**, and
shading rather than clipping is what makes that visible. It also makes visible
that **2021, the weakest summer in the record at 0.57 of the average year, lies
outside the evaluated window and was never forecast.** An earlier note here said
the two years climatology fails on are the two lowest-amplitude years; only 2015
of those two is evaluable at any horizon, and the figure now says so.

**One horizon, at one month.** It is the horizon most favorable to the fitted
methods, so showing that they do not follow the observations even there is a
stronger claim than showing it a year out. The forecast comparison already
carries the horizon story.

**Two prediction marks, not one.** Merging the seasonal average into the fitted
range was tried, because it would have removed the benchmark-against-model
framing altogether. It does not work: the seasonal average lies inside the fitted
range in only 63% of methane months and 40% of carbon dioxide months, and merging
widens the band by 16% and 38%. On carbon dioxide it usually sits below the
fitted range, which is why it wins, and merging would hide exactly that.

**The observed uncertainty band is a result, not decoration.** Drawn as a band in
the line's own ink following Deventer et al. (2019) figure 10. Comparing the
spread across the eight fitted models against the width of that band:

| gas | spread across the eight models | observed, two standard errors | ratio |
|---|---|---|---|
| methane | 13.26 | 3.49 | 3.8 |
| carbon dioxide | 0.148 | 0.362 | **0.41** |

**On carbon dioxide the eight models disagree with each other by less than half
the uncertainty in the quantity they are predicting.** That is the non-separation
finding arriving from a direction the error measures cannot reach, and it is
visible on the panel without a number: the green band sits inside the black one.
On methane the relationship inverts. The contrast is what the second panel is for.

**A count in the description was wrong and is corrected.** The measured flux falls
below **every fitted model in 12 of the 57 evaluated methane months, and below all
nine predictions in 9 of them**. The two counts differ because the seasonal
average is below the observation in three of those twelve, and an earlier draft
stated the first number against the second. A test pins both.

**No score is drawn on the panel.** Every number that could go there is either a
verdict the evidence does not support or a repeat of the forecast comparison. A
test asserts none appears.

**The two translucent fills were measured against each other**, since they overlap
across most of the carbon dioxide panel. The observed band at its chosen alpha
separates from the fitted fill by 0.160 in relative luminance and 17.8 under the
worst simulated deficiency, and where the two overlap the result is distinct from
each of them. Tests assert the greyscale separation and the overlap.

**What was left out.** Individual model lines; the other three benchmarks; any
horizon but one; a residual panel; markers on the observed series, which at 150
monthly points over sixteen years crowd where the line alone carries it; and an
annotation naming 2015 on the panel, which could not be placed without crossing a
series or the legend, so the description names it instead.

**A claim about the direction of the misses was cut back.** A draft description
said that when the predictions miss they almost always predict too much. They do
not: on methane 31 of 57 months are over-predictions and on carbon dioxide 43 of
85, both near a coin flip. What is true is an asymmetry in size rather than in
frequency. On methane the over-predictions carry 292 of the 447 units of total
absolute error, and ten of the largest fifteen misses are over-predictions; on
carbon dioxide there is no such asymmetry, with nine of the largest fifteen falling
the other way. The figure now says only that methane's largest misses are usually
over-predictions.

**The eight fitted things are called models throughout.** Four methods, each run
with and without lagged covariates, make eight models. "Four fitted methods"
naming the four algorithms is the one correct use of the other word and is left
alone. Swept across both figures and these notes, with a test pinning it.

**Both legends sit on the right, which costs the carbon dioxide panel a little.**
Placed on whichever side each panel left clear, they landed on opposite sides and
the eye had to relocate between panels. Holding both to the right means carbon
dioxide's legend must clear its right-hand months, which run higher than its
left-hand ones, and the panel's data now fills 72% of its height rather than 80%.
That is the price of not moving the key.

**Two things about the panel that cannot be improved without distorting them.**
The carbon dioxide uncertainty band is wide in summer, which reads as noise. It
is not: the eight widest bands all rest on the full 48 half-hour-of-day cells and
400 to 750 half-hours, and the correlation between band width and how many
half-hours support a month is −0.09. The band is wide because carbon dioxide flux
genuinely varies within a summer month. It exceeds the seasonal amplitude in only
2 of 192 months; the median band is a fifth of that amplitude. Narrowing it would
misstate how well the measurement is known.

The methane panel's right fifth is empty because the record ends in 2021 while the
shared axis runs to 2025. The alternatives are worse: separate axes would put the
same year in different places in two stacked time series, and clipping the axis at
2021 would delete 36 months of carbon dioxide observations, including three of the
widest uncertainty bands, to tidy a gap. The gap is information — it is why the
two evaluated windows differ in length — and it stays.

### What the forecasting half concludes

**Methane and carbon dioxide at this site are predictable in shape and not in
magnitude.** The seasonal pattern repeats reliably enough that a month-of-year
mean is the best forecast available at every horizon on both gases. The size of
the season varies substantially between years and without trend — the
June-to-September methane mean runs from 0.57 to 1.62 of the average year across
the thirteen years of record — and nothing in this study reaches that variation. Neither
statistical nor machine learning methods find it, per-fold screening does not
find a covariate that carries it, and the one case where a model does beat the
seasonal mean turns out to be one anomalous year in which last month's flux, and
no measured driver, was the informative quantity.

That is not a failed comparison. It is a statement about what the tower can and
cannot see, and it is the same statement the reconstruction half arrived at.
There the dominant failure was episodic: the 2011 shortfall is 91% carried by two
months whose covariates are unremarkable, matching the signature Irvin et al.
(2021) describe. Here the same thing appears as a forecasting limit, from a
completely different direction and on a different question. **The two halves of
the study share a conclusion: the between-year variation in these fluxes is not
a function of anything the site measures.** The reconstruction cannot project it
backward and the forecast cannot project it forward, for one reason.

The subsidiary answer to the question the original work asked is that ordinary
least squares and ridge are ahead of the random forest and gradient boosting in
twelve of sixteen comparisons. Corrected for serial correlation, four of those
sixteen reach p < 0.05 — three favoring the statistical methods and one, exogenous
methane at twelve months, favoring gradient boosting — and **none survives a
Bonferroni threshold of p = 0.0031 for sixteen tests**. The direction replicates
Makridakis et al. (2018) at a new site and on a different kind of series; the
margins do not support more than the direction.

## What the study concludes

The reconstruction is not the result. The result is that a model fitted on 2009
to 2019 cannot answer for the 1990s at this site, quantified along three
independent axes.

**The water table coefficient is a property of the sample rather than of the
system.** It drifts 51% monotonically as its supporting range narrows under
weighting and 38% without it, failing the stability criterion on both windows and
under both estimators. It cannot be projected 0.29 m beyond the range it was
fitted on, and 46.5% of the reconstruction period lies there.

Two of the sharper numbers this study once reported did not survive its own
check. Backward-transfer coverage of 62.5% and a water table coefficient never
distinguishable from zero were both substantially artifacts of two months of
instrument error, and both dissolve on the 115-month window. **The conclusion
does not depend on either.** Q10 is inside the published interval of 1.9 to 4.3
on every window, weighting and holdout, and moves a third as far as the water
table when the fitted range is narrowed; the water table coefficient is unstable and
monotone on every one; the reconstruction moves by at most 4.1% between windows;
and roughly half the reconstruction period lies outside the fitted range either
way. What changed is the strength of two supporting claims, not the finding.

**The direction of error is known and points the wrong way.** The band matching
the reconstruction's hydrological state indicates under-prediction of roughly
13%, and the estimate is not corrected for it because correcting would require
extrapolating the correction.

**The dominant failure is invisible to the covariates.** The 2011 shortfall is
97% carried by two months whose covariates are unremarkable, matching the
episodic signature Irvin et al. (2021) describe. Nothing in this data constrains
how often such episodes occurred before 2009.

**The forecasting half reaches the same conclusion from the opposite direction.**
Asked to predict forward rather than reconstruct backward, and given four methods
across two families with per-fold screening, nothing beats a month-of-year mean at
any horizon on either gas. These fluxes are predictable in shape and not in
magnitude: the seasonal pattern repeats, the size of the season varies from 0.57
to 1.62 of the average year without trend, and no covariate the tower measures
reaches that variation. Every temperature that survived screening is about 95%
explained by the calendar alone, and water table, the one covariate the calendar
cannot explain, correlates with nothing that is left. **The reconstruction cannot
project the between-year variation backward and the forecast cannot project it
forward, and it is one limitation rather than two.**

Deventer et al. (2019) permit merging observations from different measurement
systems subject to single-system flux uncertainty, and that permission is what
makes the merged series legitimate. It does not extend to projecting a fitted
relationship into a hydrological regime the record does not contain. The
distinction between those two operations is what this study measures.
