# SMS Guard for Bharat AI-SoC PS3

Paste an English SMS to get a review decision, the cues behind it, and an action you can take. The program runs locally. It treats URLs as text, never visits them, and keeps no message history.

## Brief report and Pi handoff

| Component | Status on 20 November 2026 |
| --- | --- |
| SMS detector | Working on the x86-64 development host. On 1,031 held-out English SMS messages, it flagged 120 of 128 spam messages and 6 of 903 ordinary messages. |
| Raspberry Pi 4B, 4 GB | Deployment target. The first board task is to run the two examples below with the bundled detector. Training is already complete. |
| Llama advisory | Adapter implemented. The local model, tokenizer and native ExecuTorch runner must be supplied. Inference speed, memory use and advice quality on this board remain unmeasured. |

For code changes, start with [detect.py](sms_guard/detect.py) for scoring and evidence, [adviser.py](sms_guard/adviser.py) for Llama selection, and [the CLI](sms_guard/__main__.py) for input, timing and failure reporting. The competition slides are in [the attached document](Untitled%201.odt).

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
