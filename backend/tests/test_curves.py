"""Tests for age-dependent fertility curves and adjustment factors."""

import numpy as np
import pytest

from fertility_forecaster.curves import (
    apply_odds_ratio,
    bmi_fecundability_fr,
    bmi_ivf_adjustment,
    fecundability_curve,
    frozen_egg_per_oocyte_rate,
    frozen_embryo_transfer_rate,
    frozen_embryo_transfer_rate_pgt,
    ivf_success_rate,
    male_age_miscarriage_or,
    miscarriage_curve,
    recurrent_miscarriage_or,
    smoking_fecundability_fr,
    sterility_curve,
)
from fertility_forecaster.models import SmokingStatus


class TestFecundabilityNulligravid:
    def test_exact_known_points(self):
        # Wesselink 2017 Table 3 nulligravid FRs at bracket midpoints
        ages = np.array([21, 26, 29, 32, 35, 38, 42.5])
        rates = fecundability_curve(ages, gravid=False)
        expected = np.array([1.00, 0.88, 0.80, 0.84, 0.68, 0.51, 0.20]) * 0.23
        np.testing.assert_allclose(rates, expected, atol=1e-6)

    def test_interpolation_between_points(self):
        rate = fecundability_curve(np.array([30.0]), gravid=False)[0]
        # Between age 29 (0.80*0.23=0.184) and 32 (0.84*0.23=0.1932)
        assert 0.18 < rate < 0.20

    def test_overall_decline(self):
        """Rates at oldest ages are substantially lower than youngest."""
        young = fecundability_curve(np.array([21.0]), gravid=False)[0]
        old = fecundability_curve(np.array([42.5]), gravid=False)[0]
        assert old < young * 0.3

    def test_clamped_at_boundaries(self):
        young = fecundability_curve(np.array([15.0]), gravid=False)[0]
        old = fecundability_curve(np.array([50.0]), gravid=False)[0]
        assert young == pytest.approx(0.23, abs=1e-6)
        assert old == pytest.approx(0.20 * 0.23, abs=1e-6)

    def test_vectorized_shape(self):
        ages = np.array([25, 30, 35, 40])
        result = fecundability_curve(ages, gravid=False)
        assert result.shape == (4,)


class TestFecundabilityGravid:
    def test_exact_known_points_raw(self):
        """Gravid FRs use raw Wesselink Table 3 ratios (no cap)."""
        ages = np.array([21, 26, 29, 32, 35, 38, 42.5])
        rates = fecundability_curve(ages, gravid=True)
        # Raw gravid FRs from Wesselink 2017 Table 3
        expected_fr = np.array([1.00, 0.92, 0.95, 0.88, 0.96, 0.70, 0.48])
        expected = expected_fr * 0.23
        np.testing.assert_allclose(rates, expected, atol=1e-6)

    def test_gravid_higher_than_nulligravid_at_35(self):
        """At age 35, gravid curve should be substantially higher than nulligravid."""
        ages = np.array([35.0])
        nulligravid = fecundability_curve(ages, gravid=False)
        gravid = fecundability_curve(ages, gravid=True)
        assert np.all(gravid > nulligravid)

    def test_gravid_higher_at_35(self):
        """At age 35, raw gravid FR=0.96 is substantially higher than nulligravid FR=0.68."""
        rate_gravid = fecundability_curve(np.array([35.0]), gravid=True)[0]
        rate_nulligravid = fecundability_curve(np.array([35.0]), gravid=False)[0]
        assert rate_gravid == pytest.approx(0.23 * 0.96, abs=1e-6)
        assert rate_gravid > rate_nulligravid * 1.20  # divergence exceeds 1.20x

    def test_gravid_higher_at_27(self):
        """At age 27, gravid curve is modestly higher than nulligravid."""
        rate_gravid = fecundability_curve(np.array([27.0]), gravid=True)[0]
        rate_nulligravid = fecundability_curve(np.array([27.0]), gravid=False)[0]
        assert rate_gravid > rate_nulligravid

    def test_gravidity_switch(self):
        """Gravid rates should differ from nulligravid rates."""
        ages = np.array([35.0])
        nulligravid = fecundability_curve(ages, gravid=False)[0]
        gravid = fecundability_curve(ages, gravid=True)[0]
        assert gravid > nulligravid


