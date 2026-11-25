"""
Adversarial checks for v2: the predictions P1-P8 in tests/PREDICTIONS_v2.md.
Run from the repository root:  python3 tests/test_adversarial_v2.py   (or: pytest tests)
Takes about 15 s (all agents are evaluated once and cached).
"""
import functools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

import sim_v1 as S  # noqa: E402
import sim_v2 as V  # noqa: E402


@functools.lru_cache(maxsize=None)
def results():
    return {a.name: V.evaluate_v2(a, e) for a, e in V.runs()}


def r(prefix):
    (hit,) = [v for k, v in results().items() if k.startswith(prefix)]
    return hit


def test_p1_rewritten_thermostat_fails_d8_prime():
    x = r("P1")
    assert x["lam"] > 0.1 and abs(x["rho"] - 1) < 1e-9      # v1 would pass it
    assert x["phi"] == 0 and x["lam_off"] == 0 and not x["D8'"]


def test_p2_gamed_thermostat_fails_d8_prime():
    x = r("P2")
    assert x["phi"] > 0                                       # it does ask about other states...
    assert x["lam_off"] == 0 and not x["D8'"]                 # ...but ignores the answer


def test_p3_decorative_decoder_fails_d8_and_d8_prime():
    x = r("P3")
    assert x["lam"] == 0 and x["lam_off"] == 0 and not x["D8"] and not x["D8'"]


def test_p4_lookup_table_same_behaviour_fails_d8():
    orig, tab = S.SelfSimForager(), V.TableForager()
    assert all(orig.act(s) == tab.act(s) for s in V.FORAGER_STATES)
    assert not r("P4")["D8"]          # implementation-dependent by design: open decision


def test_p5_self_simulating_foragers_pass_d8_prime():
    for name in ("P5 Self-sim forager, fixed belief", "P5 Learned self-model",
                 "P5 Learned self-model, low capacity"):
        x = results()[name]
        assert x["lam_off"] > 0 and x["D8'"], name


def test_p6_thermostat_with_self_lookahead_passes_d8_prime():
    x = r("P6")
    assert x["lam_off"] > 0 and x["D8'"]


def test_p7_gamma_do_positive_and_r15_does_not_survive():
    for name, x in results().items():
        if "R={}" not in x["split (D9)"]:
            assert x["gamma_do"] > 0, name
    low = results()["P5 Learned self-model, low capacity"]
    assert low["gamma"] < 0.01 and low["gamma_do"] > 0.05   # R15 was an artefact of gamma


def test_p8_known_open_hole2_reencoding_changes_split():
    """Documents an OPEN hole: D9 is not invariant under re-encoding of the state.
    When the coarse-graining definition lands, this test must be inverted."""
    plain = results()["Reactive forager (v0)"]["split (D9)"]
    reenc = r("P8")["split (D9)"]
    assert plain != reenc


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok ", name)
