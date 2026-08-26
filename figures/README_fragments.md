### Monthly water table elevation at Marcell Bog Lake Peatland (1990 to 2019)

![Monthly water table elevation at Marcell Bog Lake Peatland (1990 to 2019)](figures/water_table_support.png)

**Water table is one of the two measurements the reconstruction reads, and methane rises as it rises. The model only ever saw it across a 0.33 m band, because the flux record opens in 2009 after a decade of decline. Projecting back to 1990 asks for 0.29 m above that band, an excursion nearly as wide as the range the model was fitted on.**

Each point is one month's mean, and the shaded band marks the 115 months the fit used. The dashed lines are the highest and lowest water table those months reached. Everything beyond them is a value the model was never shown: 107 months above, in runs of up to 44 consecutive months from 1995 to 1998, and six below by no more than 0.06 m. The series stops in 2019 because precipitation, which the model also needs, ends there.

### The flux tower and the wind directions it measures at Marcell Bog Lake Peatland

![The flux tower and the wind directions it measures at Marcell Bog Lake Peatland](figures/site_overview.png)

**The tower stands in a poor fen in north-central Minnesota (47.5051° N, 93.4893° W), measuring carbon dioxide since 2007 and methane since 2009. Because upland forest lies to the east and southeast, flux arriving from 30° to 200° is discarded before publication, which removes 40% of the record.**

Panel a is the peatland around the tower. The white outline is the wetland the National Wetlands Inventory maps there, and the circle marks the 200 m within which the site reports its surface uniform, the assumption eddy covariance rests on. Panel b places the site among FLUXNET-CH4, the synthesis it was left out of, so no community gap-filled product exists for it. Panel c is how often the wind blew from each direction over 2009 to 2019, the years the model was fitted on. The hatched bars are the discarded sector, where the tower and the upland forest lie: they are 45% of the half-hours carrying a wind direction, and the published product holds no retained flux from them at all. The exclusion predates publication, so this study inherits it.

### Reconstructed methane emission at Marcell Bog Lake Peatland (1990 to 2008)

![Reconstructed methane emission at Marcell Bog Lake Peatland (1990 to 2008)](figures/reconstruction_series.png)

**Environmental records at this site reach back to 1990 while the flux record begins in 2009, so relationships fitted on the measured years can be projected into the earlier ones. Beyond the range the fit covered, the water table term has to be assumed rather than estimated, and the three assumptions drawn here give annual totals from 8 to 30 grams of carbon per square meter.**

Each marker is one year's emission in grams of carbon per square meter, from relationships fitted on the measured years (2009 to 2019). Beyond the fitted range the three take different views: the water table response either stops rising (flat), continues at the rate the fit found (linear), or is dropped altogether (absent). They agree closely where the water table stays inside that range, and fan apart where it does not. Almost none of this can be checked, because methane measurement stopped in 1992 and did not resume until 2009, leaving seventeen of these nineteen years with nothing to compare against. The exceptions are 1991 and 1992, measured by Shurpali and colleagues, whose published totals have not been obtained.

### Monthly methane and carbon dioxide forecast error at Marcell Bog Lake Peatland

![Monthly methane and carbon dioxide forecast error at Marcell Bog Lake Peatland](figures/forecast_error_by_horizon.png)

**Four fitted methods (ordinary least squares, ridge regression, random forest and gradient boosting), each run with and without lagged environmental covariates, are compared against four simple benchmarks: the average of that month in previous years, the same month last year, last month carried forward, and the same month last year adjusted for trend. The first two are drawn here. Each method is evaluated over 2013 to 2020 for carbon dioxide and 2014 to 2020 for methane, at forecast horizons of one to twelve months, meaning how far ahead the prediction is made. The pale band marks how far from the first of those a method would have to fall, in either direction, before the difference could be told apart from noise.**

