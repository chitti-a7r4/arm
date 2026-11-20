"""Offline SMS triage. Inputs are only held in memory."""
from collections import Counter
from functools import lru_cache
from importlib.resources import files
import json
import math
import re
import unicodedata
from urllib.parse import urlsplit


def normalize(message):
    return unicodedata.normalize("NFKC", message).casefold()


def tokens(message):
    return re.findall(r"[a-z]+|\d+", normalize(message))


@lru_cache(maxsize=1)
def model():
    return json.loads(files("sms_guard").joinpath("model.json").read_text())


def classify(message):
    data = model()
    score = data["bias"]
    for token, count in Counter(tokens(message)).items():
        score += min(3, count) * data["weights"].get(token, 0)
    return 1 / (1 + math.exp(-max(-50, min(50, score))))


def assess(message):
    if not message.strip() or len(message) > 8000:
        raise ValueError("Enter a message between 1 and 8000 characters.")
    s = normalize(message)
    evidence = []
    links = re.findall(r"(?:https?://|www\.)[^\s<>]+", s)
    if links:
        evidence.append("Contains a web link.")
    for link in links:
        try:
            host = urlsplit(link if "://" in link else "https://" + link).hostname or ""
        except ValueError:
            host = ""
        if host in {"bit.ly", "t.co", "tinyurl.com"}:
            evidence.append("A shortened link hides its destination.")
            break
    urgent = re.search(r"\b(urgent|immediately|locked|suspended|expires today|verify now)\b", s)
    sensitive = re.search(r"\b(share|send|enter|confirm|provide)\b.{0,35}\b(otp|pin|password|card details)\b", s)
    warning = re.search(r"\b(never|do not|don't)\s+(?:ever\s+)?(?:share|send|enter|confirm|provide)\b", s)
    if urgent:
        evidence.append("Uses urgency or account restrictions.")
    request = bool(sensitive and not warning)
    if request:
        evidence.append("Appears to request a secret or payment detail.")
    p = classify(message)
    if p >= 0.5:
        evidence.append("Wording resembles messages labelled as spam in the training set.")
    flagged = p >= 0.5 or request or bool(urgent and links)
    return dict(verdict="review" if flagged else "no strong signal",
                spam_model_score=round(p, 5), evidence=evidence,
                action=("Leave the message untouched. Check with the sender through an independently known channel."
                        if flagged else "If the request is unexpected, verify it independently."))
