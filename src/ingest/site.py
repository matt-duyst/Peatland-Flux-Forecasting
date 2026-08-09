"""Site identity, instrument constants and published reference values.

Flux data comes from the AmeriFlux BASE product for US-MBP. BASE is AmeriFlux's
standardised half-hourly product; its variable names carry a horizontal,
vertical and replicate qualifier suffix, so FCH4_1_1_1 and FCH4_1_1_2 are two
replicates at the same position while unqualified FCH4 is the site-aggregated
series.

Instrument, threshold and validation constants are those published in
Deventer et al. (2019), which characterises the eddy covariance
instrumentation at this site.
"""

from __future__ import annotations

SITE_ID = "US-MBP"
SITE_NAME = "Marcell Bog Lake Peatland"
LATITUDE = 47.505
LONGITUDE = -93.489
LOCATION = "USDA Forest Service Marcell Experimental Forest, Minnesota, USA"

#: The same peatland appears in the literature under two names. AmeriFlux
#: registers it as Marcell Bog Lake Peatland; it is also called Bog Lake Fen.
#: Both refer to this site.
SITE_NAME_ALTERNATE = "Bog Lake Fen"

#: Wetland class, following the scheme of Delwiche et al. (2021), which treats
#: bog and fen as distinct. The evidence favours fen. AmeriFlux carries "Bog" in
#: the registered name but describes the site as a fen. Deventer et al. (2019)
#: report the peatland as poorly minerotrophic to oligotrophic, with a mean pore
#: water pH of 4.5 over a range of 3.8 to 5.3. Minerotrophic means fed by
#: groundwater that has contacted mineral soil, which is the property separating
#: a fen from an ombrotrophic, precipitation-fed bog, and that pH range sits
#: above the strongly acidic values typical of bogs. The classification is an
#: inference from these two descriptions, not a value recorded in a site
#: database: US-MBP does not appear in the FLUXNET-CH4 Version 1.0 metadata.
WETLAND_CLASS = "Fen"
WETLAND_CLASS_QUALIFIER = "poor fen"
PORE_WATER_PH_MEAN = 4.5
PORE_WATER_PH_RANGE = (3.8, 5.3)

DATA_PRODUCT_DOI = "10.17190/AMF/1767835"
DATA_CITATION = "Roman, Kolka, Griffis and Deventer (2022), AmeriFlux BASE US-MBP"

REFERENCE_DOI = "10.1016/j.agrformet.2019.107638"
REFERENCE_CITATION = (
    "Deventer et al. (2019), Agricultural and Forest Meteorology 278, 107638"
)

FCH4_UNITS = "nmol m-2 s-1"

#: TGA-100A is the closed-path trace gas analyser; LI-7700 is the open-path
#: methane analyser. Both operated at this site between 2015 and 2018.
ANALYZER_BY_COLUMN = {
    "FCH4": "site_aggregated",
    "FCH4_1_1_1": "TGA-100A",
    "FCH4_1_1_2": "LI-7700",
}
TGA_COLUMN = "FCH4_1_1_1"
LI7700_COLUMN = "FCH4_1_1_2"
BASE_COLUMN = "FCH4"

#: Column-name slugs for per-analyser columns in derived output. Single source
#: of truth: every module naming a per-analyser column resolves it through
#: ``analyzer_slug`` rather than embedding a raw label.
ANALYZER_SLUG = {
    "site_aggregated": "site_aggregated",
    "TGA-100A": "tga100a",
    "LI-7700": "li7700",
}
SLUGS = tuple(ANALYZER_SLUG.values())
FRACTION_COLUMNS = tuple(f"frac_{slug}" for slug in SLUGS)


def analyzer_slug(label: str) -> str:
    """Slug for an analyser label, raising on any label not in ANALYZER_SLUG.

    Silently passing an unknown label through would produce a per-analyser
    column set that no longer sums to one while still looking well formed.
    """
    try:
        return ANALYZER_SLUG[label]
    except KeyError:
        known = ", ".join(sorted(ANALYZER_SLUG))
        raise ValueError(f"unknown analyser label {label!r}; known labels: {known}") from None

#: Flux detection limit, nmol m-2 s-1, from Deventer et al. (2019).
DETECTION_LIMIT = 3.0
DETECTION_LIMIT_UNCERTAINTY = 2.0

#: Deventer et al. (2019) extrapolate a daily value only from days holding at
#: least this many valid half-hours, and test thresholds from 8 to 16.
MIN_HALFHOURS_PER_DAY = 8
DAILY_THRESHOLDS = (8, 12, 16)

#: Paired-analyser statistics published by Deventer et al. (2019), for the
#: difference TGA-100A minus LI-7700. Sigma is the Laplace standard deviation.
PUBLISHED_PAIRED_STATS = {"median": 0.1, "sigma": 8.5, "iqr": 8.2, "skewness": 0.32}

#: Published reduced major axis regression of LI-7700 on TGA-100A.
PUBLISHED_RMA = {"slope": 1.08, "slope_se": 0.02, "intercept": -3.0, "intercept_se": 0.8}
PUBLISHED_TGA_RETAINED = 15033
PUBLISHED_LI7700_START = "2015-03"

#: Published annual emissions, g-CH4 m-2 yr-1, and their total uncertainty.
PUBLISHED_ANNUAL_BUDGET = {2015: 14.3, 2016: 19.0, 2017: 20.0}
PUBLISHED_BUDGET_UNCERTAINTY_PCT = (7, 17)

#: One half-hour at 1 nmol m-2 s-1 expressed as g-CH4 m-2.
MOLAR_MASS_CH4 = 16.043
SECONDS_PER_HALFHOUR = 1800
NMOL_S_TO_G_PER_HALFHOUR = 1e-9 * MOLAR_MASS_CH4 * SECONDS_PER_HALFHOUR

SEED = 20150317
