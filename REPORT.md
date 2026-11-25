# SMS Guard: Offline Edge-AI Scam & Phishing Triage on Raspberry Pi 4B

**Challenge:** Bharat AI-SoC Challenge 2026–27 — Problem Statement 3 (Edge Security Assistant)  
**Target Hardware:** Raspberry Pi 4 Model B Rev 1.2 (4 GB RAM, Quad-core Arm Cortex-A72, Armv8.0-A)  
**Runtime Stack:** Python 3.13 + ExecuTorch (`release/1.0`) + XNNPACK + Meta Llama 3.2 1B Instruct (Quantized)

---

## 1. Executive Summary & Problem Statement

Everyday mobile users frequently encounter urgent SMS messages containing embedded links or requests for one-time passcodes (OTPs), PINs, or account credentials. Sending raw messages to cloud APIs exposes private communications, incurs per-token cost, and fails during connectivity outages.

**SMS Guard** is a fully offline, privacy-preserving edge security assistant that guides non-expert users from threat detection to safe remediation directly on a 4 GB Raspberry Pi 4B:
- **Zero network dependency:** Full detection and LLM advisory selection execute locally with Wi-Fi disabled and no default internet route.
- **Privacy by design:** Messages are held strictly in volatile memory during evaluation, embedded URLs are parsed purely as text strings (never fetched), and no message history is persisted.
- **Reliable latency & low memory footprint:** A `~15 ms` statistical + rule detector owns the threat decision, while a 4-bit quantized **Llama 3.2 1B Instruct** model (`766 MiB` `.pte`) runs via **ExecuTorch + XNNPACK** within **`1,241 MiB` peak system RAM** (`0 MiB` swap used, leaving `2,553 MiB` free headroom).

---

## 2. System Architecture

SMS Guard implements the five-stage reference pipeline (`Collect → Analyse → Detect → Explain → Recommend`):

```text
┌───────────────────┐     ┌──────────────────────────────────┐     ┌─────────────────────────────┐
│  1. Collect       │────▶│  2. Analyse & 3. Detect          │────▶│  4. Explain (Rule + NB)     │
│  CLI / Stdin SMS  │     │  NFKC + casefold normaliser      │     │  Verdict: review / no sig   │
│  (max 8,000 char) │     │  Tokeniser + URL / cue regexes   │     │  Score + evidence cues[]    │
└───────────────────┘     │  Multinomial Naive Bayes (JSON)  │     │  Baseline safe action       │
                          └──────────────────────────────────┘     └──────────────┬──────────────┘
                                                                                  │
┌───────────────────┐     ┌──────────────────────────────────┐                    ▼
│  JSON Output      │◀────│  Bounded Output Validator        │◀────┌─────────────────────────────┐
│  verdict, cues,   │     │  Regex + option-prefix match     │     │  5. Recommend               │
│  priority_guidance│     │  Fallback: detector guidance     │     │  Llama 3.2 1B Instruct      │
└───────────────────┘     └──────────────────────────────────┘     │  ExecuTorch release/1.0     │
                                                                   │  XNNPACK CPU (--threads=3)  │
                                                                   └─────────────────────────────┘
```

### Architectural Safety Principle
1. **Detector owns the decision:** `sms_guard/detect.py` deterministically computes the `verdict`, `spam_model_score`, `evidence`, and baseline `action` in `~15 ms` with zero external dependencies.
2. **Bounded LLM reasoning:** `sms_guard/adviser.py` passes **only** the detector verdict, evidence strings, and a numbered list of pre-vetted actions/explanations to `llama_main` (`--temperature=0 --max_new_tokens=8`). Raw SMS text is not forwarded to free-form generation, and the LLM cannot fabricate unverified links, commands, or verdicts.
3. **Graceful degradation:** If the model bundle is absent, times out (`180 s`), or emits an invalid option, the original detector guidance remains intact and the CLI signals failure (`exit 1` or `exit 2`).

---

## 3. Methodology

### 3.1 Stage 1 — Deterministic Text Normalisation, Rule Cues, and Multinomial Naive Bayes

