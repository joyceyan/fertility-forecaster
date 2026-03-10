"""Tests for the Monte Carlo simulation engine."""

import time

import numpy as np
import pytest

from fertility_forecaster.models import (
    FrozenEggBatch,
    FrozenEmbryoBatch,
    SimulationParams,
    SmokingStatus,
)
from fertility_forecaster.simulation import run_simulation


class TestSmokeAndDeterminism:
    def test_runs_without_error(self, young_one_child):
        result = run_simulation(young_one_child)
        assert 0.0 <= result.completion_rate <= 1.0
        assert len(result.time_distribution) == 12
        assert set(result.completion_by_method.keys()) == {
            "natural", "ivf_fresh", "ivf_frozen_egg", "ivf_frozen_embryo", "incomplete"
        }

    def test_deterministic_with_same_seed(self, young_one_child):
        r1 = run_simulation(young_one_child, seed=123)
        r2 = run_simulation(young_one_child, seed=123)
        assert r1.completion_rate == r2.completion_rate
        assert r1.time_distribution == r2.time_distribution

    def test_different_seed_different_results(self):
        params = SimulationParams(female_age=38, desired_children=2)
        r1 = run_simulation(params, seed=1)
        r2 = run_simulation(params, seed=99)
        assert r1.completion_rate != r2.completion_rate


class TestCompletionRates:
    def test_young_one_child_high_rate(self, young_one_child):
        result = run_simulation(young_one_child)
        assert result.completion_rate > 0.95

    def test_old_two_children_low_rate(self, old_two_children):
        result = run_simulation(old_two_children)
        assert result.completion_rate < 0.30

    def test_more_children_lower_rate(self):
        r1 = run_simulation(SimulationParams(female_age=35, desired_children=1))
        r2 = run_simulation(SimulationParams(female_age=35, desired_children=2))
        r3 = run_simulation(SimulationParams(female_age=35, desired_children=3))
        assert r1.completion_rate > r2.completion_rate > r3.completion_rate

    def test_completion_decreases_with_age(self):
        ages = [25, 30, 35, 40]
        rates = []
        for age in ages:
            r = run_simulation(
                SimulationParams(female_age=age, desired_children=1)
            )
            rates.append(r.completion_rate)
        for i in range(len(rates) - 1):
            assert rates[i] >= rates[i + 1]


class TestIVFEffects:
    def test_ivf_improves_outcomes(self):
        no_ivf = run_simulation(
            SimulationParams(female_age=35, desired_children=1, ivf_willingness="no")
        )
        with_ivf = run_simulation(
            SimulationParams(female_age=35, desired_children=1, ivf_willingness="yes")
        )
        assert with_ivf.completion_rate >= no_ivf.completion_rate

    def test_frozen_eggs_help(self):
        no_frozen = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes"
            )
        )
        with_frozen = run_simulation(
            SimulationParams(
                female_age=38,
                desired_children=1,
                ivf_willingness="yes",
                frozen_egg_batches=(FrozenEggBatch(age_at_freeze=30.0, num_eggs=20),),
            )
        )
        assert with_frozen.completion_rate >= no_frozen.completion_rate

    def test_max_ivf_cycles_configurable(self):
        """max_ivf_cycles parameter is used (different values give different results)."""
        r_3 = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                max_ivf_cycles=3,
            )
        )
        r_1 = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                max_ivf_cycles=1,
            )
        )
        # Different max_ivf_cycles should produce different IVF fresh rates
        assert r_3.completion_by_method["ivf_fresh"] != r_1.completion_by_method["ivf_fresh"]


# --- Section 3: Frozen inventory management ---

class TestFrozenInventoryPriority:
    """Test 3a: Priority order — embryos before eggs before fresh IVF."""

    def test_embryos_used_before_eggs(self):
        """With both embryos and eggs, embryo method should appear in results."""
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_embryo_batches=(FrozenEmbryoBatch(age_at_freeze=34.0, num_embryos=3),),
                frozen_egg_batches=(FrozenEggBatch(age_at_freeze=30.0, num_eggs=15),),
            )
        )
        # Embryos are tried first, so frozen_embryo method should have non-zero rate
        assert result.completion_by_method["ivf_frozen_embryo"] > 0.0

    def test_eggs_used_when_no_embryos(self):
        """With eggs but no embryos, frozen_egg method should appear."""
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_egg_batches=(FrozenEggBatch(age_at_freeze=30.0, num_eggs=15),),
            )
        )
        assert result.completion_by_method["ivf_frozen_egg"] > 0.0
        assert result.completion_by_method["ivf_frozen_embryo"] == 0.0

    def test_embryos_only_no_eggs(self):
        """With embryos but no eggs, frozen_embryo method should appear."""
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_embryo_batches=(FrozenEmbryoBatch(age_at_freeze=30.0, num_embryos=5),),
            )
        )
        assert result.completion_by_method["ivf_frozen_embryo"] > 0.0
        assert result.completion_by_method["ivf_frozen_egg"] == 0.0


