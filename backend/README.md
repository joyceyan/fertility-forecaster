# Fertility Forecaster — Backend

Monte Carlo simulation engine for fertility planning, modeling natural conception, IVF, and frozen egg pathways with Bayesian updating.

## Setup

Requires Python 3.13+ and conda.

```bash
# Create the conda environment (one-time)
conda create -n fertility-forecaster python=3.13 -y

# Activate it
conda activate fertility-forecaster

# Install the package and all dependencies (from backend/)
cd backend
pip install -e ".[dev]"
```

## Run tests

```bash
conda activate fertility-forecaster
cd backend
pytest
```

With verbose output:

```bash
pytest -v
```

## Run the API server

```bash
conda activate fertility-forecaster
cd backend
uvicorn fertility_forecaster.api:app --reload
```

## Modules

- **models.py** — `SimulationParams` and `SimulationResult` dataclasses
- **curves.py** — Age-dependent fecundability, miscarriage, IVF success, and frozen egg curves
- **bayesian.py** — Beta-binomial conjugate updating for personalized fecundability
- **simulation.py** — Vectorized Monte Carlo simulation engine (10,000 couples × up to 180 cycles)
- **api.py** — FastAPI endpoints (`/simulate`, `/sweep`, `/health`)