class TestMiscarriageCurve:
    def test_exact_known_points(self):
        ages = np.array([18.0, 27.0, 32.0, 37.0, 42.0, 47.5])
        rates = miscarriage_curve(ages)
        np.testing.assert_allclose(
            rates, [0.098, 0.098, 0.108, 0.167, 0.322, 0.536], atol=1e-6
        )

    def test_flat_below_25(self):
        """Curve is flat at 9.8% for all ages under 25."""
        ages = np.array([18.0, 20.0, 22.0, 24.0, 27.0])
        rates = miscarriage_curve(ages)
        np.testing.assert_allclose(rates, [0.098] * 5, atol=1e-6)

    def test_interpolation(self):
        rate = miscarriage_curve(np.array([30.0]))[0]
        # Between 27 (0.098) and 32 (0.108)
        assert 0.098 < rate < 0.108

    def test_vectorized_shape(self):
        result = miscarriage_curve(np.array([25.0, 35.0, 45.0]))
        assert result.shape == (3,)


class TestIVFSuccessRate:
    """SART 2023 fresh blast + cleavage pooled, weighted by transfers."""

    def test_age_brackets(self):
        assert ivf_success_rate(np.array([30.0]))[0] == 0.405
        assert ivf_success_rate(np.array([36.0]))[0] == 0.317
        assert ivf_success_rate(np.array([39.0]))[0] == 0.213
        assert ivf_success_rate(np.array([41.0]))[0] == 0.110
        assert ivf_success_rate(np.array([43.0]))[0] == 0.04
        assert ivf_success_rate(np.array([46.0]))[0] == 0.01

    def test_boundary_35(self):
        assert ivf_success_rate(np.array([34.9]))[0] == 0.405
        assert ivf_success_rate(np.array([35.0]))[0] == 0.317

    def test_vectorized(self):
        ages = np.array([30, 36, 39, 42, 44, 46], dtype=float)
        expected = np.array([0.405, 0.317, 0.213, 0.110, 0.04, 0.01])
        np.testing.assert_allclose(ivf_success_rate(ages), expected)


class TestFrozenEggRate:
    def test_age_brackets(self):
        assert frozen_egg_per_oocyte_rate(np.array([30.0]))[0] == 0.13
        assert frozen_egg_per_oocyte_rate(np.array([36.0]))[0] == 0.09
        assert frozen_egg_per_oocyte_rate(np.array([39.0]))[0] == 0.06
        assert frozen_egg_per_oocyte_rate(np.array([42.0]))[0] == 0.04

    def test_vectorized(self):
        ages = np.array([30, 36, 39, 42], dtype=float)
        expected = np.array([0.13, 0.09, 0.06, 0.04])
        np.testing.assert_allclose(frozen_egg_per_oocyte_rate(ages), expected)


class TestFrozenEmbryoTransferRate:
    """SART 2023 blastocyst + cleavage (non-PGT-A) pooled, by age at retrieval."""

    def test_age_brackets(self):
        assert frozen_embryo_transfer_rate(np.array([30.0]))[0] == 0.405
        assert frozen_embryo_transfer_rate(np.array([36.0]))[0] == 0.317
        assert frozen_embryo_transfer_rate(np.array([39.0]))[0] == 0.213
        assert frozen_embryo_transfer_rate(np.array([41.5]))[0] == 0.110
        assert frozen_embryo_transfer_rate(np.array([44.0]))[0] == 0.036

    def test_vectorized(self):
        ages = np.array([30, 36, 39, 42, 44], dtype=float)
        expected = np.array([0.405, 0.317, 0.213, 0.110, 0.036])
        np.testing.assert_allclose(frozen_embryo_transfer_rate(ages), expected)