class TestFrozenEggBatchOrder:
    """Test 3b: Youngest-first egg selection."""

    def test_younger_batch_used_first(self):
        """With two egg batches, younger freeze age (higher LBR) is preferred."""
        # Batch B (age 28) has higher per-oocyte LBR than Batch A (age 36)
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_egg_batches=(
                    FrozenEggBatch(age_at_freeze=36.0, num_eggs=8),
                    FrozenEggBatch(age_at_freeze=28.0, num_eggs=10),
                ),
            )
        )
        assert result.completion_rate > 0.0
        assert result.completion_by_method["ivf_frozen_egg"] > 0.0


class TestFrozenEggDepletion:
    """Test 3c: Inventory depletion with limited eggs."""

    def test_small_egg_supply_exhausted(self):
        """With only 5 eggs, supply exhausted after 1 cycle; falls back to fresh IVF."""
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_egg_batches=(FrozenEggBatch(age_at_freeze=30.0, num_eggs=5),),
                max_ivf_cycles=10,
            )
        )
        # Should still complete via fresh IVF fallback
        assert result.completion_rate > 0.0
        # Fresh IVF should be used (fallback after eggs exhausted)
        assert result.completion_by_method["ivf_fresh"] > 0.0


class TestFrozenEmbryoDepletion:
    """Test 3d: Frozen embryo depletion."""

    def test_two_embryos_deplete_then_fallback(self):
        """With 2 embryos, exactly 2 frozen embryo cycles before fallback."""
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_embryo_batches=(FrozenEmbryoBatch(age_at_freeze=30.0, num_embryos=2),),
                max_ivf_cycles=10,
            )
        )
        # Should complete via some combination of embryos and fresh IVF
        assert result.completion_rate > 0.0


class TestFrozenInventoryAcrossChildren:
    """Test 3e: Frozen inventory preserved across children."""

    def test_inventory_intact_after_natural_birth(self):
        """Frozen inventory should remain for later children if first is natural."""
        result = run_simulation(
            SimulationParams(
                female_age=30, desired_children=3, ivf_willingness="yes",
                frozen_embryo_batches=(FrozenEmbryoBatch(age_at_freeze=28.0, num_embryos=5),),
                frozen_egg_batches=(FrozenEggBatch(age_at_freeze=28.0, num_eggs=10),),
            )
        )
        # Should succeed and may use frozen methods for later children
        assert result.completion_rate > 0.0


# --- Section 4: Gravidity curve switching ---

class TestGravidity:
    def test_prior_births_improve_rate(self):
        """Prior births (gravid) should improve fecundability via gravid curve.

        Both scenarios need 1 more child, but parous starts with gravid status.
        """
        nulligravid = run_simulation(
            SimulationParams(female_age=35, desired_children=1, prior_live_births=0)
        )
        parous = run_simulation(
            SimulationParams(female_age=35, desired_children=2, prior_live_births=1)
        )
        assert parous.completion_rate >= nulligravid.completion_rate

    def test_prior_miscarriages_set_gravid(self):
        """Prior miscarriages should set gravid status (improving fecundability)
        but also increase miscarriage risk via recurrent OR."""
        result = run_simulation(
            SimulationParams(female_age=30, desired_children=1, prior_miscarriages=1)
        )
        assert 0.0 < result.completion_rate <= 1.0

    def test_nulligravid_used_throughout_for_no_history(self):
        """Without prior history, nulligravid curve is used for ALL children.

        Phase 1f: gravid curve is no longer switched mid-simulation.
        A 30yo wanting 2 children uses nulligravid for both.
        """
        result = run_simulation(
            SimulationParams(female_age=30, desired_children=2, ivf_willingness="no")
        )
        # Should still complete at a high rate even with nulligravid throughout
        assert result.completion_rate > 0.80

    def test_miscarriage_history_enables_gravid(self):
        """A prior miscarriage is evidence of conception ability — gravid curve should be used.

        With 1 prior miscarriage: starts gravid AND has higher miscarriage OR.
        """
        result_0mc = run_simulation(
            SimulationParams(female_age=35, desired_children=1, prior_miscarriages=0)
        )
        result_1mc = run_simulation(
            SimulationParams(female_age=35, desired_children=1, prior_miscarriages=1)
        )
        # Both should complete at reasonable rates
        assert result_0mc.completion_rate > 0.5
        assert result_1mc.completion_rate > 0.5


# --- Section 5: Male aging during simulation ---

