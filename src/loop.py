#!/usr/bin/env python3
"""
Repeated-prompt drift experiment.
Sends the SAME user message to a local Ollama model again and again, keeping
the full conversation history, and logs every reply plus drift metrics.

Usage:
  python3 loop.py                         # defaults below
  python3 loop.py --model qwen3.5:4b --turns 200 --interval 0
  python3 loop.py --think                 # comparison condition: reasoning on
  python3 loop.py --outdir runs/a --vary --seed 9   # random message per turn from VARY_POOL

Output (in --outdir, default the current folder): run_<timestamp>.jsonl (one line
per turn) and meta.json (settings, start/end time, turns, stop reason), plus live
console printout.
Stop anytime with Ctrl+C; the log is written turn by turn.
"""
import argparse, json, math, os, random, signal, sys, time, urllib.request
from collections import Counter
from datetime import datetime

p = argparse.ArgumentParser()
p.add_argument("--model", default="qwen3.5:4b")
p.add_argument("--message", default="Continue.")
p.add_argument("--turns", type=int, default=200)
p.add_argument("--interval", type=float, default=0,
               help="seconds between turns; the model never sees time, so 0 is equivalent to 60")
p.add_argument("--ctx", type=int, default=32768,
               help="context window; Ollama's small default silently drops old turns")
p.add_argument("--temperature", type=float, default=0.8)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--think", action="store_true")
p.add_argument("--outdir", default=".", help="folder for the JSONL log and meta.json")
p.add_argument("--vary", action="store_true",
               help="pick each turn's message at random (seeded by --seed) from VARY_POOL")
a = p.parse_args()

URL = "http://localhost:11434/api/chat"
VARY_POOL = ["Continue.", "Go on.", "Next.", "Keep going.", "And then?", "Ok.", "More."]
RETRIES, RETRY_PAUSE = 3, 30          # failed Ollama request: retry 3 times, 30 s apart
os.makedirs(a.outdir, exist_ok=True)
log_path = os.path.join(a.outdir, f"run_{datetime.now():%Y%m%d_%H%M%S}.jsonl")
meta_path = os.path.join(a.outdir, "meta.json")
rng = random.Random(a.seed)
history = []

def now_iso(): return datetime.now().astimezone().isoformat(timespec="seconds")

meta = {
    "model": a.model, "message": None if a.vary else a.message, "vary": a.vary,
    **({"vary_pool": VARY_POOL} if a.vary else {}),
    "seed": a.seed, "temperature": a.temperature, "ctx": a.ctx,
    "max_turns": a.turns, "think": a.think, "interval": a.interval,
    "jsonl": os.path.basename(log_path), "start_time": now_iso(),
}

def write_meta():
    tmp = meta_path + ".tmp"
    with open(tmp, "w") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, meta_path)

def words(t): return t.lower().split()

def entropy(t):
    c = Counter(words(t)); n = sum(c.values())
    return -sum(v/n * math.log2(v/n) for v in c.values()) if n else 0.0

def distinct2(t):
    w = words(t); bg = list(zip(w, w[1:]))
    return len(set(bg)) / len(bg) if bg else 0.0

def overlap(a_, b_):
    A, B = set(words(a_)), set(words(b_))
    return len(A & B) / len(A | B) if A | B else 0.0

def chat():
    body = json.dumps({
        "model": a.model, "messages": history, "stream": False, "think": a.think,
        "options": {"num_ctx": a.ctx, "temperature": a.temperature, "seed": a.seed},
    }).encode()
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.load(r)
        except Exception as e:
            if attempt == RETRIES: raise
            print(f"[retry] Ollama request failed ({type(e).__name__}: {e}); "
                  f"retry {attempt + 1}/{RETRIES} in {RETRY_PAUSE} s", file=sys.stderr, flush=True)
            time.sleep(RETRY_PAUSE)

def on_sigterm(signum, frame): raise SystemExit("terminated")
signal.signal(signal.SIGTERM, on_sigterm)

write_meta()
prev = ""
done, stop_reason = 0, "max_turns"
print(f"model={a.model} message={'(vary)' if a.vary else repr(a.message)} think={a.think} log={log_path}\n")
try:
    for turn in range(1, a.turns + 1):
        msg = rng.choice(VARY_POOL) if a.vary else a.message
        history.append({"role": "user", "content": msg})
        r = chat()
        reply = r["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        row = {
            "turn": turn, "message": msg, "reply": reply,
            "chars": len(reply), "entropy": round(entropy(reply), 3),
            "distinct2": round(distinct2(reply), 3),
            "overlap_prev": round(overlap(reply, prev), 3),
            "prompt_tokens": r.get("prompt_eval_count"),
        }
        with open(log_path, "a") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
        done = turn
        print(f"--- turn {turn} | {row['chars']} chars | H={row['entropy']} "
              f"d2={row['distinct2']} overlap={row['overlap_prev']} ctx={row['prompt_tokens']}")
        print(reply[:600] + ("..." if len(reply) > 600 else "") + "\n")
        if row["prompt_tokens"] and row["prompt_tokens"] > 0.9 * a.ctx:
            print("Context nearly full; stopping so old turns are not silently truncated.")
            stop_reason = "context_limit"
            break
        prev = reply
        time.sleep(a.interval)
except KeyboardInterrupt:
    stop_reason = "interrupted"; raise
except SystemExit as e:
    stop_reason = str(e.code); raise
except Exception as e:
    stop_reason = f"error: {type(e).__name__}: {e}"; raise
finally:
    meta["turns"] = done
    meta["stop_reason"] = stop_reason
    # end_time only on a clean finish, so the runner redoes aborted runs on restart
    meta["end_time" if stop_reason in ("context_limit", "max_turns") else "aborted_time"] = now_iso()
    write_meta()
