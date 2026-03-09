"""Verify methodology documentation against actual code behavior.

This script checks for divergences between methodology.md, methodology.html,
and the actual simulation code.
"""

import numpy as np
from scipy import stats

# ============================================================
# 1. Beta distribution parameters
# ============================================================
print("=" * 60)
print("1. BETA DISTRIBUTION PARAMETERS")
print("=" * 60)

# What the code uses (curves.py)
CODE_CONCENTRATION = 4.33
CODE_BASE_FECUND = 0.25
code_alpha = CODE_BASE_FECUND * CODE_CONCENTRATION
code_beta = (1.0 - CODE_BASE_FECUND) * CODE_CONCENTRATION
print(f"\nCode: Beta({code_alpha:.4f}, {code_beta:.4f})  [concentration={CODE_CONCENTRATION}]")

dist_code = stats.beta(code_alpha, code_beta)
print(f"  Mean:   {dist_code.mean():.4f}")
print(f"  StdDev: {dist_code.std():.4f}")
print(f"  CV:     {dist_code.std()/dist_code.mean():.4f}")
percentiles = [5, 10, 25, 50, 75, 90, 95]
for p in percentiles:
    print(f"  {p}th percentile: {dist_code.ppf(p/100)*100:.1f}%")

# What methodology.md says (Section 8)
print("\nMethodology.md says: Beta(1.08, 3.25)")
print("  5th: 2.0%, 10th: 3.9%, 25th: 9.7%, 50th: 21.0%, 75th: 36.6%, 90th: 52.5%, 95th: 61.7%")

# What methodology.html chart uses
HTML_ALPHA = 1.25
HTML_BETA = 3.75
print(f"\nHTML chart: Beta({HTML_ALPHA}, {HTML_BETA})  [concentration={HTML_ALPHA + HTML_BETA}]")
dist_html = stats.beta(HTML_ALPHA, HTML_BETA)
print(f"  Mean:   {dist_html.mean():.4f}")
print(f"  StdDev: {dist_html.std():.4f}")
print(f"  CV:     {dist_html.std()/dist_html.mean():.4f}")
for p in percentiles:
    print(f"  {p}th percentile: {dist_html.ppf(p/100)*100:.1f}%")

# HTML percentile dot values
print("\nHTML percentile dots shown: 5th=2.7%, 25th=10.8%, 50th=21.5%, 75th=36.0%, 95th=59.2%")

print(f"\n>>> DIVERGENCE: HTML uses concentration={HTML_ALPHA + HTML_BETA}, code uses {CODE_CONCENTRATION}")
print(f">>> HTML CV={dist_html.std()/dist_html.mean():.3f} vs code CV={dist_code.std()/dist_code.mean():.3f}")


# ============================================================
# 2. Bayesian updating table comparison
# ============================================================
print("\n" + "=" * 60)
print("2. BAYESIAN UPDATING TABLE")
print("=" * 60)

for cycles_tried in [0, 6, 12]:
    alpha = CODE_BASE_FECUND * CODE_CONCENTRATION
    beta = (1.0 - CODE_BASE_FECUND) * CODE_CONCENTRATION + cycles_tried
    dist = stats.beta(alpha, beta)
    print(f"\nCycles tried = {cycles_tried}:")
    print(f"  Code: Beta({alpha:.2f}, {beta:.2f})")
    print(f"  Mean: {dist.mean()*100:.1f}%")
    print(f"  5th-95th: {dist.ppf(0.05)*100:.1f}% - {dist.ppf(0.95)*100:.1f}%")

print("\nHTML table says:")
print("  0 months: mean 23.0%, range 2.1%-56.7%")
print("  6 months: mean 10.5%, range 0.8%-28.2%")
print("  12 months: mean 6.8%, range 0.5%-18.6%")

print("\nMethodology.md says:")
print("  0 months: mean 25.0%, range 2.0%-61.7%")
print("  6 months: mean 10.5%, range 0.7%-28.8%")
print("  12 months: mean 6.6%, range 0.4%-18.6%")


# ============================================================
# 3. Parameter defaults: API vs core model vs docs
# ============================================================
print("\n" + "=" * 60)
print("3. PARAMETER DEFAULT MISMATCHES")
print("=" * 60)

print("""
Parameter           | Core Model    | API Schema    | methodology.md
--------------------|---------------|---------------|---------------
ivf_willingness     | last_resort   | no            | last_resort
min_spacing_months  | 15            | 18            | 15
female_age range    | 15-45         | 18-45         | 18-45
""")

print(">>> ivf_willingness: methodology.md says 'last_resort' which matches core model,")
print("    but API default is 'no'. Users experience 'no' unless they change it.")
print(">>> min_spacing_months: methodology.md says 15, API sends 18. Users see 18.")


# ============================================================
# 4. Male age miscarriage parameter description
# ============================================================
print("\n" + "=" * 60)
print("4. MALE AGE MISCARRIAGE DESCRIPTION")
print("=" * 60)

print("Code: male_age_miscarriage_or activates at age >= 35 (OR=1.15)")
print("methodology.md Section 4: 'when the male partner is 35 or older' ✓")
print("methodology.md param table: 'affects miscarriage risk if ≥40' ✗")
print(">>> DIVERGENCE: Param table says ≥40 but actual threshold is ≥35")


# ============================================================
# 5. README references nonexistent file
# ============================================================
print("\n" + "=" * 60)
print("5. README REFERENCES")
print("=" * 60)
print("README.md lists 'bayesian.py' as a module, but this file does not exist.")
print("The Bayesian updating logic is in curves.py:draw_individual_fecundabilities()")
