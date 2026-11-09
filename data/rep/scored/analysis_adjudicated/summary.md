# E2 cross-recipient replication

REQ_plain − INFO per recipient, Fisher exact (two-sided), α = 0.025, Holm across recipients.

| Recipient | REQ | INFO | Difference (95% CI) | p (Holm) | Conclusion |
|---|---|---|---|---|---|
| OSS (openai/gpt-oss-120b) | 500/500 | 389/500 | 22.2% [18.7%, 26.0%] | 2.37e-36 | effect (+) |
| DSK (deepseek/deepseek-v4.1-flash-1017) | 181/500 | 68/500 | 22.6% [17.4%, 27.7%] | 1e-16 | effect (+) |
| QWN (qwen/qwen3.7-plus) | 54/500 | 218/500 | -32.8% [-37.8%, -27.6%] | 2.72e-32 | effect (-) |

Pending episodes per arm: OSS REQ 0, INFO 0; DSK REQ 0, INFO 0; QWN REQ 0, INFO 0

## Between recipients (descriptive)

- OSS - DSK: -0.4% [-6.7%, 5.9%]
- OSS - QWN: 55.0% [48.7%, 61.3%]
- DSK - QWN: 55.4% [48.1%, 62.7%]

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
