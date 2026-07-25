# Project Edge-Node

A fully local, privacy-first workplace behavioral classifier. It labels one day of an
employee's telemetry as **FOCUS**, **NEUTRAL**, or **BURNOUT** using a small language
model (Qwen3 4B-Instruct) served entirely offline through [Ollama](https://ollama.com) —
no data ever leaves the machine it runs on.

The pipeline: synthetic telemetry → Pydantic validation → natural-language translation →
local SLM classification (deterministic, JSON-schema-constrained, with automatic retry) →
served over a FastAPI endpoint → containerized with Docker Compose.

---

## Quickstart (Docker — recommended)

This is the fastest path to a fully working system, and works on any machine with Docker
installed, GPU or not.

```bash
docker compose up --build -d
```

**First run only:** this will also pull the `ollama/ollama` base image (~3.2 GB) and the
`qwen3:4b-instruct` model weights (~2.5 GB) automatically via an init step — expect this
to take a while depending on your internet connection (this is a real bandwidth cost, not
a flaw in the setup). Every run after the first starts in seconds, since both the image and
the model are cached in a persistent Docker volume.

Watch the model pull complete:
```bash
docker compose logs -f ollama-init
```

Once `ollama-init` exits successfully, the API is live at `http://localhost:8000`.

**GPU note:** this setup runs Ollama on CPU by default so it works on any machine
without extra configuration. If you have an NVIDIA GPU with Docker's GPU support
correctly configured (WSL2 backend + NVIDIA Container Toolkit on Windows), GPU
acceleration can be added — see [Notes on GPU acceleration](#notes-on-gpu-acceleration)
below.

To stop everything (keeping the downloaded model cached for next time):
```bash
docker compose down
```

---

## Quickstart (running locally, without Docker)

Useful for development and matches how this project was originally built and tested.

**1. Install [Ollama](https://ollama.com) natively and pull the model:**
```bash
ollama pull qwen3:4b-instruct
ollama serve
```

**2. Set up the Python environment:**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

**3. Start the API:**
```bash
uvicorn app.main:app --reload
```

The API is now live at `http://localhost:8000`.

---

## Generating the mock data

The classifier is tested against a synthetic dataset generated with
[Faker](https://faker.readthedocs.io) and Gaussian-distributed persona sampling, rather
than pure randomness — so the data reflects realistic, distinct behavioral patterns:

- **Healthy / FOCUS persona:** 2–3 meetings, ~45 min gaps, low context switching, no
  after-hours messages.
- **Burnout-risk persona:** 8–10 back-to-back meetings, 2–4 min gaps, late-night
  activity, ~15 after-hours messages.

Generate a fresh dataset:
```bash
python app/data_gen.py
```

This writes a structured JSON file (schema-validated `Meta`/`LableMeta` records, the
latter including a ground-truth label for evaluation) to the `data/` folder.

---

## Hitting the API

The API exposes a single endpoint:

```
POST /analyze_telemetry
```

It accepts one day of telemetry (matching the `Meta` schema — **no label field**, since
producing the label is the whole point of the endpoint) and returns a JSON
classification.

### Interactive docs (easiest)

Open in a browser:
```
http://localhost:8000/docs
```
FastAPI's auto-generated Swagger UI — expand the endpoint, click "Try it out," fill in
the form, and send a real request without writing any code.

### cURL

```bash
curl -X POST http://localhost:8000/analyze_telemetry \
  -H "Content-Type: application/json" \
  --data '{"user_id": "u1", "date": "2026-07-10", "total_meetings": 8, "meeting_hours_per_day": 7.5, "average_gap_between_meetings_minutes": 5.0, "messages_sent_after_8pm": 15, "context_switches_per_hour": 18}'
```

*(On Windows PowerShell, quote-escaping JSON inline can be unreliable — write the body
to a file first and use `--data "@payload.json"` instead.)*

### PowerShell (native)

```powershell
$body = @{
    user_id = "u1"
    date = "2026-07-10"
    total_meetings = 8
    meeting_hours_per_day = 7.5
    average_gap_between_meetings_minutes = 5.0
    messages_sent_after_8pm = 15
    context_switches_per_hour = 18
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/analyze_telemetry" -Method Post -Body $body -ContentType "application/json"
```

### Reading the output

```json
{"classification": "BURNOUT", "score": 0.98}
```

- **`classification`** — one of `FOCUS`, `NEUTRAL`, or `BURNOUT`, determined by a
  calibrated rubric baked into the system prompt (meeting load, gap length, after-hours
  messaging, and context-switching frequency).
- **`score`** — the model's self-reported confidence (0.0–1.0). This is **not** a
  calibrated statistical probability — it's the model's own generated estimate, useful as
  a rough signal for flagging low-confidence rows for human review, not as a rigorous
  metric.

If the model produces malformed or invalid output, the server automatically retries
(up to 3 attempts, feeding the model its own bad output plus a correction) before
returning a `502 Bad Gateway` if it still can't produce a valid result — the pipeline
never crashes on bad model output.

---

## Running the hardware benchmark

```bash
python -m scripts.stress_test
```

This sends 50 real rows from the synthetic dataset through the live `/analyze_telemetry`
endpoint (sequential, matching real single-GPU/CPU capacity), and 10 additional rows
directly to Ollama with streaming enabled to measure Time to First Token. Throughout,
CPU%, RAM, and VRAM (via `pynvml`, if an NVIDIA GPU is present) are sampled after each
request.

Requires the API (and Ollama) to already be running — either via Docker or locally.

Output is written to `benchmark_report.md` at the project root, containing mean/median/
min/max/P95 latency, TTFT, and resource usage tables.

---

## Project structure

```
project-edge-node/
├── app/
│   ├── schema.py         # Pydantic models: Meta (telemetry), LableMeta (+ ground truth)
│   ├── translate.py      # to_text(): telemetry → natural-language prose
│   ├── ollama_script.py  # chat(): prompt → Ollama → validated classification, with retry
│   ├── main.py           # FastAPI app, POST /analyze_telemetry
│   └── data_gen.py        # synthetic dataset generator (Faker + persona sampling)
├── data/
│   └── synthetic_logs.json
├── scripts/
│   └── stress_test.py    # hardware benchmark
├── tests/                 # unit tests (schema validation, translation) — not tracked in git
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── benchmark_report.md
└── README.md
```

---

## Notes on GPU acceleration

By default, the Docker setup runs Ollama on CPU so it works everywhere without extra
configuration. Native (non-Docker) runs will use your GPU automatically if Ollama detects
one correctly.

To enable GPU passthrough inside Docker on Windows, you'll need:
1. Docker Desktop set to the WSL2 backend
2. A working NVIDIA driver + WSL2 GPU support (`nvidia-smi` should work inside a WSL
   terminal)
3. A GPU resource reservation added to the `ollama` service in `docker-compose.yml`

CPU inference is noticeably slower than GPU — see `benchmark_report.md` for measured
numbers on both.

---

## Design notes worth knowing

- **Why prose, not raw JSON, is sent to the model:** small language models are
  instruction-tuned overwhelmingly on natural language, not structured data — converting
  telemetry to a plain factual sentence gets more reliable classification than feeding
  raw JSON.
- **Why `Meta` and `LableMeta` are separate schemas:** `Meta` is what real callers send
  (no label — the endpoint's whole job is producing one). `LableMeta` extends it with a
  ground-truth `label` field, used only in synthetic data generation and evaluation, never
  sent to the model.
- **Why temperature is set to 0.0:** this selects greedy decoding (always the single most
  likely next token), making classification outputs deterministic and reproducible rather
  than creative/varied.
- **A real debugging finding:** early benchmarks showed a consistent ~2 second gap
  between Ollama's own reported inference time and measured end-to-end latency. This was
  traced to `localhost` hostname resolution overhead (likely an IPv6-first lookup that
  had to fall back to IPv4) — switching to the literal `127.0.0.1` address for local
  Ollama calls cut mean latency from ~5.4s to ~1.0s. See `benchmark_report.md` for the
  full before/after numbers.
