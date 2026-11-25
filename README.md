# SMS Guard — Offline Edge AI Scam & Phishing Triage (Bharat AI-SoC PS3)

**SMS Guard** is a privacy-preserving, completely offline SMS triage assistant built for the **Bharat AI-SoC Challenge (Problem Statement 3)** on **Raspberry Pi 4B (4 GB, Arm Cortex-A72, 64-bit Linux)**.

Given an English SMS, it runs a two-stage local pipeline:
1. **Stage 1 — Fast Deterministic Detector (`~15 ms`):** Normalises text, extracts lexical/URL/urgency/secret cues, and evaluates a multinomial Naive Bayes classifier (`sms_guard/detect.py`, `sms_guard/model.json`).
2. **Stage 2 — Bounded Local LLM Adviser (`~19–25 s`):** Passes only the detector verdict, evidence, and pre-vetted guidance options to **Llama 3.2 1B Instruct** quantized for **ExecuTorch `release/1.0` + XNNPACK** (`sms_guard/adviser.py`), selecting the highest-priority user action without external network access.

Inputs are processed strictly in memory, URLs are treated as plain text (never fetched), and no message history is stored.

---

## Architecture

```text
SMS Input ──▶ Normalise & Tokenise ──▶ Naive Bayes + Rules ──▶ Structured Evidence
                                                                       │
User Action ◀── Bounded Selection Validation ◀── Llama 3.2 1B (ExecuTorch XNNPACK)
```

The detector owns the threat classification (`review` vs. `no strong signal`) and supporting indicators; the local LLM never invents arbitrary advice or overrides the detector verdict.

---

## Verified Raspberry Pi 4B (4 GB) Performance

Measured completely offline (`wlan0 DOWN`, no default route) on **Raspberry Pi 4 Model B Rev 1.2**, **Debian GNU/Linux 13 (`trixie`, `aarch64`)**, **Python 3.13.5**, **ExecuTorch `release/1.0`** (`7b220c6f4ecc0a8b504a9c516e5643a2cf2d4376`). See [REPORT.md](REPORT.md) and [results/](results/) for full logs and SHA-256 checksums.

| Mode | Sample | Verdict | Detector (ms) | Adviser (ms) | Wall Time (s) | Peak RSS (MiB) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Detector only | Routine SMS | `no strong signal` | 15.02–15.12 | — | 0.21–0.22 | 15.8 |
| Detector only | Suspicious SMS | `review` | 15.07–15.22 | — | 0.21–0.22 | 15.8 |
| Detector + Llama 3.2 1B | Routine SMS | `no strong signal` | 14.90–15.05 | 19,390–19,397 | 19.61 | ~1,001 |
| Detector + Llama 3.2 1B | Suspicious SMS | `review` | 14.93–15.37 | 25,076–25,171 | 25.29–25.39 | ~1,001 |

- **System RAM headroom across 6 runs (133 samples):** Peak `1,241 MiB / 3,795 MiB` used, minimum `2,553 MiB` available, **`0 MiB` swap used**.
- **Held-out classification baseline (`1,031` UCI SMS messages):** Precision `95.24%`, Recall `93.75%`, False-Positive Rate `0.66%` (`120 TP, 897 TN, 6 FP, 8 FN`).

---

## Repository Layout

| Path | Purpose |
| --- | --- |
| `sms_guard/__main__.py` | CLI entry point (interactive/piped input, JSON output, timing, exit status) |
| `sms_guard/detect.py` | Text normalisation, rule cues, and Naive Bayes scoring |
| `sms_guard/model.json` | Bundled Naive Bayes vocabulary weights and prior bias |
| `sms_guard/adviser.py` | Bounded Llama 3.2 1B prompt builder, ExecuTorch subprocess runner, and output validator |
| `scripts/setup_pi.sh` | Step-by-step Raspberry Pi 4B setup and smoke test |
| `scripts/demo.sh` | End-to-end offline demo script for Raspberry Pi 4B |
| `scripts/benchmark.sh` | Repeatable 3×2 benchmark harness using `/usr/bin/time` |
| `scripts/train.py` | Reproducible training & evaluation script against UCI SMS Spam Collection |
| `dist/` | Zero-dependency installable Python wheel (`sms_guard_ps3-0.1.0-py3-none-any.whl`) |
| `results/` | Raw Raspberry Pi 4B offline logs (`pi4-detector.log`, `pi4-adviser.log`, `pi4-adviser-mem.log`, `pi4-offline-check.log`) |
| `REPORT.md` | Full engineering report (methodology, optimization, hardware utilization, results) |

---

## Quick Start on Raspberry Pi 4B (64-bit)

### 1. Run Setup & Detector Baseline

```sh
./scripts/setup_pi.sh
```

Or run directly from source (zero third-party runtime dependencies, Python >= 3.9):

```sh
echo 'Meet you at the library after lunch.' | python3 -m sms_guard
echo 'Account locked. Verify now at https://account.example.invalid' | python3 -m sms_guard
```

Or install the offline wheel in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --no-index --no-deps dist/sms_guard_ps3-0.1.0-py3-none-any.whl
echo 'Account locked. Verify now at https://account.example.invalid' | .venv/bin/sms-guard
```

### 2. Enable Local Llama 3.2 1B Advice (ExecuTorch + XNNPACK)

Due to Meta Llama licensing and binary size, weights and compiled binaries are staged outside Git under `./llama-bundle/`:
- `llama_main` and `libllama_runner.so`: Cross-compiled from ExecuTorch `release/1.0` targeting Arm Cortex-A72 (`-mcpu=cortex-a72`, `--preset llm`, `XNNPACK` + `KleidiAI`).
- `adviser.pte`: Exported from `meta-llama/Llama-3.2-1B-Instruct` (`qmode=8da4w`, `group_size=128`, `embedding_quantize=4,32`, `use_kv_cache=True`, `use_sdpa_with_kv_cache=True`, `max_seq_length=512`, `XNNPACK`).
- `tokenizer.model`: Original Llama 3.2 tokenizer.

Run with the local bundle:

```sh
bundle="$PWD/llama-bundle"
export LD_LIBRARY_PATH="$bundle${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python3 -m sms_guard \
  --runner "$bundle/llama_main" \
  --model "$bundle/adviser.pte" \
  --tokenizer "$bundle/tokenizer.model"
```

### 3. Reproduce Benchmarks & Training

```sh
# Offline benchmark (detector + adviser)
mkdir -p results
scripts/benchmark.sh > results/pi4-detector.log 2>&1
scripts/benchmark.sh \
  --runner "$bundle/llama_main" \
  --model "$bundle/adviser.pte" \
  --tokenizer "$bundle/tokenizer.model" > results/pi4-adviser.log 2>&1

# Rebuild detector weights from UCI SMS Spam Collection
curl -fLsS https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip -o /tmp/sms-collection.zip
python3 scripts/train.py /tmp/sms-collection.zip
```
