#!/bin/sh
# Step-by-step setup for SMS Guard on 64-bit Raspberry Pi OS (aarch64).
set -eu

if [ "$(uname -m)" != "aarch64" ] || [ "$(getconf LONG_BIT)" != "64" ]; then
    echo "Error: expected 64-bit aarch64 Linux, found $(uname -m) $(getconf LONG_BIT)-bit" >&2
    exit 1
fi

if ! [ -x /usr/bin/time ]; then
    echo "Installing GNU time (/usr/bin/time)..."
    sudo apt-get update -qq && sudo apt-get install -y -qq time
fi

python3 -m venv .venv
.venv/bin/python -m pip install --no-index --no-deps dist/sms_guard_ps3-0.1.0-py3-none-any.whl

echo "Detector smoke check:"
echo 'Meet you at the library after lunch.' | .venv/bin/sms-guard
echo 'Account locked. Verify now at https://account.example.invalid' | .venv/bin/sms-guard

if [ -x llama-bundle/llama_main ] && [ -r llama-bundle/adviser.pte ] && [ -r llama-bundle/tokenizer.model ]; then
    echo "Llama bundle detected. Verifying shared libraries:"
    LD_LIBRARY_PATH="$PWD/llama-bundle${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ldd llama-bundle/llama_main
else
    echo "Stage llama_main, libllama_runner.so, adviser.pte, and tokenizer.model in ./llama-bundle to enable local Llama advice."
fi
