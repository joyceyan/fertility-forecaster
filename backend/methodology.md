# Fertility Forecaster: Data Sources & Methodology

## Overview

Fertility Forecaster is a Monte Carlo simulation tool that estimates the probability of completing a desired family size given a user's age, health, reproductive history, and available fertility interventions. The model simulates 10,000 virtual couples cycle-by-cycle, incorporating published data on natural conception rates, miscarriage risk, IVF outcomes, and frozen egg/embryo success rates.

This document describes every data source used in the model, what it contributes, and how the inputs interact.

---

## How the Model Works

At a high level, the simulation runs a loop for each virtual couple:

1. At initialization, each couple draws an individual fecundability from a Beta distribution, representing their inherent "fertility type." This creates realistic between-couple variation: some couples are naturally more fertile than others.
2. Each menstrual cycle (~1 month), the model calculates a personalized per-cycle conception probability by applying age-ratio decline to the couple's individual fecundability, then multiplying by BMI and smoking adjustments. Permanently sterile couples get zero probability.
3. A random draw determines whether conception occurs.
4. If conception occurs, a second random draw determines whether the pregnancy results in a live birth or miscarriage, based on age-dependent miscarriage rates adjusted for recurrent miscarriage history and male partner age.
5. If the couple fails to conceive naturally for `cycles_before_ivf` consecutive cycles (default 12) and is open to assisted reproduction, the model uses frozen embryos first (if available), then frozen eggs (if available), then fresh IVF — up to `max_ivf_cycles` fresh IVF cycles (default 3) across the couple's lifetime. Frozen embryo and frozen egg cycles do not count toward this cap.
6. The loop repeats until the couple achieves their desired number of children or the woman turns 45.

After simulating all 10,000 couples, the model reports what percentage achieved the desired family size, how long it took, and what proportion of successes came from each conception method (natural, fresh IVF, frozen egg IVF, frozen embryo transfer).

---

## Data Sources

### 1. Base Per-Cycle Conception Probability

**What it determines:** The starting per-cycle probability of natural conception, before any age, BMI, or smoking adjustments are applied. This is the anchor from which all natural conception rates are derived.

