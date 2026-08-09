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

| Window | Months | Span | Absent from span |
|---|---|---|---|
| Fit | **117** | 2009-04 to 2019-12 (129) | 12 |
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
In covariate space standardised on the fit window, fit months sit a median 0.409
from their nearest neighbour with a 95th percentile of 0.791. Reconstruction
months sit a median 0.714 from the nearest fit month, and **110 of 230 lie
beyond that 95th percentile**, reaching 2.874. Roughly the same fraction fails
on both measures, but not the same months: falling inside every covariate's
range separately does not place a month inside the region the fit window
actually occupies.

Water table also differs between the periods in distribution, not only in range.
Tested in `src/study/stationarity.py`, the reconstruction period is wetter by
0.140 m, a standardised difference of 0.902 with Cliff's delta 0.471 and
Mann-Whitney p below 0.0001, and the result holds on anomalies from the
month-of-year mean, so it is not an artefact of month composition. Air
temperature shows no raw difference but is 1.59 °F cooler once deseasonalised
(p = 0.0009). Soil temperature and precipitation show no difference either way.

The reason is visible in the annual means. Water table sits near 413.5 to 413.6
through the 1990s and declines steadily to 413.14 to 413.18 by 2007 to 2009.
**The fit window opens in 2009, after the decline.** The model never sees the
hydrological state that prevailed through most of the period it is asked to
reconstruct. Restricting to the contrast Olson et al. (2013) drew, 1991-1999
against 2007-2011, water table falls 0.275 m with p below 0.0001, while soil
temperature, air temperature and precipitation show no significant difference.

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
at this site and reported a Q10 of 2.9 with a 95% interval of 1.9 to 4.3, an R²
of 0.88 and a root mean square error of 9.5 nmol m⁻² s⁻¹. Choosing a measured
form rather than a flexible one matters because extrapolation behaviour, not
in-sample fit, is what this study tests.

Fitted here on all 117 months, the Q10 is **2.66** by least absolute deviations
and 2.91 by least squares, and ranges 2.33 to 3.10 across the holdout fits. All
lie inside the published interval.

Water table enters clamped to the range seen in training: beyond that range the
term holds at its edge value. Deventer et al. (2019) report that the water table
response at this site is more complex than the soil temperature response and
follows neither a linear nor a log-linear form, so no functional form is
available to extrapolate with. Clamping asserts no trend where there is no
evidence, which is the conservative choice and the only one that states its
assumption legibly.

The estimator is least absolute deviations, which is maximum likelihood under
Laplace errors. Deventer et al. (2019) established that flux errors at this site
follow a Laplace rather than a Gaussian distribution, reporting a median
difference of 0.1, an interquartile range of 8.2 and a standard deviation of
8.5; that standard deviation is read as the Laplace value implied by the
interquartile range rather than as a raw second moment, an interpretation
supplied by the project owner and consistent with the two published figures,
since a Laplace distribution of standard deviation 8.5 implies an interquartile
range of 8.33. The ingestion layer reproduced the distributional finding with a
difference in the Akaike information criterion of 7,028 in favour of Laplace.
Intervals are the empirical quantiles of the training residuals, which assume no
distributional form at all, with a Laplace variant widened by each month's own
standard error.

The fit is solved as a linear program, so nothing in the estimator is
stochastic. The only stochastic step in the study is the bootstrap in
`src/study/stability.py`, whose seed is fixed at 20110801 and reported with its
results.

Weighting is by inverse variance, using the standard errors the ingestion layer
carries on each monthly mean. It is not a neutral choice: it reduces effective
sample size from 117 to 42.3 and gives July and August 1.8% and 1.3% of total
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

Unweighted, backward transfer is markedly worse: 50.2% MAPE at **62.5%
coverage** against a nominal 90%, with intervals that miss more than a third of
held-out months. Weighting repairs most of that, which was not the expected
direction given what it does to the seasonal balance of influence.

The wettest-decile test is the closest available analogue of the reconstruction
problem and the model passes it. That result is weaker than it sounds. A holdout
drawn from inside the record can only reach the record's edge: the wettest
decile extrapolates 0.05 m past its training range, against the 0.29 m the
reconstruction demands, so it covers **17% of the required extrapolation**.
Passing it rules out the cheapest failure mode and nothing more.

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

Both configurations fail, for different reasons. Unweighted, the coefficient is
not distinguishable from zero at any step and drifts 62%. Weighted, it is
comfortably non-zero but **climbs monotonically from 2.564 to 4.077**, a 59%
increase with a rank correlation against the share removed of +1.00 at p below
0.0001. The Q10 stays stable across both paths, so the instability is specific
to water table rather than general.

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
window, standardised differences are +0.15 for soil temperature, +0.07 for air
temperature, −0.10 for precipitation and +0.23 for water table. Its water table
maximum of 413.410 is below the fitted maximum of 413.460. Olson et al. (2013)
characterise 2011 as 1.3 °C warmer and 40 mm wetter than the 30-year average
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
shrink with better covariate modelling.

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
0.084 and decline monotonically. It is **not a coverage artefact**: half-hourly
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

**What cannot be resolved here.** Whether the base methane column was
reprocessed between Olson's access and the export used here. The workbook is a
2022 export carrying no data-product version stamp, and the current release is
Roman, T., Hill, A. C., Kolka, R., Griffis, T., and Deventer, J. (2025),
*AmeriFlux BASE US-MBP Marcell Bog Lake Peatland, Version 5-5*,
doi:[10.17190/AMF/1767835](https://doi.org/10.17190/AMF/1767835). Settling the
question requires either that product or Olson's original extraction, and
neither is in this repository. Olson et al. should therefore be treated as a
weak comparison rather than a benchmark.

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
midsummer day when soil temperature is maximised after 30-day smoothing. The
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
extrapolation, almost always on water table. Representative rows, g C m⁻² yr⁻¹:

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

Empirical coverage against a 90% nominal level is 89.7% in sample over the 117
fit months, 84.4% on weighted held-out backward transfer and 62.5% unweighted.
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

The joint-distance measure standardises each covariate by its standard deviation
over the fit window. A covariate that does not vary there gives a standard
deviation of zero, and dividing by it produced undefined distances. Because a
comparison against a threshold is false when either side is undefined, the
measure then reported **every month as supported**.

No published number changes, because no real covariate is constant over the fit
window. It is recorded because it is the same class of thing this study is
about: a diagnostic failing quietly toward the reassuring answer. Both
`support.joint_support` and `reconstruct._joint_distance_by_month` now drop
non-varying dimensions and raise if none remain, and tests cover both paths.

## What the study concludes

The reconstruction is not the result. The result is that a model fitted on 2009
to 2019 cannot answer for the 1990s at this site, quantified along three
independent axes.

**The water table coefficient is a property of the sample rather than of the
system.** It drifts 59% monotonically as its supporting range narrows under
weighting, and is never distinguishable from zero without it. It cannot be
projected 0.29 m beyond the range it was fitted on, and 46.5% of the
reconstruction period lies there.

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