Each panel is one gas. The green region covers all eight fitted models: four methods, each run with and without lagged environmental measurements. It sits mostly above the seasonal average, and where it reaches beneath, the difference stays inside the band; where its upper edge rises above the band, some fitted models are measurably worse than the average. The band is wide where the closest fitted model disagrees with the average erratically from month to month, not where the average is least certain. Methane is in nanomoles and carbon dioxide in micromoles, so the panels do not compare by eye.

### Observed and predicted monthly flux at Marcell Bog Lake Peatland

![Observed and predicted monthly flux at Marcell Bog Lake Peatland](figures/observed_and_predicted.png)

**Each month's flux is measured as an average of the half-hourly readings taken that month, drawn here in black with a shaded band showing the uncertainty in that average, drawn as two standard errors. Two predictions are drawn against it, both made a month in advance: the seasonal average, which uses the mean of that month across previous years, and a green band spanning the highest and lowest of eight fitted models. Neither is available for most of the record, since the models need several years of history before they can forecast at all. The shaded years mark where predictions exist.**

The predictions follow the seasonal cycle, rising and falling in step with the measurements. On methane their largest misses are usually over-predictions. In 12 of the 57 evaluated methane months the flux came in below every fitted model, and in nine of those below the seasonal average too. 2015 is the clearest example: the seasonal average predicted 94 nanomoles for July and the tower measured 40. What the models miss is not when the season happens but how large it will be in a weak year. 2021, the weakest summer, lies outside the evaluated window and was never forecast. On carbon dioxide the eight models disagree by less than half the uncertainty in the measurement, which is why the green band sits inside the black one.

### Which measurements the models used at Marcell Bog Lake Peatland (by forecast horizon)

![Which measurements the models used at Marcell Bog Lake Peatland (by forecast horizon)](figures/measurements_used_across_forecast_horizons.png)

**Each model predicts a fixed distance ahead, from one month to twelve, and was rebuilt every month as the record grew. Each time it chose which of the measurements to use, and the green bars show how often each was chosen, from never to every rebuild. The grey bars show something different: how much of that measurement can be predicted from the date alone, which is high for temperature and near zero for the water table. Reading the two together, what the models chose most often are the measurements the date already predicts, and the one thing the date cannot predict is the one they chose least.**

Two marks stand where a number would mean nothing. The date question does not apply to the flux's own past values, which are not measurements taken at the site. Last month's flux is unavailable to a model forecasting three or more months ahead. Where a grey bar does stand, it is what three seasonal terms account for: 95% of soil and air temperature, and about 5% of the water table. The sharpest case is carbon dioxide three months ahead, where the models chose none of the four measurements in any rebuild and kept only the flux's own value from a year earlier.

### The water table coefficient refitted on drier months at Marcell Bog Lake Peatland

![The water table coefficient refitted on drier months at Marcell Bog Lake Peatland](figures/coefficient_stability.png)

**The model was fitted five times, each on a smaller set of months: first all 115, then the same months with the wettest tenth removed, and on to the wettest two fifths. The water table coefficient is how much predicted emission changes per meter of water table, and each point is what that coefficient came out as, placed at the wettest month still in the fit. It climbs at every step, while the soil temperature coefficient beside it moves a third as far. A coefficient that changes when its range of water table shrinks is describing the months it was fitted on rather than the peatland, so it cannot be carried out along the arrow, where the reconstruction needs it.**

The same analysis is drawn twice, once weighting each month by how well it was measured and once not. Both fail and neither is the better treatment: weighted, the coefficient rises 51%, from 2.704 to 4.077; unweighted, 38%, from 2.385 to 3.299. Every step's range overlaps the first, so no single step is decisive, and the evidence is that it climbs at all four and never once falls. The soil temperature coefficient moves 16% along the same path, and only without weighting is it flat.

### Prediction error by year at Marcell Bog Lake Peatland (2013 to 2019)

![Prediction error by year at Marcell Bog Lake Peatland (2013 to 2019)](figures/prediction_error_by_year.png)

