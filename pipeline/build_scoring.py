"""Score the candidate rotations of every municipality, for every ENSO class.

Inputs (data/processed/): regions, power_daily, pam, crop_year_enso, composites -- so run the
fetch_* scripts and build_evidence first. Rules: config/rotations.yaml, config/analysis.yaml.
All arithmetic is in pipeline/scoring.py (pure) and pipeline/agromet.py (FAO-56 ET0).

Steps:
1. Daily reference ET0 (FAO-56 Penman-Monteith) from POWER at each centroid.
2. Monthly rain, heavy-rain days (>= 20 mm) and ET0 per ENSO class (complete months only).
3. Recent revenue per hectare per crop from PAM (production value / harvested area, last N years).
4. Yield anomaly per crop and ENSO class from the composites built by build_evidence.
5. scoring.score_rotations for each municipality x ENSO class.

Outputs (data/processed/):
    monthly_climate_by_class.parquet   code, enso_class, month, rain_mm, heavy_days, et0_mm, n_years
    rotation_scores.parquet            code, enso_class, rotation_id, result (JSON with every number)
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from pipeline import agromet, scoring
from pipeline import evidence as ev
from pipeline.common import (
    PROCESSED_DIR,
    base_parser,
    load_config,
    log,
    setup_logging,
    write_parquet,
)

ENSO_CLASSES = ["el_nino_strong", "el_nino_moderate", "neutral", "la_nina"]


def daily_et0(daily: pd.DataFrame, regions: pd.DataFrame) -> pd.Series:
    lat = daily.code.map(regions.set_index("code").centroid_lat)
    ea = agromet.actual_vapour_pressure_rh_mean(daily.T2M_MAX, daily.T2M_MIN, daily.RH2M)
    out = np.full(len(daily), np.nan)
    for code, idx in daily.groupby("code").groups.items():
        d = daily.loc[idx]
        out[np.asarray([daily.index.get_loc(i) for i in idx])] = agromet.et0_penman_monteith(
            d.T2M_MAX, d.T2M_MIN, d.ALLSKY_SFC_SW_DWN, d.WS2M, ea.loc[idx],
            float(lat.loc[idx].iloc[0]), d.date.dt.dayofyear, float(d.elevation_m.iloc[0]),
        )
    return pd.Series(out, index=daily.index)


def revenue_per_ha(pam: pd.DataFrame, code: int, years: int) -> dict[int, float]:
    """Mean of production value (thousand R$) / harvested area over the last ``years`` PAM years."""
    p = pam[(pam.code == code) & (pam.table == 1612) & (pam.flag == "")]
    last = int(p.year.max())
    p = p[p.year > last - years]
    w = p.pivot_table(index=["crop_code", "year"], columns="variable", values="value").reset_index()
    w = w[(w.get("area_harvested_ha", 0) > 0) & w.get("production_value").notna()]
    w["rs_ha"] = w.production_value * 1000 / w.area_harvested_ha
    return {int(k): float(v) for k, v in w.groupby("crop_code").rs_ha.mean().items()}


def anomalies(composites: pd.DataFrame, code: int, enso_class: str) -> dict[int, tuple[float | None, int]]:
    y = composites[(composites.kind == "yield") & (composites.code == code) & (composites.enso_class == enso_class)]
    return {int(r.crop_code): (None if pd.isna(r["mean"]) else float(r["mean"]), int(r.n)) for _, r in y.iterrows()}


def main() -> None:
    args = base_parser(__doc__ or "").parse_args()
    setup_logging(args.verbose)
    cfg = load_config("rotations.yaml")
    heavy_mm = load_config("analysis.yaml")["rain_indices"]["heavy_day_mm"]

    regions = pd.read_parquet(PROCESSED_DIR / "regions.parquet")
    daily = pd.read_parquet(PROCESSED_DIR / "power_daily.parquet")
    pam = pd.read_parquet(PROCESSED_DIR / "pam.parquet")
    cy = pd.read_parquet(PROCESSED_DIR / "crop_year_enso.parquet")
    comps = pd.read_parquet(PROCESSED_DIR / "composites.parquet")

    daily["ET0"] = daily_et0(daily, regions)
    log.info("ET0: %.0f%% of days computable (solar radiation gaps elsewhere)", 100 * daily.ET0.notna().mean())
    clim = ev.monthly_climate_by_class(daily, cy, heavy_mm)

    rows = []
    for r in regions.itertuples():
        code, region = int(r.code), r.region_id
        rev = revenue_per_ha(pam, code, cfg["meta"]["revenue_years"])
        calendar = {k: v for k, v in cfg["calendars"][region].items() if k != "source"}
        for cls in ENSO_CLASSES:
            c = clim[(clim.code == code) & (clim.enso_class == cls)].set_index("month")
            climate = {
                "heavy_days": c.heavy_days.to_dict(),
                "et0": c.et0_mm.to_dict(),
                "rain": c.rain_mm.to_dict(),
            }
            results = scoring.score_rotations(cfg["rotations"][region], cfg["crops"], calendar, climate,
                                              rev, anomalies(comps, code, cls))
            n_years = int(c.n_years.min()) if len(c) else 0
            for res in results:
                rows.append({"code": code, "enso_class": cls, "rotation_id": res["id"], "n_climate_years": n_years,
                             "result": json.dumps(res, default=_json_default)})
        log.info("%s: %d rotations x %d ENSO classes", r.name, len(cfg["rotations"][region]), len(ENSO_CLASSES))

    meta = {"generated_by": "pipeline/build_scoring.py", "rules": "config/rotations.yaml",
            "kc_source": cfg["kc_source"], "normalisation": cfg["meta"]["normalisation"],
            "climate_source": "NASA POWER daily; ET0 FAO-56 Penman-Monteith (pipeline/agromet.py)",
            "revenue_source": f"IBGE PAM table 1612, last {cfg['meta']['revenue_years']} years, nominal R$"}
    write_parquet(clim, "monthly_climate_by_class.parquet", meta)
    scores = pd.DataFrame(rows)
    write_parquet(scores, "rotation_scores.parquet", meta)

    # Console summary: the ranking under equal weights, by class.
    w = cfg["meta"]["default_weights"]
    for code in regions.code:
        for cls in ("el_nino_strong", "la_nina"):
            res = [json.loads(x) for x in scores[(scores.code == code) & (scores.enso_class == cls)].result]
            ranked = scoring.rank(res, w)
            print(f"{code} {cls}: " + " > ".join(
                f"{x['id']}({x['total']:.0f})" if x["total"] is not None else f"{x['id']}(n/a)" for x in ranked))


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    raise TypeError(type(o))


if __name__ == "__main__":
    main()
