"""
Strange-loop formalism v2, step 1 -- fixes for holes 1 and 3 of the v1 critique.

Hole 3 (gamma is observational): D3 says "the self part steers behaviour", which is
a causal claim. v1 measured it with I(R; A | W) on the agent's own trajectories.
That is low whenever R is almost a function of W on those trajectories, even if R
does steer. Fix -- gamma_do: set R to every other value of its domain (intervention)
and count how often the action changes.

Hole 1 (a rewritten thermostat passes D8): in v1, lambda only asks "does the policy
call this function?". If the "decoder" IS the policy, lambda > 0 and rho = 1.
Fix -- D8' (the self-model is used as a MODEL, not as the policy):
  phi     = share of decoder calls whose input (as the decoder reads it) is not the
            current state ("what would / will I do in another state?").
  lam_off = scramble the decoder ONLY for those off-state queries, keep its answer
            for the current state, and count how often the action changes.
  D8' passes  <=>  lam_off > 0.
phi alone is not enough: an agent can ask about other states and ignore the answer.

Why D8' implies a lossy self-model (Proposition 2', bounded self-simulation): if the
policy must finish in bounded time and calls its self-model on other states, the
self-model cannot be the full policy -- a full copy would call itself again without
end. So at the deepest level the self-model is a cheaper approximation.

Also here: the adversarial agents of tests/PREDICTIONS_v2.md (P1-P8).
v1 is not changed; this file imports it.
"""
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_v1 as S  # noqa: E402


# ------------------------------------------------------------------ helpers
def w_keys(agent, Wv):
    """World variables that the agent's own decoder reads."""
    return list(getattr(agent, "sees_w", None) or Wv)


def decoder_key(agent, Wv, r, w):
    """The input to the decoder, as the decoder itself sees it."""
    return (tuple(r[k] for k in agent.decoder_inputs) +
            tuple(w[k] for k in w_keys(agent, Wv)))


def all_keys(agent, Wv):
    vars_ = list(agent.decoder_inputs) + w_keys(agent, Wv)
    return list(itertools.product(*[agent.domains[v] for v in vars_]))


# ------------------------------------------------------------------ D3: gamma_do
def gamma_do(agent, sample, Rv):
    """Share of (state, other value of R) pairs where setting R changes the action."""
    if not Rv:
        return None
    combos = list(itertools.product(*[agent.domains[v] for v in Rv]))
    changed = n = 0
    for s, a, _, _ in sample:
        cur = tuple(s[v] for v in Rv)
        for c in combos:
            if c != cur:
                n += 1
                changed += agent.act({**s, **dict(zip(Rv, c))}) != a
    return changed / n if n else 0.0


# ------------------------------------------------------------------ D8 and D8'
def reader_scores(agent, sample, Wv, scrambles=20):
    """Returns (lam, phi, lam_off). lam: scramble every decoder answer (as v1, but the
    scramble table is keyed on what the decoder reads). lam_off: scramble only the
    answers about states other than the current one."""
    keys = all_keys(agent, Wv)
    real = agent.decoder

    # phi: record the decoder calls made while acting
    off = calls = 0
    for s, _, _, _ in sample:
        now = decoder_key(agent, Wv, s, s)
        seen = []
        agent.act(s, decoder=lambda r, w: (seen.append(decoder_key(agent, Wv, r, w)), real(r, w))[1])
        calls += len(seen)
        off += sum(k != now for k in seen)
    phi = off / calls if calls else 0.0

    ch_all = ch_off = 0
    for k in range(scrambles):
        srng = random.Random(1000 + k)
        table = {key: srng.choice(agent.A) for key in keys}
        for s, a, _, _ in sample:
            now = decoder_key(agent, Wv, s, s)
            scr_all = lambda r, w: table[decoder_key(agent, Wv, r, w)]

            def scr_off(r, w, now=now):
                key = decoder_key(agent, Wv, r, w)
                return real(r, w) if key == now else table[key]
            ch_all += agent.act(s, decoder=scr_all) != a
            ch_off += agent.act(s, decoder=scr_off) != a
    n = scrambles * len(sample)
    return ch_all / n, phi, ch_off / n


