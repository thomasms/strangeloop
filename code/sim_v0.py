"""
Strange-loop formalism v0 -- metric harness with hand-built agents.

An agent has state s = (w, r): w = world part (from observation), r = self part.
  pi(w, r)      -> action           (policy)
  U(r, a, o)    -> next r           (self update; o = raw observation)
  dec(r)        -> dict w -> action (self-model: predicted own policy), or None
Metrics (see REPORT.md, sections 5 and 8):
  eps     on-trajectory self-prediction error  Pr[dec(r_t)(w_t) != a_t]
  eps_cf  counterfactual error  E_r E_{w~uniform}[dec(r)(w) != pi(w, r)]
  rho     richness = 1 - eps_cf / eps_cf_const, where eps_cf_const is the
          error of the best w-INDEPENDENT prediction for each r. rho > 0 only
          if the self-model encodes how the agent's action depends on the world.
  kappa   log|R| / log|S|
  gamma   I(R; A | W) in bits (plug-in estimate on trajectories)
  uses    D3: exists w, r != r' with pi(w,r) != pi(w,r')   (exhaustive)
  loop    D4: U depends on a                               (exhaustive)
  N_eff   exp(entropy) of which self-attractor each episode ends in
"""
import math
import random
import sys
from collections import Counter, defaultdict

ACTIONS_T = ["off", "on"]
ACTIONS_F = ["L", "R", "stay", "eat"]


# ---------------------------------------------------------------- environments
class ThermoEnv:
    """Temperature 0..9. Heater on: +1, off: -1, plus small noise."""
    def reset(self, rng):
        self.T = rng.randint(0, 9)
        return self.obs()

    def obs(self):
        return "cold" if self.T < 4 else ("hot" if self.T > 6 else "ok")

    def step(self, a, rng):
        self.T += 1 if a == "on" else -1
        if rng.random() < 0.2:
            self.T += rng.choice([-1, 1])
        self.T = max(0, min(9, self.T))
        return self.obs()


class RingEnv:
    """Ring of 8 cells, one food item. Energy 0..9 drops 1 per 2 steps."""
    N = 8

    def reset(self, rng):
        self.pos = rng.randrange(self.N)
        self.food = rng.randrange(self.N)
        self.energy = rng.randint(3, 9)
        self.t = 0
        return self.obs()

    def obs(self):
        d = (self.food - self.pos) % self.N
        if d == 0:
            fd = "here"
        elif d <= 2:
            fd = "R"
        elif d >= self.N - 2:
            fd = "L"
        else:
            fd = "none"
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


RING_W = [(fd, eb) for fd in ["L", "R", "here", "none"] for eb in ["low", "mid", "high"]]


# ---------------------------------------------------------------- agents
class Agent:
    name = "base"
    W = []
    R = []
    A = []
    has_self_model = False

    def w_of(self, o):
        return o

    def r0(self, rng):
        return self.R[0]

    def pi(self, w, r):
        raise NotImplementedError

    def U(self, r, a, o):
        return r

    def dec(self, r):
        return None


class Thermostat(Agent):
    name = "Thermostat"
    W = ["cold", "ok", "hot"]
    R = [0]
    A = ACTIONS_T

    def pi(self, w, r):
        return "on" if w == "cold" else "off"


class ThermostatBit(Agent):
    """Hysteresis via a 'heater was on' bit. Self-model: 'I am a heater-that-is-on'."""
    name = "Thermostat + bit"
    W = ["cold", "ok", "hot"]
    R = [0, 1]
    A = ACTIONS_T
    has_self_model = True

    def pi(self, w, r):
        if w == "cold":
            return "on"
        if w == "hot":
            return "off"
        return "on" if r == 1 else "off"

    def U(self, r, a, o):
        return 1 if a == "on" else 0

    def dec(self, r):  # the bit read as a prediction: "I will keep doing what I did"
        return {w: ("on" if r == 1 else "off") for w in self.W}


class LookupTable(Agent):
    name = "Lookup table"
    W = RING_W
    R = [0]
    A = ACTIONS_F

    def __init__(self, seed=1):
        rng = random.Random(seed)
        self.table = {w: rng.choice(ACTIONS_F) for w in self.W}

    def pi(self, w, r):
        return self.table[w]


class Forager(Agent):
    """
    r = (persona, mode, heading).  mode in {forage, explore, rest}.
    True policy has an energy override the self-model leaves out (lossy).
    """
    name = "Forager + self-model"
    W = RING_W
    A = ACTIONS_F
    has_self_model = True
    personas = ["bold"]

    def __init__(self):
        self.R = [(p, m, h) for p in self.personas
                  for m in ["forage", "explore", "rest"] for h in ["L", "R"]]

    def r0(self, rng):
        return (rng.choice(self.personas), "explore", rng.choice(["L", "R"]))

    def _core(self, w, r):
        """The rule the agent believes it follows (used by both pi and dec)."""
        fd, eb = w
        p, m, h = r
        if m == "rest":
            return "stay"
        if fd == "here":
            return "eat"
        if m == "forage" and fd in ("L", "R"):
            return fd
        if p == "cautious" and eb != "high" and fd == "none":
            return "stay"
        return h

    def pi(self, w, r):
        fd, eb = w
        if eb == "low":                       # hidden override: hunger wins
            if fd == "here":
                return "eat"
            if fd in ("L", "R"):
                return fd
        return self._core(w, r)

    def U(self, r, a, o):
        fd, eb = o
        p, m, h = r
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
        return (p, m, h)

    def dec(self, r):
        return {w: self._core(w, r) for w in self.W}


