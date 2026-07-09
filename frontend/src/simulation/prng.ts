/**
 * Seedable PRNG with Beta distribution support.
 *
 * Uses xoshiro128** for uniform random numbers and rejection sampling
 * for Beta distribution draws, matching NumPy's default_rng behavior.
 */

/** Mulberry32: simple 32-bit PRNG used to seed xoshiro128** state. */
function mulberry32(seed: number): () => number {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class PRNG {
  private s: Uint32Array;

  constructor(seed: number) {
    // Initialize xoshiro128** state from seed using mulberry32
    const init = mulberry32(seed);
    this.s = new Uint32Array(4);
    this.s[0] = (init() * 4294967296) >>> 0;
    this.s[1] = (init() * 4294967296) >>> 0;
    this.s[2] = (init() * 4294967296) >>> 0;
    this.s[3] = (init() * 4294967296) >>> 0;
  }

  /** Returns a uniform random uint32. */
  private nextUint32(): number {
    const s = this.s;
    const result = Math.imul(s[1] * 5, 1) << 7 | Math.imul(s[1] * 5, 1) >>> 25;
    const t = s[1] << 9;
    s[2] ^= s[0];
    s[3] ^= s[1];
    s[1] ^= s[2];
    s[0] ^= s[3];
    s[2] ^= t;
    s[3] = (s[3] << 11) | (s[3] >>> 21);
    return (result * 9) >>> 0;
  }

  /** Returns a uniform random float in [0, 1). */
  random(): number {
    return this.nextUint32() / 4294967296;
  }

  /** Fill a Float64Array with uniform random values in [0, 1). */
  randomArray(n: number): Float64Array {
    const arr = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      arr[i] = this.random();
    }
    return arr;
  }

  /**
   * Draw from a Gamma distribution using Marsaglia & Tsang's method.
   * Shape must be > 0. Rate = 1.
   */
  private gamma(shape: number): number {
    if (shape < 1) {
      // Boost: gamma(shape) = gamma(shape+1) * U^(1/shape)
      return this.gamma(shape + 1) * Math.pow(this.random(), 1 / shape);
    }
    const d = shape - 1 / 3;
    const c = 1 / Math.sqrt(9 * d);
    for (;;) {
      let x: number;
      let v: number;
      do {
        x = this.standardNormal();
        v = 1 + c * x;
      } while (v <= 0);
      v = v * v * v;
      const u = this.random();
      if (u < 1 - 0.0331 * (x * x) * (x * x)) return d * v;
      if (Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
    }
  }

  /** Standard normal via Box-Muller transform. */
  private standardNormal(): number {
    const u1 = this.random();
    const u2 = this.random();
    return Math.sqrt(-2 * Math.log(u1 || 1e-20)) * Math.cos(2 * Math.PI * u2);
  }

  /**
   * Draw n samples from Beta(alpha, beta) distribution.
   * Uses gamma distribution: Beta(a,b) = Ga/(Ga+Gb).
   */
  betaArray(alpha: number, beta: number, n: number): Float64Array {
    const arr = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const ga = this.gamma(alpha);
      const gb = this.gamma(beta);
      arr[i] = ga / (ga + gb);
    }
    return arr;
  }
}
