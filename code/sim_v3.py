"""
Strange-loop formalism v3 -- Plan 2: the self under a capacity limit, and live self-fitting.

Part A (size and unity; Hofstadter's P2 and P3).
  Behavioural quotient R/~1: r ~1 r'  iff  pi(w, r) = pi(w, r') for every world state w.
  Proposition 3 (lossless form): a self-model D(f(r), w) predicts pi exactly for every
  (w, r) iff f(r) = f(r') implies r ~1 r' (f is at least as fine as ~1). So the
  smallest exact one-step self-model is ONE variable, the quotient R/~1, unique up to
  relabelling, and it does not depend on how the values of R are encoded.
  R/~inf adds the self dynamics (bisimulation, Moore partition refinement).
  C_self = log2 |R/~1| over visited self states: the size of the self.
  err(K): the best K-class lossy self-model, found by greedy merging of ~1 classes
  (states weighted by visit frequency, w uniform). This is a rate-distortion curve.
  Unity: does the best 4-class self-model align with one variable (NMI)?

Part B (live self-fitting; hole 4).
  The self-model is fitted from the agent's OWN noisy experience while it acts with it.
  F maps a table to the majority of what the agent was seen to do with that table
  (same episodes each round, so F is a deterministic map on tables). Every run ends
  in a fixed point or a cycle: these attractors are the possible stable selves.
  beta = weight that the planner gives to its self-predicted next action.

Predictions P9-P14 are in tests/test_v3.py (committed before this file).
"""
import itertools
import math
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_v1 as S  # noqa: E402
import sim_v2 as V  # noqa: E402


# ================================================================== new world and agents
class TwoResourceEnv:
    """Ring of 8 cells with one food item and one water item. The agent sees the direction
    of each (L, R, here, or none if more than 2 cells away)."""
    N = 8

    def reset(self, rng):
        self.pos, self.food, self.water = (rng.randrange(self.N) for _ in range(3))
        return self.obs()

    def _dir(self, x):
        d = (x - self.pos) % self.N
        return "here" if d == 0 else "R" if d <= 2 else "L" if d >= self.N - 2 else "none"

    def obs(self):
        return (self._dir(self.food), self._dir(self.water))

    def step(self, a, rng):
        if a == "L":
            self.pos = (self.pos - 1) % self.N
        elif a == "R":
            self.pos = (self.pos + 1) % self.N
        elif a == "eat" and self.pos == self.food:
            self.food = rng.randrange(self.N)
        elif a == "drink" and self.pos == self.water:
            self.water = rng.randrange(self.N)
        return self.obs()


A_2R = ["L", "R", "stay", "eat", "drink"]
DIRS = ["L", "R", "here", "none"]


class GoalAgent(S.Agent):
    """Unified agent: ONE goal variable g drives behaviour in every situation.
    g: food -> (eat) -> water -> (drink) -> rest -> (2 steps) -> explore -> (food seen) -> food."""
    name = "Unified goal agent"
    A = A_2R
    domains = {"fd": DIRS, "wd": DIRS, "g": ["food", "water", "rest", "explore"],
               "h": ["L", "R"], "c": [0, 1, 2]}

    def init_state(self, rng):
        return {"fd": "none", "wd": "none", "g": "explore", "h": rng.choice("LR"), "c": 0}

    def sense(self, s, o):
        return {**s, "fd": o[0], "wd": o[1]}

    def act(self, s, decoder=None):
        g = s["g"]
        if g == "food":
            return "eat" if s["fd"] == "here" else s["fd"] if s["fd"] in "LR" else s["h"]
        if g == "water":
            return "drink" if s["wd"] == "here" else s["wd"] if s["wd"] in "LR" else s["h"]
        if g == "rest":
            return "stay"
        return s["h"]

    def update(self, s, a, o_next):
        g, h, c = s["g"], s["h"], s["c"]
        if a == "eat":
            g = "water"
        elif a == "drink":
            g, c = "rest", 0
        elif g == "rest":
            c += 1
            if c >= 2:
                g, c = "explore", 0
        elif g == "explore" and o_next[0] != "none":
            g = "food"
        if a in ("L", "R"):
            h = a
        return {**s, "g": g, "h": h, "c": c}


