# Project Edge-Node — Hardware Benchmark Report

## Debugging note
Initial benchmarks showed a consistent ~2s gap between Ollama's own reported
`total_duration` and measured end-to-end latency. Traced to `localhost` hostname
resolution overhead (likely an IPv6-first lookup falling back to IPv4). Switching to
the literal `127.0.0.1` address for local Ollama calls cut mean latency from 5.356s
to 0.973s — see the tables above for the full before/after comparison.

**Model:** qwen3:4b-instruct | **Latency requests:** 50 (failed: 0) | **TTFT requests:** 10
**Data source:** real rows from data\synthetic_logs.json, labels stripped

## Latency — full round trip through /analyze_telemetry
| Metric | Value |
|---|---|
| Mean | 0.973s |
| Median | 0.952s |
| Min | 0.906s |
| Max | 1.223s |
| P95 | 1.080s |

## Time to First Token — direct to Ollama, streaming
| Metric | Value |
|---|---|
| Mean | 0.351s |
| Median | 0.353s |
| Min | 0.339s |
| Max | 0.358s |

## System Resource Usage (sampled after each Phase 1 request)
| Metric | Value |
|---|---|
| Avg CPU % | 52.5% |
| Peak CPU % | 65.5% |
| Avg RAM (MB) | 13422 |
| Peak RAM (MB) | 13497 |
| Avg VRAM (MB) | 2478 |
| Peak VRAM (MB) | 2479 |
