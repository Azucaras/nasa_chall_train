# Rotation scoring

How Field Phase ranks candidate rotations for a municipality and a kind of year. Code:
[`pipeline/scoring.py`](../pipeline/scoring.py) (pure, no I/O), [`pipeline/agromet.py`](../pipeline/agromet.py)
(FAO-56 ET0), [`pipeline/build_scoring.py`](../pipeline/build_scoring.py) (assembles the inputs),
[`config/rotations.yaml`](../config/rotations.yaml) (candidates, crop parameters, calendars).

## The idea

A rotation is good or bad **for a kind of year**. The same rotation that protects a farm in a
La Niña year can hurt it in a strong El Niño year. So every candidate is scored separately for each
ENSO class — strong El Niño, weak/moderate El Niño, neutral, La Niña — and the farmer sees the
ranking for the class the current season is forecast to be (and can switch to compare).

The three priorities the farmer weights are each a **measured quantity first**, from this
municipality's own data, and only then a 0–100 score:

| Priority | Measured quantity | Better | Data |
|---|---|---|---|
| **Protect soil** | heavy-rain days (≥ 20 mm) per year that fall in months the rotation leaves the soil **bare** | lower | NASA POWER daily rain → mean heavy-rain days per calendar month in years of that ENSO class |
| **Conserve water** | crop **water deficit**, mm/yr: for each month the field is cropped, crop water use (Kc × ET0) minus that month's rain, counted only when positive | lower | ET0 by FAO-56 Penman–Monteith from POWER; Kc from FAO-56 Table 12; rain from POWER |
| **Income stability** | change in the rotation's **gross revenue** in years of that ENSO class, % | higher | IBGE PAM: recent revenue per hectare per crop, and each crop's yield anomaly in that class |

## Step by step

### 1. Calendar → months in the field (`occupancy`)

Each crop has a sowing and a harvest (or, for cover crops, termination) month per region. The months
in between are the crop's cycle; FAO-56 stages are assigned by position: first month **initial**,
second **development**, then **mid-season**, last **end**. Two crops may share only the hand-over
month (one harvested, the next sown); anything else is an impossible calendar and is rejected.

A month with no crop is **bare soil**.

### 2. Monthly climate for each ENSO class (`monthly_climate_by_class`)

From NASA POWER, 1982 to today, at the municipality's centroid: for every complete calendar month,
total rain, number of days ≥ 20 mm, and total ET0. Each month takes the ENSO class of its crop year
(Jul–Jun); the means are taken over the years of each class. ET0 needs solar radiation, which POWER
lacks for some early-1980s days, so ET0 months with any gap are left out (93 % of days have ET0).

**ET0** is the FAO-56 Penman–Monteith grass-reference evapotranspiration (equations 6–42 of
FAO-56), from POWER's Tmax, Tmin, mean relative humidity (Eq. 19), 2 m wind, solar radiation and the
grid cell's elevation. The implementation reproduces FAO-56's worked Example 18 (Ra 41.09,
ET0 3.88 mm/day) in `tests/test_agromet.py`.

### 3. The three components

**Soil** = Σ over bare months of mean heavy-rain days in that month (for the ENSO class).
A rotation with a crop or a cover crop in every month scores 0 days.

**Water** = Σ over cropped months of max(0, Kc × ET0 − rain). Kc per month: Kc ini in the sowing
month, (Kc ini + Kc mid)/2 in the development month (FAO-56's development stage is a linear rise),
Kc mid after that, Kc end in the harvest month; in a hand-over month each crop counts at half weight.
A wet December never offsets a dry March: each month stands alone.

**Income** = (Σ revenue × (1 + yield anomaly)) / (Σ revenue) − 1, over the rotation's cash crops:
- *revenue*: IBGE PAM production value ÷ harvested area, mean of the last 5 years, nominal R$;
- *yield anomaly*: the crop's mean deviation from its yield trend in years of that ENSO class (the
  same composites shown in the yield section; winter crops are matched to the ENSO they grew
  through);
- cover crops have no revenue. It is income **stability**: a rotation that earns less but loses
  nothing in El Niño years can beat one that earns more and loses a third.

### 4. Scores and total (`normalise`, `weighted_total`, `rank`)

Each component is min–max scaled across the candidates of that municipality and ENSO class:
100 = best candidate on that priority, 0 = worst (all equal → all 100). Then

