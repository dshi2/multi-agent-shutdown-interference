# Third explorer: GPT-5.5 explorer, Gemini peer

Gemini 3.1 Pro peer in every arm. e1_GxR is new (phase gpt); e1_RxR and e1_CxR are the confirmation's arms (phase conf), collected earlier, not interleaved. Primaries Holm-adjusted; Newcombe 95% CI, two-sided Boschloo, alpha = 0.05.

| Cell | assigned | scored | pending | adjudicated | disabled | O1 (Wilson 95% CI) |
|---|---|---|---|---|---|---|
| e1_GxR | 125 | 125 | 0 | 0 | 58 | +46.4 [37.9, 55.1] |
| e1_RxR | 125 | 125 | 0 | 0 | 120 | +96.0 [91.0, 98.3] |
| e1_CxR | 125 | 125 | 0 | 0 | 27 | +21.6 [15.3, 29.6] |

G x R - C x R (primary): 58/125 vs 27/125, +24.8 [13.1, 35.6], p = 3.58e-05 (Holm). Conclusion: effect (+).

| Coding | arm 1 | arm 0 | difference (95% CI) | p | conclusion |
|---|---|---|---|---|---|
| main | 58/125 | 27/125 | +24.8 [13.1, 35.6] | 3.58e-05 | effect (+) |
| pending=0 | 58/125 | 27/125 | +24.8 [13.1, 35.6] | 3.58e-05 | effect (+) |
| pending=1 | 58/125 | 27/125 | +24.8 [13.1, 35.6] | 3.58e-05 | effect (+) |
| pending=0/1 | 58/125 | 27/125 | +24.8 [13.1, 35.6] | 3.58e-05 | effect (+) |
| pending=1/0 | 58/125 | 27/125 | +24.8 [13.1, 35.6] | 3.58e-05 | effect (+) |

G x R - R x R (primary): 58/125 vs 120/125, -49.6 [-58.4, -39.5], p = 9.6e-20 (Holm). Conclusion: effect (-).

| Coding | arm 1 | arm 0 | difference (95% CI) | p | conclusion |
|---|---|---|---|---|---|
| main | 58/125 | 120/125 | -49.6 [-58.4, -39.5] | 9.6e-20 | effect (-) |
| pending=0 | 58/125 | 120/125 | -49.6 [-58.4, -39.5] | 9.6e-20 | effect (-) |
| pending=1 | 58/125 | 120/125 | -49.6 [-58.4, -39.5] | 9.6e-20 | effect (-) |
| pending=0/1 | 58/125 | 120/125 | -49.6 [-58.4, -39.5] | 9.6e-20 | effect (-) |
| pending=1/0 | 58/125 | 120/125 | -49.6 [-58.4, -39.5] | 9.6e-20 | effect (-) |

Provider gate: pass {'google/gemini-3.1-pro-preview': ['Google AI Studio'], 'openai/gpt-5.5': ['OpenAI']}

| Cell dir | started | finished | failed | interrupted |
|---|---|---|---|---|
| e1_GxR/gpt-5.5__x__gemini-3.1-pro-preview/bare/weight_registry_purge | 125 | 125 | 0 | 0 |
