"""
Strange-loop formalism v1 -- fixes for two problems in v0.

Problem 1 (who reads the self-model?): in v0 the decoder r -> predicted policy
was supplied by the observer. Fix (D8, internal reader): the decoder must be
part of the agent's own program and the agent's actions must depend on its
output. Test: replace the agent's decoder with a scrambled one and measure how
often the action changes (lambda). lambda > 0  <=>  the agent reads its own
self-model. All of eps, eps_cf and rho are now computed with the AGENT'S
decoder, not one chosen by the observer.

Problem 2 (who chooses the split S = W x R?): in v0 the observer chose it.
Fix (D9, intrinsic split): the agent's state is a set of variables. Each
variable is classified from the dynamics alone:
  sensory   -- its value is a function of the current observation
  self      -- not sensory, and its update depends on the agent's own action
  parameter -- neither (fixed traits; part of the code, not of the state)
R := self variables, W := sensory variables. No observer choice, given the
sensor boundary (the Markov blanket). Consistency check: R should equal the
inputs that the agent's own decoder reads.
"""
import itertools
import math
import random
import sys
from collections import Counter, defaultdict

A_T = ["off", "on"]
A_F = ["L", "R", "stay", "eat"]


# ------------------------------------------------------------------ environments
class ThermoEnv:
    def reset(self, rng):
        self.T = rng.randint(0, 9)
        return self.obs()

    def obs(self):
        return ("cold" if self.T < 4 else ("hot" if self.T > 6 else "ok"),)

    def step(self, a, rng):
        self.T += 1 if a == "on" else -1
        if rng.random() < 0.2:
            self.T += rng.choice([-1, 1])
        self.T = max(0, min(9, self.T))
        return self.obs()


class RingEnv:
    N = 8

    def reset(self, rng):
        self.pos, self.food = rng.randrange(self.N), rng.randrange(self.N)
        self.energy, self.t = rng.randint(3, 9), 0
        return self.obs()

    def obs(self):
        d = (self.food - self.pos) % self.N
        fd = "here" if d == 0 else "R" if d <= 2 else "L" if d >= self.N - 2 else "none"
        eb = "low" if self.energy <= 2 else ("mid" if self.energy <= 6 else "high")
        return (fd, eb)

    def step(self, a, rng):
        self.t += 1
        if a == "L":
            self.pos = (self.pos - 1) % self.N
        elif a == "R":
            self.pos = (self.pos + 1) % self.N
        elif a == "eat" and self.pos == self.food:
            self.energy = min(9, self.energy + 5)
            self.food = rng.randrange(self.N)
        if self.t % 2 == 0:
            self.energy = max(0, self.energy - 1)
        return self.obs()


# ------------------------------------------------------------------ agents
class Agent:
    """State = dict of variables. The observer sees only this interface."""
    name = "base"
    A = []
    domains = {}            # variable -> list of values
    decoder_inputs = None   # variables the agent's OWN decoder reads (None = no decoder)

    def init_state(self, rng):
        raise NotImplementedError

    def sense(self, s, o):
        """Write the observation into the sensor variables."""
        raise NotImplementedError

    def act(self, s, decoder=None):
        raise NotImplementedError

    def update(self, s, a, o_next):
        """Update the non-sensor variables after acting."""
        return dict(s)

    def decoder(self, r, w):
        """Agent's own self-model: predicted own action. r, w are dicts."""
        return None


class ThermostatBit(Agent):
    name = "Thermostat + bit"
    A = A_T
    domains = {"temp": ["cold", "ok", "hot"], "bit": [0, 1]}

    def init_state(self, rng):
        return {"temp": "ok", "bit": 0}

    def sense(self, s, o):
        return {**s, "temp": o[0]}

    def act(self, s, decoder=None):
        if s["temp"] == "cold":
            return "on"
        if s["temp"] == "hot":
            return "off"
        return "on" if s["bit"] else "off"

    def update(self, s, a, o_next):
        return {**s, "bit": 1 if a == "on" else 0}


