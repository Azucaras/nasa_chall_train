"""Pure functions behind the analog-year evidence. No I/O: everything takes and returns DataFrames.

Vocabulary used throughout:

crop year   Jul-Jun, labelled by the harvest year (crop year 2016 = Jul 2015 - Jun 2016).
season      the months in regions.yaml ``season_months`` (Sep-Apr) of one crop year.
ENSO class  el_nino_strong / el_nino_moderate / neutral / la_nina, from RONI at the reference
            season (config/analysis.yaml).
baseline    crop years 1991-2020; every anomaly is relative to their mean.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

ENSO_CLASSES = ["el_nino_strong", "el_nino_moderate", "neutral", "la_nina"]


# --------------------------------------------------------------------------------------------
# Calendar
# --------------------------------------------------------------------------------------------


def crop_year(dates: pd.Series, start_month: int = 7) -> pd.Series:
    """Harvest-year label: months >= start_month belong to the next calendar year's crop year."""
    return dates.dt.year + (dates.dt.month >= start_month).astype(int)


# --------------------------------------------------------------------------------------------
# Rainfall indices
# --------------------------------------------------------------------------------------------


def max_dry_spell(rain: Iterable[float], wet_day_mm: float) -> int:
    """ETCCDI CDD: the longest run of consecutive days with rain below ``wet_day_mm``."""
    best = run = 0
    for r in rain:
        if r < wet_day_mm:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def rain_indices(rain: pd.Series, cfg: dict[str, Any]) -> dict[str, float]:
    """Total, CDD, R20mm and Rx5day for one contiguous block of daily rainfall (mm/day)."""
    rain = rain.astype(float)
    return {
        "rain_mm": float(rain.sum()),
        "cdd_days": float(max_dry_spell(rain, cfg["wet_day_mm"])),
        "r20_days": float((rain >= cfg["heavy_day_mm"]).sum()),
        "rx5_mm": float(rain.rolling(cfg["rx_window_days"]).sum().max()),
    }


def seasonal_climate(
    daily: pd.DataFrame,
    season_months: list[int],
    sub_seasons: dict[str, list[int]],
    rain_cfg: dict[str, Any],
    start_month: int = 7,
) -> pd.DataFrame:
    """One row per (code, crop_year): rainfall indices for the season and each sub-season, plus
    mean root-zone wetness and mean Tmax over the season.

    A season only gets a row if every one of its days is present -- a half-observed season would
    look like a drought.
    """
    df = daily.copy()
    df["crop_year"] = crop_year(df["date"], start_month)
    df["month"] = df["date"].dt.month
    rows = []
    for (code, cy), g in df.groupby(["code", "crop_year"]):
        season = g[g.month.isin(season_months)].sort_values("date")
        expected = sum(_days_in_month(cy, m, start_month) for m in season_months)
        if len(season) != expected or season.PRECTOTCORR.isna().any():
            continue
        row: dict[str, Any] = {"code": code, "crop_year": cy}
        row.update({f"season_{k}": v for k, v in rain_indices(season.PRECTOTCORR, rain_cfg).items()})
        for name, months in sub_seasons.items():
            part = season[season.month.isin(months)]
            row.update({f"{name}_{k}": v for k, v in rain_indices(part.PRECTOTCORR, rain_cfg).items()})
        row["season_gwetroot"] = float(season.GWETROOT.mean())
        row["season_tmax_c"] = float(season.T2M_MAX.mean())
        rows.append(row)
    return pd.DataFrame(rows)


def _days_in_month(cy: int, month: int, start_month: int) -> int:
    year = cy - 1 if month >= start_month else cy
    return pd.Period(f"{year}-{month:02d}").days_in_month


def add_anomalies(df: pd.DataFrame, metrics: list[str], baseline: tuple[int, int]) -> pd.DataFrame:
    """For each metric add ``<metric>_anom`` (minus the baseline mean) and, for totals,
    ``<metric>_anom_pct``. Baseline means are per municipality."""
    out = df.copy()
    base = out[(out.crop_year >= baseline[0]) & (out.crop_year <= baseline[1])]
    means = base.groupby("code")[metrics].mean()
    for m in metrics:
        mean = out["code"].map(means[m])
        out[f"{m}_anom"] = out[m] - mean
        if m.endswith("_mm"):
            out[f"{m}_anom_pct"] = 100 * (out[m] - mean) / mean
    return out


# --------------------------------------------------------------------------------------------
# ENSO label per crop year
# --------------------------------------------------------------------------------------------


def crop_year_enso(seasonal: pd.DataFrame, reference_season: str, strong: list[str]) -> pd.DataFrame:
    """ENSO class of each crop year from the RONI phase/strength at ``reference_season``.

    ``enso_seasonal.parquet`` already carries ``crop_year`` per 3-month season, so NDJ 2015
    (Nov 2015 - Jan 2016) lands in crop year 2016, as it should.
    """
    ref = seasonal[seasonal.season == reference_season].dropna(subset=["roni"])
    rows = []
    for r in ref.itertuples():
        phase = str(r.roni_phase)
        if phase.startswith("el_nino"):
            cls = "el_nino_strong" if r.roni_strength in strong else "el_nino_moderate"
        elif phase.startswith("la_nina"):
            cls = "la_nina"
        else:
            cls = "neutral"
        rows.append({
            "crop_year": int(r.crop_year), "enso_class": cls, "roni_ref": float(r.roni),
            "roni_strength": r.roni_strength, "provisional": phase.endswith("_provisional"),
            "basis": f"RONI {reference_season} {int(r.year)}",
        })
    return pd.DataFrame(rows)