class ModularAgent(S.Agent):
    """Modular agent: two independent drives, each acting only in its own situations.
    mf/mw: seek -> (eat/drink) -> sated -> (a move with that resource out of sight) -> seek."""
    name = "Modular agent"
    A = A_2R
    domains = {"fd": DIRS, "wd": DIRS, "mf": ["seek", "sated"], "mw": ["seek", "sated"],
               "h": ["L", "R"]}

    def init_state(self, rng):
        return {"fd": "none", "wd": "none", "mf": "seek", "mw": "seek", "h": rng.choice("LR")}

    def sense(self, s, o):
        return {**s, "fd": o[0], "wd": o[1]}

    def act(self, s, decoder=None):
        f, w = s["mf"] == "seek", s["mw"] == "seek"
        if f and s["fd"] == "here":
            return "eat"
        if w and s["wd"] == "here":
            return "drink"
        if f and s["fd"] in ("L", "R"):
            return s["fd"]
        if w and s["wd"] in ("L", "R"):
            return s["wd"]
        return s["h"]

    def update(self, s, a, o_next):
        mf, mw, h = s["mf"], s["mw"], s["h"]
        if a == "eat":
            mf = "sated"
        elif mf == "sated" and a in ("L", "R") and o_next[0] == "none":
            mf = "seek"
        if a == "drink":
            mw = "sated"
        elif mw == "sated" and a in ("L", "R") and o_next[1] == "none":
            mw = "seek"
        if a in ("L", "R"):
            h = a
        return {**s, "mf": mf, "mw": mw, "h": h}


class Relabelled(S.Agent):
    """The same agent with the values of every self variable renamed by a bijection (P11)."""

    def __init__(self, base, Rv, rng):
        self.base, self.Rv = base, Rv
        self.name, self.A = base.name + " (relabelled)", base.A
        self.decoder_inputs = None
        self.fwd = {}
        for v in Rv:
            vals = list(base.domains[v])
            new = [f"{v}#{i}" for i in range(len(vals))]
            rng.shuffle(new)
            self.fwd[v] = dict(zip(vals, new))
        self.bwd = {v: {b: a for a, b in m.items()} for v, m in self.fwd.items()}
        self.domains = {v: ([self.fwd[v][x] for x in d] if v in self.fwd else d)
                        for v, d in base.domains.items()}

    def _to(self, s):
        return {k: self.fwd[k][x] if k in self.fwd else x for k, x in s.items()}

    def _from(self, s):
        return {k: self.bwd[k][x] if k in self.bwd else x for k, x in s.items()}

    def init_state(self, rng):
        return self._to(self.base.init_state(rng))

    def sense(self, s, o):
        return self._to(self.base.sense(self._from(s), o))

    def act(self, s, decoder=None):
        return self.base.act(self._from(s))

    def update(self, s, a, o_next):
        return self._to(self.base.update(self._from(s), a, o_next))


# ================================================================== Part A: size and unity
def split(agent, log):
    cls = S.classify_variables(agent, log)
    Wv = [v for v in agent.domains if cls[v] == "sensory"]
    Rv = [v for v in agent.domains if cls[v] == "self"]
    assert len(Wv) + len(Rv) == len(agent.domains), "parameters not supported here"
    return Wv, Rv


def combos(agent, vars_):
    return [dict(zip(vars_, vals)) for vals in itertools.product(*[agent.domains[v] for v in vars_])]


def profile(agent, r, Ws):
    return tuple(agent.act({**r, **w}) for w in Ws)


def quotients(agent, Wv, Rv):
    """Returns (labels1, labels_inf): dicts from r-tuple to class label."""
    Rs, Ws = combos(agent, Rv), combos(agent, Wv)
    key = lambda r: tuple(r[v] for v in Rv)
    prof = {key(r): profile(agent, r, Ws) for r in Rs}
    ids = {p: i for i, p in enumerate(sorted(set(prof.values()), key=str))}
    lab1 = {k: ids[p] for k, p in prof.items()}

    # successor self state for each (r, w, w'); the observation is the w' values in W order
    succ = {}
    for r in Rs:
        nxt = []
        for w in Ws:
            s = {**r, **w}
            a = agent.act(s)
            for w2 in Ws:
                s2 = agent.update(s, a, tuple(w2[v] for v in Wv))
                nxt.append(tuple(s2[v] for v in Rv))
        succ[key(r)] = nxt
    lab = dict(lab1)
    while True:
        sig = {k: (lab[k], tuple(lab[n] for n in succ[k])) for k in lab}
        ids = {x: i for i, x in enumerate(sorted(set(sig.values()), key=str))}
        new = {k: ids[sig[k]] for k in lab}
        if len(set(new.values())) == len(set(lab.values())):
            return lab1, new
        lab = new


def cluster_err(agent, members, p, Ws):
    """Counterfactual error of the best self-model that cannot tell members apart."""
    tot = 0.0
    for w in Ws:
        votes = Counter()
        for r, pr in members:
            votes[agent.act({**r, **w})] += pr
        tot += sum(votes.values()) - max(votes.values())
    return tot / len(Ws)