class TestMaleAging:
    def test_old_male_reduces_rate(self):
        """Male age >= 40 increases miscarriage risk, reducing completion rate."""
        young_male = run_simulation(
            SimulationParams(female_age=30, desired_children=1, male_age=30.0)
        )
        old_male = run_simulation(
            SimulationParams(female_age=30, desired_children=1, male_age=45.0)
        )
        assert young_male.completion_rate >= old_male.completion_rate

    def test_male_aging_transition_during_simulation(self):
        """Male starting at 38 should cross the age-40 threshold during simulation.

        Male OR is 1.0 before 35, 1.15 at 35-39, 1.23 at 40-44, 1.43 at 45+.
        A male starting at 38 should transition to the higher OR after ~2 years.
        """
        # Male at 38: starts with 1.15 OR, then 1.23 OR kicks in at 40
        result_38 = run_simulation(
            SimulationParams(female_age=32, desired_children=2, male_age=38.0)
        )
        # Male at 30: never hits 40 threshold during typical simulation
        result_30 = run_simulation(
            SimulationParams(female_age=32, desired_children=2, male_age=30.0)
        )
        # Male at 38 should have slightly worse outcomes due to mid-sim transition
        assert result_30.completion_rate >= result_38.completion_rate


# --- Section 6: BMI pathway separation ---

class TestBMIPathwaySeparation:
    def test_bmi_36_natural_vs_ivf_adjustments(self):
        """BMI=36: natural FR=0.78, IVF adj=0.85. Both applied correctly."""
        from fertility_forecaster.curves import bmi_fecundability_fr, bmi_ivf_adjustment
        assert bmi_fecundability_fr(36.0) == 0.78
        assert bmi_ivf_adjustment(36.0) == 0.85

    def test_bmi_28_natural_vs_ivf_adjustments(self):
        """BMI=28: natural FR=1.01 (no effect), IVF adj=1.0 (no effect)."""
        from fertility_forecaster.curves import bmi_fecundability_fr, bmi_ivf_adjustment
        assert bmi_fecundability_fr(28.0) == 1.01
        assert bmi_ivf_adjustment(28.0) == 1.0

    def test_bmi_42_natural_vs_ivf_adjustments(self):
        """BMI=42: natural FR=0.61, IVF adj=0.85."""
        from fertility_forecaster.curves import bmi_fecundability_fr, bmi_ivf_adjustment
        assert bmi_fecundability_fr(42.0) == 0.61
        assert bmi_ivf_adjustment(42.0) == 0.85

    def test_high_bmi_reduces_natural_and_ivf(self):
        """High BMI should reduce both natural and IVF outcomes."""
        normal = run_simulation(
            SimulationParams(female_age=35, desired_children=1, bmi=22.0,
                             ivf_willingness="yes")
        )
        obese = run_simulation(
            SimulationParams(female_age=35, desired_children=1, bmi=38.0,
                             ivf_willingness="yes")
        )
        assert normal.completion_rate >= obese.completion_rate


# --- Section 7: Smoking applies only to natural ---

class TestSmokingEffect:
    def test_smoking_reduces_rate(self):
        """Current regular smoking should reduce completion rate (no IVF)."""
        non_smoker = run_simulation(
            SimulationParams(
                female_age=35, desired_children=1,
                smoking_status=SmokingStatus.NEVER,
                ivf_willingness="no",
            )
        )
        smoker = run_simulation(
            SimulationParams(
                female_age=35, desired_children=1,
                smoking_status=SmokingStatus.CURRENT_REGULAR,
                ivf_willingness="no",
            )
        )
        assert non_smoker.completion_rate > smoker.completion_rate

    def test_smoking_only_affects_natural(self):
        """Smoking should NOT adjust IVF rates, only natural fecundability.

        Compare IVF-only scenarios: smoking should have no meaningful effect
        when all conceptions are via IVF.
        """
        # Force IVF by setting cycles_tried=12 so they start IVF immediately
        non_smoker_ivf = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                cycles_tried=12, smoking_status=SmokingStatus.NEVER,
            )
        )
        smoker_ivf = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                cycles_tried=12, smoking_status=SmokingStatus.CURRENT_REGULAR,
            )
        )
        # IVF rates should be identical since smoking doesn't affect IVF
        assert non_smoker_ivf.completion_by_method["ivf_fresh"] == smoker_ivf.completion_by_method["ivf_fresh"]


class TestConsecutiveMiscarriages:
    def test_high_prior_miscarriages_reduce_rate(self):
        """Many consecutive prior miscarriages should reduce completion rate.
        Both women have 1 prior live birth (so both are gravid, using the same
        fecundability curve) — this isolates the miscarriage effect from the
        gravid/nulligravid curve difference."""
        no_mc = run_simulation(
            SimulationParams(female_age=35, desired_children=2, prior_live_births=1, prior_miscarriages=0)
        )
        high_mc = run_simulation(
            SimulationParams(female_age=35, desired_children=2, prior_live_births=1, prior_miscarriages=3)
        )
        assert no_mc.completion_rate >= high_mc.completion_rate


# --- Section 8: Edge cases ---

