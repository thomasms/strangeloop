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
