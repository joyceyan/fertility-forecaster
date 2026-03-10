# Fertility Forecaster: Data Sources & Methodology

## Overview

Fertility Forecaster is a Monte Carlo simulation tool that estimates the probability of completing a desired family size given a user's age, health, reproductive history, and available fertility interventions. The model simulates 10,000 virtual couples cycle-by-cycle, incorporating published data on natural conception rates, miscarriage risk, IVF outcomes, and frozen egg/embryo success rates.

This document describes every data source used in the model, what it contributes, and how the inputs interact.

---

## How the Model Works

At a high level, the simulation runs a loop for each virtual couple:

1. At initialization, each couple draws an individual fecundability from a Beta distribution, representing their inherent "fertility type." This creates realistic between-couple variation: some couples are naturally more fertile than others.
2. Each menstrual cycle (~1 month), the model calculates a personalized per-cycle conception probability by applying age-ratio decline to the couple's individual fecundability, then multiplying by BMI and smoking adjustments.
3. A random draw determines whether conception occurs.
4. If conception occurs, a second random draw determines whether the pregnancy results in a live birth or miscarriage, based on age-dependent miscarriage rates adjusted for recurrent miscarriage history and male partner age.
5. If the couple fails to conceive naturally for `cycles_before_ivf` consecutive cycles (default 12) and is open to assisted reproduction, the model uses frozen embryos first (if available), then frozen eggs (if available), then fresh IVF — up to `max_ivf_cycles` fresh IVF cycles per child (default 3). The counter resets after each live birth. Frozen embryo and frozen egg cycles do not count toward this cap.
6. The loop repeats until the couple achieves their desired number of children or the woman turns 50.

After simulating all 10,000 couples, the model reports what percentage achieved the desired family size, how long it took, and what proportion of successes came from each conception method (natural, fresh IVF, frozen egg IVF, frozen embryo transfer).

---

## Data Sources

### 1. Base Per-Cycle Conception Probability

**What it determines:** The starting per-cycle probability of natural conception, before any age, BMI, or smoking adjustments are applied. This is the anchor from which all natural conception rates are derived.

