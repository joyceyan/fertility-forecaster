"""Beta-binomial conjugate updating for fecundability estimation."""

from __future__ import annotations

import numpy as np


def compute_prior_params(
    population_mean: float | np.ndarray,
    sample_size: float = 8.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute Beta prior parameters from a population mean.

    A sample_size of 8 gives a moderately informative prior — equivalent
    to having observed ~8 cycles of data.
    """
    population_mean = np.asarray(population_mean, dtype=float)
    alpha = population_mean * sample_size
    beta = (1.0 - population_mean) * sample_size
    return alpha, beta


def posterior_mean(
    alpha: np.ndarray,
    beta: np.ndarray,
    failures: np.ndarray,
) -> np.ndarray:
    """Posterior mean of fecundability after observing failures.

    Uses the Beta-Binomial conjugate update where each failure
    increments the beta parameter by 1.
    """
    alpha = np.asarray(alpha, dtype=float)
    beta = np.asarray(beta, dtype=float)
    failures = np.asarray(failures, dtype=float)
    return alpha / (alpha + beta + failures)
