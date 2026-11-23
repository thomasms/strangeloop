# Handoff brief

For the next person or agent who continues this work. Read this first, then `REPORT.md`.

## Context

- Project "I" asks: *Is AI conscious?* This repository covers one strand: a formal version of Hofstadter's strange-loop self.
- Owner: a physicist (PhD) with 10 years of software engineering. Technical language is fine in technical places. For explanations, the owner prefers short, clear sentences (ASD-STE100 style).
- **Do not** use the owner's credentials (git, cloud) and **do not** run destructive commands (such as `rm`) without asking. The owner prefers to run those commands themselves.
- A related project document exists in claude.ai: `claude/strange-loop-formalism-v0.md` (same content as sections 5–12 of the report, in shorter form). Another project doc, `claude/hofstadter-strange-loop-argument.md`, holds Hofstadter's argument (P1–P10) and its critique.

## State of the work (2026-11-23)

Done:
- Formalism v0 (REPORT §5): Props 1–2 (exact self-code possible, exact self-state impossible), D1–D6, bridge axiom A0.
- Simulation v0 (REPORT §8): richness ρ (D7) separates trivial from rich self-models.
- Critique (REPORT §9) and formalism v1 (REPORT §10): D8 internal reader (decoder intervention λ), D9 intrinsic split (sensory / self / parameter), D5 as self-fitting fixed point.
- Simulation v1 (REPORT §11): all three fixes behave as intended on toy agents.
- Current definition: REPORT §12. Results list: REPORT §13.

Not done (from the plan, REPORT §7 and §15):
1. **Plan 2 — learned agents under a capacity limit** (information bottleneck on R). Highest priority. Goal: test Proposition 3 ("the optimal lossy self-model is one agent variable") and give ρ an independent justification.
2. Weight self-fitting by visit frequency (REPORT §11.2, finding 8).
3. Derive the sensor boundary (Markov blanket) instead of assuming it.
4. Second-order self-model (predict U, not only actions).
5. Unity experiments (N_eff; decide scoring per trajectory or per system).
6. Plan 4 thought experiments: self without experience, experience without self (ego dissolution test of A0).
7. Read the Szangolies preprint (academia.edu/50989457) and finish the comparison.
8. Apply the measures to a real LLM agent with persistent self-notes.

## Known issues and caveats

- Agents, planner, world model and rewards are hand-designed. Results partly reflect those choices.
- Thresholds δ, ρ₀, the distribution μ (uniform) and the scramble distribution for λ are arbitrary.
- λ is identical (0.1564) for the fixed-belief and learned self-simulating foragers. This is expected: they choose the same action in all 72 states and use the same scramble seeds.
- In `sim_v1.py`, the low-capacity learned agent's γ is ≈ 0.0017; it prints as 0.00.
- The Szangolies details in REPORT §3.3 come from his abstract, a summary, his blog and a forum post, not from the full paper.
- The "Strange Loop Model" reference (Frontiers 2021) has an unchecked title and authors.

## How to verify

```bash
python3 code/sim_v0.py   > /tmp/v0.md && diff /tmp/v0.md results/sim_v0_output.md
python3 code/sim_v1.py   > /tmp/v1.md && diff /tmp/v1.md results/sim_v1_output.md
python3 tests/test_results.py
```

All runs are deterministic (fixed seeds). No diff and six "ok" lines mean the repository is consistent with the report.
