# Fertility Forecaster

Evidence-based fertility planning tool that estimates your probability of having the family you want. The simulation runs entirely client-side in the browser.

## Development

```bash
cd frontend
npm install
npm run dev
```

## How it works

The app runs a Monte Carlo simulation of 5,000 virtual couples cycle-by-cycle, incorporating published data on natural conception rates, miscarriage risk, IVF outcomes, and frozen egg/embryo success rates. See [methodology.md](methodology.md) or the in-app methodology page for full details and data sources.

### Key files

- `frontend/src/simulation/simulation.ts` — Monte Carlo simulation engine
- `frontend/src/simulation/curves.ts` — Age-dependent fertility curves and adjustment factors
- `frontend/src/simulation/sweep.ts` — Runs simulation across a range of starting ages
- `frontend/src/simulation/prng.ts` — Seedable PRNG with Beta distribution support
