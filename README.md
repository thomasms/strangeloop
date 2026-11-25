# strange-loop-consciousness

A minimal formal theory of Hofstadter's "strange loop" self, with a Python test harness.

Part of the project **"I"**: review the literature on consciousness, build thought experiments that narrow down what it is, and answer *"Is AI conscious?"*

## Contents

| Path | What it is |
|---|---|
| [`REPORT.md`](REPORT.md) | Full report: aims, literature, formalism (formal and plain-language layers), simulations, results, limits, references |
| [`HANDOFF.md`](HANDOFF.md) | Short brief for the next person or agent who continues this work |
| `code/sim_v0.py` | Simulation for formalism v0 |
| `code/sim_v1.py` | Simulation for formalism v1 (internal reader, intrinsic split, self-fitting fixed point) |
| `code/sim_v2.py` | v2 step 1: interventional γ_do (D3) and off-state reading λ_off (D8′), plus adversarial agents |
| `tests/test_results.py` | Regression checks for the main results |
| `tests/PREDICTIONS_v2.md` | v2 predictions (committed before the v2 code) and their outcome |
| `tests/test_adversarial_v2.py` | Adversarial checks P1–P8 |
| `results/` | Saved outputs of the simulations |

## Quick start

Python 3.8 or later, no dependencies.

```bash
python3 code/sim_v0.py
python3 code/sim_v1.py
python3 code/sim_v2.py
python3 tests/test_results.py
python3 tests/test_adversarial_v2.py
```

## One-paragraph summary

A part of a system can know the system's *rules* exactly, but can never hold an exact copy of the system's *current state*, so every self-model is a simplified sketch. Starting from this, we define a strange loop by five measurable conditions — the self part steers behaviour, is updated by behaviour, is read by the agent itself, is a fixed point of self-fitting, and is rich (predicts the agent's behaviour in other situations) — with the "self" variables found from the dynamics rather than chosen by an observer. Toy simulations show that each condition is needed. The theory covers the structure of a self only; the claim that this structure is consciousness is kept as a separate, testable axiom.
