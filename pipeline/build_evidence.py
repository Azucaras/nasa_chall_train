"""Build the analog-year evidence from POWER, PAM and the ENSO record.

Inputs (data/processed/): regions, power_daily, pam, enso_seasonal, enso_strength_forecast.
Run the fetch_* scripts first. All the arithmetic lives in pipeline/evidence.py (pure).

Outputs (data/processed/):
    crop_year_enso.parquet     ENSO class of every crop year (+ the current one, as a forecast)
    climate_seasonal.parquet   rainfall indices per municipality x crop year, with anomalies
    yield_anomalies.parquet    detrended PAM yield anomalies per municipality x crop x year
    composites.parquet         mean anomaly by ENSO class, with n and the years behind it
    season_progress.parquet    cumulative rain this season vs climatology vs strong-El-Nino years
"""

from __future__ import annotations

import pandas as pd

from pipeline import evidence as ev
from pipeline.common import (
    PROCESSED_DIR,
    base_parser,
    load_config,
    log,
    setup_logging,
    write_parquet,
)

STRONG_BINS = ["p1.5_p2.0", "ge_p2.0"]
MODERATE_BINS = ["p0.5_p1.0", "p1.0_p1.5"]

CLIMATE_METRICS = [
    f"{part}_{m}"
    for part in ("season", "early", "late")
    for m in ("rain_mm", "cdd_days", "r20_days", "rx5_mm")
] + ["season_gwetroot", "season_tmax_c"]

# Metrics carried into composites: percent anomalies for totals, absolute for counts and means.
COMPOSITE_METRICS = {
    "season_rain_mm_anom_pct": "%",
    "early_rain_mm_anom_pct": "%",
    "late_rain_mm_anom_pct": "%",
    "early_r20_days_anom": "days",
    "late_cdd_days_anom": "days",
    "early_rx5_mm_anom_pct": "%",
    "season_gwetroot_anom": "0-1",
    "season_tmax_c_anom": "C",
}