class TestApplyOddsRatio:
    def test_or_of_one_returns_same(self):
        result = apply_odds_ratio(0.2, 1.0)
        assert pytest.approx(float(result)) == 0.2

    def test_or_greater_than_one_increases(self):
        result = apply_odds_ratio(0.2, 2.0)
        assert float(result) > 0.2

    def test_known_calculation(self):
        # base=0.2, OR=2.0 → (0.2*2)/(1-0.2+0.2*2) = 0.4/1.2 = 1/3
        result = apply_odds_ratio(0.2, 2.0)
        assert pytest.approx(float(result), abs=1e-6) == 1.0 / 3.0

    def test_vectorized(self):
        bases = np.array([0.1, 0.2, 0.3])
        ors = np.array([1.0, 2.0, 3.0])
        result = apply_odds_ratio(bases, ors)
        assert result.shape == (3,)
        assert pytest.approx(float(result[0])) == 0.1

    @pytest.mark.parametrize("base,or_val,expected", [
        (0.10, 1.54, 0.146),
        (0.10, 2.21, 0.197),
        (0.10, 3.97, 0.306),
        (0.322, 2.21, 0.512),
        (0.322, 3.97, 0.654),
        (0.536, 1.43, 0.623),
    ])
    def test_precise_conversion(self, base, or_val, expected):
        """Verify OR-to-probability conversion matches canonical formula."""
        result = float(apply_odds_ratio(base, or_val))
        assert pytest.approx(result, abs=0.001) == expected
        assert 0.0 < result < 1.0

    def test_high_base_high_or_stays_below_one(self):
        """Critical: high base prob + high OR must NOT exceed 1.0."""
        # 45+ woman (base ~0.536) with male age OR 1.43
        result = float(apply_odds_ratio(0.536, 1.43))
        assert result < 1.0
        # 42yo (base ~0.322) with recurrent miscarriage OR 3.97
        result = float(apply_odds_ratio(0.322, 3.97))
        assert result < 1.0

    def test_stacking_equivalent_to_combined_odds(self):
        """Sequential apply_odds_ratio is equivalent to multiplying ORs on odds scale."""
        base = 0.322
        or1, or2 = 2.21, 1.43
        # Sequential application
        p1 = float(apply_odds_ratio(base, or1))
        p_sequential = float(apply_odds_ratio(p1, or2))
        # Combined on odds scale
        base_odds = base / (1 - base)
        combined_odds = base_odds * or1 * or2
        p_combined = combined_odds / (1 + combined_odds)
        assert pytest.approx(p_sequential, abs=1e-10) == p_combined
        assert p_sequential < 1.0

    def test_all_age_brackets_with_all_ors_bounded(self):
        """Miscarriage probability stays in [0,1] for all age × recurrent MC × male age combos."""
        # Magnus 2019 miscarriage rates (flattened below 25)
        mc_rates = np.array([0.098, 0.098, 0.108, 0.167, 0.322, 0.536])
        recurrent_ors = [1.0, 1.54, 2.21, 3.97]
        male_ors = [1.0, 1.15, 1.23, 1.43]
        for base in mc_rates:
            for rec_or in recurrent_ors:
                p = float(apply_odds_ratio(base, rec_or))
                assert 0.0 <= p <= 1.0, f"Failed: base={base}, rec_or={rec_or} → {p}"
                for male_or in male_ors:
                    p2 = float(apply_odds_ratio(p, male_or))
                    assert 0.0 <= p2 <= 1.0, f"Failed: base={base}, rec_or={rec_or}, male_or={male_or} → {p2}"


class TestRecurrentMiscarriageOR:
    def test_zero_miscarriages(self):
        result = recurrent_miscarriage_or(np.array([0]))
        assert float(result[0]) == 1.0

    def test_one_miscarriage(self):
        result = recurrent_miscarriage_or(np.array([1]))
        assert float(result[0]) == 1.54

    def test_two_miscarriages(self):
        result = recurrent_miscarriage_or(np.array([2]))
        assert float(result[0]) == 2.21

    def test_three_plus_miscarriages(self):
        result = recurrent_miscarriage_or(np.array([3]))
        assert float(result[0]) == 3.97
        result = recurrent_miscarriage_or(np.array([5]))
        assert float(result[0]) == 3.97

    def test_vectorized(self):
        result = recurrent_miscarriage_or(np.array([0, 1, 2, 3]))
        np.testing.assert_allclose(result, [1.0, 1.54, 2.21, 3.97])


