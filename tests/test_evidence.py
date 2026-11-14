"""Tests for the pure evidence functions (pipeline/evidence.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline import evidence as ev

RAIN_CFG = {"wet_day_mm": 1.0, "heavy_day_mm": 20.0, "rx_window_days": 5}


def test_crop_year_is_labelled_by_harvest_year():
    d = pd.Series(pd.to_datetime(["2015-06-30", "2015-07-01", "2016-01-15"]))
    assert ev.crop_year(d).tolist() == [2015, 2016, 2016]


@pytest.mark.parametrize("rain,expected", [
    ([5, 0, 0, 0, 5], 3),
    ([0.9, 0.5, 1.0, 0], 2),  # 1.0 mm is a wet day (ETCCDI)
    ([5, 5, 5], 0),
    ([], 0),
])
def test_max_dry_spell(rain, expected):
    assert ev.max_dry_spell(rain, 1.0) == expected


def test_rain_indices():
    r = pd.Series([0, 25, 0, 0, 30, 1, 1, 0])
    out = ev.rain_indices(r, RAIN_CFG)
    assert out["rain_mm"] == 57
    assert out["r20_days"] == 2
    assert out["cdd_days"] == 2
    assert out["rx5_mm"] == 56  # 25 + 0 + 0 + 30 + 1


def _daily(start: str, end: str, rain: float = 2.0) -> pd.DataFrame:
    dates = pd.date_range(start, end)
    return pd.DataFrame({"code": 1, "date": dates, "PRECTOTCORR": rain,
                         "GWETROOT": 0.5, "T2M_MAX": 30.0})


class TestSeasonalClimate:
    MONTHS = [9, 10, 11, 12, 1, 2, 3, 4]
    SUBS = {"early": [9, 10, 11, 12], "late": [1, 2, 3, 4]}

    def test_full_season_gets_a_row_with_right_totals(self):
        out = ev.seasonal_climate(_daily("2015-07-01", "2016-06-30"), self.MONTHS, self.SUBS, RAIN_CFG)
        row = out.set_index("crop_year").loc[2016]
        assert row.season_rain_mm == pytest.approx(2.0 * 243)  # Sep 2015-Apr 2016, leap year
        assert row.early_rain_mm == pytest.approx(2.0 * 122)

    def test_partial_season_is_dropped_not_reported_as_drought(self):
        out = ev.seasonal_climate(_daily("2026-07-01", "2026-11-11"), self.MONTHS, self.SUBS, RAIN_CFG)
        assert out.empty

    def test_season_with_missing_day_is_dropped(self):
        d = _daily("2015-07-01", "2016-06-30")
        d.loc[d.date == "2015-10-10", "PRECTOTCORR"] = np.nan
        assert ev.seasonal_climate(d, self.MONTHS, self.SUBS, RAIN_CFG).empty


def test_anomalies_use_only_the_baseline_years():
    df = pd.DataFrame({"code": 1, "crop_year": [1990, 1991, 1992, 2021], "x_mm": [0.0, 100.0, 200.0, 300.0]})
    out = ev.add_anomalies(df, ["x_mm"], (1991, 1992))
    assert out.x_mm_anom.tolist() == [-150.0, -50.0, 50.0, 150.0]
    assert out.x_mm_anom_pct.iloc[-1] == pytest.approx(100.0)


class TestCropYearEnso:
    def seasonal(self, phase, strength, roni=2.0):
        return pd.DataFrame([{"season": "NDJ", "year": 2015, "crop_year": 2016, "roni": roni,
                              "roni_phase": phase, "roni_strength": strength}])

    def test_strong(self):
        out = ev.crop_year_enso(self.seasonal("el_nino", "very_strong"), "NDJ", ["strong", "very_strong"])
        assert out.iloc[0].crop_year == 2016
        assert out.iloc[0].enso_class == "el_nino_strong"

    def test_moderate_and_provisional(self):
        out = ev.crop_year_enso(self.seasonal("el_nino_provisional", "moderate", 1.2), "NDJ", ["strong"])
        assert out.iloc[0].enso_class == "el_nino_moderate"
        assert bool(out.iloc[0].provisional)

    def test_forecast_class_picks_most_likely(self):
        row = pd.Series({"p_p1.5_p2.0": 4, "p_ge_p2.0": 96, "p_p0.5_p1.0": 0, "p_p1.0_p1.5": 0,
                         "p_neutral": 0, "p_la_nina": 0})
        assert ev.forecast_class(row, ["p1.5_p2.0", "ge_p2.0"], ["p0.5_p1.0", "p1.0_p1.5"]) == ("el_nino_strong", 100)


class TestYield:
    def test_linear_trend_is_removed(self):
        years = np.arange(2000, 2012)
        y = 2000 + 50 * (years - 2000)  # pure trend
        s = pd.DataFrame({"year": years, "yield_kg_ha": y.astype(float)})
        s.loc[s.year == 2005, "yield_kg_ha"] *= 0.8  # one bad year
        out = ev.yield_anomalies(s, 10).set_index("year")
        assert out.loc[2005, "anomaly_pct"] < -15
        assert abs(out.drop(index=2005).anomaly_pct).max() < 5

    def test_short_series_gives_nothing(self):
        s = pd.DataFrame({"year": range(2000, 2005), "yield_kg_ha": 1000.0})
        assert ev.yield_anomalies(s, 10).empty

    def test_zero_yield_is_not_a_crop_failure_datapoint(self):
        """A '-' (zero) yield means the crop was not grown, not that it failed."""
        s = pd.DataFrame({"year": range(2000, 2012), "yield_kg_ha": [1000.0] * 11 + [0.0]})
        out = ev.yield_anomalies(s, 10)
        assert 2011 not in out.year.tolist()

    def test_main_crops_by_area_share(self):
        area = pd.DataFrame({"year": [2025] * 3, "crop_code": [1, 2, 3], "value": [990.0, 9.0, 1.0]})
        assert ev.main_crops(area, 5, 0.005) == [1, 2]


def test_composite_reports_every_class_even_when_empty():
    df = pd.DataFrame({"code": 1, "crop_year": [2000, 2001, 2002],
                       "enso_class": ["neutral", "neutral", "el_nino_strong"], "v": [0.0, 2.0, -10.0]})
    out = ev.composite(df, "v", ["code"]).set_index("enso_class")
    assert set(out.index) == set(ev.ENSO_CLASSES)
    assert out.loc["la_nina", "n"] == 0 and np.isnan(out.loc["la_nina", "mean"])
    assert out.loc["el_nino_strong", "minus_neutral"] == -11.0
    assert out.loc["neutral", "years"] == "2000,2001"


def test_season_progress_cumulates_from_season_start():
    d = _daily("1990-07-01", "1992-06-30", rain=1.0)
    d = pd.concat([d, _daily("2026-07-01", "2026-09-10", rain=3.0)])
    out = ev.season_progress(d, 1, 9, 242, 2027, (1991, 1992), [1992])
    assert out.loc[0, "current_mm"] == 3.0
    assert out.loc[9, "current_mm"] == 30.0
    assert np.isnan(out.loc[20, "current_mm"])  # not happened yet
    assert out.loc[9, "baseline_mean_mm"] == 10.0
    assert out.n_baseline.iloc[0] == 2
    assert out.n_analog.iloc[0] == 1
