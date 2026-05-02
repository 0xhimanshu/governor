# Governor Tool Filter Benchmarks

Local deterministic v1.1 run. These cases test signal preservation, not just token reduction.

Live Claude CLI evaluator runs are optional and were not included in this snapshot because
the local Claude CLI auth currently returns `Invalid API key · Please run /login`.

| Case | Tool | Filtered | Expected | Raw tokens | Summary tokens | Blocked | Hook ms | Terms | Signal preserved |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| noisy-pytest | Bash | yes | yes | 2773 | 997 | 64.0% | 112.2 | 3/3 | yes |
| burp-mcp-structured | mcp__burp__proxy_history | yes | yes | 3597 | 327 | 90.9% | 103.4 | 4/4 | yes |
| large-read-safety | Read | no | no | 7306 | - | 0.0% | 122.9 | 0/0 | yes |