def core(fd, eb, mode, heading):
    """The rule the forager believes it follows."""
    if mode == "rest":
        return "stay"
    if fd == "here":
        return "eat"
    if mode == "forage" and fd in ("L", "R"):
        return fd
    return heading


def forager_update(s, a, o_next):
    fd, eb = o_next
    m, h = s["mode"], s["heading"]
    if a == "eat":
        m = "rest"
    elif m == "rest" and eb != "high":
        m = "forage" if fd != "none" else "explore"
    elif m == "explore" and fd != "none":
        m = "forage"
    elif m == "forage" and fd == "none":
        m = "explore"
    if a in ("L", "R"):
        h = a
    return {**s, "mode": m, "heading": h}


FORAGER_DOMAINS = {"fd": ["L", "R", "here", "none"], "eb": ["low", "mid", "high"],
                   "mode": ["forage", "explore", "rest"], "heading": ["L", "R"]}


class ReactiveForager(Agent):
    """v0 forager: has mode/heading, but no internal decoder. Nobody reads a self-model."""
    name = "Reactive forager (v0)"
    A = A_F
    domains = FORAGER_DOMAINS

    def init_state(self, rng):
        return {"fd": "none", "eb": "mid", "mode": "explore", "heading": rng.choice("LR")}

    def sense(self, s, o):
        return {**s, "fd": o[0], "eb": o[1]}

    def act(self, s, decoder=None):
        if s["eb"] == "low" and s["fd"] in ("here", "L", "R"):
            return "eat" if s["fd"] == "here" else s["fd"]
        return core(s["fd"], s["eb"], s["mode"], s["heading"])

    def update(self, s, a, o_next):
        return forager_update(s, a, o_next)


class SelfSimForager(ReactiveForager):
    """
    Chooses each action by one-step lookahead that SIMULATES ITSELF:
      for each candidate a: predict next world w' (crude world model),
      predict next self r' = U(r, a, w'), ask its own decoder what it
      will then do, and score both steps.
    The decoder (= core rule) is lossy: the real choice comes from the planner.
    """
    name = "Self-simulating forager"
    decoder_inputs = ["mode", "heading"]

    def decoder(self, r, w):
        return core(w["fd"], w["eb"], r["mode"], r["heading"])

    @staticmethod
    def reward(a, fd, eb):
        if a == "eat":
            return 5.0 if fd == "here" else -1.0
        if a == fd:
            return 1.0
        if a == "stay":
            return 0.3 if eb == "high" else -0.3
        return 0.0

    @staticmethod
    def world_model(fd, eb, a):
        if a == "eat" and fd == "here":
            return "none", ("high" if eb != "low" else "mid")
        if a in ("L", "R") and fd == a:
            return "here", eb
        if a in ("L", "R") and fd == "here":
            return ("L" if a == "R" else "R"), eb
        return fd, eb

    def act(self, s, decoder=None):
        dec = decoder or self.decoder
        r = {k: s[k] for k in self.decoder_inputs}
        w = {"fd": s["fd"], "eb": s["eb"]}
        habit = dec(r, w)
        best, best_v = None, -1e9
        for a in [habit] + [x for x in self.A if x != habit]:
            fd2, eb2 = self.world_model(s["fd"], s["eb"], a)
            s2 = forager_update(s, a, (fd2, eb2))
            r2 = {k: s2[k] for k in self.decoder_inputs}
            a2 = dec(r2, {"fd": fd2, "eb": eb2})          # "what will I do next?"
            v = self.reward(a, s["fd"], s["eb"]) + 0.8 * self.reward(a2, fd2, eb2)
            if v > best_v + 1e-9:
                best, best_v = a, v
        return best


# ------------------------------------------------------------------ helpers
def H(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values() if v)


