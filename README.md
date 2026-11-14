# Field Phase

**ENSO-conditioned crop rotation planning for Brazilian farms, built on NASA Earth observations.**
NASA Space Apps Challenge 2026 — *Field Shift: Adapting Farms with NASA Data*.

> **Status: Phase 1 data + evidence + interface done; rotation scoring not started.** ENSO, NASA
> POWER and IBGE PAM are ingested for both pilots, the analog-year evidence is built, and a web
> interface shows it. See [Current state](#current-state).
>
> **New here?** Read [docs/how_it_works.md](docs/how_it_works.md) — the backend explained end to
> end. Reusing the interface in another project: [web/README.md](web/README.md).

---

## The problem

As of the **12 November 2026** ENSO Diagnostic Discussion, NOAA's Climate Prediction Center has an
**El Niño Advisory** in force with the event still strengthening: sea surface temperature anomalies
above **+4.0 °C** in the eastern equatorial Pacific, Niño-3.4 at **+2.5 °C**, and a **~60 % chance of
a historic event** (3-month RONI ≥ +2.5 °C) in October–December and November–January. That would
exceed every El Niño since 1950; RONI's highest value so far is +2.40 °C (DJF 1983). The latest
official index value is RONI ASO 2026 = **+1.97 °C** (very strong).

These figures go stale every month. `pipeline/fetch_enso.py` re-reads them from CPC and stores them,
with their issue date, in `data/processed/enso_current.parquet`; the interface reads them from there.

In Brazil that signal is a **dipole**, and the dipole is the point:

| Region | El Niño effect | What it costs a farmer |
|---|---|---|
| **South** (Rio Grande do Sul) | rainfall surplus, Sep–Dec | waterlogging, erosion, delayed planting, rain at harvest |
| **North / Northeast / Centre-North** (MATOPIBA) | rainfall deficit, mid-season dry spells (*veranicos*) | summer-crop stress, failed *safrinha* |

So the rotation that protects a farm in Rio Grande do Sul this season is not the one that protects a
farm in western Bahia. **Field Phase makes that difference explicit, and shows the evidence behind it.**

The signal is already visible in the official statistics. Soybean yield in Luís Eduardo Magalhães
(BA), from IBGE's PAM survey:

| Crop year | Yield (kg/ha) |
|---|---|
| 2015 | 3 240 |
| 2016 (strong El Niño) | **2 100** — a 35 % drop |

Phase 4 tests that relationship systematically, across crops and both regions, and reports the
result whether or not it is flattering.

## What the tool does

1. The farmer picks a municipality on the map.
2. The app fills in soil texture and carbon, agricultural history, and the current ENSO phase
   and intensity — automatically, from public data.
3. The farmer weights three priorities: **protect soil**, **conserve water**, **income stability**.
4. The app returns **ranked candidate rotations**, each with an annual calendar and analog-year
   evidence — rainfall, soil moisture, NDVI and yield anomalies in strong El Niño years versus
   neutral years.
5. Every recommendation carries a plain-language explanation of *why*, and every score can be
   opened up into its components.

## Pilot municipalities

| Region | Municipality | IBGE code | Centroid (lon, lat) | Signal |
|---|---|---|---|---|
| Rio Grande do Sul | Tupanciretã | 4322202 | −54.0037, −29.0205 | water excess |
| MATOPIBA | Luís Eduardo Magalhães (BA) | 2919553 | −46.0201, −12.1984 | water deficit |

Codes come from the IBGE *localidades* API; centroids are area-weighted polygon centroids computed
from the IBGE *malhas* mesh by `pipeline/fetch_regions.py`. Neither was typed from memory.

---

## Running it

`uv` manages its own Python 3.11 — you do not need a system Python.

```bash
uv sync                                  # install Phase 1 dependencies
uv run pytest                            # run the test suite
uv run python -m pipeline.fetch_regions  # municipality boundaries + centroids (IBGE)
uv run python -m pipeline.fetch_enso     # ONI, RONI, weekly Niño, CPC discussion + strength outlook
uv run python -m pipeline.fetch_power    # daily NASA POWER at each centroid, 1981-today
uv run python -m pipeline.fetch_pam      # IBGE PAM yields, tables 1612 and 839
uv run python -m pipeline.build_evidence # seasons, anomalies, ENSO composites, season-to-date
uv run python -m api.export              # write the API responses as JSON for the web app
uv run python -m pipeline.probe_sources  # check that every data source still answers (a few KB each)
```

Then the interface (Node 18+):

```bash
cd web && npm install && npm run dev
```

Or serve the live API instead of static files: `uv run uvicorn api.main:app --reload` (docs at
`/docs`) and start the web app with `VITE_DATA_MODE=api`.

If `uv` is not found, restart your shell (winget added it to PATH) or call it at
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`.

Phase 2 onwards additionally needs the satellite stack and NASA Earthdata credentials:

```bash
uv sync --extra satellite
```

### Earthdata credentials

Not required for Phase 0 or Phase 1. From Phase 2 (IMERG, SMAP, MODIS):

1. Create a free account at <https://urs.earthdata.nasa.gov>.
2. In your profile, authorise the **GES DISC** and **NSIDC DAAC** applications.
3. Put the credentials in `~/.netrc` (or the `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`
   environment variables). **Never commit them** — `.netrc` and `.env` are gitignored.

## Layout

```
pipeline/   fetch_* (one per source), build_* (derived products), scoring.py (pure, no I/O)
api/        FastAPI over the processed Parquet
web/        React + Vite + TypeScript + MapLibre GL + Recharts
config/     regions.yaml, crops.yaml, rotations.yaml
tests/      pytest
data/       raw/ (HTTP cache), processed/ (Parquet) — both gitignored, both reproducible
notebooks/  exploration and presentation figures
```

## Data sources

| What | Source | Period | Auth |
|---|---|---|---|
| ENSO index (official) | NOAA CPC RONI, [`RONI.ascii.txt`](https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt) | 1950– | none |
| ENSO index (legacy) | NOAA CPC ONI, [`oni.ascii.txt`](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) | 1950– | none |
| ENSO weekly | NOAA CPC Niño SSTs, [`wksst9120.for`](https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for) | 1981– | none |
| ENSO alert and outlook | CPC [Diagnostic Discussion](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml), [Strength Probabilities](https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths/) (scraped) | current | none |
| Agroclimate, daily | [NASA POWER](https://power.larc.nasa.gov/) (MERRA-2) | 1981– | none |
| Yield and area | IBGE PAM, [SIDRA](https://apisidra.ibge.gov.br/) table 1612 | 1974– | none |
| Municipality codes, boundaries | IBGE *localidades* and *malhas* APIs | current | none |
| Rainfall | GPM IMERG Final `GPM_3IMERGDF`; [CHIRPS v3.0](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/) | 2000–; 1981– | Earthdata; none |
| Station weather | INMET automatic stations, `apitempo.inmet.gov.br` | varies | none (send a User-Agent) |
| Root-zone soil moisture | SMAP L4 `SPL4SMGP`, 9 km | **2015–** | Earthdata |
| Vegetation | MODIS MOD13Q1 v061, 250 m (VIIRS VNP13 as fallback) | 2000– | Earthdata |
| Evapotranspiration | MOD16A2 | 2000– | Earthdata |
| Land-use history | MapBiomas, latest collection | 1985– | TBD |
| Soil texture and carbon | SoilGrids 250 m, 0–30 cm | static | none |

**Why two ENSO indices.** RONI has been CPC's official index since February 2026 (NWS PIS 26-05), and
it is published as a plain-text file like ONI, so RONI drives both the current phase and the
historical classification of analog years. ONI is kept alongside for comparison with older
literature. Episode and strength rules are CPC's own and live in `config/enso.yaml` with their
sources.

**Scope is Brazil only.** Every source is Brazilian or global with coverage of Brazil. US-only
datasets (PRISM, NRCS soils, CropScape, NLCD, NAIP, CoCoRaHS, USGS water data) were reviewed and
excluded; the review and their replacements are in [docs/data_sources.md](docs/data_sources.md).

## Ground rules

These are enforced in review, and in `CLAUDE.md`:

1. **No invented values.** Every number in the interface traces to a fetched dataset or to a
   `config/*.yaml` entry carrying a `source:` field.
2. **Mock data is labelled `mock`** in the code *and* visibly in the interface. There are no
   unlabelled placeholders.
3. **Crop parameters without a citable source** are marked `source: suposicao` and that flag
   propagates to a visible warning in the UI. Assumptions are never silently promoted to facts.
4. **Credentials are never committed.** `data/` is gitignored and fully reproducible.
5. **Validation is reported honestly** — including a weak result.
6. **TLS verification is never disabled.** Where a TLS-inspecting proxy breaks `certifi`,
   `pipeline/common.py` routes verification through the OS trust store via `truststore`.

## Current state

**Done (Phase 0):**

- `uv` toolchain with a managed Python 3.11.17; dependencies resolved and locked.
- Project layout, `CLAUDE.md`, `.gitignore`.
- `config/regions.yaml` — pilot regions, ENSO signals, hazards, climatology baseline (1991–2020),
  crop-year convention (Jul–Jun, labelled by harvest year, to align with PAM).
- `pipeline/common.py` — config loading, caching HTTP fetcher, Parquet writer that embeds
  provenance in the file's key-value metadata.
- `pipeline/fetch_regions.py` → `data/processed/regions.parquet`.
- 14 tests passing.
- All five upstream endpoints verified reachable and returning the expected payloads.

**Done (Phase 1, ENSO slice):**

- `pipeline/fetch_enso.py` → `enso_seasonal.parquet` (ONI + RONI, CPC episode phases, RONI strength,
  crop year), `enso_weekly.parquet`, `enso_current.parquet` (latest discussion + index values),
  `enso_strength_forecast.parquet` (CPC strength probabilities, next 9 seasons).
- `config/enso.yaml`: CPC's episode, strength and "historic" thresholds, each with its source.
- `config/sources.yaml` + `pipeline/probe_sources.py`: a registry of the 14 Brazilian / global
  sources and a cheap reachability check.
- 42 tests passing (including a guard that every registered source covers Brazil).

**Done (Phase 1, POWER + PAM + evidence + interface):**

- `fetch_regions` falls back to IBGE's 2025 per-state municipal shapefile when the *malhas* API is
  unreachable, and writes `regions.geojson` for the map.
- `fetch_power` → `power_daily.parquet`: 10 daily variables at each centroid, 1981 to the latest
  published day (~3-day lag).
- `fetch_pam` → `pam.parquet`: SIDRA table 1612 (all temporary crops) and 839 (maize 1st / 2nd
  harvest), 1974–2025, with SIDRA's symbols kept as flags.
- `pipeline/evidence.py` (pure) + `build_evidence` → crop-year ENSO labels, ETCCDI rain indices per
  season, 1991–2020 anomalies, detrended yield anomalies, composites by ENSO class with n and
  years, and season-to-date rain vs climatology and strong-El-Niño years.
- `config/analysis.yaml` (method choices, each sourced or marked *project choice*) and
  `config/crops.yaml` (SIDRA codes; summer/winter season marked `suposicao`).
- `api/` — FastAPI over the processed data (contract v1) and a static JSON exporter.
- `web/` — React + Vite + TypeScript + Recharts + MapLibre interface, pt-BR with an English switch,
  light/dark, every chart with a table view; the `web/src/fieldphase/` kit is portable.
- 79 tests passing, including an end-to-end pipeline→API contract test on synthetic data.

**First results (n is small — see limitations):**

| Strong El Niño years vs normal | Tupanciretã (RS) | Luís Eduardo Magalhães (BA) |
|---|---|---|
| Rain Sep–Dec | +40 % (n=5) | −18 % (n=5) |
| Longest dry spell Jan–Apr | +1.3 days (n=5) | +4.5 days (n=5) |
| Soybean yield vs trend | +15.5 % (n=5) | −16 % (n=2) |
| Wheat yield vs trend | −32.5 % (n=5) | — |
| Sorghum yield vs trend | — | −20 % (n=2) |
| Rain since 1 Sep 2026 | 624 mm vs 448 mm normal | 93 mm vs 169 mm normal |

**Not started:** rotation scoring (`pipeline/scoring.py`, `config/rotations.yaml`), CHIRPS, Phases
2–4.

### Known limitations

- Centroids are computed in degrees rather than an equal-area projection. At municipality scale the
  error is far below NASA POWER's ~0.5° grid, so it cannot affect which cell is sampled.
- A polygon centroid can fall outside a sufficiently concave municipality. It does not for either
  pilot, but this needs a point-in-polygon check before Phase 3 scales to every municipality in
  Rio Grande do Sul and MATOPIBA.
- SMAP begins in 2015, so its anomalies cannot use the 1991–2020 baseline. Wherever SMAP appears it
  will be labelled with its own shorter baseline.
- The two scraped CPC pages are parsed by structure and fail loudly (`LayoutChanged`) if CPC
  redesigns them; that is a hard stop, never a silent guess.
- From outside Brazil, IBGE *localidades*/*malhas* reset the connection; `fetch_regions` then uses
  the per-state shapefile from `geoftp.ibge.gov.br`. SIDRA is unaffected.
- **Small samples.** LEM's PAM series starts in 2001, so it has only two strong El Niño years
  (2010, 2016). The UI attaches a caution to any composite with fewer than 3 years.
- NASA POWER values are ~50 km grid-cell averages from reanalysis (MERRA-2; GEOS-IT for recent
  days), not station readings; the two model streams are joined without homogenisation.
- Yield anomalies use a single linear trend per crop; a crop whose technology trend bent (e.g. the
  LEM soy expansion) is only approximately detrended.
- Crop seasons in `config/crops.yaml` (which ENSO year a winter crop is compared with) are
  `suposicao` until the CONAB crop calendar is cited; the UI shows that warning.
- `config/regions.yaml` describes LEM as "soy-safrinha maize and cotton", but PAM records 2nd-crop
  maize there only in 2012–2015 (~1 000 ha) and none since; the main companions of soy are cotton,
  sorghum, 1st-crop maize and beans. The *safrinha_failure* hazard label may need revisiting.
- The map basemap uses OpenStreetMap tiles (fine for a demo, not for heavy traffic); set
  `VITE_BASEMAP_TILES` to another provider for production.
- MapBiomas access is unresolved — the latest collection may require manual download or Earth
  Engine. To be settled in Phase 3.
