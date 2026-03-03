"""Tests for Bayesian fecundability updating."""

import numpy as np
import pytest

from fertility_forecaster.bayesian import compute_prior_params, posterior_mean


class TestComputePriorParams:
    def test_params_sum_to_sample_size(self):
        alpha, beta = compute_prior_params(0.20, sample_size=8.0)
        assert pytest.approx(alpha + beta) == 8.0

    def test_prior_mean_equals_population_mean(self):
        mean = 0.20
        alpha, beta = compute_prior_params(mean, sample_size=8.0)
        assert pytest.approx(alpha / (alpha + beta)) == mean

    def test_different_sample_sizes(self):
        alpha, beta = compute_prior_params(0.25, sample_size=10.0)
        assert pytest.approx(alpha) == 2.5
        assert pytest.approx(beta) == 7.5

    def test_vectorized(self):
        means = np.array([0.20, 0.15, 0.10])
        alpha, beta = compute_prior_params(means)
        assert alpha.shape == (3,)
        assert beta.shape == (3,)
        np.testing.assert_allclose(alpha / (alpha + beta), means)


class TestPosteriorMean:
    def test_no_failures_equals_prior(self):
        alpha, beta = compute_prior_params(0.20)
        result = posterior_mean(alpha, beta, np.array(0))
        assert pytest.approx(float(result)) == 0.20

    def test_posterior_decreases_with_failures(self):
        alpha, beta = compute_prior_params(0.25)
        failures = np.arange(0, 20)
        posteriors = posterior_mean(alpha, beta, failures)
        assert np.all(np.diff(posteriors) < 0)

    def test_twelve_failures_at_age_25(self):
        """After 12 failures at age 25 (fecundability=0.25):
        alpha=2.0, beta=6.0, posterior = 2.0 / (2.0 + 6.0 + 12) = 0.1
        """
        alpha, beta = compute_prior_params(0.25, sample_size=8.0)
        result = posterior_mean(alpha, beta, np.array(12))
        assert pytest.approx(float(result), abs=0.01) == 0.10

    def test_vectorized(self):
        alpha = np.array([2.0, 2.0, 2.0])
        beta = np.array([6.0, 6.0, 6.0])
        failures = np.array([0, 6, 12])
        result = posterior_mean(alpha, beta, failures)
        assert result.shape == (3,)
        # Should be decreasing
        assert result[0] > result[1] > result[2]