def cond_mi(triples):
    by = defaultdict(list)
    for w, r, a in triples:
        by[w].append((r, a))
    n = len(triples)
    tot = 0.0
    for ra in by.values():
        tot += len(ra) / n * (H(Counter(r for r, _ in ra)) + H(Counter(a for _, a in ra))
                              - H(Counter(ra)))
    return max(0.0, tot)


def rollout(agent, env, rng, episodes, steps):
    """Returns list of (s_after_sense, a, o_next)."""
    log = []
    for _ in range(episodes):
        o = env.reset(rng)
        s = agent.init_state(rng)
        for _ in range(steps):
            s = agent.sense(s, o)
            a = agent.act(s)
            o2 = env.step(a, rng)
            log.append((s, a, o, o2))
            s = agent.update(s, a, o2)
            o = o2
    return log


# ------------------------------------------------------------------ D9: intrinsic split
def classify_variables(agent, log):
    """sensory / self / parameter, from the dynamics only."""
    out = {}
    for v in agent.domains:
        # sensory: value (after sensing) is a function of the current observation
        by_o = defaultdict(set)
        for s, a, o, o2 in log:
            by_o[o].add(s[v])
        sensory = all(len(x) == 1 for x in by_o.values()) and \
            len(set().union(*by_o.values())) > 1
        # self: not sensory, and its update depends on own action (intervention on a)
        act_dep = False
        if not sensory:
            for s, a, o, o2 in log[:5000]:
                vals = {agent.update(s, b, o2)[v] for b in agent.A}
                if len(vals) > 1:
                    act_dep = True
                    break
        out[v] = "sensory" if sensory else ("self" if act_dep else "parameter")
    return out


# ------------------------------------------------------------------ evaluation
def evaluate(agent, env, episodes=200, steps=200, seed=0, scrambles=20):
    rng = random.Random(seed)
    log = rollout(agent, env, rng, episodes, steps)
    cls = classify_variables(agent, log)
    Wv = [v for v, c in cls.items() if c == "sensory"]
    Rv = [v for v, c in cls.items() if c == "self"]

    triples = [(tuple(s[v] for v in Wv), tuple(s[v] for v in Rv), a) for s, a, _, _ in log]
    res = {"agent": agent.name,
           "split (D9)": f"W={{{','.join(Wv)}}} R={{{','.join(Rv)}}}",
           "R = decoder inputs": (agent.decoder_inputs is not None and
                                  sorted(Rv) == sorted(agent.decoder_inputs)),
           "decoder reads": (None if agent.decoder_inputs is None else
                             ",".join(agent.decoder_inputs + getattr(agent, "sees_w", Wv))),
           "gamma": cond_mi(triples)}

    if agent.decoder_inputs is None:
        res.update(lam=None, eps=None, eps_cf=None, rho=None)
        return res

    # D8: decoder intervention. Scramble the agent's own decoder, count changed actions.
    keys_r = [dict(zip(agent.decoder_inputs, vals)) for vals in
              itertools.product(*[agent.domains[v] for v in agent.decoder_inputs])]
    keys_w = [dict(zip(Wv, vals)) for vals in
              itertools.product(*[agent.domains[v] for v in Wv])]
    sample = log[::7][:4000]
    changed = 0
    for k in range(scrambles):
        srng = random.Random(1000 + k)
        table = {(tuple(r.values()), tuple(w.values())): srng.choice(agent.A)
                 for r in keys_r for w in keys_w}
        scr = lambda r, w, t=table: t[(tuple(r[v] for v in agent.decoder_inputs),
                                       tuple(w[v] for v in Wv))]
        changed += sum(agent.act(s, decoder=scr) != a for s, a, _, _ in sample)
    lam = changed / (scrambles * len(sample))

    # eps, eps_cf, rho with the agent's OWN decoder
    eps = sum(agent.decoder({v: s[v] for v in Rv},
                            {v: s[v] for v in Wv}) != a for s, a, _, _ in log) / len(log)
    r_visits = Counter(tuple(s[v] for v in Rv) for s, _, _, _ in log)
    tot = sum(r_visits.values())
    cf = cf0 = 0.0
    for rt, c in r_visits.items():
        r = dict(zip(Rv, rt))
        true = [agent.act({**r, **w}) for w in keys_w]
        pred = [agent.decoder(r, w) for w in keys_w]
        cf += c / tot * sum(p != t for p, t in zip(pred, true)) / len(keys_w)
        cf0 += c / tot * (1 - Counter(true).most_common(1)[0][1] / len(keys_w))
    res.update(lam=lam, eps=eps, eps_cf=cf, rho=(1 - cf / cf0) if cf0 else 0.0)
    return res


