"""Monte Carlo fertility simulation engine."""

from __future__ import annotations

import numpy as np

from .curves import (
    ART_MISCARRIAGE_RATE,
    OOCYTE_SURVIVAL_RATE,
    apply_odds_ratio,
    bmi_fecundability_fr,
    bmi_ivf_adjustment,
    draw_individual_fecundabilities,
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
from .models import SimulationParams, SimulationResult

# Method codes for birth_methods array
_NATURAL = 1
_IVF_FRESH = 2
_IVF_FROZEN_EGG = 3
_IVF_FROZEN_EMBRYO = 4


def run_simulation(
    params: SimulationParams,
    seed: int = 42,
) -> SimulationResult:
    """Run a vectorized Monte Carlo fertility simulation.

    Loops over cycles (max determined by age to 45), with vectorized NumPy
    operations across all simulated couples within each cycle.
    """
    N = params.num_simulations
    rng = np.random.default_rng(seed)
    bmi_fr = bmi_fecundability_fr(params.bmi)
    bmi_ivf = bmi_ivf_adjustment(params.bmi)
    smoking_fr = smoking_fecundability_fr(params.smoking_status)

    # Handle case where desired family size is already met
    if params.prior_live_births >= params.desired_children:
        return SimulationResult(
            completion_rate=1.0,
            median_time_to_completion_months=0.0,
            mean_age_at_completion=params.female_age,
            time_distribution=[1.0] + [0.0] * 11,
            completion_by_method={
                "natural": 1.0,
                "ivf_fresh": 0.0,
                "ivf_frozen_egg": 0.0,
                "ivf_frozen_embryo": 0.0,
                "incomplete": 0.0,
            },
        )

    # --- Per-couple state arrays ---
    age = np.full(N, params.female_age, dtype=float)
    children_born = np.full(N, params.prior_live_births, dtype=int)
    cycles_tried = np.full(N, params.cycles_tried, dtype=int)
    active = np.ones(N, dtype=bool)
    waiting_months = np.zeros(N, dtype=int)
    on_ivf = np.zeros(N, dtype=bool)
    total_ivf_cycles_used = np.zeros(N, dtype=int)
    ivf_exhausted = np.zeros(N, dtype=bool)  # per-child: resets after each live birth

    # Gravidity: fixed at initialization based on user-reported history.
    # When no prior pregnancies, use nulligravid curve for ALL simulated children
    # (the simulation's own filtering handles the selection effect).
    # When user reports prior pregnancies, use gravid curve (real information).
    has_prior_conceptions = params.prior_live_births > 0 or params.prior_miscarriages > 0
    use_gravid = has_prior_conceptions
    consecutive_miscarriages = np.full(N, params.prior_miscarriages, dtype=int)

    # Male age tracking
    has_male_age = params.male_age is not None
    if has_male_age:
        male_age = np.full(N, params.male_age, dtype=float)

    # Sterility tracking — each couple gets a random threshold; they become
    # permanently sterile (for natural conception) when the age-dependent
    # cumulative sterility probability exceeds their threshold.
    # If user has prior conceptions, condition the threshold on known fertility:
    # their threshold must be above the sterility curve at their last known
    # fertile age (since they demonstrably conceived at that age).
    if has_prior_conceptions:
        if params.age_at_last_birth is not None:
            last_fertile_age = params.age_at_last_birth
        elif params.age_at_last_miscarriage is not None:
            last_fertile_age = params.age_at_last_miscarriage
        else:
            last_fertile_age = params.female_age - 2.0  # conservative fallback
        min_threshold = float(sterility_curve(np.array([last_fertile_age]))[0])
        sterility_thresholds = min_threshold + rng.random(N) * (1.0 - min_threshold)
    else:
        sterility_thresholds = rng.random(N)
    already_sterile = np.zeros(N, dtype=bool)

    # --- Frozen embryo batches (sorted youngest-first) ---
    embryo_batches_sorted = sorted(params.frozen_embryo_batches, key=lambda b: b.age_at_freeze)
    B_e = len(embryo_batches_sorted)
    if B_e > 0:
        embryo_batch_remaining = np.zeros((N, B_e), dtype=int)
        embryo_batch_ages = np.array([b.age_at_freeze for b in embryo_batches_sorted], dtype=float)
        embryo_batch_pgt = np.array([b.pgt_tested for b in embryo_batches_sorted], dtype=bool)
        for i, b in enumerate(embryo_batches_sorted):
            embryo_batch_remaining[:, i] = b.num_embryos
    else:
        embryo_batch_remaining = np.zeros((N, 0), dtype=int)
        embryo_batch_ages = np.array([], dtype=float)
        embryo_batch_pgt = np.array([], dtype=bool)

    # --- Frozen egg batches (sorted youngest-first) ---
    egg_batches_sorted = sorted(params.frozen_egg_batches, key=lambda b: b.age_at_freeze)
    B_g = len(egg_batches_sorted)
    if B_g > 0:
        egg_batch_remaining = np.zeros((N, B_g), dtype=int)
        egg_batch_ages = np.array([b.age_at_freeze for b in egg_batches_sorted], dtype=float)
        for i, b in enumerate(egg_batches_sorted):
            egg_batch_remaining[:, i] = b.num_eggs
    else:
        egg_batch_remaining = np.zeros((N, 0), dtype=int)
        egg_batch_ages = np.array([], dtype=float)

    using_frozen_embryo = np.zeros(N, dtype=bool)
    using_frozen_egg = np.zeros(N, dtype=bool)
    current_embryo_batch_idx = np.full(N, -1, dtype=int)
    current_egg_batch_idx = np.full(N, -1, dtype=int)

    # Birth tracking
    birth_ages = np.full((N, params.desired_children), np.nan, dtype=float)
    birth_methods = np.zeros((N, params.desired_children), dtype=int)

    # --- Individual fecundability draws ---
    # Each couple gets a fixed "fertility type" drawn from a Beta distribution.
    # Age-related decline is applied as a ratio on top of their individual value.
    init_mean_fecund = float(fecundability_curve(np.array([params.female_age]), gravid=use_gravid)[0])
    individual_fecund = draw_individual_fecundabilities(
        init_mean_fecund, N, rng, cycles_tried=params.cycles_tried,
    )
    # Store the starting-age population mean for computing age ratios
    starting_age_mean = init_mean_fecund

    max_cycles = params.max_months

    for _cycle in range(max_cycles):
        if not np.any(active):
            break

        # 1. Deactivate couples where age >= 45
        too_old = active & (age >= 45.0)
        active[too_old] = False

        # 2. Handle waiting couples
        is_waiting = active & (waiting_months > 0)
        waiting_months[is_waiting] -= 1
        age[is_waiting] += 1.0 / 12.0
        if has_male_age:
            male_age[is_waiting] += 1.0 / 12.0
        if not np.any(active & ~is_waiting):
            continue

        # 3. Update sterility status — couples become permanently sterile
        #    when the cumulative sterility prob for their age exceeds their threshold.
        current_sterility_prob = sterility_curve(age)
        newly_sterile = ~already_sterile & (current_sterility_prob >= sterility_thresholds)
        already_sterile |= newly_sterile

        # 4. Identify trying couples (active AND not waiting)
        trying = active & (waiting_months <= 0)
        if not np.any(trying):
            continue

        eligible_for_assisted = (
            trying
            & (cycles_tried >= params.cycles_before_ivf)
            & (params.ivf_willingness != "no")
            & ~on_ivf
            & ~ivf_exhausted
            & ~using_frozen_embryo
            & ~using_frozen_egg
        )
        if np.any(eligible_for_assisted):
            # Priority 1: Frozen embryos
            if B_e > 0:
                for bidx in range(B_e):
                    can_use = eligible_for_assisted & (current_embryo_batch_idx == -1) & (embryo_batch_remaining[:, bidx] > 0)
                    if np.any(can_use):
                        using_frozen_embryo[can_use] = True
                        current_embryo_batch_idx[can_use] = bidx
                        eligible_for_assisted = eligible_for_assisted & ~can_use

            # Priority 2: Frozen eggs
            if B_g > 0:
                for bidx in range(B_g):
                    can_use = eligible_for_assisted & (current_egg_batch_idx == -1) & (egg_batch_remaining[:, bidx] > 0)
                    if np.any(can_use):
                        using_frozen_egg[can_use] = True
                        current_egg_batch_idx[can_use] = bidx
                        eligible_for_assisted = eligible_for_assisted & ~can_use

            # Priority 3: Fresh IVF
            still_eligible = eligible_for_assisted
            on_ivf[still_eligible] = True

        # 6. Compute conception probability
        p_conceive = np.zeros(N, dtype=float)

        # Natural pathway (sterile couples get p=0)
        natural = trying & ~on_ivf & ~using_frozen_embryo & ~using_frozen_egg
        if np.any(natural):
            # Age-ratio decline: current population mean / starting population mean
            current_mean = fecundability_curve(age[natural], gravid=use_gravid)
            if starting_age_mean > 0:
                age_ratio = current_mean / starting_age_mean
            else:
                age_ratio = np.zeros_like(current_mean)
            p_natural = individual_fecund[natural] * age_ratio
            p_natural *= bmi_fr * smoking_fr
            p_natural[already_sterile[natural]] = 0.0
            p_conceive[natural] = p_natural

        # Fresh IVF pathway
        # ivf_success_rate returns live birth rates; convert to clinical
        # pregnancy rates so the separate miscarriage roll yields correct LBR.
        ivf_mask = trying & on_ivf
        if np.any(ivf_mask):
            lbr = ivf_success_rate(age[ivf_mask]) * bmi_ivf
            p_conceive[ivf_mask] = lbr / (1.0 - ART_MISCARRIAGE_RATE)

        # Frozen embryo pathway
        fe_mask = trying & using_frozen_embryo
        if np.any(fe_mask):
            fe_indices = current_embryo_batch_idx[fe_mask]
            creation_ages = embryo_batch_ages[fe_indices]
            fe_pgt = embryo_batch_pgt[fe_indices]
            p_fe = np.where(
                fe_pgt,
                frozen_embryo_transfer_rate_pgt(creation_ages),
                frozen_embryo_transfer_rate(creation_ages),
            ) * bmi_ivf
            p_conceive[fe_mask] = p_fe / (1.0 - ART_MISCARRIAGE_RATE)
            # Decrement 1 embryo per cycle from current batch
            fe_rows = np.where(fe_mask)[0]
            for r in fe_rows:
                bidx = current_embryo_batch_idx[r]
                if bidx >= 0 and embryo_batch_remaining[r, bidx] > 0:
                    embryo_batch_remaining[r, bidx] -= 1

        # Frozen egg pathway
        fg_mask = trying & using_frozen_egg
        if np.any(fg_mask):
            fg_rows = np.where(fg_mask)[0]
            fg_indices = current_egg_batch_idx[fg_mask]
            freeze_ages = egg_batch_ages[fg_indices]
            # Thaw min(remaining, 9) eggs
            eggs_remaining_for_mask = np.array([
                egg_batch_remaining[r, current_egg_batch_idx[r]] for r in fg_rows
            ])
            eggs_this_cycle = np.minimum(eggs_remaining_for_mask, 9)
            surviving = eggs_this_cycle.astype(float) * OOCYTE_SURVIVAL_RATE
            per_oocyte = frozen_egg_per_oocyte_rate(freeze_ages)
            p_fg = (1.0 - (1.0 - per_oocyte) ** surviving) * bmi_ivf
            p_conceive[fg_mask] = p_fg / (1.0 - ART_MISCARRIAGE_RATE)
            # Decrement eggs (never below 0)
            for i, r in enumerate(fg_rows):
                bidx = current_egg_batch_idx[r]
                if bidx >= 0:
                    egg_batch_remaining[r, bidx] = max(
                        0, egg_batch_remaining[r, bidx] - int(eggs_this_cycle[i])
                    )

        # Clip conception probability to [0, 1] for numerical stability
        np.clip(p_conceive, 0.0, 1.0, out=p_conceive)

        # 7. Random draw for conception
        conceived = trying & (rng.random(N) < p_conceive)

        # 8. Miscarriage check
        # Natural conceptions: age-dependent miscarriage with recurrent/male-age ORs
        p_miscarriage = miscarriage_curve(age)
        p_miscarriage = apply_odds_ratio(p_miscarriage, recurrent_miscarriage_or(consecutive_miscarriages))
        if has_male_age:
            p_miscarriage = apply_odds_ratio(p_miscarriage, male_age_miscarriage_or(male_age))
        # ART conceptions: flat pooled miscarriage rate (timeline adjustment only;
        # live birth rates already account for age-dependent losses)
        art_conceived = conceived & (on_ivf | using_frozen_embryo | using_frozen_egg)
        p_miscarriage[art_conceived] = ART_MISCARRIAGE_RATE
        # Clip miscarriage probability to [0, 1] for numerical stability
        np.clip(p_miscarriage, 0.0, 1.0, out=p_miscarriage)
        miscarried = conceived & (rng.random(N) < p_miscarriage)
        live_birth = conceived & ~miscarried

        # 9. Live birth
        if np.any(live_birth):
            birth_idx = children_born[live_birth]
            rows = np.where(live_birth)[0]
            for r, idx in zip(rows, birth_idx):
                if idx < params.desired_children:
                    birth_ages[r, idx] = age[r]
                    if using_frozen_embryo[r]:
                        birth_methods[r, idx] = _IVF_FROZEN_EMBRYO
                    elif using_frozen_egg[r]:
                        birth_methods[r, idx] = _IVF_FROZEN_EGG
                    elif on_ivf[r]:
                        birth_methods[r, idx] = _IVF_FRESH
                    else:
                        birth_methods[r, idx] = _NATURAL

            children_born[live_birth] += 1
            waiting_months[live_birth] = params.min_spacing_months
            cycles_tried[live_birth] = 0
            on_ivf[live_birth] = False
            using_frozen_embryo[live_birth] = False
            using_frozen_egg[live_birth] = False
            current_embryo_batch_idx[live_birth] = -1
            current_egg_batch_idx[live_birth] = -1
            # Reset IVF cycles for next child — cap is per-child (Habbema 2015)
            total_ivf_cycles_used[live_birth] = 0
            ivf_exhausted[live_birth] = False
            consecutive_miscarriages[live_birth] = 0

            # Deactivate completed couples
            done = live_birth & (children_born >= params.desired_children)
            active[done] = False

        # 10. Miscarriage recovery
        if np.any(miscarried):
            waiting_months[miscarried] = 3
            consecutive_miscarriages[miscarried] += 1
            on_ivf[miscarried] = False
            using_frozen_embryo[miscarried] = False
            using_frozen_egg[miscarried] = False
            current_embryo_batch_idx[miscarried] = -1
            current_egg_batch_idx[miscarried] = -1

        # 11. No conception
        no_conception = trying & ~conceived
        cycles_tried[no_conception] += 1

        # IVF cycle tracking — per-child cap, resets after live birth
        ivf_no_conceive = no_conception & on_ivf
        total_ivf_cycles_used[ivf_no_conceive] += 1
        newly_exhausted = ivf_no_conceive & (total_ivf_cycles_used >= params.max_ivf_cycles)
        on_ivf[newly_exhausted] = False
        ivf_exhausted[newly_exhausted] = True  # permanent

        # Frozen embryo exhaustion
        if B_e > 0:
            fe_no_conceive = no_conception & using_frozen_embryo
            if np.any(fe_no_conceive):
                fe_nc_rows = np.where(fe_no_conceive)[0]
                for r in fe_nc_rows:
                    bidx = current_embryo_batch_idx[r]
                    if bidx >= 0 and embryo_batch_remaining[r, bidx] <= 0:
                        # Try next batch
                        found_next = False
                        for next_bidx in range(bidx + 1, B_e):
                            if embryo_batch_remaining[r, next_bidx] > 0:
                                current_embryo_batch_idx[r] = next_bidx
                                found_next = True
                                break
                        if not found_next:
                            using_frozen_embryo[r] = False
                            current_embryo_batch_idx[r] = -1

        # Frozen egg exhaustion
        if B_g > 0:
            fg_no_conceive = no_conception & using_frozen_egg
            if np.any(fg_no_conceive):
                fg_nc_rows = np.where(fg_no_conceive)[0]
                for r in fg_nc_rows:
                    bidx = current_egg_batch_idx[r]
                    if bidx >= 0 and egg_batch_remaining[r, bidx] <= 0:
                        found_next = False
                        for next_bidx in range(bidx + 1, B_g):
                            if egg_batch_remaining[r, next_bidx] > 0:
                                current_egg_batch_idx[r] = next_bidx
                                found_next = True
                                break
                        if not found_next:
                            using_frozen_egg[r] = False
                            current_egg_batch_idx[r] = -1

        # 12. Advance age
        ivf_or_frozen = trying & (on_ivf | using_frozen_embryo | using_frozen_egg)
        natural_trying = trying & ~on_ivf & ~using_frozen_embryo & ~using_frozen_egg
        age[ivf_or_frozen] += 4.0 / 12.0
        age[natural_trying] += 1.0 / 12.0
        if has_male_age:
            male_age[ivf_or_frozen] += 4.0 / 12.0
            male_age[natural_trying] += 1.0 / 12.0

    # --- Result compilation ---
    completed = children_born >= params.desired_children
    completion_rate = float(np.mean(completed))

    # Median time to completion
    if np.any(completed):
        last_birth_col = params.desired_children - 1
        last_birth_ages = birth_ages[completed, last_birth_col]
        time_months = (last_birth_ages - params.female_age) * 12.0
        median_time = float(np.median(time_months))
        mean_age = float(np.mean(last_birth_ages))
    else:
        median_time = None
        mean_age = None

    # Time distribution (histogram)
    if np.any(completed):
        hist_values, _ = np.histogram(
            time_months, bins=12, range=(0, max_cycles)
        )
        time_distribution = (hist_values / N).tolist()
    else:
        time_distribution = [0.0] * 12

    # Completion by method (hierarchy-based classification)
    if np.any(completed):
        completed_methods = birth_methods[completed]
        actual_births = completed_methods > 0

        has_frozen_embryo = np.any(completed_methods == _IVF_FROZEN_EMBRYO, axis=1)
        has_frozen_egg = np.any(completed_methods == _IVF_FROZEN_EGG, axis=1) & ~has_frozen_embryo
        has_ivf_fresh = (
            np.any(completed_methods == _IVF_FRESH, axis=1)
            & ~has_frozen_embryo
            & ~has_frozen_egg
        )
        all_natural = (
            np.all((completed_methods == _NATURAL) | ~actual_births, axis=1)
            & ~has_frozen_embryo
            & ~has_frozen_egg
            & ~has_ivf_fresh
        )

        natural_rate = float(np.sum(all_natural)) / N
        ivf_fresh_rate = float(np.sum(has_ivf_fresh)) / N
        ivf_frozen_egg_rate = float(np.sum(has_frozen_egg)) / N
        ivf_frozen_embryo_rate = float(np.sum(has_frozen_embryo)) / N
    else:
        natural_rate = 0.0
        ivf_fresh_rate = 0.0
        ivf_frozen_egg_rate = 0.0
        ivf_frozen_embryo_rate = 0.0

    incomplete_rate = 1.0 - completion_rate

    completion_by_method = {
        "natural": natural_rate,
        "ivf_fresh": ivf_fresh_rate,
        "ivf_frozen_egg": ivf_frozen_egg_rate,
        "ivf_frozen_embryo": ivf_frozen_embryo_rate,
        "incomplete": incomplete_rate,
    }

    return SimulationResult(
        completion_rate=completion_rate,
        median_time_to_completion_months=median_time,
        mean_age_at_completion=mean_age,
        time_distribution=time_distribution,
        completion_by_method=completion_by_method,
    )