```
total = (w_soil × score_soil + w_water × score_water + w_income × score_income) / (w_soil + w_water + w_income)
```

over the priorities with weight > 0. The interface's sliders set the weights (0 Ignore … 3 High) and
recompute the total in the browser with the same formula (`web/src/fieldphase/scoring.ts`); the API
also ranks for any weights: `/api/v1/municipalities/{code}/rotations?soil=3&water=1&income=1&enso_class=la_nina`.

**Missing data is never filled in.** If a cash crop has no yield history for that ENSO class
(canola in Tupanciretã: fewer than 10 PAM years), its income component is empty, the rotation gets
no total while income has weight, and the card says why. Set income to "Ignore" and it is ranked on
soil and water.

## Where every parameter comes from

| Parameter | Source | Status |
|---|---|---|
| Kc ini / mid / end | FAO-56 Table 12, read from [fao.org](https://www.fao.org/4/x0490e/x0490e0b.htm) 2026-11-14; ranges → midpoint | cited |
| ET0 method | FAO-56 Penman–Monteith, [chapters 2–4](https://www.fao.org/4/x0490e/x0490e00.htm) | cited, tested against Example 18 |
| Heavy-rain threshold 20 mm | ETCCDI R20mm (same as the evidence section) | cited |
| Rain, heavy days, ET0 inputs | NASA POWER, this municipality, by ENSO class | data |
| Revenue per hectare | IBGE PAM table 1612, last 5 years | data |
| Yield anomaly by ENSO class | IBGE PAM, linear-trend anomalies (evidence section) | data |
| Sowing / harvest months | general agronomic knowledge | **`suposicao`** — the CONAB *Calendário de Plantio e Colheita de Grãos no Brasil* (2022) is the source to check against ([PDF](https://antigo.conab.gov.br/outras-publicacoes/item/download/45710_77f0a5ee35e765e2248999f4c61e70c8)); it could not be read from the build environment (TLS certificate mismatch on CONAB's server). The UI shows the assumption warning. |
| Candidate list | crops IBGE records in each municipality, plus one cover crop per region | project choice |
| Min–max scaling, equal default weights | | project choice |

## Results for the current season (forecast: strong El Niño), equal weights

**Tupanciretã (RS)**

| # | Rotation | Soil | Water | Income | Total |
|---|---|---|---|---|---|
| 1 | Soy → oats (cover) | 0 bare-month heavy-rain days | 0 mm deficit | **+15.5 %** | 100 |
| 2 | Soy → oats (grain) | 0 | 0 | +4.4 % | 81 |
| 3 | Soy → fallow | **16.8 days** | 0 | +15.5 % | 67 |
| 4 | Maize → oats (cover) | 2.2 | 0 | −3.1 % (n = 2) | 64 |
| 5 | Soy → wheat | 3.0 | 0 | **−4.4 %** (wheat −32.5 %) | 61 |
| — | Soy → canola | 0 | 0 | no canola history | unranked |

**Switch to La Niña** and soy → wheat rises to **#2** (wheat +6.4 % in La Niña years, n = 20), soy →
grain oats becomes #1, and the cover crop drops to #3. That reversal is the point of the tool.

**Luís Eduardo Magalhães (BA)**, strong El Niño: maize → fallow 95, soy → fallow 59, soy → millet
(cover) 54, soy → sorghum 41, cotton 14. Read with care: the income numbers rest on **n = 2**
strong-El-Niño years (PAM starts in 2001 there), and the interface says so on every card.

## Limitations (also stated in the interface)

- **Water balance without soil storage.** Monthly Kc × ET0 − rain ignores water stored in the soil
  profile, so crops that finish in the dry season (cotton Apr–Jul, second-crop sorghum) look drier
  than they are. Next step: a soil-water bucket using available water capacity (SoilGrids) and
  rooting depth (FAO-56 Table 22).
- **Gross revenue, not margin.** Production costs are not included (cotton is expensive to grow).
- **Scores are relative.** Min–max scaling can turn a small absolute difference (1.0 vs 2.6 heavy-rain
  days) into a large score gap; the raw values are always shown next to the scores.
- **Calendars are assumptions** until checked against CONAB.
- **Small samples** for strong El Niño (n = 2–5) — every card shows n.
- **No within-month dry spells.** A monthly balance can hide a three-week *veranico*; the evidence
  section shows dry spells separately.
