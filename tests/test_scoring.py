"""Tests for the pure rotation scoring (pipeline/scoring.py)."""

from __future__ import annotations

import pytest

from pipeline import scoring as sc

KC = {
    "soja": {"ini": 0.4, "mid": 1.15, "end": 0.5},
    "trigo": {"ini": 0.3, "mid": 1.15, "end": 0.325},
    "aveia_cobertura": {"ini": 0.3, "mid": 1.15, "end": 0.25},
}
CROPS = {
    "soja": {"revenue_pam_code": 1, "anomaly_pam_code": 1, "kc": KC["soja"]},
    "trigo": {"revenue_pam_code": 2, "anomaly_pam_code": 2, "kc": KC["trigo"]},
    "aveia_cobertura": {"cover_crop": True, "kc": KC["aveia_cobertura"]},
}
CAL = {"soja": {"sow": 11, "harvest": 4}, "trigo": {"sow": 6, "harvest": 11},
       "aveia_cobertura": {"sow": 5, "harvest": 10}}


class TestCalendar:
    def test_months_wrap_over_new_year(self):
        assert sc.crop_months(11, 4) == [11, 12, 1, 2, 3, 4]
        assert sc.crop_months(6, 6) == [6]

    def test_stages(self):
        assert sc.stages(6) == ["ini", "dev", "mid", "mid", "mid", "end"]
        assert sc.stages(2) == ["ini", "end"]

    def test_handover_month_is_shared(self):
        occ = sc.occupancy(["soja", "trigo"], CAL)
        nov = {e["crop"]: e for e in occ[11]}
        assert nov["trigo"]["stage"] == "end" and nov["soja"]["stage"] == "ini"
        assert nov["trigo"]["share"] == nov["soja"]["share"] == 0.5
        assert occ[5] == []  # May is bare in soy-wheat

    def test_overlapping_crops_are_rejected(self):
        with pytest.raises(sc.RotationError, match="month"):
            sc.occupancy(["soja", "trigo"], {"soja": {"sow": 11, "harvest": 4}, "trigo": {"sow": 3, "harvest": 9}})

    def test_kc_development_is_midpoint(self):
        assert sc.kc_value("dev", KC["soja"]) == pytest.approx((0.4 + 1.15) / 2)


class TestComponents:
    def test_soil_counts_heavy_rain_on_bare_months_only(self):
        occ = sc.occupancy(["soja"], CAL)  # bare May-Oct
        heavy = {m: 1.0 for m in range(1, 13)}
        heavy[9] = 3.0
        out = sc.soil_component(occ, heavy)
        assert out["bare_months"] == [7, 8, 9, 10, 5, 6]
        assert out["value"] == 8.0

    def test_cover_crop_removes_bare_months(self):
        occ = sc.occupancy(["soja", "aveia_cobertura"], CAL)
        assert sc.soil_component(occ, {m: 2.0 for m in range(1, 13)})["value"] == 0

    def test_water_deficit_is_month_by_month_and_never_negative(self):
        occ = sc.occupancy(["soja"], {"soja": {"sow": 11, "harvest": 12}})  # ini, end
        et0 = {m: 100.0 for m in range(1, 13)}
        rain = {m: 0.0 for m in range(1, 13)}
        rain[12] = 500.0  # surplus in December must not offset November
        out = sc.water_component(occ, {"soja": KC["soja"]}, et0, rain)
        assert out["value"] == pytest.approx(40.0)  # Nov: 0.4 x 100 - 0
        assert out["demand_mm"] == pytest.approx(40.0 + 50.0)

    def test_income_change_weights_crops_by_revenue(self):
        out = sc.income_component(["soja", "trigo"], CROPS, {1: 6000.0, 2: 2000.0}, {1: (10.0, 5), 2: (-30.0, 5)})
        # (6000*1.1 + 2000*0.7) / 8000 - 1 = 0%
        assert out["value"] == pytest.approx(0.0)
        assert out["min_n_years"] == 5

    def test_cover_crop_has_no_revenue(self):
        out = sc.income_component(["soja", "aveia_cobertura"], CROPS, {1: 6000.0}, {1: (15.5, 5)})
        assert out["value"] == pytest.approx(15.5)

    def test_missing_history_is_none_not_zero(self):
        out = sc.income_component(["soja", "trigo"], CROPS, {1: 6000.0, 2: 2000.0}, {1: (10.0, 5)})
        assert out["value"] is None and "trigo" in out["reason"]


class TestCombining:
    def test_normalise(self):
        assert sc.normalise([0, 5, 10], higher_is_better=False) == [100.0, 50.0, 0.0]
        assert sc.normalise([0, 5, None], higher_is_better=True) == [0.0, 100.0, None]
        assert sc.normalise([3, 3], higher_is_better=True) == [100.0, 100.0]

    def test_weighted_total(self):
        assert sc.weighted_total({"soil": 100, "water": 0, "income": 50}, {"soil": 2, "water": 1, "income": 1}) == 62.5

    def test_zero_weight_ignores_a_missing_component(self):
        s = {"soil": 80, "water": 60, "income": None}
        assert sc.weighted_total(s, {"soil": 1, "water": 1, "income": 1}) is None
        assert sc.weighted_total(s, {"soil": 1, "water": 1, "income": 0}) == 70

    def test_end_to_end_ranking_and_trade_off(self):
        rotations = [{"id": "soja_trigo", "crops": ["soja", "trigo"]},
                     {"id": "soja_cob", "crops": ["soja", "aveia_cobertura"]},
                     {"id": "soja_pousio", "crops": ["soja"]}]
        climate = {"heavy_days": {m: 2.0 for m in range(1, 13)},
                   "et0": {m: 100.0 for m in range(1, 13)}, "rain": {m: 120.0 for m in range(1, 13)}}
        res = sc.score_rotations(rotations, CROPS, CAL, climate, {1: 6000.0, 2: 2000.0}, {1: (15.0, 5), 2: (-30.0, 5)})
        by = {r["id"]: r for r in res}
        assert by["soja_pousio"]["soil"]["score"] == 0  # most bare months
        assert by["soja_cob"]["soil"]["score"] == 100
        assert by["soja_trigo"]["income"]["score"] == 0  # wheat drags revenue in this class
        soil_first = sc.rank(res, {"soil": 1, "water": 0, "income": 0})
        income_first = sc.rank(res, {"soil": 0, "water": 0, "income": 1})
        assert soil_first[0]["id"] == "soja_cob"
        assert income_first[-1]["id"] == "soja_trigo"
        assert [r["rank"] for r in soil_first] == [1, 2, 3]
