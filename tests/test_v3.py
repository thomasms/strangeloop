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
"""
