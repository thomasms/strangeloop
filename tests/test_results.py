"""
Regression checks for the main results in REPORT.md.
Run from the repository root:  python3 tests/test_results.py   (or: pytest tests)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

import sim_v0  # noqa: E402
import sim_v1  # noqa: E402


def test_v0_richness_separates_thermostat_bit():
    bit = sim_v0.evaluate(sim_v0.ThermostatBit(), sim_v0.ThermoEnv())
    forager = sim_v0.evaluate(sim_v0.Forager(), sim_v0.RingEnv())
    assert bit["gamma_bits"] > forager["gamma_bits"]   # causal use alone fails
    assert abs(bit["rho"]) < 1e-9                       # richness excludes the bit
    assert forager["rho"] > 0.3


def test_v0_multi_persona_n_eff():
    r = sim_v0.evaluate(sim_v0.MultiPersona(), sim_v0.RingEnv())
    assert abs(r["N_eff"] - 2.0) < 0.05


def test_v1_intrinsic_split():
    for agent, env, R in [(sim_v1.ThermostatBit(), sim_v1.ThermoEnv(), {"bit"}),
                          (sim_v1.SelfSimForager(), sim_v1.RingEnv(), {"mode", "heading"})]:
        r = sim_v1.evaluate(agent, env)
        assert ("R={" + ",".join(sorted(R, key=list(agent.domains).index)) + "}") in r["split (D9)"]


def test_v1_internal_reader():
    assert sim_v1.evaluate(sim_v1.ThermostatBit(), sim_v1.ThermoEnv())["lam"] is None
    assert sim_v1.evaluate(sim_v1.ReactiveForager(), sim_v1.RingEnv())["lam"] is None
    r = sim_v1.evaluate(sim_v1.SelfSimForager(), sim_v1.RingEnv())
    assert r["lam"] > 0.1 and r["rho"] < 0                # reads a wrong self-model
    assert r["R = decoder inputs"]


def test_v1_fixed_point():
    a = sim_v1.LearnedSelfSimForager()
    hist = a.fit()
    assert hist[-1] == 0 and len(hist) <= 3
    r = sim_v1.evaluate(a, sim_v1.RingEnv())
    assert r["eps"] == 0 and abs(r["rho"] - 1) < 1e-9


def test_v1_low_capacity_d3_d8_independent():
    a = sim_v1.LearnedSelfSimForager(decoder_inputs=("mode",), sees_w=("fd",))
    a.fit()
    r = sim_v1.evaluate(a, sim_v1.RingEnv())
    assert r["lam"] > 0.1 and r["gamma"] < 0.01


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok ", name)