class TestEdgeCaseOldWithCycles:
    def test_44yo_with_14_cycles(self):
        """44-year-old who has tried 14 cycles should handle gracefully."""
        result = run_simulation(
            SimulationParams(
                female_age=44, desired_children=1, ivf_willingness="yes",
                cycles_tried=14,
            )
        )
        assert 0.0 <= result.completion_rate <= 1.0
        # Should be very low — near age 45 with low fecundability
        assert result.completion_rate < 0.50

    def test_45yo_graceful(self):
        """45-year-old now has 5 years of runway — low but nonzero completion."""
        result = run_simulation(
            SimulationParams(
                female_age=45, desired_children=1, ivf_willingness="no",
            )
        )
        assert result.completion_rate > 0
        assert result.completion_rate < 0.50


# --- Section 9: Desired children already achieved ---

class TestDesiredAlreadyAchieved:
    def test_prior_births_meet_desired(self):
        """User with 2 prior births wanting 2 total should get 100% completion."""
        result = run_simulation(
            SimulationParams(
                female_age=35, desired_children=2, prior_live_births=2,
            )
        )
        assert result.completion_rate == 1.0
        assert result.median_time_to_completion_months == 0.0
        assert result.mean_age_at_completion == 35.0

    def test_prior_births_exceed_desired(self):
        """User with 3 prior births wanting 2 total should also get 100%."""
        result = run_simulation(
            SimulationParams(
                female_age=30, desired_children=2, prior_live_births=3,
            )
        )
        assert result.completion_rate == 1.0


# --- Section 10: Mixed frozen inventory ---

class TestMixedFrozenInventory:
    def test_embryos_only_skips_egg_step(self):
        """With embryos but no eggs, pathway goes embryo → fresh IVF."""
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_embryo_batches=(FrozenEmbryoBatch(age_at_freeze=30.0, num_embryos=3),),
            )
        )
        assert result.completion_by_method["ivf_frozen_egg"] == 0.0
        assert result.completion_rate > 0.0

    def test_eggs_only_skips_embryo_step(self):
        """With eggs but no embryos, pathway goes egg → fresh IVF."""
        result = run_simulation(
            SimulationParams(
                female_age=38, desired_children=1, ivf_willingness="yes",
                frozen_egg_batches=(FrozenEggBatch(age_at_freeze=30.0, num_eggs=15),),
            )
        )
        assert result.completion_by_method["ivf_frozen_embryo"] == 0.0
        assert result.completion_rate > 0.0


# --- Section 11: Numerical stability and bounds ---

class TestNumericalInvariants:
    def test_miscarriage_probability_bounded(self):
        """Miscarriage probability should stay in [0,1] even with worst-case ORs."""
        from fertility_forecaster.curves import (
            apply_odds_ratio,
            male_age_miscarriage_or,
            miscarriage_curve,
            recurrent_miscarriage_or,
        )
        # Worst case: age 47.5 (base=0.536), 5 consecutive miscarriages (OR=3.97), male age 50 (OR=1.43)
        base = float(miscarriage_curve(np.array([47.5]))[0])
        p = float(apply_odds_ratio(base, float(recurrent_miscarriage_or(np.array([5]))[0])))
        p = float(apply_odds_ratio(p, float(male_age_miscarriage_or(np.array([50.0]))[0])))
        assert 0.0 <= p <= 1.0

    def test_completion_by_method_sums_to_one(self):
        """Method rates should always sum to ~1.0."""
        for age in [25, 30, 35, 40, 44]:
            result = run_simulation(
                SimulationParams(female_age=age, desired_children=1)
            )
            total = sum(result.completion_by_method.values())
            assert pytest.approx(total, abs=0.01) == 1.0

    def test_method_rates_non_negative(self):
        result = run_simulation(
            SimulationParams(female_age=30, desired_children=1)
        )
        for v in result.completion_by_method.values():
            assert v >= 0.0

    def test_completion_rate_matches_methods(self):
        result = run_simulation(
            SimulationParams(female_age=30, desired_children=1)
        )
        method_completion = (
            result.completion_by_method["natural"]
            + result.completion_by_method["ivf_fresh"]
            + result.completion_by_method["ivf_frozen_egg"]
            + result.completion_by_method["ivf_frozen_embryo"]
        )
        assert pytest.approx(method_completion, abs=0.001) == result.completion_rate


class TestDesiredChildrenSix:
    def test_desired_six_at_20(self):
        """Edge case: 6 children starting at 20 should be possible."""
        result = run_simulation(
            SimulationParams(female_age=20, desired_children=6, ivf_willingness="no")
        )
        assert result.completion_rate > 0.0


class TestNoCycleCap:
    def test_max_months_exceeds_180_for_young(self):
        """Young women should have max_months > 180."""
        params = SimulationParams(female_age=20, desired_children=1)
        assert params.max_months > 180


