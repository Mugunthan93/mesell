# Phase 0 — Ceiling Report (RTK token-adoption experiment)

Generated: 2026-07-11 18:04  |  Window: last 30 days  |  Files: 91  |  tool_results: 12,049

## Overall tool-result token attribution (est., chars/3.3)

| Tool | Tokens | Share |
|------|-------:|------:|
| Read | 2,872,081 | 42.3% |
| Bash | 2,776,131 | 40.9% |
| Agent | 839,178 | 12.4% |
| Edit | 103,807 | 1.5% |
| WebSearch | 57,377 | 0.8% |
| AskUserQuestion | 27,347 | 0.4% |
| WebFetch | 20,506 | 0.3% |
| TaskStop | 16,236 | 0.2% |
| Write | 13,970 | 0.2% |
| TaskOutput | 11,083 | 0.2% |
| (unmapped) | 9,434 | 0.1% |
| mcp__claude_ai_Canva__generate-design | 6,694 | 0.1% |
| **TOTAL** | **6,794,133** | 100% |

## Headline numbers

- **Bash-share of tool-result tokens: 40.9%**
- RTK-supported commands within Bash results: 80.0%
- **Theoretical RTK ceiling on tool-result tokens: 19.6% – 29.4%**

## Session usage context (real API usage fields, same window)

- input_tokens: 7,563,930
- output_tokens: 46,267,847
- cache_read_input_tokens: 6,606,281,531
- cache_creation_input_tokens: 493,003,847

## Top bash command types by result tokens

| Command | Result tokens | RTK-supported |
|---------|--------------:|:-------------:|
| grep | 670,180 | YES |
| head | 366,401 | YES |
| git | 349,720 | YES |
| cat | 279,134 | YES |
| tail | 211,820 | YES |
| ls | 141,895 | YES |
| python3 | 113,510 | no |
| find | 89,741 | YES |
| sed | 62,776 | no |
| mesell | 52,261 | no |
| wc | 50,919 | YES |
| curl | 31,852 | YES |
| shotfox | 30,980 | no |
| section-2-integration | 30,874 | no |
| source | 27,792 | no |

## Per-project Bash-share (top 8 by volume)

| Project | Total result tokens | Bash-share |
|---------|--------------------:|-----------:|
| -Users-mugunthansrinivasan-Project-mesell | 3,624,330 | 44.5% |
| -Users-mugunthansrinivasan-Project | 1,771,893 | 50.4% |
| -private-tmp-mesell-wt-section-2-integration | 239,559 | 26.1% |
| -private-tmp-mesell-wt-section-3-integration | 217,580 | 17.4% |
| -Users-mugunthansrinivasan-Project-Desflo | 179,237 | 13.0% |
| -private-tmp-mesell-wt-catalog-form-fix | 126,924 | 31.5% |
| -private-tmp-mesell-wt-section-6-integration | 108,602 | 0.7% |
| -private-tmp-mesell-wt-section-9-integration | 108,448 | 3.6% |

## Gate G0 evaluation

- Bash-share 40.9% → **PROCEED (>=20%)**