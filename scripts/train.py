"""Rebuild the detector and evaluate the complete policy on held-out UCI SMS."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sms_guard.detect import assess, normalize, tokens

archive = Path(sys.argv[1])
if hashlib.sha256(archive.read_bytes()).hexdigest() != "1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3":
    sys.exit("Unexpected UCI archive hash.")
groups = defaultdict(set)
with zipfile.ZipFile(archive) as z:
    for line in z.read("SMSSpamCollection").decode().splitlines():
        label, msg = line.split("\t", 1)
        groups[" ".join(normalize(msg).split())].add(label)

counts = {k: Counter() for k in ("ham", "spam")}
train = Counter()
test = []
for label in counts:
    rows = sorted(m for m, labels in groups.items() if labels == {label})
    random.Random(42).shuffle(rows)
    n = len(rows) // 5
    test.extend((label, m) for m in rows[:n])
    for msg in rows[n:]:
        train[label] += 1
        counts[label].update({k: min(v, 3) for k, v in Counter(tokens(msg)).items()})

vocab = sorted(k for k, v in (counts["ham"] + counts["spam"]).items() if v >= 2)
weights = {}
for label, sign in (("spam", 1), ("ham", -1)):
    denom = sum(counts[label][k] for k in vocab) + len(vocab)
    for k in vocab:
        weights[k] = weights.get(k, 0) + sign * math.log((counts[label][k] + 1) / denom)
data = dict(bias=math.log(train["spam"] / train["ham"]),
            weights={k: round(v, 5) for k, v in weights.items()})
(ROOT / "sms_guard/model.json").write_text(json.dumps(data, separators=(",", ":")))
confusion = Counter()
latencies = []
for label, msg in test:
    start = time.perf_counter_ns()
    flagged = assess(msg)["verdict"] == "review"
    latencies.append((time.perf_counter_ns() - start) / 1e6)
    confusion[{(True, True): "TP", (True, False): "FP", (False, True): "FN",
               (False, False): "TN"}[flagged, label == "spam"]] += 1
tp, fp, fn, tn = (confusion[k] for k in ("TP", "FP", "FN", "TN"))
print(json.dumps(dict(training=train, held_out=len(test), confusion=confusion,
                      precision=tp/(tp+fp), recall=tp/(tp+fn), false_positive_rate=fp/(fp+tn),
                      median_detector_ms=statistics.median(latencies)), indent=2))