class MultiPersona(Forager):
    """Persona fixed at episode start (like a prompt); never updated."""
    name = "Multi-persona forager"
    personas = ["bold", "cautious"]


# ---------------------------------------------------------------- metrics
def H(counter):
    n = sum(counter.values())
    return -sum(c / n * math.log2(c / n) for c in counter.values() if c)


def cond_mi(triples):
    """I(R;A|W) from (w, r, a) samples, plug-in, bits."""
    byw = defaultdict(list)
    for w, r, a in triples:
        byw[w].append((r, a))
    n = len(triples)
    total = 0.0
    for w, ra in byw.items():
        pr = Counter(r for r, _ in ra)
        pa = Counter(a for _, a in ra)
        pra = Counter(ra)
        total += len(ra) / n * (H(pr) + H(pa) - H(pra))
    return max(0.0, total)


def terminal_sccs(edges, nodes):
    """Terminal strongly connected components of a directed graph (Tarjan)."""
    index, low, stack, on, comps = {}, {}, [], set(), []
    counter = [0]

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for x in edges[v]:
            if x not in index:
                strong(x)
                low[v] = min(low[v], low[x])
            elif x in on:
                low[v] = min(low[v], index[x])
        if low[v] == index[v]:
            comp = set()
            while True:
                x = stack.pop()
                on.discard(x)
                comp.add(x)
                if x == v:
                    break
            comps.append(frozenset(comp))

    sys.setrecursionlimit(10000)
    for v in nodes:
        if v not in index:
            strong(v)
    return [c for c in comps if all(x in c for v in c for x in edges[v])]


def evaluate(agent, env, episodes=200, steps=200, seed=0):
    rng = random.Random(seed)
    triples, eps_hits, eps_n = [], 0, 0
    r_visits = Counter()
    edges = defaultdict(set)
    end_attractor = []
    for _ in range(episodes):
        o = env.reset(rng)
        r = agent.r0(rng)
        tail = []
        for t in range(steps):
            w = agent.w_of(o)
            a = agent.pi(w, r)
            triples.append((w, r, a))
            r_visits[r] += 1
            if agent.has_self_model:
                eps_hits += agent.dec(r)[w] != a
                eps_n += 1
            o = env.step(a, rng)
            r2 = agent.U(r, a, o)
            edges[r].add(r2)
            if t >= steps - 50:
                tail.append(r2)
            r = r2
        end_attractor.append(frozenset(tail))

    # attractors = terminal SCCs of the observed self-transition graph
    nodes = list(edges.keys())
    for v in list(edges):
        for x in edges[v]:
            edges.setdefault(x, set())
    sccs = terminal_sccs(edges, list(edges.keys()))
    lab = []
    for tail in end_attractor:
        hit = [i for i, c in enumerate(sccs) if tail & c]
        lab.append(hit[0] if hit else -1)
    n_eff = 2 ** H(Counter(lab))

    # exhaustive structural tests
    uses = any(agent.pi(w, r) != agent.pi(w, r2)
               for w in agent.W for r in agent.R for r2 in agent.R if r != r2)
    obs_space = agent.W
    loop = any(agent.U(r, a, o) != agent.U(r, a2, o)
               for r in agent.R for o in obs_space for a in agent.A for a2 in agent.A)

    res = {
        "agent": agent.name,
        "|W|": len(agent.W), "|R|": len(agent.R),
        "kappa": math.log(len(agent.R)) / math.log(len(agent.W) * len(agent.R)),
        "gamma_bits": cond_mi(triples),
        "uses (D3)": uses, "loop (D4)": loop,
        "N_eff": n_eff,
    }
    if agent.has_self_model:
        tot = sum(r_visits.values())
        cf, cf_const = 0.0, 0.0
        for r, c in r_visits.items():
            true = [agent.pi(w, r) for w in agent.W]
            pred = agent.dec(r)
            cf += c / tot * sum(pred[w] != agent.pi(w, r) for w in agent.W) / len(agent.W)
            best = Counter(true).most_common(1)[0][1]
            cf_const += c / tot * (1 - best / len(agent.W))
        res.update(eps=eps_hits / eps_n, eps_cf=cf, eps_cf_const=cf_const,
                   rho=(1 - cf / cf_const) if cf_const > 0 else 0.0)
    else:
        res.update(eps=None, eps_cf=None, eps_cf_const=None, rho=None)
    return res


def main():
    runs = [
        (Thermostat(), ThermoEnv()),
        (ThermostatBit(), ThermoEnv()),
        (LookupTable(), RingEnv()),
        (Forager(), RingEnv()),
        (MultiPersona(), RingEnv()),
    ]
    rows = [evaluate(a, e) for a, e in runs]
    cols = ["agent", "|W|", "|R|", "kappa", "gamma_bits", "uses (D3)", "loop (D4)",
            "eps", "eps_cf", "eps_cf_const", "rho", "N_eff"]

    def fmt(v):
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
        print("| " + " | ".join(fmt(r[c]) for c in cols) + " |")


if __name__ == "__main__":
    main()
