# Raspberry Pi agent handoff — SMS Guard for Bharat AI-SoC PS3

Paste an English SMS to get a review decision, the cues behind it, and an action you can take. The program runs locally. It treats URLs as text, never visits them, and keeps no message history.

## Brief report and Pi handoff

| Component | Status on 20 November 2026 |
| --- | --- |
| SMS detector | Working on the x86-64 development host. On 1,031 held-out English SMS messages, it flagged 120 of 128 spam messages and 6 of 903 ordinary messages. |
| Raspberry Pi 4B, 4 GB | Deployment target. The first board task is to run the two examples below with the bundled detector. Training is already complete. |
| Llama advisory | Adapter implemented. The local model, tokenizer and native ExecuTorch runner must be supplied. Inference speed, memory use and advice quality on this board remain unmeasured. |

For code changes, start with [detect.py](sms_guard/detect.py) for scoring and evidence, [adviser.py](sms_guard/adviser.py) for Llama selection, and [the CLI](sms_guard/__main__.py) for input, timing and failure reporting. The slide notes below preserve the mentoring guidance from the supplied document.

## What the nine PS3 mentoring slides expect

These notes capture the content of the slides supplied in November 2026. They describe the challenge expectations. The implementation status and measurements elsewhere in this file describe what SMS Guard has achieved.

### 1. Problem and goal

Build one security assistant that guides a person from detection to action. The slides describe five capabilities:

- **Network anomaly detection.** Monitor and classify traffic patterns to flag unusual behaviour and possible intrusions.
- **Phishing URL detection.** Assess suspicious domains, redirects and known malicious patterns.
- **Scam message detection.** Identify suspicious SMS or other communications using language and contextual signals.
- **Plain-language explanations.** Tell the user what triggered the alert, why it matters and how confident the system is.
- **Remediation guidance.** Give a practical next step appropriate to the evidence, such as independent verification, blocking, reporting or disconnecting.

### 2. Why edge AI

Keeping sensitive messages and network metadata on the device supports privacy. Detection can happen close to the event, core checks can continue through an internet outage, and local processing makes operating costs and availability more predictable. Demonstrate these properties by running the full detection and advice flow with internet access disabled.

### 3. Reference architecture

| Stage | What it does |
| --- | --- |
| Collect | Accept an SMS, URL or network flow. |
| Analyse | Clean and normalise text or metadata, parse the input and extract features. |
| Detect | Apply a classifier, anomaly model or rules combined with machine learning. Produce a label, score and supporting indicators. |
| Explain | Combine relevant signals, apply a decision threshold and pass structured evidence to the advisory component. |
| Recommend | Use Llama through ExecuTorch for a short, bounded explanation and practical action based on that evidence. |

The detector owns the threat decision. Keeping its evidence available lets the user inspect why an alert appeared, even if the adviser fails.

### 4. Required technology

A small text, URL or network-flow detector may run on the CPU or a compatible accelerator. A **Llama-family model running on-device through ExecuTorch** must provide advisory or reasoning support. Measure inference latency, memory consumption and reliability. Hailo is optional. If used, document which supported workloads run on its NPU through HailoRT and which run on the Arm CPU through ExecuTorch. The proposed Pi 4B design uses the CPU for both detection and advice.

### 5. Choose a focused use case

| Primary scenario | Input and model | Expected output |
| --- | --- | --- |
| Scam SMS | Message text and a spam/scam classifier | Risk assessment and highlighted cues. The mentors identify this as a good choice for a quick end-to-end demo. |
| Phishing URL | URL string and features, with a URL classifier or reputation feed | Suspicious indicators and a safe next action. |
| Network anomaly | Flow or packet metadata and an anomaly or intrusion classifier | An alert with the key signals behind it. |

The mentors recommend **one primary scenario** with an architecture that can accept other input types later. SMS Guard takes the SMS route and uses embedded links as additional evidence.

### 6. Example user journey

A message claims an account is locked and demands immediate verification. Combine available cues such as urgency, a link and sender information. Explain in ordinary language why those cues matter, then recommend keeping credentials private and verifying the claim independently through a known channel. Let the user decide whether to report or dismiss the alert. The slides suggest local feedback as a later learning step. SMS Guard currently accepts pasted text and offers advice. Sender metadata, reporting, dismissal tracking and feedback collection are outside the current implementation.

The slides explicitly caution against opening links automatically, deleting messages automatically or claiming certainty from the LLM alone.

### 7. Evaluation and milestones

| Evaluation area | Evidence to collect |
| --- | --- |
| Detection quality | Precision, recall, false-positive rate and detection latency for each threat type evaluated. |
| On-device performance | Inference time, memory use, CPU or accelerator load, and operation without internet access. |
| User effectiveness | Can a user explain the risk, understand the advice and complete a safe action? Record the observed outcome. |

The suggested sequence is to (1) build the data pipeline and baseline detectors, (2) integrate local inference and risk scoring, (3) add explanations and remediation, and (4) test robustness, privacy and usability on the target hardware.

### 8. Target hardware and measurements

