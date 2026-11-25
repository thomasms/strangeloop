"""
Checks for v3 (Plan 2: the self under a capacity limit, and live self-fitting).

PREDICTIONS -- committed before code/sim_v3.py existed (git history shows the order).

Definitions used below
  R/~1      behavioural quotient of the self part: r ~1 r' iff pi(w, r) = pi(w, r')
            for every world state w. The minimal exact one-step self-model.
  R/~inf    the same, but r and r' must also lead to equivalent self states for every
            input sequence (bisimulation; computed by partition refinement).
  C_self    "size of the self" = log2 |R/~1|, counted over self states the agent visits.
  err(K)    counterfactual error of the best self-model that may read only K classes of R
            (classes merged greedily; states weighted by visit frequency, w uniform).
  NMI       normalised mutual information between the K-class partition and a variable.
  beta      weight that the planner gives to its self-predicted next action.

  P9   Size term (fixes R22). C_self = 1 bit for Thermostat + bit and for the look-ahead
       thermostat (P6); >= 2 bits for the learned self-simulating forager; >= 2.5 bits for
       the unified goal agent. So the size term separates P6 from the foragers.
  P10  Unity (Proposition 3, Hofstadter P3). Unified goal agent (one goal variable g drives
       behaviour in all situations): the best 4-class self-model aligns with g, NMI >= 0.8.
       Modular agent (independent drives, each acting in its own situations): the best
       4-class self-model has NMI < 0.8 with every single self variable.
  P11  Invariance. C_self, |R/~inf| and err(K) do not change when the values of the self
       variables are relabelled by any bijection.
  P12  Live self-fitting converges. Fitting the self-model from the agent's own noisy
       experience reaches a fixed point or a cycle of length <= 4 within 30 iterations,
       for every start and every beta in {0, 0.8, 2.0}.
  P13  Accurate where it lives. At the attractors, mean on-trajectory error eps <= 0.10,
       and mean counterfactual error eps_cf > mean eps.
  P14  Exploratory. For beta = 2.0, the attractors include >= 2 behaviourally different
       selves (self-fulfilling self-models). No prediction for beta = 0 or 0.8.

OUTCOME -- added after running code/sim_v3.py (results/sim_v3_output.txt).

  P9   PARTLY FAILS. Thermostat + bit and P6: 1 bit (as predicted). Unified goal agent:
       2.81 bits (as predicted). But the learned self-simulating forager is also 1 bit
       (predicted >= 2): its behaviour depends on its self state only through 2 classes.
       So C_self does NOT separate P6 from the learned forager. The forager's self-model
       is large because it models how its RULES depend on the world, not because its
       self STATE is large (compare R14: rules versus state).
  P10  HOLDS, with a small margin. Unified: NMI(g) = 0.87. Modular: max NMI = 0.72 (mw).
  P11  HOLDS (5 random relabellings per agent; checked below with 3).
  P12  FAILS at beta = 2.0: 18 of 30 runs do not converge in 30 rounds, and the cycles
       have lengths up to 12. Holds at beta = 0 (all fixed points) and 0.8 (fixed points
       or 2-cycles).
  P13  HOLDS for beta = 0 and 0.8 (eps = 0.008 and 0.007; eps_cf = 0.46 and 0.47).
       FAILS at beta = 2.0 (eps = 0.83): no stable, accurate self.
  P14  HOLDS as stated (12 different selves at beta = 2.0), but they are cycles, not
       self-fulfilling fixed points. Measure ADDED AFTER THE RUN ("distinct lives": same
       world and seeds, different action sequence): beta = 0 gives 9 different lives from
       30 random starts, all fixed points. Several stable, accurate selves exist, and the
       initial self-model selects which one the agent becomes.
"""
import functools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

import sim_v3 as T  # noqa: E402


@functools.lru_cache(maxsize=None)
def sizes():
    return {a.name: T.self_size(a, e) for a, e in T.size_agents()}


@functools.lru_cache(maxsize=None)
def live():
    return dict(T.live_experiment())


def test_p9_size_term_partly_fails():
    z = sizes()
    assert z["Thermostat + bit"]["C_self"] == 1.0
    assert z["P6 Thermostat with self-look-ahead"]["C_self"] == 1.0
    assert z["Unified goal agent"]["C_self"] >= 2.5
    # predicted >= 2 bits; observed 1 bit -> the size term does not separate P6 from it
    assert z["P5 Learned self-model"]["C_self"] == 1.0


def test_p10_unity():
    z = sizes()
    assert z["Unified goal agent"]["nmi4"]["g"] >= 0.8
    assert max(z["Modular agent"]["nmi4"].values()) < 0.8


def test_p11_invariance_under_relabelling():
    for agent, env in T.size_agents()[2:]:
        a = sizes()[agent.name]
        for k in range(3):
            b = T.self_size(T.Relabelled(agent, a["Rv"], random.Random(k)), env)
            assert (a["|R/~1|"], a["|R/~inf|"]) == (b["|R/~1|"], b["|R/~inf|"])
            assert all(abs(a["curve"][K][0] - b["curve"][K][0]) < 1e-9 for K in a["curve"])


def test_p12_convergence_fails_at_high_beta():
    L = live()
    assert all(r["status"] == "fixed" for r in L[0.0])
    assert all(r["status"] in ("fixed", "cycle") and r["cycle_len"] <= 4 for r in L[0.8])
    assert sum(r["status"] == "none" for r in L[2.0]) > 0          # prediction failed


def test_p13_accurate_where_it_lives_only_for_low_beta():
    for beta in (0.0, 0.8):
        rows = live()[beta]
        eps = sum(r["eps"] for r in rows) / len(rows)
        cf = sum(r["eps_cf"] for r in rows) / len(rows)
        assert eps <= 0.10 and cf > eps
    done = [r for r in live()[2.0] if r["eps"] is not None]
    assert sum(r["eps"] for r in done) / len(done) > 0.5            # prediction failed


def test_p14_several_selves():
    done = [r for r in live()[2.0] if r["eps"] is not None]
    assert len({r["behaviour"] for r in done}) >= 2
    # added after the run: several stable selves already at beta = 0
    assert len({r["life"] for r in live()[0.0]}) >= 2


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok ", name)
