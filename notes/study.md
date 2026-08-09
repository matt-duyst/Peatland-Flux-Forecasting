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
| **Water table** | **412.51 to 413.46** | **413.07 to 413.75** | **107 (46.5%)** |

**111 of 230 reconstruction months, 48.3%, hold at least one covariate outside
the fitted range**, and water table accounts for almost all of it. Temperature
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
| **Q10, unweighted** | **2.66** | **2.57** |
| **Q10, weighted** | **2.43** | **2.41** |
| Water table coefficient, unweighted | 1.826 | **2.385**, +30.6% |
| Water table coefficient, weighted | 2.564 | **2.704**, +5.5% |
| Clamp bounds | 412.51 to 413.46 | **413.13 to 413.46** |

Every Q10 stays inside the published interval of 1.9 to 4.3, under both
estimators and across all sixteen holdout fits, whose range is 2.33 to 2.72. The
water table coefficient steepens, and it steepens six times more without
weighting than with it, because inverse-variance weighting had already discounted
the two months to 0.28% of total weight against a 1.71% equal share.

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
as the paper's headline figure. Fitted on the 115 months, the Q10 is **2.57**
unweighted and 2.41 weighted, and it ranges **2.33 to 2.72** across the sixteen
holdout fits. On the nominal 117 it was 2.66 unweighted and 2.43 weighted.

**Every one of those values falls inside the published interval of 1.9 to 4.3**,
under both estimators and across all four holdouts, and the whole holdout range
also sits inside the 2.3 to 3.1 the paper reports across its own years. The
agreement therefore does not depend on which estimator is used or on which block
of the record is withheld. Q10 is the one coefficient in this model that behaves
as a property of the site rather than of the sample, which is the contrast the
water table result below draws.

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
sample size from 115 to 42.3 and gives July and August 1.8% and 1.3% of total
weight against an equal share of 8.5%, because high-flux months are variable
months. It was adopted because it was the most consistent configuration across
all four holdout experiments, not on principle.

## Held-out experiments

Four blocks of the fit window are withheld in turn by `src/study/holdout.py`,
each chosen to resemble the reconstruction problem. Weighted full model, 90%
nominal intervals:

| Withheld | MedAE (log) | MAPE | Coverage |
|---|---|---|---|
| Wettest decile | 0.188 | 20.2% | 0.833 |
| Coldest decile | 0.246 | 25.8% | 0.917 |
| Earliest three years | 0.232 | 31.5% | 0.844 |
| Latest three years | 0.174 | 20.5% | 0.889 |

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
monotonically as the range narrows. The Q10 stays stable across every path, so
the instability remains specific to water table.

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
| Wettest decile | unweighted | +0.143 | 0.867 | predicts low 13.3% |
| Wettest decile | weighted | +0.126 | 0.882 | predicts low 11.8% |
| Earliest three years | unweighted | −0.214 | 1.238 | predicts high 23.8% |
| Earliest three years | weighted | +0.017 | 0.983 | predicts low 1.7% |

The reconstruction period is both earlier and wetter, so the two effects apply
together. Combining them additively is unreliable: it gives a net of −0.071
unweighted and +0.143 weighted, **opposite signs**.

The additive assumption also fails a direct test. Inside the fit window the two
axes are near-independent, with a correlation between calendar time and water
table of +0.098 at p = 0.291, and the earliest three years are slightly drier
than the rest rather than wetter. But splitting the backward-transfer holdout by
water table shows the bias is not uniform:

| Water table band | Mean | Unweighted | Weighted |
|---|---|---|---|
| Driest | 413.16 | −0.492 (high 63.5%) | −0.131 (high 13.9%) |
| Middle | 413.22 | −0.194 (high 21.4%) | +0.055 (low 5.4%) |
| **Wettest** | **413.35** | **+0.074 (low 7.1%)** | **+0.148 (low 13.8%)** |

The backward-transfer bias depends on water table, so the two effects interact
and cannot be summed. The band matching the reconstruction is the wettest, and
it gives a consistent answer in both configurations: **the model is expected to
predict low by roughly 7% unweighted and 14% weighted.**

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
`src/study/residuals.py`. Of the total shortfall against observations,
September 2011 alone carries 46.7% and September with August carries **91.2%**.
Six of eleven months are under-predicted and five over-predicted; June is
over-predicted by a factor of 3.2. Against the same calendar month in other
years, September 2011 stands at **+6.07 standard deviations**, November at
+3.44 and August at +3.43.

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
CC-BY-4.0. The workbook names 65 AmeriFlux sites and none is US-MBP; no cell
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

**Six of twenty years lie inside the fitted support.** Fourteen require
extrapolation, almost always on water table. On the effective range described
under support, four years lie inside rather than six; the table below is on the
nominal range, as the reconstruction itself was. Representative rows, g C m⁻² yr⁻¹:

