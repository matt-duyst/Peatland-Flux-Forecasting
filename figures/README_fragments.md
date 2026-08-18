### Monthly water table elevation at Marcell Bog Lake Peatland, Minnesota (1990 to 2019)

![Monthly water table elevation at Marcell Bog Lake Peatland, Minnesota (1990 to 2019)](figures/water_table_support.png)

**The water table runs 0.29 m past the fitted maximum, against a fitted range only 0.33 m wide**

Reconstruction means estimating methane emissions for years before measurements began in 2009, from relationships fitted on 2009 to 2019. Each point is one month's mean. The shaded band marks the 115 months the fit used. The water table fell through the 2000s, so the fit window opens after the wetter state has gone, sampling only the drier conditions. The dashed lines mark the highest and lowest water table they reached. Points beyond them lie outside anything the model has seen: 107 above in runs lasting years, six below by under 0.06 m. Those lines sit 0.33 m apart, and the reconstruction runs 0.29 m above the upper one: the excursion is nearly as wide as the whole fitted span. It stops at 2019 because precipitation, a covariate it needs, ends there.

### The flux tower at Marcell Bog Lake Peatland, Minnesota, and the directions it measures

![The flux tower at Marcell Bog Lake Peatland, Minnesota, and the directions it measures](figures/site_overview.png)

**Flux is discarded from 30 to 200 degrees, where upland forest lies, which removes 40% of the record**

Panel a is the peatland around the tower, with the wetland polygon the National Wetlands Inventory maps there and a circle at the 200 m over which the site reports its surface uniform. Panel b places the site among the FLUXNET-CH4 network: it is not one of them, so no community gap-filled product exists for it. Panel c is how often the wind blew from each direction over 2009 to 2019, the years the model was fitted on. Flux is discarded from 30 to 200 degrees, where the tower and the upland forest lie. That sector holds 45% of the half-hours that carry a wind direction and 40% of the whole record, and the published product holds no retained flux from it at all.

### Reconstructed methane emission at Marcell Bog Lake Peatland (1990 to 2008)

![Reconstructed methane emission at Marcell Bog Lake Peatland (1990 to 2008)](figures/reconstruction_series.png)

**The water table coefficient drifts as its range narrows: flat, linear, or absent (the three give 10 to 30 g C per square meter)**

Each marker is one year's emission in grams of carbon per square meter, from relationships fitted on 2009 to 2019. The three lines each assume something different about the water table beyond the range it was fitted on, and they agree only where it stays inside that range. The strip below gives the share of each year's months that fall outside it. Measurement at this peatland stopped in 1992 and did not resume until 2007, so eighteen of these twenty years can never be checked against one. Only 1991 and 1992 were measured, by Shurpali et al. (1993) and Shurpali and Verma (1998). Their published totals have not been obtained; this reconstruction predicts 9.29 and 8.49 g C for May to October.

### Monthly methane and carbon dioxide forecast error at Marcell Bog Lake Peatland

![Monthly methane and carbon dioxide forecast error at Marcell Bog Lake Peatland](figures/forecast_error_by_horizon.png)

**Four fitted methods (ordinary least squares, ridge regression, random forest and gradient boosting), each run with and without lagged environmental covariates, are compared against four simple benchmarks. Each is evaluated at forecast horizons of one to twelve months, meaning how far ahead the prediction is made. The most accurate at every horizon on both gases is the simplest: predicting each month as the average of that month in previous years. The pale band marks how far below that average a method would have to fall before the difference could be told apart from noise.**

Methane is measured in nanomoles and carbon dioxide in micromoles, so the two panels cannot be compared by eye. The blue region spans all eight fitted models. Its lower edge dips below the seasonal average at one month on both gases, and at six months on methane, though never by more than the band. Its upper edge rises above the band at three, six and twelve months: some fitted models are distinguishably worse than the average. The band is wide where the closest fitted model disagrees with the average erratically from month to month, not where the average is least certain.

### Observed and predicted monthly flux at Marcell Bog Lake Peatland

![Observed and predicted monthly flux at Marcell Bog Lake Peatland](figures/observed_and_predicted.png)

**Each month's flux is measured as an average of the half-hourly readings taken that month, drawn here in black with a shaded band showing the uncertainty in that average, drawn as two standard errors. Two predictions are drawn against it, both made a month in advance: the seasonal average, which uses the mean of that month across previous years, and a blue band spanning the highest and lowest of eight fitted models. Neither is available for most of the record, since the models need several years of history before they can forecast at all. The shaded years mark where predictions exist.**

The predictions follow the seasonal cycle, rising and falling in step with the measurements. On methane their largest misses are usually over-predictions. In 12 of the 57 evaluated methane months the flux came in below every fitted model, and in nine of those below the seasonal average too. 2015 is the clearest example: the seasonal average predicted 94 nanomoles for July and the tower measured 40. What the models miss is not when the season happens but how large it will be in a weak year. 2021, the weakest summer, lies outside the evaluated window and was never forecast. On carbon dioxide the eight models disagree by less than half the uncertainty in the measurement, which is why the blue band sits inside the black one.