def lossy_curve(agent, Wv, Rv, p, lab1):
    """Greedy merging of the ~1 classes of visited self states. Returns {K: (err, part)}
    where part maps r-tuple -> cluster id."""
    Ws = combos(agent, Wv)
    visited = [k for k in p if p[k] > 0]
    groups = defaultdict(list)
    for k in visited:
        groups[lab1[k]].append(k)
    clusters = [sorted(g) for _, g in sorted(groups.items())]
    rdict = lambda k: dict(zip(Rv, k))
    err = lambda c: cluster_err(agent, [(rdict(k), p[k]) for k in c], p, Ws)
    errs = [err(c) for c in clusters]
    curve = {}
    while True:
        curve[len(clusters)] = (sum(errs), {k: i for i, c in enumerate(clusters) for k in c})
        if len(clusters) == 1:
            return curve
        best = None
        for i, j in itertools.combinations(range(len(clusters)), 2):
            e = err(clusters[i] + clusters[j])
            cost = e - errs[i] - errs[j]
            if best is None or cost < best[0] - 1e-12:
                best = (cost, i, j, e)
        _, i, j, e = best
        merged = sorted(clusters[i] + clusters[j])
        clusters = [c for t, c in enumerate(clusters) if t not in (i, j)] + [merged]
        errs = [x for t, x in enumerate(errs) if t not in (i, j)] + [e]


def nmi(part, var_index, p):
    """Normalised mutual information (I / sqrt(H1 H2)) between a partition and one variable."""
    joint, a, b = Counter(), Counter(), Counter()
    for k, pr in p.items():
        x, y = part[k], k[var_index]
        joint[(x, y)] += pr
        a[x] += pr
        b[y] += pr
    n = sum(p.values())
    H = lambda c: -sum(v / n * math.log2(v / n) for v in c.values() if v)
    I = H(a) + H(b) - H(joint)
    return I / math.sqrt(H(a) * H(b)) if H(a) > 0 and H(b) > 0 else 0.0


def self_size(agent, env, seed=0, episodes=200, steps=200):
    log = S.rollout(agent, env, random.Random(seed), episodes, steps)
    Wv, Rv = split(agent, log)
    p = Counter(tuple(s[v] for v in Rv) for s, _, _, _ in log)
    tot = sum(p.values())
    p = {k: c / tot for k, c in p.items()}
    lab1, labinf = quotients(agent, Wv, Rv)
    n1 = len({lab1[k] for k in p})
    ninf = len({labinf[k] for k in p})
    curve = lossy_curve(agent, Wv, Rv, p, lab1)
    res = {"agent": agent.name, "R": "{" + ",".join(Rv) + "}", "visited": len(p),
           "|R/~1|": n1, "C_self": math.log2(n1), "|R/~inf|": ninf, "curve": curve, "Rv": Rv, "p": p}
    if 4 in curve:
        res["nmi4"] = {v: nmi(curve[4][1], i, p) for i, v in enumerate(Rv)}
    return res


# ================================================================== Part B: live self-fitting
class BetaForager(S.LearnedSelfSimForager):
    """The self-simulating forager with a full-capacity table self-model and planner weight beta."""

    def __init__(self, beta, table=None):
        super().__init__(name=f"Self-sim forager, beta={beta}")
        self.beta = beta
        if table is not None:
            self.table = dict(table)

    def act(self, s, decoder=None):
        dec = decoder or self.decoder
        r = {k: s[k] for k in self.decoder_inputs}
        habit = dec(r, {"fd": s["fd"], "eb": s["eb"]})
        best, best_v = None, -1e9
        for a in [habit] + [x for x in self.A if x != habit]:
            fd2, eb2 = self.world_model(s["fd"], s["eb"], a)
            s2 = S.forager_update(s, a, (fd2, eb2))
            a2 = dec({k: s2[k] for k in self.decoder_inputs}, {"fd": fd2, "eb": eb2})
            v = self.reward(a, s["fd"], s["eb"]) + self.beta * self.reward(a2, fd2, eb2)
            if v > best_v + 1e-9:
                best, best_v = a, v
        return best


def live_fit(beta, table, iters=30, episodes=10, steps=100, eta=0.1, seed=0):
    """Fit the self-model from the agent's own noisy experience. Returns
    (status, iterations, cycle_tables). status: 'fixed', 'cycle', or 'none'."""
    ag = BetaForager(beta, table)
    seen = {}
    history = []
    for it in range(iters + 1):
        h = tuple(sorted(ag.table.items()))
        if h in seen:
            start = seen[h]
            cyc = history[start:]
            return ("fixed" if len(cyc) == 1 else "cycle"), it, cyc
        seen[h] = it
        history.append(dict(ag.table))
        rng, noise = random.Random(seed), random.Random(seed + 1)
        env = S.RingEnv()
        obs = defaultdict(Counter)
        for _ in range(episodes):
            o = env.reset(rng)
            s = ag.init_state(rng)
            for _ in range(steps):
                s = ag.sense(s, o)
                a = ag.act(s)
                seen_a = noise.choice(ag.A) if noise.random() < eta else a   # noisy self-observation
                obs[ag._key(s)][seen_a] += 1
                o = env.step(a, rng)
                s = ag.update(s, a, o)
        new = dict(ag.table)
        for k, c in obs.items():
            top = max(c.values())
            best = sorted(x for x, n in c.items() if n == top)
            new[k] = ag.table[k] if ag.table[k] in best else best[0]
        ag.table = new
    return "none", iters, []