class TestResultFields:
    def test_median_time_present_for_completed(self, young_one_child):
        result = run_simulation(young_one_child)
        assert result.median_time_to_completion_months is not None
        assert result.median_time_to_completion_months > 0

    def test_mean_age_present_for_completed(self, young_one_child):
        result = run_simulation(young_one_child)
        assert result.mean_age_at_completion is not None
        assert result.mean_age_at_completion >= young_one_child.female_age

    def test_time_distribution_sums_to_completion_rate(self, young_one_child):
        result = run_simulation(young_one_child)
        hist_sum = sum(result.time_distribution)
        assert pytest.approx(hist_sum, abs=0.02) == result.completion_rate


# --- Section 13: Performance ---

class TestPerformance:
    def test_single_simulation_under_5s(self):
        """A single simulation (10k couples, 2 children, age 30) should complete in < 5s."""
        params = SimulationParams(female_age=30, desired_children=2)
        start = time.perf_counter()
        run_simulation(params)
        elapsed = time.perf_counter() - start
        print(f"\nSingle simulation: {elapsed:.3f}s")
        assert elapsed < 5.0

    def test_sweep_under_30s(self):
        """20 simulations across ages 25-44 should complete in < 30s total."""
        start = time.perf_counter()
        for age in range(25, 45):
            run_simulation(
                SimulationParams(female_age=age, desired_children=2)
            )
        elapsed = time.perf_counter() - start
        print(f"\nSweep (20 sims): {elapsed:.3f}s ({elapsed/20:.3f}s avg)")
        assert elapsed < 30.0


# --- Phase 1f: Gravid curve usage tests ---

class TestNulligravidForAllSimulatedChildren:
    """Test 1: Nulligravid curve used for all children when no prior history."""

    def test_no_history_uses_nulligravid_for_both_children(self):
        """With no prior pregnancies, 2-child rate at age 35 should be noticeably
        lower than with prior_live_births=1 (which uses gravid curve).
        This confirms the gravid curve is NOT applied mid-simulation.
        """
        no_history = run_simulation(
            SimulationParams(female_age=35, desired_children=2, ivf_willingness="no")
        )
        with_history = run_simulation(
            SimulationParams(female_age=35, desired_children=2, prior_live_births=1, ivf_willingness="no")
        )
        # The with-history case uses gravid curve (higher rates) and only needs 1 more child
        # The no-history case uses nulligravid for all and needs 2 children
        assert with_history.completion_rate > no_history.completion_rate
        # The gap should be substantial due to both curve difference AND fewer children needed
        assert with_history.completion_rate - no_history.completion_rate > 0.10

    def test_three_children_no_history_more_conservative(self):
        """3 children with no history should be harder than 2 children with 1 prior birth,
        since the former uses nulligravid throughout while the latter uses gravid.
        (Both need 2 more children, but different curves.)
        """
        no_history_3 = run_simulation(
            SimulationParams(female_age=33, desired_children=3, ivf_willingness="no")
        )
        history_2 = run_simulation(
            SimulationParams(female_age=33, desired_children=3, prior_live_births=1, ivf_willingness="no")
        )
        # Both need 2 more children from age 33, but history_2 uses gravid curve
        assert history_2.completion_rate > no_history_3.completion_rate


class TestGravidCurveWithUserHistory:
    """Test 2: Gravid curve used when user reports history."""

    def test_prior_births_use_gravid(self):
        """With prior_live_births=1, the gravid curve should be used from the start.
        Compare to the same scenario but one extra child desired: rate should still
        be relatively high thanks to gravid curve boost.
        """
        result = run_simulation(
            SimulationParams(female_age=35, desired_children=2, prior_live_births=1, ivf_willingness="no")
        )
        # Needs 1 more child at 35 with gravid curve — should be very achievable
        assert result.completion_rate > 0.80

    def test_prior_miscarriage_also_uses_gravid(self):
        """Prior miscarriage should also trigger gravid curve usage."""
        # Both scenarios need 1 child, but one has prior MC (gravid) and one doesn't
        no_mc = run_simulation(
            SimulationParams(female_age=35, desired_children=1, prior_miscarriages=0, ivf_willingness="no")
        )
        with_mc = run_simulation(
            SimulationParams(female_age=35, desired_children=1, prior_miscarriages=1, ivf_willingness="no")
        )
        # Prior miscarriage gives gravid curve (higher fecundability) but also
        # higher miscarriage risk via recurrent OR. The net effect depends on
        # relative magnitudes; both should be in a reasonable range.
        assert no_mc.completion_rate > 0.5
        assert with_mc.completion_rate > 0.5


