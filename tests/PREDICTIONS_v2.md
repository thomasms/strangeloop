# Predictions for v2 (written before the v2 code)

This file was committed **before** `code/sim_v2.py` and `tests/test_adversarial_v2.py` existed.
Git history shows the order. The aim is to stop us from tuning the definitions to the results.

Honesty note: P1 and P7 were partly known from a quick probe on the v1 code
(rewritten thermostat: λ = 0.46, ρ = 1; low-capacity agent: do(mode) changes the action in 7.6% of states).

## New measures in v2

- **γ_do (D3, interventional).** On sampled states from the agent's own trajectories, set the self part R
  to each other value of its domain and count how often the action changes. Replaces γ = I(R; A | W) as the test for D3.
- **φ (off-state share).** The share of the agent's own decoder calls whose input (as the decoder reads it)
  is not the current state.
- **λ_off (D8′, off-state reading).** Scramble the decoder **only** for off-state queries; keep the answer
  for the current state. Count how often the action changes.
- **D8′ passes ⟺ λ_off > 0.** The agent's behaviour depends on what its self-model says about states
  other than the current one. "The self-model is used as a model, not as the policy."

## Predictions

| # | Agent | Prediction |
|---|---|---|
| P1 | Thermostat + bit, rewritten so that `act` = `decoder` | λ > 0, φ = 0, λ_off = 0 → **fails D8′** (v1 wrongly passed it) |
| P2 | Gamed thermostat: as P1, plus an extra decoder call on another state, result ignored | φ > 0, λ_off = 0 → **fails D8′** (shows why φ alone is not enough) |
| P3 | Forager with a decorative decoder (called, output ignored) | λ = 0 and λ_off = 0 → **fails D8 and D8′** |
| P4 | Lookup-table copy of the self-simulating forager | Same action in all 72 states as the original; no decoder → **fails D8**. *Open decision for the owner: Hofstadter cares about the pattern; is it right that an exact behavioural copy fails?* |
| P5 | Self-simulating forager: fixed belief, learned, learned low-capacity | λ_off > 0 → **passes D8′** |
| P6 | Thermostat with a one-step look-ahead on itself | λ_off > 0 → **passes D8′**. Accepted as a small, genuine loop (low grade). |
| P7 | All agents with a self part, including the low-capacity agent | γ_do > 0. For the low-capacity agent γ_do > 0.05 while γ < 0.01 → **result R15 ("D3 and D8 are independent") does not survive** |
| P8 | Reactive forager, state re-encoded (mode and food direction stored as one variable) | D9 gives a different split → **invariance fails. Known open hole 2**; fixed only by the coarse-graining definition (later step). |

## Outcome (added after running `code/sim_v2.py`; see `results/sim_v2_output.md`)

All eight predictions hold, with one exception: the "low grade" part of P6.

| # | Result |
|---|---|
| P1 | λ = 0.46, ρ = 1, but φ = 0 and λ_off = 0 → fails D8′. ✔ |
| P2 | φ = 0.50, λ_off = 0 → fails D8′. ✔ |
| P3 | λ = 0, λ_off = 0 → fails D8 and D8′. ✔ |
| P4 | Same action in 72/72 states; no decoder → fails D8. ✔ (decision still open) |
| P5 | λ_off = 0.012 (fixed belief), 0.123 (learned), 0.147 (low capacity) → all pass D8′. ✔ |
| P6 | λ_off = 0.16 → passes D8′. ✔ **But not "low grade":** its λ_off is higher than every forager's, and ρ = 1. ✘ |
| P7 | γ_do > 0 for every agent with a self part. Low capacity: γ = 0.002, γ_do = 0.061 → R15 withdrawn. ✔ |
| P8 | Split changes from R = {mode, heading} to R = {x, heading}. ✔ (hole 2 still open) |

### Findings not predicted

1. **The grade does not see size (P6).** A thermostat with a one-step look-ahead scores as high as or higher than
   the foragers on λ_off and ρ. Nothing in the grade measures how much there is to model. A capacity or size term
   is needed (Plan 2, rate–distortion). Until then, "degree of self" is not defined by the grade vector.
2. **A wrong self-model is barely used off-state.** The fixed-belief forager has λ_off = 0.012, ten times lower
   than the learned one (0.123), although λ is the same (0.156). Its planner mostly ignores what its wrong
   self-model says about other states.
3. **γ can hide strong steering.** Reactive forager: γ is only 0.17 bits, but setting R to another value changes
   the action in 71% of cases (γ_do = 0.71; a fraction, not bits, so the two numbers are not directly comparable).
   Caveat: the interventions
   include states that never occur on the agent's trajectories (for example mode = rest with low energy).
   A version that weights interventions towards reachable states is still to do.
4. **λ changed slightly for the low-capacity agent** (0.156 in v1, 0.189 in v2), because v2 keys the scramble
   table on what the decoder actually reads.
