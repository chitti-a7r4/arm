#!/bin/sh
# Fast end-to-end live demo on the Raspberry Pi 4B (~45s total).
set -eu

bundle="${LLAMA_BUNDLE:-$PWD/llama-bundle}"
export LD_LIBRARY_PATH="$bundle${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo "=== 1. Target Hardware & OS ==="
tr -d '\000' < /proc/device-tree/model 2>/dev/null || true
echo
uname -smr
free -h

echo
echo "=== 2. Offline Verification ==="
ip -br addr
ping -c 1 -W 1 1.1.1.1 2>&1 || echo "Offline confirmed: external network unreachable."

echo
echo "=== 3. Routine SMS (Detector + Local Llama 3.2 1B) ==="
echo 'Meet you at the library after lunch.' | python3 -m sms_guard \
  --runner "$bundle/llama_main" \
  --model "$bundle/adviser.pte" \
  --tokenizer "$bundle/tokenizer.model"

echo
echo "=== 4. Suspicious SMS (Detector + Local Llama 3.2 1B) ==="
echo 'Account locked. Verify now at https://account.example.invalid' | python3 -m sms_guard \
  --runner "$bundle/llama_main" \
  --model "$bundle/adviser.pte" \
  --tokenizer "$bundle/tokenizer.model"