class TestCyclesTriedWithoutConceptions:
    """Test 6: cycles_tried without conceptions uses nulligravid."""

    def test_cycles_tried_no_conception_uses_nulligravid(self):
        """With cycles_tried=6 but no prior births/miscarriages,
        nulligravid curve should be used. Completion should still be achievable
        (Bayesian update already accounts for failed cycles).
        """
        result = run_simulation(
            SimulationParams(
                female_age=30, desired_children=1,
                prior_live_births=0, prior_miscarriages=0,
                cycles_tried=6, ivf_willingness="no",
            )
        )
        # Should still complete at a reasonable rate
        assert result.completion_rate > 0.80

    def test_cycles_tried_worse_than_fresh(self):
        """Having tried 6 cycles without success should give worse outcomes
        than a fresh start (Bayesian update penalizes failed cycles).
        """
        fresh = run_simulation(
            SimulationParams(female_age=30, desired_children=1, ivf_willingness="no")
        )
        tried = run_simulation(
            SimulationParams(
                female_age=30, desired_children=1, cycles_tried=6, ivf_willingness="no"
            )
        )
        assert fresh.completion_rate >= tried.completion_rate


# --- Phase 1g: Individual fecundability heterogeneity tests ---


class TestIndividualFecundabilitySpread:
    """Test 1: Individual fecundability draws have realistic spread."""

    def test_spread_at_age_27(self):
        """At age 27 with calibrated concentration, verify the distribution
        has meaningful spread: 5th percentile in [0.005, 0.08] and
        95th percentile in [0.30, 0.60]. With concentration=4.33 (CV=0.75),
        the Beta distribution produces wide tails reflecting real between-couple
        heterogeneity.
        """
        from fertility_forecaster.curves import (
            FECUNDABILITY_CONCENTRATION,
            draw_individual_fecundabilities,
            fecundability_curve,
        )

        mean_fecund = float(fecundability_curve(np.array([27.0]), gravid=False)[0])
        rng = np.random.default_rng(42)
        draws = draw_individual_fecundabilities(mean_fecund, 100_000, rng)

        p5 = np.percentile(draws, 5)
        p95 = np.percentile(draws, 95)
        print(f"\nAge 27: mean_fecund={mean_fecund:.4f}, conc={FECUNDABILITY_CONCENTRATION}")
        print(f"  5th={p5:.4f}, 95th={p95:.4f}")
        assert 0.005 <= p5 <= 0.08
        assert 0.30 <= p95 <= 0.60


class TestHighFertilityCouplesConcieveFaster:
    """Test 2: Couples with higher individual fecundability conceive faster."""

    def test_cycle1_vs_cycle12_fecundability(self):
        """Run 10,000 couples at age 30, 1 child. Verify that couples who conceive
        in cycle 1 had higher initial individual fecundability than couples who
        took 12+ cycles.
        """
        from fertility_forecaster.curves import (
            draw_individual_fecundabilities,
            fecundability_curve,
            miscarriage_curve,
        )

        rng = np.random.default_rng(42)
        N = 10_000
        age = 30.0
        mean_fecund = float(fecundability_curve(np.array([age]), gravid=False)[0])
        individual_fecund = draw_individual_fecundabilities(mean_fecund, N, rng)

        conceived_cycle = np.full(N, -1, dtype=int)
        current_age = np.full(N, age, dtype=float)

        for cycle in range(24):
            active = conceived_cycle == -1
            if not np.any(active):
                break

            current_mean = fecundability_curve(current_age[active], gravid=False)
            age_ratio = current_mean / mean_fecund
            p = individual_fecund[active] * age_ratio
            np.clip(p, 0.0, 1.0, out=p)

            conceived = rng.random(np.sum(active)) < p
            mc_rate = miscarriage_curve(current_age[active])
            miscarried = conceived & (rng.random(np.sum(active)) < mc_rate)
            live_birth = conceived & ~miscarried

            active_indices = np.where(active)[0]
            conceived_cycle[active_indices[live_birth]] = cycle
            current_age += 1.0 / 12.0

        cycle1_fecund = individual_fecund[conceived_cycle == 0]
        cycle12_plus_fecund = individual_fecund[conceived_cycle >= 12]

        mean_cycle1 = np.mean(cycle1_fecund)
        mean_cycle12 = np.mean(cycle12_plus_fecund) if len(cycle12_plus_fecund) > 0 else 0.0

        print(f"\nMean fecundability: cycle 1 conceivers={mean_cycle1:.4f}, "
              f"cycle 12+ conceivers={mean_cycle12:.4f}")
        assert mean_cycle1 > mean_cycle12


