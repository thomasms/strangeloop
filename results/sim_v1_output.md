| agent | split (D9) | R = decoder inputs | gamma | lam | eps | eps_cf | rho |
|---|---|---|---|---|---|---|---|
| Thermostat + bit | W={temp} R={bit} | no | 0.71 | - | - | - | - |
| Reactive forager (v0) | W={fd,eb} R={mode,heading} | no | 0.17 | - | - | - | - |
| Self-simulating forager | W={fd,eb} R={mode,heading} | yes | 0.15 | 0.16 | 0.28 | 0.63 | -0.08 |

Thermostat + bit {'temp': 'sensory', 'bit': 'self'}
Reactive forager (v0) {'fd': 'sensory', 'eb': 'sensory', 'mode': 'self', 'heading': 'self'}
Self-simulating forager {'fd': 'sensory', 'eb': 'sensory', 'mode': 'self', 'heading': 'self'}

--- Learned self-models (fixed-point iteration T <- F(T)) ---
| agent | fixed point after | gamma | lam | eps | eps_cf | rho |
|---|---|---|---|---|---|---|
| Learned self-model (reads mode,heading,fd,eb) | 2 it. [32, 0] | 0.15 | 0.16 | 0.00 | 0.00 | 1.00 |
| Learned self-model, low capacity (reads mode,fd) | 2 it. [5, 0] | 0.00 | 0.16 | 0.33 | 0.08 | 0.86 |