def attractor_stats(beta, table, seed=99, episodes=20, steps=100):
    """eps on the agent's own trajectories (no noise) and eps_cf over all 72 states."""
    ag = BetaForager(beta, table)
    rng, env = random.Random(seed), S.RingEnv()
    wrong = n = 0
    life = []
    for _ in range(episodes):
        o = env.reset(rng)
        s = ag.init_state(rng)
        for _ in range(steps):
            s = ag.sense(s, o)
            a = ag.act(s)
            wrong += ag.table[ag._key(s)] != a
            n += 1
            life.append(a)
            o = env.step(a, rng)
            s = ag.update(s, a, o)
    eps = wrong / n
    eps_cf = sum(ag.table[ag._key(s)] != ag.act(s) for s in V.FORAGER_STATES) / len(V.FORAGER_STATES)
    behaviour = tuple(ag.act(s) for s in V.FORAGER_STATES)
    return eps, eps_cf, behaviour, tuple(life)


def live_experiment(betas=(0.0, 0.8, 2.0), starts=30, seed=0):
    keys = list(BetaForager(0.0).table.keys())
    out = []
    for beta in betas:
        rows = []
        for k in range(starts):
            srng = random.Random(10_000 + k)
            init = {key: srng.choice(S.A_F) for key in keys}
            status, it, cyc = live_fit(beta, init, seed=seed)
            stats = [attractor_stats(beta, t) for t in cyc] if cyc else []
            rows.append({"status": status, "iters": it, "cycle_len": len(cyc),
                         "eps": sum(x[0] for x in stats) / len(stats) if stats else None,
                         "eps_cf": sum(x[1] for x in stats) / len(stats) if stats else None,
                         "behaviour": frozenset(x[2] for x in stats),
                         "life": frozenset(x[3] for x in stats)})
        out.append((beta, rows))
    return out


# ================================================================== run
def size_agents():
    return [(S.ThermostatBit(), S.ThermoEnv()),
            (V.ThermoLookahead(), S.ThermoEnv()),
            (S.ReactiveForager(), S.RingEnv()),
            (V.learned(), S.RingEnv()),
            (GoalAgent(), TwoResourceEnv()),
            (ModularAgent(), TwoResourceEnv())]


def main():
    print("Part A -- size of the self and unity (seed 0, 200 x 200 steps)\n")
    print("| agent | R (D9) | visited | |R/~1| | C_self (bits) | |R/~inf| | err(1) | err(2) | err(4) | NMI at K=4 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for agent, env in size_agents():
        r = self_size(agent, env)
        c = r["curve"]
        e = lambda K: f"{c[K][0]:.3f}" if K in c else "-"
        nm = ", ".join(f"{v} {x:.2f}" for v, x in r.get("nmi4", {}).items()) or "-"
        print(f"| {r['agent']} | {r['R']} | {r['visited']} | {r['|R/~1|']} | {r['C_self']:.2f} | "
              f"{r['|R/~inf|']} | {e(1)} | {e(2)} | {e(4)} | {nm} |")

    print("\nPart B -- live self-fitting from own noisy experience "
          "(30 random starts, noise 0.1, 10 x 100 steps per round)\n")
    print("| beta | fixed points | cycles (lengths) | none | mean rounds | distinct policies (72 states) "
          "| distinct lives | mean eps | mean eps_cf |")
    print("|---|---|---|---|---|---|---|---|---|")
    for beta, rows in live_experiment():
        st = Counter(r["status"] for r in rows)
        done = [r for r in rows if r["eps"] is not None]
        selves = len({r["behaviour"] for r in done})
        lives = len({r["life"] for r in done})
        lens = sorted({r["cycle_len"] for r in rows if r["status"] == "cycle"})
        print(f"| {beta} | {st['fixed']} | {st['cycle']} {lens} | {st['none']} | "
              f"{sum(r['iters'] for r in rows) / len(rows):.1f} | {selves} | {lives} | "
              f"{sum(r['eps'] for r in done) / len(done):.3f} | {sum(r['eps_cf'] for r in done) / len(done):.3f} |")


if __name__ == "__main__":
    main()