def forecast_class(strength_row: pd.Series, strong_bins: list[str], moderate_bins: list[str]) -> tuple[str, int]:
    """Most likely ENSO class for a not-yet-observed season, from CPC strength probabilities.

    Returns (class, probability %). Only used for the current crop year before its reference
    season has been observed; labelled as a forecast everywhere it appears.
    """
    p = {
        "el_nino_strong": int(sum(strength_row[f"p_{b}"] for b in strong_bins)),
        "el_nino_moderate": int(sum(strength_row[f"p_{b}"] for b in moderate_bins)),
        "neutral": int(strength_row["p_neutral"]),
        "la_nina": int(strength_row["p_la_nina"]),
    }
    best = max(p, key=p.get)
    return best, p[best]


# --------------------------------------------------------------------------------------------
# Yield
# --------------------------------------------------------------------------------------------


def yield_anomalies(series: pd.DataFrame, min_years: int) -> pd.DataFrame:
    """Linear-trend anomalies for one municipality x crop yield series (columns year, yield).

    Only positive, flag-free yields enter the trend. Returns an empty frame when there are fewer
    than ``min_years`` of them.
    """
    s = series.dropna(subset=["yield_kg_ha"])
    s = s[s.yield_kg_ha > 0].sort_values("year")
    if len(s) < min_years:
        return s.iloc[0:0].assign(trend_kg_ha=[], anomaly_pct=[])
    slope, intercept = np.polyfit(s.year, s.yield_kg_ha, 1)
    trend = slope * s.year + intercept
    return s.assign(trend_kg_ha=trend, anomaly_pct=100 * (s.yield_kg_ha - trend) / trend)


def main_crops(area: pd.DataFrame, last_years: int, min_share: float) -> list[int]:
    """Crop codes whose mean planted area over the last ``last_years`` PAM years is at least
    ``min_share`` of the municipality's total (columns year, crop_code, value)."""
    recent = area[area.year > area.year.max() - last_years]
    mean = recent.groupby("crop_code").value.mean()
    total = mean.sum()
    if total <= 0:
        return []
    return mean[mean / total >= min_share].sort_values(ascending=False).index.astype(int).tolist()


# --------------------------------------------------------------------------------------------
# Composites
# --------------------------------------------------------------------------------------------


def composite(df: pd.DataFrame, value_col: str, keys: list[str]) -> pd.DataFrame:
    """Mean of ``value_col`` by ENSO class within ``keys``, with n and the years used.

    Every class appears for every key, with n = 0 and mean NaN when there were no such years, so
    the UI can show "no strong El Nino on record here" instead of silently dropping the bar.
    """
    rows = []
    for key, g in df.dropna(subset=[value_col]).groupby(keys):
        key = key if isinstance(key, tuple) else (key,)
        neutral = g[g.enso_class == "neutral"][value_col]
        for cls in ENSO_CLASSES:
            sub = g[g.enso_class == cls]
            vals = sub[value_col]
            rows.append({
                **dict(zip(keys, key)),
                "enso_class": cls,
                "n": int(len(vals)),
                "mean": float(vals.mean()) if len(vals) else np.nan,
                "median": float(vals.median()) if len(vals) else np.nan,
                "minus_neutral": float(vals.mean() - neutral.mean()) if len(vals) and len(neutral) else np.nan,
                "years": ",".join(str(int(y)) for y in sorted(sub.crop_year)),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------
# Season to date (the "impact preview")
# --------------------------------------------------------------------------------------------


def season_progress(
    daily: pd.DataFrame,
    code: int,
    season_start_month: int,
    season_days: int,
    current_crop_year: int,
    baseline: tuple[int, int],
    analog_years: list[int],
    start_month: int = 7,
) -> pd.DataFrame:
    """Cumulative rainfall from the first day of the season, day by day.

    Columns: day (0 = first day of the season), current (this crop year, to date), baseline mean
    and 10th/90th percentile across baseline crop years, and the mean over ``analog_years``.
    Days are counted from the season start, so leap years shift a calendar date by one day at
    most from February on.
    """
    d = daily[daily.code == code].copy()
    d["crop_year"] = crop_year(d["date"], start_month)

    def cumulative(cy: int) -> pd.Series:
        start_year = cy - 1 if season_start_month >= start_month else cy
        start = pd.Timestamp(start_year, season_start_month, 1)
        part = d[(d.date >= start) & (d.date < start + pd.Timedelta(days=season_days))]
        s = part.set_index((part.date - start).dt.days).PRECTOTCORR.cumsum()
        return s

    base_years = [y for y in range(baseline[0], baseline[1] + 1)]
    base = pd.DataFrame({y: cumulative(y) for y in base_years}).reindex(range(season_days))
    complete = base.columns[base.notna().all()]
    base = base[complete]
    analog = pd.DataFrame({y: cumulative(y) for y in analog_years}).reindex(range(season_days))
    analog = analog[analog.columns[analog.notna().all()]]
    cur = cumulative(current_crop_year).reindex(range(season_days))

    first = pd.Timestamp(current_crop_year - 1 if season_start_month >= start_month else current_crop_year,
                         season_start_month, 1)
    return pd.DataFrame({
        "code": code,
        "day": range(season_days),
        "date": [first + pd.Timedelta(days=i) for i in range(season_days)],
        "current_mm": cur.to_numpy(),
        "baseline_mean_mm": base.mean(axis=1).to_numpy(),
        "baseline_p10_mm": base.quantile(0.1, axis=1).to_numpy(),
        "baseline_p90_mm": base.quantile(0.9, axis=1).to_numpy(),
        "analog_mean_mm": analog.mean(axis=1).to_numpy() if analog.shape[1] else np.nan,
        "n_baseline": base.shape[1],
        "n_analog": analog.shape[1],
        "analog_years": ",".join(str(y) for y in analog.columns),
    })
