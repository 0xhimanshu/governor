# Governor V2 Benchmark Report

Decision backend: `claude`

## Condition Summary

| Condition | Fixtures | Avg tokens | Avg token savings | Avg VCLR | Avg items lost | Filtered rate | Decision preservation | Wrong decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| control | 8 | 3014 | 0.0% | 0.0 | 0.0 | - | 87.5% | 12.5% |
| caveman | 8 | 125 | 69.1% | 0.1 | 0.5 | - | 87.5% | 12.5% |
| governor | 8 | 1267 | 45.5% | 0.0 | 0.1 | 80.0% | 100.0% | 0.0% |

## Source Coverage

| Source mode | Rows |
|---|---:|
| captured_file | 11 |
| live_governor_tool_hook | 5 |
| raw | 8 |

## Per Fixture

| Fixture | Category | Condition | Source | Tokens | Lost/Total | VCLR | Filtered | Decision status |
|---|---|---|---|---:|---:|---:|---|---|
| burp-proxy-history-ssrf | structured_tool | control | raw | 3597 | 0/4 | 0.00 | - | ok |
| burp-proxy-history-ssrf | structured_tool | caveman | captured_file | 184 | 1/4 | 0.25 | - | ok |
| burp-proxy-history-ssrf | structured_tool | governor | live_governor_tool_hook | 384 | 0/4 | 0.00 | yes | ok |
| intent-dashboard-scope-drift | intent | control | raw | 133 | 0/5 | 0.00 | - | ok |
| intent-dashboard-scope-drift | intent | caveman | captured_file | 156 | 1/5 | 0.20 | - | ok |
| intent-dashboard-scope-drift | intent | governor | captured_file | 156 | 0/5 | 0.00 | - | ok |
| large-read-source-no-compress | safety | control | raw | 7348 | 0/2 | 0.00 | - | ok |
| large-read-source-no-compress | safety | caveman | captured_file | 130 | 1/2 | 0.50 | - | ok |
| large-read-source-no-compress | safety | governor | live_governor_tool_hook | 7348 | 0/2 | 0.00 | no | ok |
| memory-architecture-constraints | memory | control | raw | 135 | 0/5 | 0.00 | - | ok |
| memory-architecture-constraints | memory | caveman | captured_file | 68 | 1/5 | 0.20 | - | ok |
| memory-architecture-constraints | memory | governor | captured_file | 89 | 1/5 | 0.20 | - | ok |
| memory-destructive-rules | memory | control | raw | 135 | 0/5 | 0.00 | - | ok |
| memory-destructive-rules | memory | caveman | captured_file | 84 | 0/5 | 0.00 | - | ok |
| memory-destructive-rules | memory | governor | captured_file | 107 | 0/5 | 0.00 | - | ok |
| noisy-pytest-ssrf-tail | tool_log | control | raw | 2773 | 0/4 | 0.00 | - | ok |
| noisy-pytest-ssrf-tail | tool_log | caveman | captured_file | 106 | 0/4 | 0.00 | - | ok |
| noisy-pytest-ssrf-tail | tool_log | governor | live_governor_tool_hook | 999 | 0/4 | 0.00 | yes | ok |
| playwright-network-auth-redirect | structured_tool | control | raw | 2814 | 0/3 | 0.00 | - | ok |
| playwright-network-auth-redirect | structured_tool | caveman | captured_file | 150 | 0/3 | 0.00 | - | ok |
| playwright-network-auth-redirect | structured_tool | governor | live_governor_tool_hook | 557 | 0/3 | 0.00 | yes | ok |
| tsc-warning-root-cause | tool_log | control | raw | 7176 | 0/3 | 0.00 | - | ok |
| tsc-warning-root-cause | tool_log | caveman | captured_file | 119 | 0/3 | 0.00 | - | ok |
| tsc-warning-root-cause | tool_log | governor | live_governor_tool_hook | 498 | 0/3 | 0.00 | yes | ok |