class TestMaleAgeMiscarriageOR:
    def test_under_35(self):
        result = male_age_miscarriage_or(np.array([25.0, 30.0, 34.9]))
        np.testing.assert_allclose(result, [1.0, 1.0, 1.0])

    def test_35_to_39(self):
        result = male_age_miscarriage_or(np.array([35.0, 39.9]))
        np.testing.assert_allclose(result, [1.15, 1.15])

    def test_40_to_44(self):
        result = male_age_miscarriage_or(np.array([40.0, 44.9]))
        np.testing.assert_allclose(result, [1.23, 1.23])

    def test_45_and_over(self):
        result = male_age_miscarriage_or(np.array([45.0, 50.0]))
        np.testing.assert_allclose(result, [1.43, 1.43])


class TestBMIFecundabilityFR:
    def test_none_returns_one(self):
        assert bmi_fecundability_fr(None) == 1.0

    def test_underweight(self):
        assert bmi_fecundability_fr(17.0) == 1.05

    def test_normal_weight(self):
        assert bmi_fecundability_fr(22.0) == 1.0

    def test_overweight(self):
        assert bmi_fecundability_fr(27.0) == 1.01

    def test_obese_class1(self):
        assert bmi_fecundability_fr(32.0) == 0.98

    def test_obese_class2(self):
        assert bmi_fecundability_fr(37.0) == 0.78

    def test_obese_class3(self):
        assert bmi_fecundability_fr(42.0) == 0.61

    def test_extreme_obesity(self):
        assert bmi_fecundability_fr(50.0) == 0.42


class TestBMIIVFAdjustment:
    def test_none_returns_one(self):
        assert bmi_ivf_adjustment(None) == 1.0

    def test_under_30(self):
        assert bmi_ivf_adjustment(25.0) == 1.0

    def test_30_and_over(self):
        assert bmi_ivf_adjustment(30.0) == 0.85
        assert bmi_ivf_adjustment(40.0) == 0.85


class TestSmokingFR:
    def test_never(self):
        assert smoking_fecundability_fr(SmokingStatus.NEVER) == 1.0

    def test_former(self):
        assert smoking_fecundability_fr(SmokingStatus.FORMER) == 0.89

    def test_current_occasional(self):
        assert smoking_fecundability_fr(SmokingStatus.CURRENT_OCCASIONAL) == 0.88

    def test_current_regular(self):
        assert smoking_fecundability_fr(SmokingStatus.CURRENT_REGULAR) == 0.77


# --- Phase 1e: Sterility curve tests ---

class TestSterilityCurve:
    """Test 1: Verify sterility_curve returns expected values at data points."""

    def test_exact_known_points(self):
        ages = np.array([20, 25, 30, 35, 38, 40, 42, 45], dtype=float)
        expected = np.array([0.005, 0.01, 0.02, 0.05, 0.10, 0.17, 0.30, 0.55])
        np.testing.assert_allclose(sterility_curve(ages), expected, atol=1e-6)

    def test_monotonically_increasing(self):
        ages = np.arange(20, 46, dtype=float)
        rates = sterility_curve(ages)
        assert np.all(np.diff(rates) >= 0)

    def test_interpolation_between_points(self):
        rate = sterility_curve(np.array([32.5]))[0]
        # Between age 30 (0.02) and 35 (0.05): 0.02 + 0.5*(0.05-0.02) = 0.035
        assert rate == pytest.approx(0.035, abs=1e-6)

    def test_clamped_at_boundaries(self):
        young = sterility_curve(np.array([15.0]))[0]
        old = sterility_curve(np.array([50.0]))[0]
        assert young == pytest.approx(0.005, abs=1e-6)  # clamped to youngest
        assert old == pytest.approx(0.55, abs=1e-6)  # clamped to oldest

    def test_vectorized_shape(self):
        result = sterility_curve(np.array([25, 35, 45], dtype=float))
        assert result.shape == (3,)