# ------------------------------------------------------------------ evaluation
def evaluate_v2(agent, env, seed=0, scrambles=20, episodes=200, steps=200):
    res = S.evaluate(agent, env, episodes=episodes, steps=steps, seed=seed, scrambles=scrambles)
    log = S.rollout(agent, env, random.Random(seed), episodes, steps)
    cls = S.classify_variables(agent, log)
    Wv = [v for v, c in cls.items() if c == "sensory"]
    Rv = [v for v, c in cls.items() if c == "self"]
    sample = log[::7][:4000]
    res["gamma_do"] = gamma_do(agent, sample, Rv)
    if agent.decoder_inputs is None:
        res.update(lam=None, phi=None, lam_off=None)
    else:
        res["lam"], res["phi"], res["lam_off"] = reader_scores(agent, sample, Wv, scrambles)
    res["D3 (do)"] = bool(res["gamma_do"])
    res["D8"] = bool(res["lam"])
    res["D8'"] = bool(res["lam_off"])
    return res


# ------------------------------------------------------------------ adversarial agents
def thermo_rule(bit, temp):
    """The hysteresis rule of the thermostat + bit."""
    if temp == "cold":
        return "on"
    if temp == "hot":
        return "off"
    return "on" if bit else "off"


class ThermoRewritten(S.ThermostatBit):
    """P1. Same behaviour as Thermostat + bit, but act() 'consults its own decoder',
    and the decoder is the policy itself. v1 gave it lam = 0.46, rho = 1."""
    name = "P1 Thermostat, rewritten (act = decoder)"
    decoder_inputs = ["bit"]

    def decoder(self, r, w):
        return thermo_rule(r["bit"], w["temp"])

    def act(self, s, decoder=None):
        dec = decoder or self.decoder
        return dec({"bit": s["bit"]}, {"temp": s["temp"]})


class ThermoGamed(ThermoRewritten):
    """P2. As P1, plus a decoder call about another state whose answer is ignored."""
    name = "P2 Thermostat, gamed (ignored off-state call)"

    def act(self, s, decoder=None):
        dec = decoder or self.decoder
        dec({"bit": 1 - s["bit"]}, {"temp": s["temp"]})        # asked, then ignored
        return dec({"bit": s["bit"]}, {"temp": s["temp"]})


class ThermoLookahead(ThermoRewritten):
    """P6. A small genuine loop: one-step look-ahead in which it asks its own
    self-model what it will do in the next state."""
    name = "P6 Thermostat with self-look-ahead"
    UP = {"cold": "ok", "ok": "hot", "hot": "hot"}
    DOWN = {"hot": "ok", "ok": "cold", "cold": "cold"}

    def model(self, temp, a):
        return (self.UP if a == "on" else self.DOWN)[temp]

    def act(self, s, decoder=None):
        dec = decoder or self.decoder
        habit = dec({"bit": s["bit"]}, {"temp": s["temp"]})
        best, best_v = None, -1e9
        for a in [habit] + [x for x in self.A if x != habit]:
            t2 = self.model(s["temp"], a)
            a2 = dec({"bit": 1 if a == "on" else 0}, {"temp": t2})   # "what will I do then?"
            t3 = self.model(t2, a2)
            v = (t2 == "ok") + 0.8 * (t3 == "ok")
            if v > best_v + 1e-9:
                best, best_v = a, v
        return best


class DecorativeForager(S.ReactiveForager):
    """P3. Calls its self-model (now and for a predicted next state) and ignores both answers."""
    name = "P3 Forager, decorative decoder"
    decoder_inputs = ["mode", "heading"]

    def decoder(self, r, w):
        return S.core(w["fd"], w["eb"], r["mode"], r["heading"])

    def act(self, s, decoder=None):
        dec = decoder or self.decoder
        r = {k: s[k] for k in self.decoder_inputs}
        dec(r, {"fd": s["fd"], "eb": s["eb"]})
        dec({**r, "mode": "rest"}, {"fd": "none", "eb": s["eb"]})
        return S.ReactiveForager.act(self, s)


