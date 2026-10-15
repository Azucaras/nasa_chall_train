# Field Phase

**ENSO-conditioned crop rotation planning for Brazilian farms, built on NASA Earth observations.**
NASA Space Apps Challenge 2026 — *Field Shift: Adapting Farms with NASA Data*.

> **Status: Phase 0 complete (foundation).** No climate or yield data has been ingested yet. The
> only data product that exists is `regions.parquet`. See [Current state](#current-state).

---

## The problem

As of **8 October 2026**, NOAA's Climate Prediction Center has an **El Niño Advisory** in force with
the event still strengthening: sea surface temperature anomalies above **+4.0 °C** in the eastern
equatorial Pacific, Niño-3.4 at **+2.1 °C**, and an **83 % chance of a historic event** (3-month
RONI ≥ +2.5 °C) during October–December 2026 — which would exceed every El Niño on record since 1950.

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
uv run python -m pipeline.fetch_regions  # resolve municipalities, compute centroids
```

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
| ENSO history | NOAA CPC ONI, [`oni.ascii.txt`](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) | 1950– | none |
| ENSO current phase | NOAA CPC [RONI](https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/) | 1950– | none |
| Agroclimate, daily | [NASA POWER](https://power.larc.nasa.gov/) (MERRA-2) | 1981– | none |
| Yield and area | IBGE PAM, [SIDRA](https://apisidra.ibge.gov.br/) table 1612 | 1974– | none |
| Municipality codes, boundaries | IBGE *localidades* and *malhas* APIs | current | none |
| Rainfall | GPM IMERG Final `GPM_3IMERGDF`; CHIRPS | 2000–; 1981– | Earthdata; none |
| Root-zone soil moisture | SMAP L4 `SPL4SMGP`, 9 km | **2015–** | Earthdata |
| Vegetation | MODIS MOD13Q1 v061, 250 m (VIIRS VNP13 as fallback) | 2000– | Earthdata |
| Evapotranspiration | MOD16A2 | 2000– | Earthdata |
| Land-use history | MapBiomas, latest collection | 1985– | TBD |
| Soil texture and carbon | SoilGrids 250 m, 0–30 cm | static | none |

**Why two ENSO indices.** RONI has been CPC's official index since February 2026, so it drives the
*current* phase shown in the interface. Only the ONI series is published in a machine-readable file,
so it drives the *historical* classification of analog years. The interface labels which index backs
which number.

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

**Not started:** everything that touches climate or yield data — Phases 1 through 4. There is no
API, no web interface, and no scoring code yet.

### Known limitations

- Centroids are computed in degrees rather than an equal-area projection. At municipality scale the
  error is far below NASA POWER's ~0.5° grid, so it cannot affect which cell is sampled.
- A polygon centroid can fall outside a sufficiently concave municipality. It does not for either
  pilot, but this needs a point-in-polygon check before Phase 3 scales to every municipality in
  Rio Grande do Sul and MATOPIBA.
- SMAP begins in 2015, so its anomalies cannot use the 1991–2020 baseline. Wherever SMAP appears it
  will be labelled with its own shorter baseline.
- MapBiomas access is unresolved — the latest collection may require manual download or Earth
  Engine. To be settled in Phase 3.