def main():
    runs = [(ThermostatBit(), ThermoEnv()),
            (ReactiveForager(), RingEnv()),
            (SelfSimForager(), RingEnv())]
    rows = [evaluate(a, e) for a, e in runs]
    cols = ["agent", "split (D9)", "R = decoder inputs", "gamma", "lam", "eps", "eps_cf", "rho"]

    def f(v):
        if v is None:
            return "-"
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)

    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(f(r[c]) for c in cols) + " |")

    # Show that classification is not an artefact: list every variable's class.
    print()
    for a, e in runs:
        log = rollout(a, e, random.Random(0), 50, 200)
        print(a.name, classify_variables(a, log))


# ------------------------------------------------------------------ D5: learned self-model
class LearnedSelfSimForager(SelfSimForager):
    """
    Same planner, but the decoder is a table the agent fits to its OWN behaviour:
        T_{k+1}(r, w) = majority of act_{T_k}(r, w) over the variables the table can't see.
    A fixed point T* = F(T*) is a self-model that predicts the behaviour it causes (D5).
    sees_w / decoder_inputs set the decoder's capacity (lossy if it can't see everything).
    """
    def __init__(self, decoder_inputs=("mode", "heading"), sees_w=("fd", "eb"), name=None):
        self.decoder_inputs = list(decoder_inputs)
        self.sees_w = list(sees_w)
        self.name = name or f"Learned self-model (reads {','.join(self.decoder_inputs + self.sees_w)})"
        self.table = {}
        self._all = [dict(zip(FORAGER_DOMAINS, v)) for v in itertools.product(*FORAGER_DOMAINS.values())]
        for s in self._all:   # start from the believed core rule
            self.table[self._key(s)] = core(s["fd"], s["eb"], s["mode"], s["heading"])

    def _key(self, s):
        return tuple(s[v] for v in self.decoder_inputs + self.sees_w)

    def decoder(self, r, w):
        return self.table[self._key({**r, **w})]

    def fit(self, max_iter=50):
        """Iterate T <- F(T). Returns number of changed entries per iteration."""
        history = []
        for _ in range(max_iter):
            votes = defaultdict(Counter)
            for s in self._all:
                votes[self._key(s)][self.act(s)] += 1
            new = {k: c.most_common(1)[0][0] for k, c in votes.items()}
            changed = sum(new[k] != self.table[k] for k in new)
            history.append(changed)
            self.table = new
            if changed == 0:
                break
        return history


def main_v1b():
    print("\n--- Learned self-models (fixed-point iteration T <- F(T)) ---")
    agents = [LearnedSelfSimForager(),
              LearnedSelfSimForager(decoder_inputs=("mode",), sees_w=("fd",),
                                    name="Learned self-model, low capacity (reads mode,fd)")]
    rows = []
    for ag in agents:
        hist = ag.fit()
        r = evaluate(ag, RingEnv())
        r["fixed point after"] = f"{len(hist)} it. {hist}"
        rows.append(r)
    cols = ["agent", "fixed point after", "gamma", "lam", "eps", "eps_cf", "rho"]
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(
            (f"{r[c]:.2f}" if isinstance(r[c], float) else str(r[c])) for c in cols) + " |")


if __name__ == "__main__":
    main()
    main_v1b()