def _read(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists():
        raise SystemExit(f"{name} missing: run the fetch_* scripts first (see README)")
    return pd.read_parquet(path)


def main() -> None:
    args = base_parser(__doc__ or "").parse_args()
    setup_logging(args.verbose)

    regions_cfg = load_config("regions.yaml")["meta"]
    cfg = load_config("analysis.yaml")
    baseline = tuple(cfg["baseline_crop_years"])
    start_month = regions_cfg["crop_year_start_month"]
    season_months = regions_cfg["season_months"]

    regions = _read("regions.parquet")
    daily = _read("power_daily.parquet")
    pam = _read("pam.parquet")
    enso = _read("enso_seasonal.parquet")
    outlook = _read("enso_strength_forecast.parquet")

    # ---- ENSO class per crop year ------------------------------------------------------------
    ce = cfg["crop_year_enso"]
    cy_enso = ev.crop_year_enso(enso, ce["reference_season"], ce["strong_classes"])
    cy_enso["forecast"] = False
    current_cy = int(ev.crop_year(daily.date.tail(1), start_month).iloc[0])
    if current_cy not in set(cy_enso.crop_year) or cy_enso.set_index("crop_year").loc[current_cy, "provisional"]:
        row = outlook[outlook.season == ce["reference_season"]]
        if row.empty:
            log.warning("no CPC outlook for %s; current crop year left unclassified", ce["reference_season"])
        else:
            cls, prob = ev.forecast_class(row.iloc[0], STRONG_BINS, MODERATE_BINS)
            cy_enso = cy_enso[cy_enso.crop_year != current_cy]
            cy_enso = pd.concat([cy_enso, pd.DataFrame([{
                "crop_year": current_cy, "enso_class": cls, "roni_ref": None,
                "roni_strength": None, "provisional": True, "forecast": True,
                "forecast_probability_pct": prob,
                "basis": f"CPC strength outlook issued {row.iloc[0].issued}, {ce['reference_season']}",
            }])], ignore_index=True)
    log.info("current crop year %d: %s", current_cy,
             cy_enso.set_index("crop_year").loc[current_cy].to_dict())

    # ---- Climate ----------------------------------------------------------------------------
    sub_seasons = {k: v for k, v in cfg["sub_seasons"].items() if k != "source"}
    climate = ev.seasonal_climate(daily, season_months, sub_seasons, cfg["rain_indices"], start_month)
    climate = ev.add_anomalies(climate, CLIMATE_METRICS, baseline)
    climate = climate.merge(cy_enso[["crop_year", "enso_class", "forecast"]], on="crop_year", how="left")

    # ---- Yield ------------------------------------------------------------------------------
    # Only crops in config/crops.yaml, each matched to the ENSO event it actually grew through:
    # winter crops harvested in PAM year Y grew during the ENSO of crop year Y + 1.
    ya = cfg["yield_anomaly"]
    crops_cfg = load_config("crops.yaml")
    offsets = crops_cfg["season_offset"]
    known = {int(k): v for k, v in crops_cfg["crops"].items()}
    enso_by_cy = cy_enso.set_index("crop_year").enso_class
    yields = []
    for code in regions.code:
        mun = pam[pam.code == code]
        area = mun[(mun.table == 1612) & (mun.variable == "area_planted_ha")]
        # Largest planted area first; that order is what the UI shows.
        main = ev.main_crops(area[["year", "crop_code", "value"]], 5, ya["min_area_share"])
        if 2711 in main:  # maize total -> use the per-harvest series from table 839 instead
            at = main.index(2711)
            main[at:at] = sorted(mun[mun.table == 839].crop_code.unique().tolist())
        for crop_code in [c for c in main if c in known]:
            spec = known[crop_code]
            s = mun[(mun.crop_code == crop_code) & (mun.variable == "yield_kg_ha") & (mun.flag == "")]
            s = s[["year", "value", "crop", "table"]].rename(columns={"value": "yield_kg_ha"})
            an = ev.yield_anomalies(s, ya["min_years"])
            if an.empty:
                continue
            offset = offsets[spec["season"]]
            yields.append(an.assign(
                code=code, crop_code=crop_code, crop_pt=spec["name_pt"], crop_en=spec["name_en"],
                season=spec["season"], crop_source=spec["source"],
                enso_crop_year=an.year + offset,
            ))
    yields = pd.concat(yields, ignore_index=True).rename(columns={"year": "crop_year"})
    yields["enso_class"] = yields.enso_crop_year.map(enso_by_cy)
    # A winter crop of the latest PAM year would map onto the forecast year: keep it out.
    forecast_years = set(cy_enso[cy_enso.forecast].crop_year)
    yields.loc[yields.enso_crop_year.isin(forecast_years), "enso_class"] = None

    # ---- Composites (observed crop years only; the forecast year is never part of the evidence)
    obs = climate[~climate.forecast.fillna(False).astype(bool)]
    comps = []
    for metric, unit in COMPOSITE_METRICS.items():
        c = ev.composite(obs, metric, ["code"])
        comps.append(c.assign(kind="climate", metric=metric, unit=unit, crop_code=None, crop=None))
    for (code, crop_code), g in yields.groupby(["code", "crop_code"]):
        c = ev.composite(g, "anomaly_pct", ["code"])
        comps.append(c.assign(kind="yield", metric="yield_anomaly_pct", unit="%",
                              crop_code=crop_code, crop=g.crop_pt.iloc[0],
                              crop_source=g.crop_source.iloc[0], season=g.season.iloc[0]))
    composites = pd.concat(comps, ignore_index=True)

    # ---- Season to date ---------------------------------------------------------------------
    season_days = sum(pd.Period(f"2001-{m:02d}").days_in_month for m in season_months)
    strong_years = cy_enso[(cy_enso.enso_class == "el_nino_strong") & ~cy_enso.forecast].crop_year.tolist()
    progress = pd.concat([
        ev.season_progress(daily, int(code), season_months[0], season_days, current_cy,
                           baseline, strong_years, start_month)
        for code in regions.code
    ], ignore_index=True)

    meta = {
        "generated_by": "pipeline/build_evidence.py",
        "rules": "config/analysis.yaml",
        "baseline_crop_years": f"{baseline[0]}-{baseline[1]}",
        "current_crop_year": str(current_cy),
    }
    write_parquet(cy_enso, "crop_year_enso.parquet", meta)
    write_parquet(climate, "climate_seasonal.parquet", {**meta, "source": "NASA POWER PRECTOTCORR, GWETROOT, T2M_MAX"})
    write_parquet(yields, "yield_anomalies.parquet", {**meta, "source": "IBGE PAM tables 1612, 839"})
    write_parquet(composites, "composites.parquet", meta)
    write_parquet(progress, "season_progress.parquet", {**meta, "source": "NASA POWER PRECTOTCORR"})

    view = composites[(composites.kind == "climate") & composites.metric.isin(
        ["early_rain_mm_anom_pct", "late_rain_mm_anom_pct", "late_cdd_days_anom"])]
    print(view.pivot_table(index=["code", "metric"], columns="enso_class", values="mean").round(1).to_string())
    print()
    soy = composites[(composites.kind == "yield") & (composites.crop_code == 2713)]
    print("Soy yield anomaly (%) by ENSO class:")
    print(soy.pivot_table(index="code", columns="enso_class", values=["mean", "n"]).round(1).to_string())


if __name__ == "__main__":
    main()