**Each panel is one evaluated year. Each point is one month, placed at the middle of what the eight fitted methods predicted for it. Prediction error is how far a prediction fell from what was measured. It is taken here as the measurement minus the prediction, so a point above the zero line was predicted too low. The grey points are the months of every other year, repeated behind every panel. Carbon dioxide runs negative because the peatland takes up more carbon than it releases, and methane runs positive because peatlands emit it. Every panel in a row shares its axes.**

Across every evaluated year the methods fail in much the same way, missing by similar amounts and in similar directions regardless of which year they are predicting. Methane in 2015 is the one exception, and it differs twice over: its months are all small ones, so a weak season holding no large months puts its points entirely in the lower half of the axis, and its months are also missed about 1.7 times as badly as months of the same size across the record.

### The seasonal cycle in monthly flux at Marcell Bog Lake Peatland

![The seasonal cycle in monthly flux at Marcell Bog Lake Peatland](figures/seasonal_cycle.png)

**Each column is one gas and each row is one part of its record. The middle row is one average shape for the whole record (the same twelve values repeated every year). The bottom row is what the measurements leave once that shape is taken out. It is where the size of each season lives. Nothing tested here predicted it: eight fitted models, four benchmarks and four measured drivers.**

What the repeating shape leaves is half the variation in the record: 0.51 of the measurements' spread on methane and 0.53 on carbon dioxide. The shape accounts for the rest, 74% of the variance on methane and 71% on carbon dioxide. The size of the season is what varies: methane's swing from lowest to highest month runs 33.7 to 150.6 across the years, a factor of 4.5, and carbon dioxide's 0.8 to 2.4, a factor of 3.0, neither of them trending (p = 0.215 and 0.505). The level was tested for a trend as well, and neither gas has one, so nothing was removed for it. This shape is fitted on every observed month, which is not what the forecast benchmark does: that one is rebuilt inside each fold from the months up to it.

### Which months each measurement and each analysis cover at Marcell Bog Lake Peatland

![Which months each measurement and each analysis cover at Marcell Bog Lake Peatland](figures/covariate_availability.png)

**Each row in the upper block is one measurement, and the bar covers the months it exists. They are ordered by where each record ends, latest first. The environmental records begin nineteen years before either flux does, which is the room the reconstruction works in. The rows below are what each analysis covers: the months the model used, and the months its forecasts were checked on. Those spans were chosen from what was available rather than being facts about the site. The study's boundaries fall where the shortest records end.**

Air temperature and precipitation stop at the end of 2019. That ends the months the model could learn from, and leaves 60 months of methane the tower recorded but the model cannot use. The check on forecasts stops in 2020 for the same reason, four years short of the flux, since the models that use the drivers cannot run past them. It also cannot begin until 48 months of flux have accumulated, which for methane took 62 calendar months because of the gaps in 2013 and 2014. The seasonal benchmarks alone reach 2024 on both gases. The two hollow marks are decisions rather than absences.

### Diagnostic check on model errors at Marcell Bog Lake Peatland (2009 to 2019)

![Diagnostic check on model errors at Marcell Bog Lake Peatland (2009 to 2019)](figures/residual_distribution_check.png)

**This is a quantile-quantile plot, which compares the errors the model made against the errors a named distribution predicts, on a log scale. Points falling on the 1:1 line are errors matching the distribution exactly; the band covers all 115 points at once, so a single point outside it is enough to say the distribution does not hold. The weighted fit counts a month resting on many measurements more heavily than one resting on few, and the study runs both throughout.**

Fitting by least absolute deviations is optimal when errors follow a Laplace distribution, which is why this study chose it. Tested directly, the errors are equally consistent with Laplace and with Gaussian, so the choice is not supported by the model's own residuals. The published Laplace result came from comparing two instruments against each other, which is a different quantity. Least absolute deviations remains robust either way, and the study's intervals are empirical rather than distributional, so nothing downstream changes.
