import argparse
import json
import subprocess
import sys
import time
from .adviser import advise
from .detect import assess


def main():
    parser = argparse.ArgumentParser(description="Check an SMS offline. Paste one line or pipe text on stdin.")
    parser.add_argument("--runner", help="Path to ExecuTorch llama_main")
    parser.add_argument("--model", help="Local Llama 3.2 1B Instruct XNNPACK .pte")
    parser.add_argument("--tokenizer", help="Matching tokenizer.model")
    args = parser.parse_args()
    assets = (args.runner, args.model, args.tokenizer)
    if any(assets) and not all(assets):
        parser.error("Provide --runner, --model and --tokenizer together.")
    if sys.stdin.isatty():
        print("Paste one SMS and press Enter.", file=sys.stderr)
        message = sys.stdin.readline(8002)
    else:
        message = sys.stdin.read(8002)
    start = time.perf_counter()
    try:
        result = assess(message.removesuffix("\n"))
    except ValueError as exc:
        parser.error(str(exc))
    result["detector_ms"] = round((time.perf_counter() - start) * 1000, 3)
    result["adviser"] = "detector guidance only"
    failed = False
    if all(assets):
        start = time.perf_counter()
        try:
            result["priority_guidance"] = advise(result, *assets)
            result["adviser"] = "local Llama / ExecuTorch"
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            result["adviser"] = "unavailable"
            print(f"Local adviser failed ({type(exc).__name__}). Check the runtime and model bundle.", file=sys.stderr)
            failed = True
        result["adviser_ms"] = round((time.perf_counter() - start) * 1000, 3)
    print(json.dumps(result, indent=2))
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
