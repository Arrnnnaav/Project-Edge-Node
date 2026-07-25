import json
import time
from pathlib import Path
from statistics import mean, median

import psutil
import requests

from app.schema import Meta
from app.translate import to_text
from app.ollama_script import SYSTEM_PROMPT, url as OLLAMA_URL

try:
    import pynvml
    pynvml.nvmlInit()
    _GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
    GPU_AVAILABLE = True
except Exception:
    GPU_AVAILABLE = False
    _GPU_HANDLE = None


API_URL = "http://127.0.0.1:8000/analyze_telemetry"
MODEL = "qwen3:4b-instruct"  
DATA_PATH = Path("data/synthetic_logs.json")

NUM_LATENCY_REQUESTS = 50
NUM_TTFT_REQUESTS = 10


def load_rows(start: int, count: int) -> list[Meta]:
    all_rows = json.loads(DATA_PATH.read_text())
    slice_ = all_rows[start:start + count]

    rows = []
    for row in slice_:
        row = dict(row)
        row.pop("label", None)
        rows.append(Meta(**row))
    return rows


def measure_latency(log: Meta) -> float:
    payload = json.loads(log.model_dump_json())
    start = time.perf_counter()
    response = requests.post(API_URL, json=payload)
    response.raise_for_status()
    return time.perf_counter() - start


def measure_ttft(log: Meta) -> float:
    prompt = to_text(log)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "options": {"temperature": 0.0},
    }

    start = time.perf_counter()
    first_token_time = None

    with requests.post(OLLAMA_URL, json=payload, stream=True) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            content_piece = chunk.get("message", {}).get("content", "")

            if first_token_time is None and content_piece:
                first_token_time = time.perf_counter() - start

            if chunk.get("done"):
                break

    return first_token_time if first_token_time is not None else time.perf_counter() - start


def percentile(data: list[float], pct: float) -> float:
    data = sorted(data)
    k = int(round((pct / 100) * (len(data) - 1)))
    return data[k]


def main():
    print(f"GPU monitoring: {'enabled' if GPU_AVAILABLE else 'unavailable'}\n")

    latency_rows = load_rows(start=0, count=NUM_LATENCY_REQUESTS)
    ttft_rows = load_rows(start=NUM_LATENCY_REQUESTS, count=NUM_TTFT_REQUESTS)
    print(f"Loaded {len(latency_rows)} rows for latency, {len(ttft_rows)} rows for TTFT\n")

    psutil.cpu_percent(interval=None)  # prime the baseline reading, discard it

    print(f"Phase 1: {len(latency_rows)} sequential requests to {API_URL}")
    latencies, cpu_samples, ram_samples, vram_samples, failures = [], [], [], [], 0

    for i, log in enumerate(latency_rows):
        try:
            latency = measure_latency(log)
            latencies.append(latency)

            cpu_samples.append(psutil.cpu_percent(interval=None))
            ram_samples.append(psutil.virtual_memory().used / (1024 ** 2))
            if GPU_AVAILABLE:
                mem = pynvml.nvmlDeviceGetMemoryInfo(_GPU_HANDLE)
                vram_samples.append(mem.used / (1024 ** 2))

            print(f"  [{i + 1}/{len(latency_rows)}] {latency:.3f}s")
        except Exception as e:
            failures += 1
            print(f"  [{i + 1}/{len(latency_rows)}] FAILED: {e}")

    print(f"\nPhase 2: {len(ttft_rows)} streaming requests direct to Ollama (TTFT)")
    ttfts = []
    for i, log in enumerate(ttft_rows):
        try:
            ttft = measure_ttft(log)
            ttfts.append(ttft)
            print(f"  [{i + 1}/{len(ttft_rows)}] {ttft:.3f}s")
        except Exception as e:
            print(f"  [{i + 1}/{len(ttft_rows)}] FAILED: {e}")

    if not latencies or not ttfts:
        print("\nNot enough successful samples to build a report.")
        return

    report = f"""# Project Edge-Node — Hardware Benchmark Report

**Model:** {MODEL} | **Latency requests:** {len(latency_rows)} (failed: {failures}) | **TTFT requests:** {len(ttft_rows)}
**Data source:** real rows from {DATA_PATH}, labels stripped

## Latency — full round trip through /analyze_telemetry
| Metric | Value |
|---|---|
| Mean | {mean(latencies):.3f}s |
| Median | {median(latencies):.3f}s |
| Min | {min(latencies):.3f}s |
| Max | {max(latencies):.3f}s |
| P95 | {percentile(latencies, 95):.3f}s |

## Time to First Token — direct to Ollama, streaming
| Metric | Value |
|---|---|
| Mean | {mean(ttfts):.3f}s |
| Median | {median(ttfts):.3f}s |
| Min | {min(ttfts):.3f}s |
| Max | {max(ttfts):.3f}s |

## System Resource Usage (sampled after each Phase 1 request)
| Metric | Value |
|---|---|
| Avg CPU % | {mean(cpu_samples):.1f}% |
| Peak CPU % | {max(cpu_samples):.1f}% |
| Avg RAM (MB) | {mean(ram_samples):.0f} |
| Peak RAM (MB) | {max(ram_samples):.0f} |
"""

    if vram_samples:
        report += f"""| Avg VRAM (MB) | {mean(vram_samples):.0f} |
| Peak VRAM (MB) | {max(vram_samples):.0f} |
"""
    else:
        report += "| VRAM | unavailable |\n"

    with open("benchmark_report.md", "w") as f:
        f.write(report)

    print("\nReport written to benchmark_report.md")


if __name__ == "__main__":
    main()