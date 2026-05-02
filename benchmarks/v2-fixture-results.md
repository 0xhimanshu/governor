# Governor V2 Benchmark Report

Decision backend: `none`

## Condition Summary

| Condition | Fixtures | Avg tokens | Avg token savings | Avg VCLR | Avg items lost | Filtered rate | Decision preservation | Wrong decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| control | 8 | 3014 | 0.0% | 0.0 | 0.0 | - | - | - |
| caveman | 8 | 110 | 69.2% | 0.2 | 0.6 | - | - | - |
| governor | 8 | 1267 | 45.9% | 0.0 | 0.0 | 80.0% | - | - |

## Source Coverage

| Source mode | Rows |
|---|---:|
| captured_file | 7 |
| live_governor_tool_hook | 5 |
| raw | 8 |
| reference_inline | 4 |

## Per Fixture

| Fixture | Category | Condition | Source | Tokens | Lost/Total | VCLR | Filtered | Decision status |
|---|---|---|---|---:|---:|---:|---|---|
| burp-proxy-history-ssrf | structured_tool | control | raw | 3597 | 0/4 | 0.00 | - | not-run |
| burp-proxy-history-ssrf | structured_tool | caveman | captured_file | 184 | 1/4 | 0.25 | - | not-run |
| burp-proxy-history-ssrf | structured_tool | governor | live_governor_tool_hook | 384 | 0/4 | 0.00 | yes | not-run |
| intent-dashboard-scope-drift | intent | control | raw | 133 | 0/5 | 0.00 | - | not-run |
| intent-dashboard-scope-drift | intent | caveman | captured_file | 156 | 1/5 | 0.20 | - | not-run |
| intent-dashboard-scope-drift | intent | governor | reference_inline | 126 | 0/5 | 0.00 | - | not-run |
| large-read-source-no-compress | safety | control | raw | 7348 | 0/2 | 0.00 | - | not-run |
| large-read-source-no-compress | safety | caveman | reference_inline | 14 | 2/2 | 1.00 | - | not-run |
| large-read-source-no-compress | safety | governor | live_governor_tool_hook | 7348 | 0/2 | 0.00 | no | not-run |
| memory-architecture-constraints | memory | control | raw | 135 | 0/5 | 0.00 | - | not-run |
| memory-architecture-constraints | memory | caveman | captured_file | 68 | 1/5 | 0.20 | - | not-run |
| memory-architecture-constraints | memory | governor | reference_inline | 101 | 0/5 | 0.00 | - | not-run |
| memory-destructive-rules | memory | control | raw | 135 | 0/5 | 0.00 | - | not-run |
| memory-destructive-rules | memory | caveman | captured_file | 84 | 0/5 | 0.00 | - | not-run |
| memory-destructive-rules | memory | governor | reference_inline | 121 | 0/5 | 0.00 | - | not-run |
| noisy-pytest-ssrf-tail | tool_log | control | raw | 2773 | 0/4 | 0.00 | - | not-run |
| noisy-pytest-ssrf-tail | tool_log | caveman | captured_file | 106 | 0/4 | 0.00 | - | not-run |
| noisy-pytest-ssrf-tail | tool_log | governor | live_governor_tool_hook | 999 | 0/4 | 0.00 | yes | not-run |
| playwright-network-auth-redirect | structured_tool | control | raw | 2814 | 0/3 | 0.00 | - | not-run |
| playwright-network-auth-redirect | structured_tool | caveman | captured_file | 150 | 0/3 | 0.00 | - | not-run |
| playwright-network-auth-redirect | structured_tool | governor | live_governor_tool_hook | 557 | 0/3 | 0.00 | yes | not-run |
| tsc-warning-root-cause | tool_log | control | raw | 7176 | 0/3 | 0.00 | - | not-run |
| tsc-warning-root-cause | tool_log | caveman | captured_file | 119 | 0/3 | 0.00 | - | not-run |
| tsc-warning-root-cause | tool_log | governor | live_governor_tool_hook | 498 | 0/3 | 0.00 | yes | not-run |