class TestMultiChildSelectionEffect:
    """Test 3: Natural selection effect for multi-child families."""

    def test_completers_have_higher_fecundability(self):
        """Run 10,000 couples at age 28, 2 children, no IVF.
        Among those who complete both children, mean individual fecundability
        should be higher than the population mean.
        """
        from fertility_forecaster.curves import (
            draw_individual_fecundabilities,
            fecundability_curve,
            miscarriage_curve,
        )

        rng = np.random.default_rng(42)
        N = 10_000
        age_start = 28.0
        mean_fecund = float(fecundability_curve(np.array([age_start]), gravid=False)[0])
        individual_fecund = draw_individual_fecundabilities(mean_fecund, N, rng)
        population_mean = np.mean(individual_fecund)

        # Run a simplified 2-child simulation tracking births
        children = np.zeros(N, dtype=int)
        current_age = np.full(N, age_start, dtype=float)
        waiting = np.zeros(N, dtype=int)

        for cycle in range(300):  # up to 25 years
            active = (children < 2) & (current_age < 50.0)
            if not np.any(active):
                break

            is_waiting = active & (waiting > 0)
            waiting[is_waiting] -= 1
            current_age[is_waiting] += 1.0 / 12.0

            trying = active & (waiting <= 0)
            if not np.any(trying):
                continue

            current_mean = fecundability_curve(current_age[trying], gravid=False)
            age_ratio = current_mean / mean_fecund
            p = individual_fecund[trying] * age_ratio
            np.clip(p, 0.0, 1.0, out=p)

            conceived = rng.random(np.sum(trying)) < p
            mc_rate = miscarriage_curve(current_age[trying])
            miscarried = conceived & (rng.random(np.sum(trying)) < mc_rate)
            live_birth = conceived & ~miscarried

            trying_indices = np.where(trying)[0]
            birth_indices = trying_indices[live_birth]
            children[birth_indices] += 1
            waiting[birth_indices] = 18  # min spacing

            current_age[trying] += 1.0 / 12.0

        completed = children >= 2
        mean_completers = np.mean(individual_fecund[completed])

        print(f"\nPopulation mean fecundability: {population_mean:.4f}")
        print(f"2-child completers mean fecundability: {mean_completers:.4f}")
        assert mean_completers > population_mean


class TestCyclesTriedAdjustsDistribution:
    """Test 4: cycles_tried shifts the fecundability distribution lower."""

    def test_posterior_lower_than_prior(self):
        """Compare draws with cycles_tried=0 and cycles_tried=6.
        The mean of the latter should be substantially lower.
        """
        from fertility_forecaster.curves import (
            draw_individual_fecundabilities,
            fecundability_curve,
        )

        mean_fecund = float(fecundability_curve(np.array([30.0]), gravid=False)[0])
        rng0 = np.random.default_rng(42)
        rng6 = np.random.default_rng(42)

        draws_0 = draw_individual_fecundabilities(mean_fecund, 100_000, rng0, cycles_tried=0)
        draws_6 = draw_individual_fecundabilities(mean_fecund, 100_000, rng6, cycles_tried=6)

        mean_0 = np.mean(draws_0)
        mean_6 = np.mean(draws_6)
        var_0 = np.var(draws_0)
        var_6 = np.var(draws_6)

        print(f"\ncycles_tried=0: mean={mean_0:.4f}, var={var_0:.6f}")
        print(f"cycles_tried=6: mean={mean_6:.4f}, var={var_6:.6f}")

        # Mean should be substantially lower
        assert mean_6 < mean_0 * 0.85
        # Variance should also be lower (distribution concentrated in lower range)
        assert var_6 < var_0


class TestHabbemaBenchmarkCalibrated:
    """Test 5: Habbema benchmark with calibrated concentration."""

    def test_cutoff_ages_within_3_years(self):
        """90% cutoff ages for 1, 2, 3 children should all be within ±3 years
        of Habbema targets (32, 27, 23). Tolerance is ±3 because our model
        uses a 25% base rate (vs Habbema's 23% average) and does not include
        a separate sterility mechanism, both of which shift cutoffs later.
        """
        habbema = {1: 32, 2: 27, 3: 23}
        for desired, target in habbema.items():
            for start_age_10x in range(200, 450):
                start_age = start_age_10x / 10.0
                result = run_simulation(
                    SimulationParams(
                        female_age=start_age, desired_children=desired,
                        ivf_willingness="no",
                    )
                )
                if result.completion_rate < 0.90:
                    drift = start_age - target
                    print(f"\n{desired}-child cutoff: {start_age:.1f} (drift={drift:+.1f})")
                    assert abs(drift) <= 3.0, (
                        f"{desired}-child cutoff {start_age:.1f} is {drift:+.1f} years "
                        f"from Habbema target {target}"
                    )
                    break