class TestBaseFecundability:
    """Test 5: Verify base fecundability is 0.23."""

    def test_base_rate_at_young_age(self):
        """At age 20 (nulligravid), per-cycle probability should be 0.23 × 1.00 = 0.23."""
        rate = fecundability_curve(np.array([20.0]), gravid=False)[0]
        # Age 20 is below age 21 data point (FR=1.00), clamped to 1.00
        assert rate == pytest.approx(0.23, abs=1e-6)

    def test_base_rate_at_21(self):
        """At age 21, exact data point: 0.23 × 1.00 = 0.23."""
        rate = fecundability_curve(np.array([21.0]), gravid=False)[0]
        assert rate == pytest.approx(0.23, abs=1e-6)


class TestGravidRawRatios:
    """Test 6 & 7: Verify raw gravid Wesselink ratios are used without capping."""

    def test_gravid_raw_at_35(self):
        """At age 35, raw gravid FR=0.96. Per-cycle gravid = 0.23 × 0.96 = 0.2208."""
        rate = fecundability_curve(np.array([35.0]), gravid=True)[0]
        assert rate == pytest.approx(0.23 * 0.96, abs=1e-6)

    def test_gravid_exceeds_nulligravid_at_35(self):
        """At age 35, gravid FR (0.96) significantly exceeds nulligravid FR (0.68).
        This divergence is real — corroborated by Steiner & Jukic 2016."""
        nulligravid = fecundability_curve(np.array([35.0]), gravid=False)[0]
        gravid = fecundability_curve(np.array([35.0]), gravid=True)[0]
        ratio = gravid / nulligravid
        assert ratio == pytest.approx(0.96 / 0.68, abs=0.01)
        assert ratio > 1.2  # raw ratio exceeds what old cap would have allowed


class TestFrozenEmbryoTransferRatePGT:
    """PGT-A tested (euploid) frozen embryo transfer rates (SART 2023 SET)."""

    def test_age_brackets(self):
        assert frozen_embryo_transfer_rate_pgt(np.array([30.0]))[0] == 0.545
        assert frozen_embryo_transfer_rate_pgt(np.array([36.0]))[0] == 0.532
        assert frozen_embryo_transfer_rate_pgt(np.array([39.0]))[0] == 0.514
        assert frozen_embryo_transfer_rate_pgt(np.array([41.5]))[0] == 0.499
        assert frozen_embryo_transfer_rate_pgt(np.array([44.0]))[0] == 0.463

    def test_vectorized(self):
        ages = np.array([30, 36, 39, 42, 44], dtype=float)
        expected = np.array([0.545, 0.532, 0.514, 0.499, 0.463])
        np.testing.assert_allclose(frozen_embryo_transfer_rate_pgt(ages), expected)

    def test_higher_than_untested(self):
        """PGT-A rates should exceed untested rates at every age bracket."""
        ages = np.array([30, 36, 39, 42, 44], dtype=float)
        pgt = frozen_embryo_transfer_rate_pgt(ages)
        untested = frozen_embryo_transfer_rate(ages)
        assert np.all(pgt > untested)

    def test_flatter_decline(self):
        """PGT-A rates decline less steeply with age than untested rates."""
        young_pgt = frozen_embryo_transfer_rate_pgt(np.array([30.0]))[0]
        old_pgt = frozen_embryo_transfer_rate_pgt(np.array([44.0]))[0]
        young_untested = frozen_embryo_transfer_rate(np.array([30.0]))[0]
        old_untested = frozen_embryo_transfer_rate(np.array([44.0]))[0]
        # PGT ratio (old/young) should be higher than untested ratio
        assert (old_pgt / young_pgt) > (old_untested / young_untested)