The slides illustrate an Arm Android smartphone with local inference, a CPU-only Raspberry Pi 5 as a latency and RAM baseline, a Pi 5 with AI HAT+ for compatible accelerated workloads, and an Arm Linux appliance with a service or UI. The team's Pi 4B with 4 GB RAM uses the Arm Linux route. Measure on that physical board. Record device and OS, model identity and quantization, ExecuTorch version, latency, memory and the offline test result. Identify any accelerator separately so the hardware used for each measurement is clear.

### 9. Deliverables, deadlines and contacts

- **Source code.** Prepare a functional GitHub repository with step-by-step setup scripts.
- **On-device application.** Supply an installable or executable artifact. The slides give an Android APK or a Linux wheel or binary as examples.
- **Demonstration video.** Record an end-to-end technical walkthrough on the target, showing a threat cue triggering detection, the supporting evidence, the explanation and the recommended action.
- **Engineering report.** Document hardware mapping, quantization settings and measured performance indicators.
- **Milestones.** The slides give 23 November 2026 for Open Qualifying and 5 February 2027 for PoC Development for shortlisted teams.
- **Official channels.** The slides list `support@armbharatchallenge.com` for mentor and expert queries. The official page also lists `tech-queries@armbharatchallenge.com` for technical questions and asks teams to put the problem statement number in the subject. Use the challenge hub for updates, Q&A and submission guidance. [Bharat AI-SoC Challenge 2026–27](https://arm-education.github.io/Arm-Developer-Labs/Bharat_AI_SoC_2026_27.html)

## Files to transfer

Copy this project directory to the Pi. Run shell examples from its root. The detector works directly from source. Copy the complete folder if you also want the benchmark, training script and packaging configuration.

| Path | Role |
| --- | --- |
| `sms_guard/__main__.py` | Interactive and piped input, JSON output, timing and exit status |
| `sms_guard/detect.py`, `sms_guard/model.json` | Evidence rules and bundled trained token weights |
| `sms_guard/adviser.py` | ExecuTorch subprocess, prompt construction and output validation |
| `scripts/train.py` | Rebuilds weights and evaluates the full review policy |
| `scripts/benchmark.sh` | Runs two examples three times each and records Linux process measurements |
| `pyproject.toml`, `dist/*.whl` | Packaging configuration and installable detector |

## Run the detector

From the project directory on a computer or a Raspberry Pi running 64-bit Raspberry Pi OS with Python 3.9 or later:

```sh
python3 -m sms_guard
```

Paste one message and press Enter. For a repeatable demo, try both inputs:

```sh
echo 'Meet you at the library after lunch.' | python3 -m sms_guard
echo 'Account locked. Verify now at https://account.example.invalid' | python3 -m sms_guard
```

Expected verdicts in order are `no strong signal` and `review`. The second result should list both the web link and urgency as evidence. Both runs should report `detector guidance only`.

Alternatively, copy the wheel in `dist/` to the Pi. In a Python virtual environment, run `python -m pip install --no-index sms_guard_ps3-0.1.0-py3-none-any.whl`, then `sms-guard`. The trained detector is included. The wheel has no third-party Python runtime dependencies.

## Add Llama advice on the Pi

The proposed target is the 4 GB Pi 4B CPU with 64-bit Linux. The challenge allows Arm Linux devices. The mentor slides recommend selecting one scenario, generating structured detector evidence and using Llama for bounded advice. SMS is the primary scenario here. URL features apply to links in messages. Standalone phishing-site classification and network-flow monitoring are future extensions. [Challenge brief](https://arm-education.github.io/Arm-Developer-Labs/Bharat_AI_SoC_2026_27.html)

1. Prepare the licensed Llama 3.2 1B Instruct checkpoint and matching original tokenizer on a development machine. Use a matching ExecuTorch release/1.0 exporter and Linux runner. Target XNNPACK CPU with 8-bit dynamic activations, 4-bit weights and quantized embeddings. Arm provides a 1B export recipe. [Model preparation](https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/build-llama3-chat-android-app-using-executorch-and-xnnpack/4-prepare-llama-models/)
2. Build the Linux AArch64 `llama_main` and its shared libraries for the Pi 4 Cortex-A72. Use a generic Armv8-A or Cortex-A72 build target. Arm's Pi 5 instructions describe the toolchain and bundle layout. The combination of this 1B export and Pi 4 build still needs validation on the board. [ExecuTorch setup](https://learn.arm.com/learning-paths/embedded-and-microcontrollers/rpi-llama3/executorch/) · [Linux runner deployment](https://learn.arm.com/learning-paths/embedded-and-microcontrollers/rpi-llama3/run/)
3. Copy the runner, libraries, exported model and tokenizer into a local directory on the Pi. With the following layout, run:

```sh
bundle="$PWD/llama-bundle"
export LD_LIBRARY_PATH="$bundle${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python3 -m sms_guard --runner "$bundle/llama_main" --model "$bundle/adviser.pte" --tokenizer "$bundle/tokenizer.model"
```

The runner receives detector evidence and a numbered list of applicable explanations and actions. Llama prioritises one for the user. Only a valid selection is shown. Timeout, runtime or parsing failures leave the original detector guidance visible and return a failing exit status. The detector-only mode and successful local inference have distinct output labels. No Llama weights or native runner are bundled.

### Runner behaviour and diagnosis

The CLI accepts up to 8,000 characters. Only the verdict, evidence and available guidance enter the Llama prompt. Each message starts a fresh runner process with three CPU threads, temperature zero, an eight-token output limit and a 180-second timeout. Measured adviser latency includes process startup and model loading.

| Observation | Meaning and next check |
| --- | --- |
| Exit 0, `detector guidance only` | Detector succeeded. Pass all three asset flags to exercise the adviser. |
| Exit 0, `local Llama / ExecuTorch` | The runner returned a valid choice. Inspect `priority_guidance` for relevance. |
| Exit 1, `unavailable` | Detector completed. Check executable permissions, architecture, shared libraries, model/tokenizer pairing and available RAM. A timeout or an invalid option also produces this status. |
| Exit 2 | Check input length, empty input and incomplete asset flags. |

Useful board checks before running the adviser:

```sh
uname -m
getconf LONG_BIT
free -h
df -h .
file "$bundle/llama_main"
ldd "$bundle/llama_main"
sha256sum "$bundle/adviser.pte" "$bundle/tokenizer.model" "$bundle/llama_main"
```

Expect AArch64 Linux, a 64-bit userspace and resolved runner libraries. Record the hashes alongside the exporter commit, build options and quantization settings so another team member can reproduce the run.

## Engineering baseline

The classifier is a multinomial Naive Bayes model. Training clips repeated token counts at three, discards training tokens seen fewer than twice, and applies add-one smoothing. The review policy triggers at a spam model score of 0.5, an apparent request for a secret, or an urgent message containing a link. The score describes the text model alone and has no fraud-probability calibration. A short URL contributes an explanation. A routine message can contain any of these cues.

The experiment uses a deterministic, stratified 80/20 split after normalising and grouping identical text and excluding conflicting groups. The vocabulary comes from the training partition. Reproduce from the project root:

```sh
curl -fLsS https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip -o /tmp/sms-collection.zip
python3 scripts/train.py /tmp/sms-collection.zip
```

The script checks the archive digest and rebuilds the bundled model. Training used 3,614 ham and 514 spam messages. On 1,031 held-out messages the full review policy produced 120 true positives, 897 true negatives, 6 false positives and 8 false negatives. Precision was 95.24%, recall 93.75%, and the false-positive rate 0.66%. Related message templates can occur across partitions. This historical English spam corpus leaves present-day phishing, Indian payment scams and multilingual messages unvalidated. Data credit: Almeida and Hidalgo, SMS Spam Collection, UCI Machine Learning Repository. [Dataset and licensing](https://archive.ics.uci.edu/dataset/228/sms%2Bspam%2Bcollection)

## Target evidence and demo

On the Pi, disconnect from the internet and run `scripts/benchmark.sh` from the project root. Repeat with the three adviser flags above. GNU time is required at `/usr/bin/time`. Each example starts a fresh process three times. Save stdout and stderr together. Record board, OS, model digest, quantization, ExecuTorch commit, offline status, successful selections, detector and adviser latency, CPU use and peak process RSS. GNU time's peak is for a process in the command tree and does not measure combined simultaneous memory use. Capture system memory and swap during inference to assess 4 GB headroom.

From the project root, with the bundle and library path set as above, capture both runs:

```sh
mkdir -p results
scripts/benchmark.sh > results/pi4-detector.log 2>&1
scripts/benchmark.sh --runner "$bundle/llama_main" --model "$bundle/adviser.pte" --tokenizer "$bundle/tokenizer.model" > results/pi4-adviser.log 2>&1
```

A successful full run exits zero and prints `"adviser": "local Llama / ExecuTorch"` plus `priority_guidance` for each example. If it exits early, inspect the last record in the adviser log and report the failing stage. Keep the Pi logs with the report.

For the walkthrough, show the board and offline state, compare a routine SMS with a suspicious SMS, point out the detector evidence, and show the local Llama selection and timing. Ask a first-time user to explain the risk and identify an independent verification step. Record whether they succeed without prompting. Board results, user observations and a recorded demo remain outstanding.

Open Qualifying is due 23 November 2026. Prepare the GitHub source, installable app, demonstration video and engineering report with measured device results. The PoC deadline for shortlisted teams is 5 February 2027. [Official timeline and submission guidance](https://arm-education.github.io/Arm-Developer-Labs/Bharat_AI_SoC_2026_27.html)

## Remaining work in order

1. Confirm both detector verdicts on the Pi. Capture the first detector benchmark.
2. Stage the compatible local Llama bundle. Run one suspicious example interactively and verify the selected advice before timing the full suite.
3. Demonstrate offline operation and capture all six adviser runs. If accessing the Pi over SSH, retain the local management connection while isolating internet access.
4. Summarise measured Pi results and user observations. Package the source, wheel, report and demo for the team to submit. At handoff time the board run, video, final engineering report and submission are pending.