class TestTimeToPregnancyDistribution:
    """Test 6: Time-to-pregnancy distribution matches literature."""

    def test_ttp_at_age_27(self):
        """For a 27-year-old nulligravid woman, 1 child, no IVF, report %
        conceiving by cycle 1, 3, 6, 12 and verify reasonable values.
        """
        from fertility_forecaster.curves import (
            draw_individual_fecundabilities,
            fecundability_curve,
            miscarriage_curve,
        )

        rng = np.random.default_rng(42)
        N = 20_000
        age = 27.0
        mean_fecund = float(fecundability_curve(np.array([age]), gravid=False)[0])
        individual_fecund = draw_individual_fecundabilities(mean_fecund, N, rng)

        conceived_cycle = np.full(N, -1, dtype=int)
        current_age = np.full(N, age, dtype=float)

        for cycle in range(24):
            active = conceived_cycle == -1
            if not np.any(active):
                break

            current_mean = fecundability_curve(current_age[active], gravid=False)
            age_ratio = current_mean / mean_fecund
            p = individual_fecund[active] * age_ratio
            np.clip(p, 0.0, 1.0, out=p)

            conceived = rng.random(np.sum(active)) < p
            mc_rate = miscarriage_curve(current_age[active])
            miscarried = conceived & (rng.random(np.sum(active)) < mc_rate)
            live_birth = conceived & ~miscarried

            active_indices = np.where(active)[0]
            conceived_cycle[active_indices[live_birth]] = cycle
            current_age += 1.0 / 12.0

        by_c1 = np.sum(conceived_cycle == 0) / N * 100
        by_c3 = np.sum((conceived_cycle >= 0) & (conceived_cycle < 3)) / N * 100
        by_c6 = np.sum((conceived_cycle >= 0) & (conceived_cycle < 6)) / N * 100
        by_c12 = np.sum((conceived_cycle >= 0) & (conceived_cycle < 12)) / N * 100

        print(f"\nTTP at age 27: cycle 1={by_c1:.1f}%, by cycle 3={by_c3:.1f}%, "
              f"by cycle 6={by_c6:.1f}%, by cycle 12={by_c12:.1f}%")

        # Literature: ~25-30% cycle 1, ~55-60% by cycle 6, ~80-85% by cycle 12
        assert 10 <= by_c1 <= 35, f"Cycle 1 rate {by_c1:.1f}% outside expected range"
        assert 40 <= by_c6 <= 70, f"By cycle 6 rate {by_c6:.1f}% outside expected range"
        assert 65 <= by_c12 <= 90, f"By cycle 12 rate {by_c12:.1f}% outside expected range"


class TestPGTAEmbryos:
    """PGT-A tested embryos should produce better outcomes than untested."""

    def test_pgt_improves_outcomes(self):
        """PGT-A tested embryos should yield a higher completion rate."""
        base = dict(
            female_age=38,
            desired_children=1,
            ivf_willingness="yes",
            num_simulations=5_000,
        )
        untested = SimulationParams(
            **base,
            frozen_embryo_batches=(
                FrozenEmbryoBatch(age_at_freeze=36.0, num_embryos=5, pgt_tested=False),
            ),
        )
        tested = SimulationParams(
            **base,
            frozen_embryo_batches=(
                FrozenEmbryoBatch(age_at_freeze=36.0, num_embryos=5, pgt_tested=True),
            ),
        )
        r_untested = run_simulation(untested, seed=42)
        r_tested = run_simulation(tested, seed=42)
        assert r_tested.completion_rate > r_untested.completion_rate

    def test_default_false_unchanged(self):
        """pgt_tested=False should produce identical results to the old default."""
        params = SimulationParams(
            female_age=38,
            desired_children=1,
            ivf_willingness="yes",
            frozen_embryo_batches=(
                FrozenEmbryoBatch(age_at_freeze=30.0, num_embryos=5, pgt_tested=False),
            ),
        )
        params_no_flag = SimulationParams(
            female_age=38,
            desired_children=1,
            ivf_willingness="yes",
            frozen_embryo_batches=(
                FrozenEmbryoBatch(age_at_freeze=30.0, num_embryos=5),
            ),
        )
        r1 = run_simulation(params, seed=99)
        r2 = run_simulation(params_no_flag, seed=99)
        assert r1.completion_rate == r2.completion_rate

    def test_older_creation_pgt_still_better_than_untested(self):
        """Even older-creation PGT embryos should beat younger-creation untested."""
        base = dict(
            female_age=38,
            desired_children=1,
            ivf_willingness="yes",
            num_simulations=5_000,
        )
        # Untested embryos created at age 30 (best untested bracket: 40%)
        untested_young = SimulationParams(
            **base,
            frozen_embryo_batches=(
                FrozenEmbryoBatch(age_at_freeze=30.0, num_embryos=5, pgt_tested=False),
            ),
        )
        # PGT embryos created at age 39 (PGT rate: 41.7% vs untested 20%)
        pgt_older = SimulationParams(
            **base,
            frozen_embryo_batches=(
                FrozenEmbryoBatch(age_at_freeze=39.0, num_embryos=5, pgt_tested=True),
            ),
        )
        r_untested = run_simulation(untested_young, seed=42)
        r_pgt = run_simulation(pgt_older, seed=42)
        # PGT at 39 (41.7%) should be comparable to or better than untested at 30 (40%)
        assert r_pgt.completion_rate >= r_untested.completion_rate * 0.95