**Source:** Habbema JDF, et al. "Realizing a desired family size: when should couples start?" *Human Reproduction*. 2015. [DOI: 10.1093/humrep/dev148](https://doi.org/10.1093/humrep/dev148), building on the Leridon (2004) natural fertility model.

**The value:** We set the base per-cycle conception probability at **0.23 (23%)**. This rate applies at full strength to the youngest ages in the model (18–24); it then declines with age via the fecundability ratios in Section 2.

**Where does 23% come from?** Habbema et al. 2015 states: "The model assumes an average natural per cycle conception rate (fecundability) of 23% between age 20 and 30 years, which is in line with data of contemporary populations." This value originates from the Leridon (2004) micro-simulation model, which is based on historical data on monthly pregnancy chances in natural non-contraceptive populations collected by Henry (1965) and Leridon (1977).

A commonly cited figure in reproductive medicine is ~25% per cycle for young women, but this likely reflects upward selection bias — studies that recruit couples actively trying to conceive (e.g., the PRESTO cohort, Wesselink 2017) tend to enroll higher-fertility couples and exclude the lower end of the fertility distribution. The 23% figure is designed to represent the general population, including those who may take longer to conceive.

This value was validated by calibrating the model against Habbema's benchmark cutoff ages (the ages at which 90% of couples complete 1, 2, or 3 children), where our model matches within ±2 years across all benchmarks.

**How it's used in the model:** This 23% base rate is multiplied by age-specific fecundability ratios (see Section 2) to produce the population-mean conception probability at each age. Individual couples then draw from a Beta distribution centered on this mean (see Section 8), producing realistic between-couple variation.

---

### 2. Age-Specific Fecundability (Natural Conception)

**What it determines:** How the per-cycle probability of conception changes with the woman's age, relative to the 18-24 baseline.

**Source:** Wesselink AK, et al. "Age and fecundability in a North American preconception cohort study." *American Journal of Obstetrics and Gynecology*. 2017. [DOI: 10.1016/j.ajog.2017.09.002](https://doi.org/10.1016/j.ajog.2017.09.002)

**About the study:** The PRESTO (Pregnancy Study Online) cohort is a web-based prospective study of North American couples actively trying to conceive. This analysis included 2,962 couples with no history of infertility who had been trying for ≤3 cycles at enrollment. Couples were followed for up to 12 menstrual cycles.

**What we use:** The study reports adjusted fecundability ratios (FRs) by age group relative to the 21-24 age reference group, stratified by gravidity (whether the woman has ever been pregnant before). We use both the nulligravid and gravid curves from Table 3 to construct two separate age-fecundability functions. At each age, we multiply the base per-cycle conception probability (see Section 1) by the appropriate FR.

**Expansion to ages 18-20:** The Wesselink study's youngest group is 21-24. Our model allows users as young as 18, so we extend the reference group to 18-24 by assuming that women aged 18-20 have the same fecundability ratio (1.00) as the 21-24 group. This is a reasonable assumption: there is no published evidence of meaningful fecundability differences within the 18-24 range, and the biological rationale for age-related decline (diminishing ovarian reserve, increased oocyte aneuploidy) does not apply at these young ages.

**Key data points (fecundability ratios, adjusted, relative to ages 21-24, from Table 3):**

| Age group | Nulligravid | Previously gravid |
|-----------|-------------|-------------------|
| 18-24     | 1.00        | 1.00              |
| 25-27     | 0.88        | 0.92              |
| 28-30     | 0.80        | 0.95              |
| 31-33     | 0.84        | 0.88              |
| 34-36     | 0.68        | 0.96              |
| 37-39     | 0.51        | 0.70              |
| 40-45     | 0.20        | 0.48              |

The divergence between the two curves at older ages is striking — at 34-36, the gravid FR is 0.96 (almost no decline) while the nulligravid FR is 0.68. This is a real selection effect, not an artifact. Steiner & Jukic 2016 ([DOI: 10.1016/j.fertnstert.2016.02.028](https://doi.org/10.1016/j.fertnstert.2016.02.028)) independently corroborate this: women who have never conceived by their late 30s likely include a higher proportion with underlying subfertility conditions (e.g., tubal occlusion, endometriosis, anovulation), which drags the nulligravid group average down. The model uses these raw ratios directly — no cap is applied.

**How it's used in the model:** Gravidity status is determined once at initialization from user-reported history: nulligravid if the user has zero prior pregnancies (live births + miscarriages = 0), gravid otherwise. This selection is fixed for the entire simulation — in-simulation conceptions do not switch a couple from nulligravid to gravid. The rationale is that the simulation's own Monte Carlo filtering (couples who conceive quickly are inherently more fertile) already handles the selection effect that the gravid curve captures in observational data.

The population-mean fecundability at the starting age is used as the center of the Beta distribution from which individual fecundabilities are drawn (see Section 8). During the simulation, age-related decline is applied as a ratio: `individual_fecund × (current_pop_mean / starting_pop_mean)`.

---

### 3. Age-Specific Miscarriage Rates

**What it determines:** The probability that a conception results in pregnancy loss rather than live birth, at each maternal age.

**Source:** Magnus MC, et al. "Role of maternal age and pregnancy history in risk of miscarriage: prospective register based study." *BMJ*. 2019. [DOI: 10.1136/bmj.l869](https://doi.org/10.1136/bmj.l869)

**About the study:** A population-based registry study of all 421,201 pregnancies in Norway between 2009 and 2013, linking data from the Medical Birth Register, the Norwegian Patient Register, and the induced abortion register. This is one of the largest and most comprehensive studies of miscarriage risk by age.

**What we use:** Age-specific miscarriage rates adjusted for induced abortions, and age-adjusted odds ratios for recurrent miscarriage.

**Key data points (miscarriage rate by age, adjusted for induced abortions):**

| Age group | Miscarriage rate |
|-----------|-----------------|
| < 20      | 15.8%           |
| 20-24     | 11.3%           |
| 25-29     | 9.8%            |
| 30-34     | 10.8%           |
| 35-39     | 16.7%           |
| 40-44     | 32.2%           |
| 45+       | 53.6%           |

The study also provides recurrent miscarriage risk, showing a strong pattern of increasing odds after consecutive losses:

| Prior consecutive miscarriages | Age-adjusted OR |
|-------------------------------|-----------------|
| 0 (first pregnancy)          | 1.00 (ref)      |
| 1                             | 1.54            |
| 2                             | 2.21            |
| 3+                            | 3.97            |

**How it's used in the model:** Every time a simulated conception occurs, the model draws a miscarriage outcome using the age-appropriate rate. The rate is further adjusted if the woman has experienced consecutive miscarriages within the simulation, using odds ratios applied on the odds scale via the formula: `adjusted_prob = (base × OR) / (1 - base + base × OR)`. This prevents impossible values (>100%) at high base rates. A miscarriage adds a 3-month recovery period before the couple resumes trying. Consecutive miscarriages are tracked per couple and reset to zero on live birth.

---

### 4. Male Age and Miscarriage Risk

**What it determines:** An additional adjustment to miscarriage rates when the male partner is 40 or older.

**Source:** Boxem AJ, et al. "Preconception and Early-Pregnancy Body Mass Index in Women and Men, Time to Pregnancy, and Risk of Miscarriage." *JAMA Network Open*. 2024. [DOI: 10.1001/jamanetworkopen.2024.36157](https://doi.org/10.1001/jamanetworkopen.2024.36157)

**About the study:** A population-based prospective cohort study (Generation R) of 3,604 women and their partners in Rotterdam, Netherlands, followed from preconception through birth.

**What we use:** Men aged ≥40 have approximately 2x the odds of their partner experiencing a miscarriage (OR ≈ 2.09 relative to men aged 30-34). Male age does not meaningfully affect per-cycle conception probability after controlling for female age (consistent with findings from Wesselink 2017).

**How it's used in the model:** If a male partner age is provided and is ≥40, the miscarriage OR of 2.09 is applied to the miscarriage probability (on the odds scale, stacked multiplicatively with any recurrent miscarriage adjustment). The male ages during the simulation alongside the female, so this adjustment activates when he crosses age 40 mid-simulation.

---

### 5. BMI and Natural Conception

**What it determines:** The effect of female BMI on per-cycle natural conception probability.

**Source:** McKinnon CJ, et al. "Body mass index, physical activity and fecundability in a North American preconception cohort study." *Fertility and Sterility*. 2016. [DOI: 10.1016/j.fertnstert.2016.04.011](https://doi.org/10.1016/j.fertnstert.2016.04.011)

**About the study:** Analysis of 2,062 female pregnancy planners from the PRESTO cohort (same cohort as the fecundability data). Reports female-specific fecundability ratios by BMI category.

**What we use:**

| Female BMI   | Fecundability Ratio | 95% CI     |
|-------------|---------------------|------------|
| < 18.5      | 1.05                | 0.76-1.46  |
| 18.5-24     | 1.00 (ref)          | —          |
| 25-29       | 1.01                | 0.89-1.15  |
| 30-34       | 0.98                | 0.82-1.18  |
| 35-39       | 0.78                | 0.60-1.02  |
| 40-44       | 0.61                | 0.42-0.88  |
| ≥ 45        | 0.42                | 0.23-0.76  |

A key finding is that BMI below 35 has essentially no meaningful effect on fecundability. The significant reductions begin at BMI 35+, and they're dose-dependent.

**How it's used in the model:** The FR for the user's BMI category is applied as a multiplier to the per-cycle natural conception probability. This stacks with the age and smoking adjustments.

---

### 6. BMI and IVF Success

**What it determines:** The effect of female obesity on IVF live birth rates.

**Source:** Sermondade N, et al. "Female obesity is negatively associated with live birth rate following IVF: a systematic review and meta-analysis." *Human Reproduction Update*. 2019. [DOI: 10.1093/humupd/dmz011](https://doi.org/10.1093/humupd/dmz011)

**About the study:** A systematic review and meta-analysis of 21 studies evaluating the relationship between female BMI and IVF outcomes.

**What we use:** Obese women (BMI ≥ 30) had a risk ratio of 0.85 (95% CI 0.82-0.87) for live birth compared to normal weight women. The effect persisted even with donor eggs, suggesting the uterine environment is affected.

**How it's used in the model:** When BMI ≥ 30, the per-transfer IVF live birth rate is multiplied by 0.85. This applies to all IVF pathways: fresh IVF, frozen egg IVF, and frozen embryo transfer.

---

### 7. Smoking and Fecundability

**What it determines:** The effect of female cigarette smoking on per-cycle conception probability.

**Source:** Wesselink AK, et al. "Prospective study of cigarette smoking and fecundability." *Human Reproduction*. 2019. [DOI: 10.1093/humrep/dey372](https://doi.org/10.1093/humrep/dey372)

**About the study:** Analysis of 5,473 female pregnancy planners from the PRESTO cohort. Reports fecundability ratios by smoking status.

**What we use:**

| Smoking status                  | Fecundability Ratio |
|--------------------------------|---------------------|
| Never smoker                   | 1.00 (ref)          |
| Former smoker                  | 0.89                |
| Current occasional smoker      | 0.88                |
| Current regular (≥10/day, ≥10yr)| 0.77                |

The effect is dose-dependent: heavy long-term smokers see a 23% reduction in per-cycle conception probability.

**How it's used in the model:** Applied as a multiplier to natural conception probability only. IVF success rates are not adjusted for smoking (the IVF data already reflects its own population characteristics).

---

### 8. Individual Fecundability Heterogeneity

**What it determines:** The between-couple variation in fertility, which is essential for realistic multi-child family completion modeling.

**Why it matters:** Population-level fecundability curves represent averages across all couples. In reality, some couples are inherently more fertile than others due to factors not captured by age, BMI, or smoking alone (e.g., ovarian reserve, sperm quality, uterine receptivity). Without modeling this heterogeneity, the simulation treats all couples as equally fertile, which causes systematic errors: single-child predictions may be acceptable, but multi-child predictions become too optimistic because the model doesn't account for the fact that low-fertility couples who struggle with their first child will also struggle with subsequent children.

**Implementation:** At initialization, each couple draws an individual per-cycle conception probability from a Beta distribution centered on the population mean for their starting age and gravidity status:

- `alpha = mean_fecund × concentration`
- `beta = (1 - mean_fecund) × concentration + cycles_tried`

The **concentration parameter** (set to 5.0) controls how much fertility varies between couples. Lower values produce more spread; higher values make couples more homogeneous. This value was calibrated against Habbema et al. 2015 benchmarks (90% completion cutoff ages for 1/2/3 children: 32/27/23). At concentration = 5.0, the model produces cutoffs of approximately 31.6/27.7/23.9 — all within ±1 year.

With a population mean of 23% and concentration of 5.0, the resulting Beta(1.15, 3.85) distribution produces the following spread across couples:

| Percentile | Per-cycle conception rate |
|------------|--------------------------|
| 5th        | 2.1%                     |
| 10th       | 3.9%                     |
| 25th       | 9.2%                     |
| 50th       | 19.3%                    |
| 75th       | 33.4%                    |
| 90th       | 48.0%                    |
| 95th       | 56.7%                    |

The middle 90% of couples receive a per-cycle rate between 2.1% and 56.7%. A couple at the 95th percentile has roughly a coin-flip chance of conceiving each cycle, while a couple at the 5th percentile faces long odds — and that personal rate is fixed for life. This is what makes the multi-child predictions realistic: a couple who struggled with child #1 will also struggle with child #2.

**Bayesian updating for couples already trying:** If the user reports `cycles_tried > 0` (they've already been trying without success), the Beta distribution's beta parameter is increased by the number of failed cycles. This shifts the entire distribution lower, reflecting the Bayesian insight that couples who haven't conceived quickly are more likely to have below-average fertility:

| Cycles tried | Mean rate | Middle 90% range |
|-------------|-----------|------------------|
| 0 (fresh)   | 23.0%     | 2.1% – 56.7%    |
| 6 months    | 10.5%     | 0.8% – 28.2%    |
| 12 months   | 6.8%      | 0.5% – 18.6%    |

After 12 months of unsuccessful trying, the model estimates the couple's expected per-cycle rate has dropped to ~7% — not because their biology changed, but because the population of couples who take that long to conceive is disproportionately lower-fertility.

**Source for the Bayesian framework:** van Eekelen R, et al. "External validation of a dynamic prediction model for repeated predictions of natural conception over time." *Human Reproduction*. 2018. [DOI: 10.1093/humrep/dey317](https://doi.org/10.1093/humrep/dey317)

**Age-ratio decline:** During the simulation, each couple's individual rate declines with age proportionally to the population-level curve: `p_natural = individual_fecund × (current_pop_mean / starting_pop_mean) × bmi_fr × smoking_fr`. This preserves between-couple variation while applying the correct age-related decline trajectory.

---

### 9. Permanent Sterility

**What it determines:** The probability that a couple is permanently unable to conceive naturally, independent of age-related fecundability decline.

**Source:** Habbema JDF, et al. 2015 / Leridon model. Age-dependent cumulative probability of permanent sterility (e.g., premature ovarian failure, complete tubal occlusion).

**Key data points:**

| Female age | Cumulative sterility probability |
|-----------|----------------------------------|
| 20        | 0.5%                             |
| 25        | 1.0%                             |
| 30        | 2.0%                             |
| 35        | 5.0%                             |
| 38        | 10.0%                            |
| 40        | 17.0%                            |
| 42        | 30.0%                            |
| 45        | 55.0%                            |

**How it's used in the model:** At initialization, each couple draws a random sterility threshold uniformly from [0, 1]. As the woman ages, the cumulative sterility probability increases. When it exceeds the couple's threshold, they become permanently sterile for natural conception (IVF can still bypass most causes of sterility).

**Conditioning on known fertility:** If the user reports prior conceptions (live births or miscarriages), the sterility threshold is conditioned on the fact that they demonstrably conceived at a known age. The threshold is drawn uniformly from [sterility_curve(last_fertile_age), 1.0] rather than [0, 1], ensuring the model never assigns premature sterility to someone who was recently fertile.

---

### 10. IVF Success Rates (Fresh Cycles)

**What it determines:** Per-transfer live birth rates for IVF using the woman's current-age eggs.

**Sources:**
- CDC Assisted Reproductive Technology National Summary Reports (public dataset, updated annually)
- UK Human Fertilisation and Embryology Authority (HFEA) dataset (250K+ treatment records, publicly downloadable)

**What we use (approximate per-transfer live birth rates by female age):**

| Female age | LBR per transfer |
|-----------|-----------------|
| < 35      | 0.40            |
| 35-37     | 0.30            |
| 38-40     | 0.20            |
| 41-42     | 0.12            |
| 43-44     | 0.05            |
| 45+       | 0.02            |

**How it's used in the model:** After `cycles_before_ivf` consecutive cycles of failed natural conception (default 12, configurable), if the user is open to assisted reproduction, the simulation switches to an assisted reproduction pathway. Frozen embryos are used first (if available), then frozen eggs (if available), then fresh IVF. Each IVF cycle takes approximately 2 months. The per-transfer success rate depends on the woman's current age at the time of the cycle. If the user has a BMI ≥ 30, the rate is further multiplied by 0.85 (Sermondade adjustment).

**Lifetime IVF cap:** The couple may attempt up to `max_ivf_cycles` fresh IVF cycles total across their entire reproductive timeline (default 3). Once exhausted, IVF is permanently unavailable — the couple cannot re-qualify for IVF by trying naturally again. This reflects the clinical reality that most couples undergo a limited number of IVF cycles, consistent with the Habbema et al. 2015 modeling framework.

---

### 11. Frozen Egg (Oocyte Cryopreservation) Outcomes

**What it determines:** Success rates when using previously frozen eggs for IVF.

**Sources:**

*Oocyte survival and overall live birth rates:*
Hirsch A, et al. "Planned oocyte cryopreservation: a systematic review and meta-regression analysis." *Human Reproduction Update*. 2024. [DOI: 10.1093/humupd/dmae009](https://doi.org/10.1093/humupd/dmae009)

A systematic review and meta-analysis of 10 studies covering 8,750 women who underwent planned egg freezing. The oocyte survival rate after thawing was 78.5%. Live birth rate per patient was 52% for women who froze at age ≤35 and 19% for women who froze at age ≥40.

*Number of eggs needed and per-oocyte live birth rate:*
Namath A, et al. "The number of autologous, vitrified mature oocytes needed to obtain three euploid blastocysts increases with age." *Fertility and Sterility*. 2025. [DOI: 10.1016/j.fertnstert.2025.04.023](https://doi.org/10.1016/j.fertnstert.2025.04.023)

Analysis of 1,041 thaw cycles. Expected live births per thawed mature oocyte:
- Frozen at < 35: 0.13 per oocyte
- Frozen at 35-37: 0.09 per oocyte (estimated)
- Frozen at 38-40: 0.06 per oocyte (estimated)
- Frozen at > 40: 0.04 per oocyte

To achieve ~93% probability of at least one child, women need approximately 15 mature oocytes if frozen before 35, ~30 if frozen at ≥38, and ~45 if frozen after 40.

*Age at transfer does not affect success:*
Barrett FG, et al. "Maternal age at transfer following autologous oocyte cryopreservation is not associated with live birth rates." *Journal of Assisted Reproduction and Genetics*. 2024. [DOI: 10.1007/s10815-024-03149-y](https://doi.org/10.1007/s10815-024-03149-y)

In a study of 169 oocyte thaw patients matched to 338 IVF patients, the age at which the embryo was transferred did not predict live birth rate after controlling for age at retrieval. This means a woman who froze eggs at 30 and uses them at 40 has success rates determined by her egg quality at 30, not her uterine age at 40.

**How it's used in the model:** Users can input multiple batches of frozen eggs, each with an age at freeze and number of eggs. When assisted reproduction is triggered, frozen eggs are prioritized after frozen embryos but before fresh IVF (youngest-frozen batches first, as they have the highest per-oocyte success rates). In each frozen egg cycle, up to 9 eggs are thawed. The survival rate (78.5%) is applied, then the per-oocyte LBR based on age at freeze is used to compute the per-cycle success probability: `p = 1 - (1 - per_oocyte_rate) ^ surviving_eggs`. The egg supply is decremented each cycle. The BMI IVF adjustment (Sermondade) applies to frozen egg cycles.

---

### 12. Frozen Embryo Transfer Outcomes

**What it determines:** Per-transfer live birth rates for previously created and frozen embryos.

**Source:** CDC ART National Summary Reports, combined with the Barrett 2024 finding that transfer age doesn't affect outcomes.

**What we use (approximate per-transfer live birth rates, by age at embryo creation):**

| Age at embryo creation | LBR per transfer |
|------------------------|-----------------|
| < 35                   | 0.40            |
| 35-37                  | 0.30            |
| 38-40                  | 0.20            |
| 41-42                  | 0.12            |
| > 42                   | 0.05            |

These mirror the fresh IVF rates because embryo quality is primarily determined at the time of creation. The key insight (from Barrett 2024) is that these rates apply regardless of how old the woman is when the transfer occurs.

#### PGT-A Tested (Euploid) Embryos

Embryos that have undergone preimplantation genetic testing for aneuploidy (PGT-A) and confirmed euploid have higher per-transfer live birth rates because the dominant age-dependent failure mode — chromosomal aneuploidy — has been removed.

**Source:** Jiang et al. 2025 "Live birth rates after single euploid frozen embryo transfer: a retrospective cohort study." *Journal of Ovarian Research*. [DOI: 10.1186/s13048-025-01602-9](https://doi.org/10.1186/s13048-025-01602-9), n=1,037 single euploid transfers.

| Age at embryo creation | Untested LBR | PGT-A tested LBR | Source |
|------------------------|-------------|-------------------|--------|
| < 35                   | 0.40        | 0.545             | Jiang 2025 |
| 35-37                  | 0.30        | 0.540             | Jiang 2025 |
| 38-40                  | 0.20        | 0.417             | Jiang 2025 |
| 41-42                  | 0.12        | 0.350             | Extrapolated |
| > 42                   | 0.05        | 0.300             | Extrapolated |

The 41-42 and 43+ brackets are extrapolated downward from the Jiang data. Even euploid embryos from older oocytes have reduced implantation potential from non-chromosomal factors such as mitochondrial quality and epigenetic integrity.

**How it's used in the model:** Users can input multiple batches of frozen embryos, optionally marking each batch as PGT-A tested. Frozen embryos are the highest-priority assisted reproduction pathway (since they skip the egg-to-embryo attrition step and have higher per-transfer success). One embryo is transferred per cycle, and the batch is decremented. Batches are used youngest-creation-age first. When a batch is depleted, the next batch is used. The BMI IVF adjustment applies. When a batch is marked as PGT-A tested, the euploid transfer rates are used instead of the aggregate rates.

---

## Simulation Parameters

The following parameters can be configured by the user:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `female_age` | (required) | Woman's current age (18-45) |
| `desired_children` | (required) | Target family size (1-6) |
| `male_age` | None | Male partner age (affects miscarriage risk if ≥40) |
| `bmi` | None | Female BMI (affects natural conception and IVF) |
| `smoking_status` | never | Never, former, current occasional, current regular |
| `ivf_willingness` | last_resort | "yes", "no", or "last_resort" |
| `cycles_before_ivf` | 12 | Months of natural trying before IVF eligibility |
| `max_ivf_cycles` | 3 | Lifetime cap on fresh IVF cycles |
| `min_spacing_months` | 18 | Minimum months between births |
| `prior_live_births` | 0 | Number of existing children |
| `prior_miscarriages` | 0 | Consecutive miscarriages since last live birth (resets to 0 after each live birth; used to seed recurrent miscarriage risk) |
| `cycles_tried` | 0 | Months already spent trying (shifts fecundability draws lower) |
| `frozen_egg_batches` | () | Batches of frozen eggs (age at freeze, count) |
| `frozen_embryo_batches` | () | Batches of frozen embryos (age at freeze, count) |
| `age_at_last_birth` | None | Used to condition sterility threshold |
| `age_at_last_miscarriage` | None | Used to condition sterility threshold |
| `num_simulations` | 10,000 | Number of Monte Carlo couples |

---

## Factors NOT Included (and Why)

**Caffeine:** Purdue-Smithe et al. 2022 ([DOI: 10.1093/ajcn/nqab435](https://doi.org/10.1093/ajcn/nqab435)) found no association between female caffeine intake and fecundability at low-to-moderate consumption levels when measured via both serum metabolites and self-report.

**Alcohol:** Pooled analysis from PRESTO and the Danish SnartForaeldre cohort (Høyer et al. 2020, [DOI: 10.1093/humrep/dez294](https://doi.org/10.1093/humrep/dez294)) found little evidence of an association between male alcohol consumption and fecundability. Female alcohol data also lacks a strong consistent association at moderate intake.

**Marijuana:** Wise et al. 2018 ([DOI: 10.1136/jech-2017-209755](https://doi.org/10.1136/jech-2017-209755)) from PRESTO found no overall association for either female or male use.

**Stress:** Schliep et al. 2019 ([DOI: 10.1097/EDE.0000000000001079](https://doi.org/10.1097/EDE.0000000000001079)) found a meaningful association (FOR = 0.71 in highest stress quartile), but stress is difficult to quantify as a stable user input.

**Vitamin D:** Subramanian et al. 2022 ([DOI: 10.1093/humrep/deac155](https://doi.org/10.1093/humrep/deac155)) found no association with miscarriage risk.

**Male BMI:** Sundaram et al. 2017 ([DOI: 10.1093/humrep/dex001](https://doi.org/10.1093/humrep/dex001)) found that individual male BMI was not associated with TTP when modeled alone — only the couple-level effect (both partners BMI ≥35) was significant. Zhang et al. 2022 ([DOI: 10.1111/jog.15299](https://doi.org/10.1111/jog.15299)) found no association between male BMI and IVF outcomes.

**Intercourse frequency:** This is a meaningful factor (the base fecundability curves assume regular intercourse), but it is behavioral, variable over time, and potentially sensitive to ask about. Considered for a future version.

---

## Limitations

This model provides population-level statistical estimates. Individual outcomes depend on many biological factors not captured here, including ovarian reserve (AMH levels), specific medical conditions (PCOS, endometriosis, tubal factors), sperm parameters, and genetic factors. The model assumes no underlying fertility diagnoses beyond what is captured by age, BMI, smoking, and reproductive history.

All parameter values are derived from published research on specific populations (primarily North American and Northern European). Results may not generalize equally across all ethnic groups and geographic populations.

The model does not account for the emotional, financial, or logistical costs of extended trying periods or IVF cycles.

This tool is not medical advice. Consult a healthcare provider for personalized fertility assessment.
