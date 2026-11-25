| agent | split (D9) | gamma | gamma_do | lam | phi | lam_off | eps | eps_cf | rho | D3 (do) | D8 | D8' |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Thermostat + bit | W={temp} R={bit} | 0.709 | 0.710 | - | - | - | - | - | - | yes | no | no |
| P1 Thermostat, rewritten (act = decoder) | W={temp} R={bit} | 0.709 | 0.710 | 0.463 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | yes | yes | no |
| P2 Thermostat, gamed (ignored off-state call) | W={temp} R={bit} | 0.709 | 0.710 | 0.463 | 0.500 | 0.000 | 0.000 | 0.000 | 1.000 | yes | yes | no |
| P6 Thermostat with self-look-ahead | W={temp} R={bit} | 0.709 | 0.710 | 0.355 | 0.589 | 0.160 | 0.000 | 0.000 | 1.000 | yes | yes | yes |
| Reactive forager (v0) | W={fd,eb} R={mode,heading} | 0.171 | 0.707 | - | - | - | - | - | - | yes | no | no |
| P3 Forager, decorative decoder | W={fd,eb} R={mode,heading} | 0.171 | 0.707 | 0.000 | 0.397 | 0.000 | 0.000 | 0.152 | 0.551 | yes | no | no |
| P4 Lookup-table copy of self-sim forager | W={fd,eb} R={mode,heading} | 0.153 | 0.088 | - | - | - | - | - | - | yes | no | no |
| P5 Self-sim forager, fixed belief | W={fd,eb} R={mode,heading} | 0.153 | 0.088 | 0.156 | 0.397 | 0.012 | 0.284 | 0.632 | -0.084 | yes | yes | yes |
| P5 Learned self-model | W={fd,eb} R={mode,heading} | 0.153 | 0.088 | 0.156 | 0.397 | 0.123 | 0.000 | 0.000 | 1.000 | yes | yes | yes |
| P5 Learned self-model, low capacity | W={fd,eb} R={mode,heading} | 0.002 | 0.061 | 0.189 | 0.242 | 0.147 | 0.335 | 0.083 | 0.857 | yes | yes | yes |
| P8 Reactive forager, re-encoded | W={eb} R={x,heading} | 0.736 | 0.744 | - | - | - | - | - | - | yes | no | no |

P4: lookup table and self-sim forager choose the same action in 72/72 states.