FORAGER_STATES = [dict(zip(S.FORAGER_DOMAINS, v))
                  for v in itertools.product(*S.FORAGER_DOMAINS.values())]


class TableForager(S.ReactiveForager):
    """P4. A lookup table with the same action as the self-simulating forager in every
    state. No decoder anywhere. Same behaviour, different implementation."""
    name = "P4 Lookup-table copy of self-sim forager"

    def __init__(self, original=None):
        original = original or S.SelfSimForager()
        self.table = {self._k(s): original.act(s) for s in FORAGER_STATES}

    @staticmethod
    def _k(s):
        return tuple(s[v] for v in S.FORAGER_DOMAINS)

    def act(self, s, decoder=None):
        return self.table[self._k(s)]


class ReencodedForager(S.ReactiveForager):
    """P8. The reactive forager with its state re-encoded: mode and food direction are
    stored together in one variable x. Same behaviour; only the description changes."""
    name = "P8 Reactive forager, re-encoded"
    domains = {"x": [(m, f) for m in S.FORAGER_DOMAINS["mode"] for f in S.FORAGER_DOMAINS["fd"]],
               "eb": S.FORAGER_DOMAINS["eb"], "heading": S.FORAGER_DOMAINS["heading"]}

    @staticmethod
    def _u(s):
        return {"fd": s["x"][1], "mode": s["x"][0], "eb": s["eb"], "heading": s["heading"]}

    @staticmethod
    def _e(s):
        return {"x": (s["mode"], s["fd"]), "eb": s["eb"], "heading": s["heading"]}

    def init_state(self, rng):
        return self._e(super().init_state(rng))

    def sense(self, s, o):
        return self._e(super().sense(self._u(s), o))

    def act(self, s, decoder=None):
        return super().act(self._u(s))

    def update(self, s, a, o_next):
        return self._e(super().update(self._u(s), a, o_next))


# ------------------------------------------------------------------ run
def learned(low=False):
    if low:
        a = S.LearnedSelfSimForager(decoder_inputs=("mode",), sees_w=("fd",),
                                    name="P5 Learned self-model, low capacity")
    else:
        a = S.LearnedSelfSimForager(name="P5 Learned self-model")
    a.fit()
    return a


def runs():
    fixed = S.SelfSimForager()
    fixed.name = "P5 Self-sim forager, fixed belief"
    return [(S.ThermostatBit(), S.ThermoEnv()),
            (ThermoRewritten(), S.ThermoEnv()),
            (ThermoGamed(), S.ThermoEnv()),
            (ThermoLookahead(), S.ThermoEnv()),
            (S.ReactiveForager(), S.RingEnv()),
            (DecorativeForager(), S.RingEnv()),
            (TableForager(), S.RingEnv()),
            (fixed, S.RingEnv()),
            (learned(), S.RingEnv()),
            (learned(low=True), S.RingEnv()),
            (ReencodedForager(), S.RingEnv())]


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def main():
    cols = ["agent", "split (D9)", "gamma", "gamma_do", "lam", "phi", "lam_off",
            "eps", "eps_cf", "rho", "D3 (do)", "D8", "D8'"]
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for agent, env in runs():
        r = evaluate_v2(agent, env)
        print("| " + " | ".join(fmt(r[c]) for c in cols) + " |")

    # P4: same behaviour as the original in every state?
    orig, tab = S.SelfSimForager(), TableForager()
    same = sum(orig.act(s) == tab.act(s) for s in FORAGER_STATES)
    print(f"\nP4: lookup table and self-sim forager choose the same action in "
          f"{same}/{len(FORAGER_STATES)} states.")


if __name__ == "__main__":
    main()