| Year | Support | Months outside | Estimate | Interval | Sensitivity span |
|---|---|---|---|---|---|
| 1991 | **inside** | 0 | 11.77 | 7.54 to 19.36 | **2%** |
| 1992 | **inside** | 0 | 11.05 | 7.08 to 18.18 | **2%** |
| 1994 | outside | 9 | 17.02 | 10.90 to 28.01 | 66% |
| 1997 | outside | 12 | 16.74 | 10.72 to 27.54 | **107%** |
| 1999 | outside | 9 | 17.30 | 11.08 to 28.46 | 98% |
| 2004 | **inside** | 0 | 11.20 | 7.17 to 18.42 | 8% |
| 2008 | **inside** | 0 | 8.08 | 5.17 to 13.29 | 17% |

The sensitivity span reaches 107% of the estimate in 1997: the three water table
variants disagree by more than the estimate itself. Inside-support years span 2
to 17%. The span tracks support closely, which is the demonstration working:
where the model has evidence it is nearly indifferent to the assumption, and
where it does not the assumption determines the answer.

Empirical coverage against a 90% nominal level is 89.7% in sample over the fit
months, 84.4% on weighted held-out backward transfer and 87.5% unweighted on the
115-month window, against 62.5% on the nominal window.
**No empirical coverage can be computed over the reconstruction period**,
because nothing was observed there. The held-out figures are the only evidence
about how these intervals behave away from the fit window. Irvin et al. (2021)
report that raw machine learning ensemble uncertainties are underestimated and
require calibration, which is consistent with the direction seen here.

Against the retrospective range of Olson et al. (2013), +7.8 to +15.2 ± 2.7 g C
m⁻² yr⁻¹ for 1991 to 2011, this reconstruction gives 7.78 to 17.30 across
eighteen complete years with a mean of 14.40. Both were produced by fitting a
short flux record and projecting backward, so this is method agreement and not
independent confirmation.

## The pending independent validation

Shurpali, N. J., Verma, S. B., Clement, R. J., and Billesbach, D. P. (1993),
*Seasonal distribution of methane flux in a Minnesota peatland measured by eddy
correlation*, Journal of Geophysical Research **98**, 20,649-20,655; and
Shurpali, N. J., and Verma, S. B. (1998), *Micrometeorological measurements of
methane flux in a Minnesota peatland during two growing seasons*,
Biogeochemistry **40**, 1-15. These measured the 1991 and 1992 growing seasons
at this site, seventeen years before the flux record used here begins, and are
the only genuinely independent out-of-sample validation available.

This reconstruction gives, for May to October: **1991, 9.16 g C m⁻² (5.87 to
15.08); 1992, 8.36 g C m⁻² (5.35 to 13.75).**

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

## Data caveats beyond the study windows

**The water table series steps by about 2 m at 2020-01 and never returns.** Every
month from 1990 to 2019-12 sits between 413.07 and 413.75; every month from
2020-01 to the end of the record in 2021-01 sits between 411.08 and 411.22. The
transition is a single step of −2.25 m between 2019-12 and 2020-01, with no
intervening values, and the series afterwards is as smooth as it was before.
That is the signature of a change of datum or of gauge, not of hydrology.

Nothing in this study touches it. The fit window ends 2019-12 and the
reconstruction ends 2009-03, so no fitted coefficient, holdout or reconstructed
year draws on a post-2019 value. It is recorded because it falls just outside
both windows and will be the first thing anyone extending this study meets: the
2020 and 2021 methane months cannot be added without resolving the datum first,
and a naive extension would read the step as a two-meter drawdown.

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
| Wind direction | AmeriFlux BASE version 5-5, this site | 254,111 half-hours, 2009 to 2024 |

The imagery covers 47.497 to 47.515 N and −93.500 to −93.478 W. The southern
edge is 47.497 rather than the 47.495 first wanted because the quarter-quad
holding the tower begins there, and a second scene for 220 m would have added a
seam and a second acquisition to attribute.

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
does not depend on either.** Q10 is stable and inside the published interval on
every window, weighting and holdout; the water table coefficient is unstable and
monotone on every one; the reconstruction moves by at most 4.1% between windows;
and roughly half the reconstruction period lies outside the fitted range either
way. What changed is the strength of two supporting claims, not the finding.

**The direction of error is known and points the wrong way.** The band matching
the reconstruction's hydrological state indicates under-prediction of roughly
14%, and the estimate is not corrected for it because correcting would require
extrapolating the correction.

**The dominant failure is invisible to the covariates.** The 2011 shortfall is
91% carried by two months whose covariates are unremarkable, matching the
episodic signature Irvin et al. (2021) describe. Nothing in this data constrains
how often such episodes occurred before 2009.

Deventer et al. (2019) permit merging observations from different measurement
systems subject to single-system flux uncertainty, and that permission is what
makes the merged series legitimate. It does not extend to projecting a fitted
relationship into a hydrological regime the record does not contain. The
distinction between those two operations is what this study measures.