Implemented in `sms_guard/detect.py` and trained via `scripts/train.py`:
- **Dataset & Deduplication:** Evaluated on the UCI SMS Spam Collection (Almeida & Hidalgo; SHA-256 verified: `1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3`). Messages are Unicode NFKC-normalised, case-folded, and whitespace-collapsed; conflicting duplicates are excluded before splitting.
- **Stratified Split:** Deterministic 80/20 stratified split (`random.Random(42)`), yielding **3,614 ham** and **514 spam** training messages and **1,031 held-out test messages**.
- **Feature Engineering & Model:**
  - Alphanumeric tokens (`[a-z]+|\d+`) with per-message term frequency clipped at `3` (`min(3, count)`).
  - Vocabulary pruning discards tokens occurring fewer than `2` times in the training split.
  - Multinomial Naive Bayes log-likelihood ratios with Laplace add-one smoothing, serialized to compact JSON (`sms_guard/model.json`, `54 KiB`).
- **Hybrid Policy & Evidence Generation:**
  - `Contains a web link.` — detects `http(s)://` or `www.` URLs without resolving or fetching them.
  - `A shortened link hides its destination.` — flags URL shorteners (`bit.ly`, `t.co`, `tinyurl.com`).
  - `Uses urgency or account restrictions.` — matches coercion phrases (`urgent`, `immediately`, `locked`, `suspended`, `expires today`, `verify now`).
  - `Appears to request a secret or payment detail.` — matches credential/payment solicitation (`share|send|enter|confirm|provide` near `otp|pin|password|card details`) while suppressing false positives on safety warnings (`never share ...`).
  - **Review trigger:** `p >= 0.5` OR secret solicitation OR (`urgent` AND `links`).

### 3.2 Stage 2 — On-Device Advisory with Llama 3.2 1B Instruct & ExecuTorch