**Sources:**
- American Society for Reproductive Medicine (ASRM). ["Defining Infertility."](https://www.reproductivefacts.org/news-and-publications/fact-sheets-and-infographics/defining-infertility/) Patient fact sheet citing 25–30% per cycle for women in their 20s to early 30s.
- Wesselink AK, et al. "Age and fecundability in a North American preconception cohort study." *American Journal of Obstetrics and Gynecology*. 2017. [DOI: 10.1016/j.ajog.2017.09.002](https://doi.org/10.1016/j.ajog.2017.09.002). Uses the 21–24 age group as the highest-fecundability reference (FR = 1.00).
- Habbema JDF, et al. "Realizing a desired family size: when should couples start?" *Human Reproduction*. 2015. [DOI: 10.1093/humrep/dev148](https://doi.org/10.1093/humrep/dev148). Reports an average fecundability of 23% across ages 20–30, building on the Leridon (2004) natural fertility model.

**The value:** We set the base per-cycle conception probability at **0.23 (23%)**. This rate applies at full strength to the youngest ages in the model (18–24); it then declines with age via the fecundability ratios in Section 2.

**Where does 23% come from?** Habbema et al. 2015 uses 23% as the population-average fecundability across ages 20–30. The ASRM cites 25–30% as the peak for women in their early 20s. We use 23% rather than the higher peak estimate because the Wesselink PRESTO cohort — from which we derive our age-decline ratios — includes unknowingly subfertile and sterile women in its enrollment pool (it excludes only self-reported infertility and women trying >3 cycles). This means the Wesselink fecundability ratios already partially reflect population-level sterility, pulling the observed ratios down from what a purely fertile population would show. Using 23% as the base anchors the model to the same population-average level as Habbema while avoiding over-optimistic rates at younger ages.

This value was validated by calibrating the model against Habbema's benchmark cutoff ages (the ages at which 90% of couples complete 1, 2, or 3 children), where our model matches within ±1.5 years across all without-IVF benchmarks.

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

**Extrapolation beyond age 42.5:** The Wesselink study's oldest age group is 40–45, centered at 42.5. The simulation runs until age 50, so we need rates for ages 42.5–50. Rather than flat-lining at the last observed FR (which would overestimate fertility for women in their mid-to-late 40s), we linearly taper both curves from their 42.5 values to 0 at age 50. This produces a gradual decline — nulligravid fecundability drops from FR=0.20 at 42.5 to 0 at 50, and gravid from FR=0.48 to 0. This taper serves a similar role to the Leridon sterility curve used in Habbema's model: it progressively removes couples from the fertile pool at older ages. Without it, the model would be unrealistically optimistic for women starting in their early-to-mid 40s, as couples with favorable Beta draws would accumulate small but nonzero conception probabilities over many years.

**How it's used in the model:** Gravidity status is determined once at initialization from user-reported history: nulligravid if the user has zero prior pregnancies (live births + miscarriages = 0), gravid otherwise. This selection is fixed for the entire simulation — in-simulation conceptions do not switch a couple from nulligravid to gravid. The rationale is that the simulation's own Monte Carlo filtering (couples who conceive quickly are inherently more fertile) already handles the selection effect that the gravid curve captures in observational data.

The population-mean fecundability at the starting age is used as the center of the Beta distribution from which individual fecundabilities are drawn (see Section 8). During the simulation, age-related decline is applied as a ratio: `individual_fecund × (current_pop_mean / starting_pop_mean)`.

---

### 3. Age-Specific Miscarriage Rates

**What it determines:** The probability that a conception results in pregnancy loss rather than live birth, at each maternal age.

**Source:** Magnus MC, et al. "Role of maternal age and pregnancy history in risk of miscarriage: prospective register based study." *BMJ*. 2019. [DOI: 10.1136/bmj.l869](https://doi.org/10.1136/bmj.l869)

**About the study:** A population-based registry study of all 421,201 pregnancies in Norway between 2009 and 2013, linking data from the Medical Birth Register, the Norwegian Patient Register, and the induced abortion register. This is one of the largest and most comprehensive studies of miscarriage risk by age.

**What we use:** Age-specific miscarriage rates adjusted for induced abortions, and age-adjusted odds ratios for recurrent miscarriage.

**Key data points (miscarriage rate by age, adjusted for induced abortions):**

| Age group | Magnus rate | Model rate |
|-----------|-------------|------------|
| < 20      | 15.8%       | 9.8%       |
| 20-24     | 11.3%       | 9.8%       |
| 25-29     | 9.8%        | 9.8%       |
| 30-34     | 10.8%       | 10.8%      |
| 35-39     | 16.7%       | 16.7%      |
| 40-44     | 32.2%       | 32.2%      |
| 45+       | 53.6%       | 53.6%      |

**Flattening below age 25:** The Magnus study shows elevated miscarriage rates for women under 25 (15.8% at <20, 11.3% at 20-24). However, the study covers *all* recognized pregnancies in Norway, including unplanned ones. The authors note this elevated young-age risk may reflect "unrecognised social causes of miscarriage" (lifestyle factors, delayed prenatal care associated with unplanned pregnancies) rather than biology. Since our model targets women who are actively planning pregnancies, we flatten the curve below age 25 to the 25-29 baseline of 9.8%, removing the social-confounder artifact while preserving the well-established age-related rise after 30.

The study also provides recurrent miscarriage risk, showing a strong pattern of increasing odds after consecutive losses:

| Prior consecutive miscarriages | Age-adjusted OR |
|-------------------------------|-----------------|
| 0 (first pregnancy)          | 1.00 (ref)      |
| 1                             | 1.54            |
| 2                             | 2.21            |
| 3+                            | 3.97            |

**Comparison with Habbema/Leridon miscarriage rates:** Our Magnus 2019 rates are notably more pessimistic at older ages. Habbema/Leridon assumed ~25% at age 40 and ~35% at age 45, while Magnus 2019 reports 32.2% at 40-44 and 53.6% at 45+. This divergence is most pronounced above age 42 and contributes to our model being slightly more conservative for late starters at moderate confidence levels.

**How it's used in the model:** Every time a simulated conception occurs, the model draws a miscarriage outcome using the age-appropriate rate. The rate is further adjusted if the woman has experienced consecutive miscarriages within the simulation, using odds ratios applied on the odds scale via the formula: `adjusted_prob = (base × OR) / (1 - base + base × OR)`. This prevents impossible values (>100%) at high base rates. A miscarriage adds a 3-month recovery period before the couple resumes trying. Consecutive miscarriages are tracked per couple and reset to zero on live birth.

---

### 4. Male Age and Miscarriage Risk

**What it determines:** An additional adjustment to miscarriage rates when the male partner is 35 or older.

**Source:** du Fossé NA, et al. "Advanced paternal age is associated with an increased risk of spontaneous miscarriage: a systematic review and meta-analysis." *Human Reproduction Update*. 2020. [DOI: 10.1093/humupd/dmaa010](https://doi.org/10.1093/humupd/dmaa010)

**About the study:** A systematic review and meta-analysis of 11 cohort studies and 8 case-control studies examining the association between paternal age and miscarriage risk. This is the most comprehensive synthesis of the evidence on this topic.

**What we use:** The meta-analysis reports age-bracket-specific odds ratios for miscarriage:

| Male age | Odds ratio | 95% CI |
|----------|-----------|--------|
| < 35     | 1.00 (ref) | — |
| 35–39    | 1.15      | 1.04–1.27 |
| 40–44    | 1.23      | 1.06–1.43 |
| ≥ 45     | 1.43      | 1.13–1.81 |

We omit the 30–34 bracket (OR 1.04, 95% CI 0.90–1.21) as the effect is negligible and the confidence interval crosses 1.0. Male age does not meaningfully affect per-cycle conception probability after controlling for female age (consistent with findings from Wesselink 2017).

**How it's used in the model:** If a male partner age is provided, the appropriate OR is applied based on his current age bracket (1.0 if <35, 1.15 if 35–39, 1.23 if 40–44, 1.43 if ≥45). The OR is applied to the miscarriage probability on the odds scale, stacked multiplicatively with any recurrent miscarriage adjustment. The male ages during the simulation alongside the female, so this adjustment activates when he crosses age thresholds mid-simulation.

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

The **concentration parameter** (set to 4.23, corresponding to CV = 0.80) controls how much fertility varies between couples. Lower values produce more spread; higher values make couples more homogeneous. This value was calibrated against all 18 Habbema et al. 2015 benchmark scenarios (1–3 children × 50/75/90% thresholds × with/without IVF), achieving MAE = 0.49 years, max error = 1.4 years, and RMSE = 0.62.

With a population mean of 23% and concentration of 4.23, the resulting Beta(0.97, 3.26) distribution produces the following spread across couples:

| Percentile | Per-cycle conception rate |
|------------|--------------------------|
| 5th        | 1.4%                     |
| 10th       | 3.0%                     |
| 25th       | 8.0%                     |
| 50th       | 18.6%                    |
| 75th       | 34.0%                    |
| 90th       | 50.1%                    |
| 95th       | 59.6%                    |

The middle 90% of couples receive a per-cycle rate between 1.4% and 59.6%. A couple at the 95th percentile has roughly a coin-flip chance of conceiving each cycle, while a couple at the 5th percentile faces long odds — and that personal rate is fixed for life. This is what makes the multi-child predictions realistic: a couple who struggled with child #1 will also struggle with child #2.

**Bayesian updating for couples already trying:** If the user reports `cycles_tried > 0` (they've already been trying without success), the Beta distribution's beta parameter is increased by the number of failed cycles. This shifts the entire distribution lower, reflecting the Bayesian insight that couples who haven't conceived quickly are more likely to have below-average fertility:

| Cycles tried | Mean rate | Middle 90% range |
|-------------|-----------|------------------|
| 0 (fresh)   | 23.0%     | 1.4% – 59.6%    |
| 6 months    | 9.5%      | 0.5% – 27.3%    |
| 12 months   | 6.0%      | 0.3% – 17.6%    |

After 12 months of unsuccessful trying, the model estimates the couple's expected per-cycle rate has dropped to ~6% — not because their biology changed, but because the population of couples who take that long to conceive is disproportionately lower-fertility.

**Source for the Bayesian framework:** van Eekelen R, et al. "External validation of a dynamic prediction model for repeated predictions of natural conception over time." *Human Reproduction*. 2018. [DOI: 10.1093/humrep/dey317](https://doi.org/10.1093/humrep/dey317)

**Age-ratio decline:** During the simulation, each couple's individual rate declines with age proportionally to the population-level curve: `p_natural = individual_fecund × (current_pop_mean / starting_pop_mean) × bmi_fr × smoking_fr`. This preserves between-couple variation while applying the correct age-related decline trajectory.

---

### 9. IVF Success Rates (Fresh Cycles)

**What it determines:** Per-transfer live birth rates for IVF using the woman's current-age eggs.

**Source:** [SART 2023 Outcome Tables](https://www.sartcorsonline.com/EmbryoOutcome/PublicSARTOutcomeTables) — fresh blastocyst + fresh cleavage (non-PGT-A), pooled across single-embryo and multiple-embryo transfers, weighted by number of transfers.

We pool both blastocyst-stage and cleavage-stage transfers to capture the full spectrum of fresh IVF outcomes. While blastocyst culture is the current standard of care in the US (~90% of transfers for <35) and increasingly in the UK (~75% as of 2023), cleavage-stage transfers still represent a meaningful proportion, particularly for older women with fewer embryos. Weighting by transfer count ensures each age bracket reflects the actual mix of protocols patients experience.

The 43-44 and 45+ brackets are extrapolated from the SART >42 bucket (3.6% pooled LBR, 1,449 transfers).

**What we use (per-transfer live birth rates by female age):**

| Female age | LBR per transfer |
|-----------|-----------------|
| < 35      | 0.405           |
| 35-37     | 0.317           |
| 38-40     | 0.213           |
| 41-42     | 0.110           |
| 43-44     | 0.04            |
| 45+       | 0.01            |

**How it's used in the model:** After `cycles_before_ivf` consecutive cycles of failed natural conception (default 12, configurable), if the user is open to assisted reproduction, the simulation switches to an assisted reproduction pathway. Frozen embryos are used first (if available), then frozen eggs (if available), then fresh IVF. Each IVF cycle takes approximately 4 months (following Habbema et al. 2015: "a course of three IVF cycles with 4-month intervals"). The per-transfer success rate depends on the woman's current age at the time of the cycle. If the user has a BMI ≥ 30, the rate is further multiplied by 0.85 (Sermondade adjustment).

**ART miscarriage handling:** Since the SART live birth rates already account for miscarriage losses, the simulation does not apply age-dependent miscarriage rates to ART conceptions (which would double-count). Instead, each ART conception has a flat 15% chance of miscarriage (pooled across all ages) used solely for timeline simulation — if an ART pregnancy miscarries, the couple waits 3 months before the next cycle, reflecting real-world recovery time. The effective live birth rate per transfer remains as shown in the table above.

**Per-child IVF cap:** The couple may attempt up to `max_ivf_cycles` fresh IVF cycles per child (default 3). The counter resets after each live birth, so a couple wanting 3 children could use up to 9 fresh IVF cycles total. This is consistent with the Habbema et al. 2015 modeling framework, which assumes "a course of three IVF cycles" per child.

---

### 10. Frozen Egg (Oocyte Cryopreservation) Outcomes

**What it determines:** Success rates when using previously frozen eggs for IVF.

**Sources:**

*Oocyte survival and overall live birth rates:*
Hirsch A, et al. "Planned oocyte cryopreservation: a systematic review and meta-regression analysis." *Human Reproduction Update*. 2024. [DOI: 10.1093/humupd/dmae009](https://doi.org/10.1093/humupd/dmae009)

A systematic review and meta-analysis of 10 studies covering 8,750 women who underwent planned egg freezing. The oocyte survival rate after thawing was 78.5%. Live birth rate per patient was 52% for women who froze at age ≤35 and 19% for women who froze at age ≥40.

*Number of eggs needed and per-oocyte live birth rate:*
Namath A, et al. "The number of autologous, vitrified mature oocytes needed to obtain three euploid blastocysts increases with age." *Fertility and Sterility*. 2025. [DOI: 10.1016/j.fertnstert.2025.04.023](https://doi.org/10.1016/j.fertnstert.2025.04.023)

Analysis of 1,041 thaw cycles. The study directly reports expected live births per thawed mature oocyte for two age brackets:
- Frozen at < 35: 0.13 per oocyte
- Frozen at > 40: 0.04 per oocyte

The intermediate brackets are linearly interpolated between these two data points, as the study does not report per-oocyte rates for the 35-40 range:
- Frozen at 35-37: 0.09 per oocyte (interpolated)
- Frozen at 38-40: 0.06 per oocyte (interpolated)

To achieve ~93% probability of at least one child, women need approximately 15 mature oocytes if frozen before 35, ~30 if frozen at ≥38, and ~45 if frozen after 40.

*Age at transfer does not affect success:*
Barrett FG, et al. "Maternal age at transfer following autologous oocyte cryopreservation is not associated with live birth rates." *Journal of Assisted Reproduction and Genetics*. 2024. [DOI: 10.1007/s10815-024-03149-y](https://doi.org/10.1007/s10815-024-03149-y)

In a study of 169 oocyte thaw patients matched to 338 IVF patients, the age at which the embryo was transferred did not predict live birth rate after controlling for age at retrieval. This means a woman who froze eggs at 30 and uses them at 40 has success rates determined by her egg quality at 30, not her uterine age at 40.

**How it's used in the model:** Users can input multiple batches of frozen eggs, each with an age at freeze and number of eggs. When assisted reproduction is triggered, frozen eggs are prioritized after frozen embryos but before fresh IVF (youngest-frozen batches first, as they have the highest per-oocyte success rates). In each frozen egg cycle, up to 9 eggs are thawed. The survival rate (78.5%) is applied, then the per-oocyte LBR based on age at freeze is used to compute the per-cycle success probability: `p = 1 - (1 - per_oocyte_rate) ^ surviving_eggs`. The egg supply is decremented each cycle. The BMI IVF adjustment (Sermondade) applies to frozen egg cycles.

---

### 11. Frozen Embryo Transfer Outcomes

**What it determines:** Per-transfer live birth rates for previously created and frozen embryos.

**Source:** [SART 2023 Outcome Tables](https://www.sartcorsonline.com/EmbryoOutcome/PublicSARTOutcomeTables), stratified by age of woman at retrieval (= age at embryo creation).

- **Untested (non-PGT-A):** Blastocyst + cleavage pooled across SET and MET, weighted by number of transfers. Same pooling methodology as the fresh IVF rates in Section 9. The >42 rate uses the raw SART >42 bucket (3.6% pooled LBR).
- **PGT-A tested (euploid):** Single embryo transfer rates. n=96,855 transfers across all age groups.

The key insight (from Barrett 2024, [DOI: 10.1007/s10815-024-03149-y](https://doi.org/10.1007/s10815-024-03149-y)) is that success depends on the woman's age when eggs were retrieved, not her age at transfer — a 30-year-old's frozen embryo retains 30-year-old success rates even if transferred at 40. Barrett controlled for retrieval age in a multivariate regression and found no transfer-age effect on live birth rates (p=0.24).

#### PGT-A Tested (Euploid) Embryos

Embryos that have undergone preimplantation genetic testing for aneuploidy (PGT-A) and confirmed euploid have higher per-transfer live birth rates because the dominant age-dependent failure mode — chromosomal aneuploidy — has been removed. The PGT-A advantage is largest for older age groups, where aneuploidy rates are highest.

**What we use (per-transfer live birth rates, by age at retrieval):**

| Age at embryo creation | Untested LBR | PGT-A tested LBR |
|------------------------|-------------|-------------------|
| < 35                   | 0.405       | 0.545             |
| 35-37                  | 0.317       | 0.532             |
| 38-40                  | 0.213       | 0.514             |
| 41-42                  | 0.110       | 0.499             |
| > 42                   | 0.036       | 0.463             |

The PGT-A curve is notably flat: even at >42, euploid embryos achieve a 46.3% live birth rate per transfer, compared to just 3.6% for untested embryos. This is because PGT-A removes the dominant age-related failure mode (chromosomal aneuploidy), leaving only non-chromosomal factors (mitochondrial quality, epigenetics, cytoplasmic integrity) to drive the modest remaining decline.

**How it's used in the model:** Users can input multiple batches of frozen embryos, optionally marking each batch as PGT-A tested. Frozen embryos are the highest-priority assisted reproduction pathway (since they skip the egg-to-embryo attrition step and have higher per-transfer success). One embryo is transferred per cycle, and the batch is decremented. Batches are used youngest-creation-age first. When a batch is depleted, the next batch is used. The BMI IVF adjustment applies. When a batch is marked as PGT-A tested, the euploid transfer rates are used instead of the aggregate rates.

---

## Simulation Parameters

The following parameters can be configured by the user:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `female_age` | (required) | Woman's current age (18-45) |
| `desired_children` | (required) | Target family size (1-6) |
| `male_age` | None | Male partner age (affects miscarriage risk if ≥35) |
| `bmi` | None | Female BMI (affects natural conception and IVF) |
| `smoking_status` | never | Never, former, current occasional, current regular |
| `ivf_willingness` | last_resort | "yes", "no", or "last_resort" |
| `cycles_before_ivf` | 12 | Months of natural trying before IVF eligibility |
| `max_ivf_cycles` | 3 | Max fresh IVF cycles per child (resets after each live birth) |
| `min_spacing_months` | 18 | Minimum months after birth before resuming trying |
| `prior_live_births` | 0 | Number of existing children |
| `prior_miscarriages` | 0 | Consecutive miscarriages since last live birth (resets to 0 after each live birth; used to seed recurrent miscarriage risk) |
| `cycles_tried` | 0 | Months already spent trying (shifts fecundability draws lower) |
| `frozen_egg_batches` | () | Batches of frozen eggs (age at freeze, count) |
| `frozen_embryo_batches` | () | Batches of frozen embryos (age at freeze, count) |
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

## Comparison with Habbema et al. 2015

Our model is based on the family completion simulation framework from [Habbema et al. 2015](https://doi.org/10.1093/humrep/dev148). We match their 90% benchmark cutoff ages within ±2 years, but use different underlying data and distributional assumptions. The key differences are summarized below.

### Fecundability age-decline curve

We reverse-engineered Habbema's fecundability decline curve by fitting a standalone Habbema-faithful simulation (using their published sterility, miscarriage, and IVF parameters) to 114 data points digitized from their published completion rate figures across 19 starting ages × 6 scenarios (1/2/3 children × with/without IVF). The best fit (SSE=0.075, mean absolute error 2.2 percentage points) reveals a sharp decline from 0.23 at age 30 to ~0.09 at age 32, followed by a gentle decline to ~0.05 by age 44.

Our model uses the Wesselink 2017 age-fecundability curves (Section 2), which decline more gradually through the 30s. Unlike Habbema's flat 23% from ages 20–30, our model also shows a mild decline starting in the mid-20s:

| Age | Our model (nulligravid) | Our model (gravid) | Habbema (reverse-engineered) |
|-----|------------------------|-------------------|------------------------------|
| 20 | 23.0% | 23.0% | 23.0% |
| 25 | 20.8% | 21.5% | 23.0% |
| 30 | 18.7% | 21.8% | 23.0% |
| 32 | 19.3% | 20.2% | 8.8% |
| 35 | 15.6% | 22.1% | 7.7% |
| 38 | 11.7% | 16.1% | 6.6% |
| 42 | 5.4% | 11.6% | 5.4% |

The curves converge by the early 40s but differ substantially in the early-to-mid 30s, where our model retains much higher per-cycle rates. Habbema's curve drops sharply from 23% to ~9% between ages 30 and 31, while our Wesselink-based curves decline gradually throughout.

### Fecundability heterogeneity distribution

Habbema uses a truncated Normal distribution with CV=0.52 for between-couple fecundability variation. Our model uses a Beta distribution with concentration=4.23, which produces CV=0.80 — 54% more between-couple spread.

| Property | Our Beta(0.97, 3.26) | Habbema TruncNorm(0.23, 0.12) |
|----------|---------------------|-------------------------------|
| Mean | 0.23 | 0.23 |
| CV | 0.80 | 0.52 |
| Fraction < 5% fecundability | 16.4% | 4.0% |
| Fraction > 40% fecundability | 18.3% | 8.0% |
| Median | 18.6% | 23.4% |

Our distribution creates ~4× more "essentially subfertile" couples (below 5% per cycle) and ~2.3× more "super-fertile" couples (above 40% per cycle). The concentration parameter (4.23) was calibrated so that these distributional differences, combined with the gentler Wesselink decline curve and the 42.5–50 fecundability taper, produce completion rates that match Habbema's cutoff ages across all 18 benchmark scenarios with MAE = 0.49 years.

However, the underlying differences in both the decline curve shape and the heterogeneity distribution mean the models may diverge at other confidence levels, particularly the 50% level where the shape of the fecundability distribution matters more than the tails.

### Other differences

- **Miscarriage rates:** We use Magnus et al. 2019 (Section 3), which reports higher rates than Habbema's Leridon 2004 data at older ages (32.2% at 40–44 vs ~25%). We also model recurrent miscarriage risk and male partner age effects.
- **IVF success rates:** We use SART 2023 per-transfer live birth rates (Section 9), which are generally higher than Habbema's 2013 Netherlands data due to advances in embryo culture and vitrification.
- **Additional ART pathways:** Frozen eggs, frozen embryos, and PGT-A tested embryos (Sections 10–11), none of which were in Habbema's model.
- **Gravid/nulligravid distinction:** We use separate Wesselink 2017 age-decline curves based on pregnancy history (Section 2). Habbema used a single curve for all women.
- **Configurable parameters:** Birth spacing, IVF timing, and IVF cycle caps are user-adjustable rather than hardcoded.

---

## Limitations

This model provides population-level statistical estimates. Individual outcomes depend on many biological factors not captured here, including ovarian reserve (AMH levels), specific medical conditions (PCOS, endometriosis, tubal factors), sperm parameters, and genetic factors. The model assumes no underlying fertility diagnoses beyond what is captured by age, BMI, smoking, and reproductive history.

All parameter values are derived from published research on specific populations (primarily North American and Northern European). Results may not generalize equally across all ethnic groups and geographic populations.

The model does not account for the emotional, financial, or logistical costs of extended trying periods or IVF cycles.

This tool is not medical advice. Consult a healthcare provider for personalized fertility assessment.
