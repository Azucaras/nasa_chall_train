# Field Phase

ENSO-conditioned crop rotation advisor for the NASA Space Apps Challenge 2026
(*Field Shift: Adapting Farms with NASA Data*).

A farmer picks a Brazilian municipality; the app fills in soil, agricultural history and the current
ENSO phase automatically; the farmer weights three priorities (protect soil / conserve water / income
stability); the app returns ranked candidate rotations with an annual calendar, analog-year evidence
and a plain-language explanation of every recommendation.

## Why now

NOAA CPC's ENSO Diagnostic Discussion of 8 Oct 2026 carries an **El Nino Advisory** with the event
still strengthening: SST anomalies above +4.0 C in the eastern equatorial Pacific, Nino-3.4 at
+2.1 C, and an 83% chance of a *historic* event (3-month RONI >= +2.5 C) in Oct-Dec 2026 -- stronger
than any El Nino since 1950.

In Brazil the signal is a dipole, and that is the whole point of the tool:

- **South (Rio Grande do Sul):** excess rain Sep-Dec -- waterlogging, erosion, delayed planting.
- **North / Northeast / Centre-North (MATOPIBA):** rainfall deficit and mid-season dry spells
  (*veranicos*) -- risk to the summer crop and to the *safrinha*.

The best rotation therefore changes with the sign of the ENSO signal. Showing that is the deliverable.

## Pilot municipalities

| Region | Municipality | IBGE code | Signal |
|---|---|---|---|
| Rio Grande do Sul | Tupancireta | 4322202 | water excess |
| MATOPIBA | Luis Eduardo Magalhaes (BA) | 2919553 | water deficit |

Both codes were read from the IBGE *localidades* API, not from memory. Centroids are computed from
the IBGE municipal mesh by `pipeline/fetch_regions.py` -- never hand-typed.

## Hard rules

1. **Never invent a value.** Every number in the UI traces to a fetched dataset or to a
   `config/*.yaml` entry carrying a `source:` field.
2. **Mock data must be labelled `mock`** in the code *and* visibly in the UI. There is no
   unlabelled placeholder anywhere.
3. **Crop parameters without a citable source** get `source: suposicao` ("assumption"). That flag
   propagates through the API to a visible warning in the UI. Do not silently upgrade an assumption.
4. **Never commit credentials.** NASA Earthdata goes in `~/.netrc` or an env var; `data/` is
   gitignored and fully reproducible from the pipeline.
5. **Report validation honestly.** If the composite-vs-yield relationship in Phase 4 is weak, the
   weak number goes in the README and the UI.
6. **Before a heavy download**, fetch a small slice first and print the estimated full size.

## Conventions

- **Code, identifiers and comments: English. UI strings: Brazilian Portuguese**, held in one
  dictionary module so the presentation can be switched to English (the pitch is in English).
- **Parquet** is the interchange format between pipeline and API; `data/processed/`.
- **One fetch script per source**, idempotent, caching raw responses in `data/raw/`. Re-running must
  not re-download what is already cached unless `--refresh` is passed.
- **Scoring is pure.** `pipeline/scoring.py` does no I/O so it stays unit-testable.
- **The API always returns score components**, never just the total -- the UI must be able to open
  the arithmetic.
- Crop year runs **Jul-Jun, labelled by the harvest year**, to line up with IBGE PAM.
- Baseline climatology: **1991-2020**, recorded as Parquet metadata. SMAP only starts in 2015 and is
  labelled accordingly wherever it appears.

## Layout

```
pipeline/   fetch_* (one per source), build_* (derived products), scoring.py (pure)
api/        FastAPI over the processed Parquet
web/        React + Vite + TypeScript + MapLibre GL + Recharts
config/     regions.yaml, crops.yaml, rotations.yaml
tests/      pytest -- anomalies, scoring, parsers
data/       raw/ (cache), processed/ (Parquet) -- both gitignored
notebooks/  exploration and presentation figures
```

## Commands

`uv` manages its own Python 3.11. It was installed via winget and lives at
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`
(on PATH after a shell restart).

```bash
uv sync                      # Phase 1 deps
uv sync --extra satellite    # Phase 2+ (needs Earthdata credentials)
uv run pytest
uv run python -m pipeline.fetch_regions
uv run uvicorn api.main:app --reload
cd web && npm run dev
```

## Data sources

| What | Source | Auth |
|---|---|---|
| ENSO history 1950- | CPC ONI `cpc.ncep.noaa.gov/data/indices/oni.ascii.txt` | none |
| ENSO current | CPC RONI (HTML table, scraped + cached) | none |
| Agroclimate daily | NASA POWER `power.larc.nasa.gov/api/temporal/daily/point` | none |
| Yield / area | IBGE PAM via SIDRA table 1612 | none |
| Municipality codes & mesh | IBGE *localidades* + *malhas* APIs | none |
| Rainfall | GPM IMERG Final (`GPM_3IMERGDF`), CHIRPS | Earthdata / none |
| Root-zone soil moisture | SMAP L4 `SPL4SMGP` (2015-) | Earthdata |
| Vegetation | MODIS MOD13Q1 v061 (VIIRS VNP13 as fallback) | Earthdata |
| Evapotranspiration | MOD16A2 (OpenET does not cover Brazil) | Earthdata |
| Land use history | MapBiomas, latest collection | TBD |
| Soil texture & carbon | SoilGrids 250 m, 0-30 cm | none |

RONI is CPC's official index since Feb 2026, so it drives the *current* phase shown in the UI; the
machine-readable ONI series drives the *historical* classification. The UI labels which index backs
which number.

## Phases

- **0 Foundation** -- toolchain, layout, configs. *(current)*
- **1 MVP** -- POWER + PAM + ONI/RONI, 2 municipalities, end to end.
- **2 Satellite** -- IMERG, SMAP, MODIS, CHIRPS.
- **3 Soil, history, scale** -- SoilGrids, MapBiomas, all of RS + MATOPIBA.
- **4 Validation** -- composite water score vs observed PAM yield deviations in El Nino years.

At the end of every phase: run the tests, update the README (how to run, sources, limitations), and
state explicitly what was left undone.
