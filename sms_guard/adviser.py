"""Bounded Llama advisory using the ExecuTorch release/1.0 llama_main CLI."""
from pathlib import Path
import re
import subprocess


GUIDANCE = {
    "Contains a web link.": "A link in a message can lead somewhere unexpected. Open the service's app yourself to check.",
    "A shortened link hides its destination.": "You cannot see where this short link goes. Use a known address to check the request.",
    "Uses urgency or account restrictions.": "The message pressures you to act quickly. Pause and check the claim through a known contact.",
    "Appears to request a secret or payment detail.": "Someone appears to be asking for private details. Keep codes and passwords to yourself.",
    "Wording resembles messages labelled as spam in the training set.": "This resembles past spam. Check who sent the message before responding.",
}


def advise(result, runner, model, tokenizer):
    options = [GUIDANCE[e] for e in result["evidence"]]
    options.append(result["action"])
    choices = "\n".join(f"{i}. {option}" for i, option in enumerate(options, 1))
    prompt = ("<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
              "Select the most useful explanation and action for a nonexpert. "
              "Return only the number of one available option.\nDetector verdict: "
              + result["verdict"] + "\nEvidence: " + " ".join(result["evidence"])
              + "\nOptions:\n" + choices
              + "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n")
    proc = subprocess.run([str(Path(runner).resolve()), "--model_path=" + model,
                           "--tokenizer_path=" + tokenizer, "--prompt=" + prompt,
                           "--cpu_threads=3", "--temperature=0", "--max_new_tokens=8"],
                          capture_output=True, text=True, timeout=180, check=True)
    reply = proc.stdout.removeprefix(prompt)
    reply = re.sub(r"(?m)^PyTorchObserver\s+.*$", "", reply)
    reply = reply.replace("<|eot_id|>", "").strip()
    match = re.fullmatch(r"([1-9])(?:\s*[.)](?:\s*(.+))?)?", reply, re.DOTALL)
    if not match or int(match[1]) > len(options):
        raise ValueError("The local model returned an invalid advisory selection.")
    choice = options[int(match[1]) - 1]
    if match[2] and not choice.startswith(match[2].strip()):
        raise ValueError("The local model returned an invalid advisory selection.")
    return choice