Implemented in `sms_guard/adviser.py`:
- Constructs a Llama 3.2 Instruct chat-template prompt containing the detector verdict, combined evidence, and numbered options (`1..N`, mapping each evidence cue to a plain-language explanation plus the detector's baseline `action`).
- Invokes the native C++ ExecuTorch `llama_main` runner with deterministic greedy decoding (`--temperature=0`), bounded generation (`--max_new_tokens=8`), and `--cpu_threads=3`.
- Strips `PyTorchObserver {...}` JSON telemetry printed to `stdout` by ExecuTorch `release/1.0` and validates that the selection begins with a valid option index `1..N` (and if the model echoes trailing words up to the token limit, verifies they match a prefix of the selected option text).

---

## 4. Optimization Techniques

### 4.1 Model-Level & Algorithmic Optimizations
- **Term-frequency clipping & vocabulary pruning:** Clipping per-SMS token counts at `3` prevents repetition stuffing, while dropping tokens with frequency `< 2` shrinks the detector payload to `54 KiB` (`sms_guard/model.json`) with zero runtime dependencies (Python standard library only).
- **Bounded-choice LLM formulation:** Instead of generating multi-sentence explanations (which requires 40–100+ decoded tokens at slow Arm CPU decode speeds), framing the LLM task as **option prioritization** reduces generation to **1–7 tokens**, cutting inference time dramatically while eliminating hallucination risk.

### 4.2 Quantization & ExecuTorch Graph Lowering
Exported from `meta-llama/Llama-3.2-1B-Instruct` (`consolidated.00.pth`, `2.47 GB` BF16) using ExecuTorch `1.0.1` (`torch==2.9.1+cpu`, `torchao==0.14.0+cpu`):
- **Weights & Activations (`qmode=8da4w`):** 4-bit groupwise weight quantization (`group_size=128`) paired with 8-bit dynamic per-token activation quantization.
- **Embedding Quantization (`4,32`):** 4-bit groupwise quantization (`group_size=32`) on Llama 3.2's `128,256 × 2,048` embedding table, reclaiming ~350+ MiB of RAM.
- **Attention & Memory Optimizations:** Enabled `use_kv_cache=True`, `use_sdpa_with_kv_cache=True`, and `enable_dynamic_shape=True` (`max_seq_length=512`, `max_context_length=512`).
- **XNNPACK Backend Delegation:** Lowered via `XnnpackDynamicallyQuantizedPartitioner` + `XnnpackPartitioner` (`extended_ops=True`), reducing the exported flatbuffer (`adviser.pte`) from `2.47 GB` to **`766 MiB`** with only **`88,211,520` bytes (~84.1 MiB)** of planned activation buffer memory.

### 4.3 Systems, OS, and Compiler Optimizations for Raspberry Pi 4B
- **Headless 64-bit OS Footprint:** Deployed on **Raspberry Pi OS Lite (64-bit, Debian 13 `trixie`)** without a desktop/display server, yielding **`3.5 GiB` available RAM** (`~182 MiB` idle OS footprint) out of `3,795 MiB` total.
- **Cortex-A72 ISA Compatibility Fix:** Cross-compiled ExecuTorch `release/1.0` (`commit 7b220c6f4ecc0a8b504a9c516e5643a2cf2d4376`) in `debian:trixie` (`aarch64-linux-gnu-g++ 14.2.0`) with `-mcpu=cortex-a72`, `--preset llm`, and `-DSUPPORT_REGEX_LOOKAHEAD=ON`. During binary disassembly (`objdump`), ExecuTorch's `extension/llm/custom_ops/CMakeLists.txt` was found to export `-march=armv8.2-a+dotprod` as `PUBLIC`, emitting Armv8.2-only `sdot` instructions into `llama_main`. Scoping that option `PRIVATE` on `custom_ops` kept `llama_main` and `libllama_runner.so` clean of unconditional Armv8.2 instructions, preventing `SIGILL` crashes on the Armv8.0-A Cortex-A72.
- **Thread Allocation (`--cpu_threads=3`):** Reserves 1 of the 4 Cortex-A72 cores for Python, OS interrupts, and SSH/management responsiveness while dedicating 3 threads to XNNPACK matrix kernels.

---

## 5. Experimental Setup & Reproducibility

| Artifact / Environment Field | Verified Value |
| --- | --- |
| **Target Board** | Raspberry Pi 4 Model B Rev 1.2 (4 GB LPDDR4, Cortex-A72) |
| **OS & Kernel** | Debian GNU/Linux 13 (`trixie`, `aarch64`), `Linux 6.18.50+rpt-rpi-v8` |
| **Python Runtime** | Python 3.13.5 |
| **ExecuTorch Source Commit** | `7b220c6f4ecc0a8b504a9c516e5643a2cf2d4376` (`release/1.0`) |
| **Exporter Packages** | `executorch==1.0.1`, `torch==2.9.1+cpu`, `torchao==0.14.0+cpu` |
| **`adviser.pte` SHA-256** | `b0e6aee04ab3c086ac514efce92d9d9f1174de66d395ae851b584fb9bedf7dbb` |
| **`tokenizer.model` SHA-256** | `82e9d31979e92ab929cd544440f129d9ecd797b69e327f80f17e1c50d5551b55` |
| **`llama_main` SHA-256** | `af7f4a9de689b3578093699da77290fddd197780d22e438c6ae595969cee07d2` |
| **`libllama_runner.so` SHA-256** | `eb1c1175a36f83063928b58a22a8f34fe94eb8e61fce4449068f14adc36be2f4` |

### Offline Isolation Verification (`results/pi4-offline-check.log`)
Before running benchmarks, the Pi's Wi-Fi radio was switched off (`nmcli radio wifi off`, `wlan0 DOWN`) and the default route was deleted (`ip route` restricted to `10.42.0.0/24` LAN SSH). `ping -c 1 -W 2 1.1.1.1` returned `ping: connect: Network is unreachable`, confirming fully air-gapped external operation during inference.

---

## 6. Results & Hardware Utilization

### 6.1 Detection Quality (Held-Out UCI SMS Corpus, `N = 1,031`)

| Metric | Value | Notes |
| --- | --- | --- |
| Training Split | 3,614 ham, 514 spam | Stratified 80%, deduplicated |
| Held-Out Confusion Matrix | `120 TP`, `897 TN`, `6 FP`, `8 FN` | Full hybrid policy (Naive Bayes + rules) |
| **Precision** | **95.24%** | `120 / (120 + 6)` |
| **Recall** | **93.75%** | `120 / (120 + 8)` |
| **False-Positive Rate** | **0.66%** | `6 / (6 + 897)` |

### 6.2 On-Device Latency & Throughput (Raspberry Pi 4B, Offline, `3 × 2` Runs)

Measured via `scripts/benchmark.sh` with `/usr/bin/time` (each run launches a cold Python + `llama_main` subprocess, including model load from disk):

| Configuration | Sample Input | Verdict | Detector (ms) | Adviser (ms) | Wall Time (s) | CPU Util | Peak Process RSS | Exit |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Detector Only** | Routine SMS | `no strong signal` | 15.02–15.12 | — | 0.21–0.22 | 99–100% | 16,148–16,156 KiB (~15.8 MiB) | `0` |
| **Detector Only** | Suspicious SMS | `review` | 15.07–15.22 | — | 0.21–0.22 | 99% | 16,148–16,160 KiB (~15.8 MiB) | `0` |
| **Detector + Llama 3.2 1B** | Routine SMS | `no strong signal` | 14.90–15.05 | 19,390–19,397 | 19.61 | 162–163% | 1,024,832–1,024,844 KiB (~1,001 MiB) | `0` |
| **Detector + Llama 3.2 1B** | Suspicious SMS | `review` | 14.93–15.37 | 25,076–25,171 | 25.29–25.39 | 194% | 1,024,756–1,025,048 KiB (~1,001 MiB) | `0` |

**Subprocess Phase Breakdown (observed via ExecuTorch `PyTorchObserver` on suspicious SMS, `136` prompt tokens):**
- Model load & memory map (`model_load`): `~11.96 s` (`11,956 ms`)
- Prompt prefill (`prompt_eval`): `~12.01 s` (`12,015 ms`, ~`11.3 tokens/s` prefill on Cortex-A72)
- Output decode (`1` token: `1<|eot_id|>`): `~0.19 s` (`187 ms`)
- Python subprocess + startup overhead: `~0.95 s`

### 6.3 System Memory, Swap, and CPU Utilization (`results/pi4-adviser-mem.log`)

Sampled every 1 second (`133` samples) across the complete 6-run Llama benchmark suite on the 4 GB Pi 4B:

| Resource Metric | Measured Value | Interpretation |
| --- | --- | --- |
| Total System RAM | `3,795 MiB` | Physical RAM available to Linux kernel |
| **Peak System RAM Used** | **`1,241 MiB`** | `32.7%` peak memory utilization (including OS + Python + Llama 3.2 1B) |
| **Minimum Available RAM** | **`2,553 MiB`** | Over `2.49 GiB` free headroom maintained continuously |
| **Peak Swap Used** | **`0 MiB`** (`2,047 MiB` total) | Zero swap thrashing; model stays fully resident in RAM |
| Multi-Core CPU Load | `162% – 194%` | Effective utilization of `--cpu_threads=3` across cold load + XNNPACK prefill |

### 6.4 Qualitative Verification on Target Samples

- **Routine SMS (`Meet you at the library after lunch.`):**  
  Verdict: `no strong signal` (`score=2e-05`), Evidence: `[]`, Priority Guidance: `"If the request is unexpected, verify it independently."`
- **Suspicious SMS (`Account locked. Verify now at https://account.example.invalid`):**  
  Verdict: `review` (`score=0.81124`), Evidence: `["Contains a web link.", "Uses urgency or account restrictions.", "Wording resembles messages labelled as spam in the training set."]`, Priority Guidance: `"A link in a message can lead somewhere unexpected. Open the service's app yourself to check."`

---

## 7. Limitations, Safeguards, and Future Work

1. **Cold-start latency (`~12 s` model load):** Because the CLI currently invokes `llama_main` as a fresh subprocess per SMS, nearly half of the `25.1 s` latency is process/model initialization. Keeping a persistent local daemon or UNIX socket worker would cut per-message advisory latency to `~12 s` on Pi 4B.
2. **Corpus generalization:** The Naive Bayes classifier was trained on the historical English UCI SMS Spam Collection. While rule cues catch generic urgency, links, shorteners, and OTP/PIN requests, modern regional phishing (e.g., Indian UPI/KYC scams and multilingual/transliterated messages) requires localized fine-tuning data.
3. **Architecture extensibility:** The `Collect → Analyse → Detect → Explain → Recommend` pipeline already separates feature extraction from advisory reasoning, enabling direct future plug-ins for standalone phishing-URL reputation/lexical classifiers and local network-flow anomaly detectors (and optional Hailo NPU offloading on Pi 5 + AI HAT+).
4. **Usability evaluation:** *(Record your first-time user observation outcome here if completed prior to final PDF export.)*
