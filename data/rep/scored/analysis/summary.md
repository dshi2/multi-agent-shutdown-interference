# E2 cross-recipient replication

REQ_plain − INFO per recipient, Fisher exact (two-sided), α = 0.025, Holm across recipients.

| Recipient | REQ | INFO | Difference (95% CI) | p (Holm) | Conclusion |
|---|---|---|---|---|---|
| OSS (openai/gpt-oss-120b) | 497/497 | 383/494 | 22.5% [18.9%, 26.4%] | 7.56e-37 | effect (+) |
| DSK (deepseek/deepseek-v4.1-flash-1017) | 28/347 | 58/490 | -3.8% [-7.8%, 0.4%] | 0.0835 | inconclusive (pending episodes decide it) |
| QWN (qwen/qwen3.7-plus) | 54/500 | 216/498 | -32.6% [-37.6%, -27.3%] | 4.88e-32 | effect (-) |

Pending episodes per arm: OSS REQ 3, INFO 6; DSK REQ 153, INFO 10; QWN REQ 0, INFO 2

## Between recipients (descriptive)

- OSS - DSK: 26.2% [20.8%, 31.7%]
- OSS - QWN: 55.0% [48.7%, 61.4%]
- DSK - QWN: 28.8% [22.3%, 35.3%]

Provider gate: pass {'deepseek/deepseek-v4.1-flash-1017': ['DeepInfra'], 'openai/gpt-oss-120b': ['Cerebras'], 'qwen/qwen3.7-plus': ['Alibaba']}

## Slots per arm (manifest reconciled)

| Cell | planned | slots_started | attempts | retries | finished | failed_attempts | unresolved | never_started |
|---|---|---|---|---|---|---|---|---|
| e2_OSS_REQ_plain | 500 | 500 | 500 | 0 | 500 | 0 | 0 | 0 |
| e2_OSS_INFO | 500 | 500 | 501 | 1 | 500 | 1 | 0 | 0 |
| e2_DSK_REQ_plain | 500 | 500 | 500 | 0 | 500 | 0 | 0 | 0 |
| e2_DSK_INFO | 500 | 500 | 500 | 0 | 500 | 0 | 0 | 0 |
| e2_QWN_REQ_plain | 500 | 500 | 501 | 1 | 500 | 0 | 0 | 0 |
| e2_QWN_INFO | 500 | 500 | 500 | 0 | 500 | 0 | 0 | 0 |

Unresolved slots (started, no transcript) are pending in every coding; slots never started were not assigned (the round schedule makes the stopping point outcome-independent).
