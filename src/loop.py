#!/usr/bin/env python3
"""
Repeated-prompt drift experiment.
Sends the SAME user message to a local Ollama model again and again, keeping
the full conversation history, and logs every reply plus drift metrics.

Usage:
  python3 loop.py                         # defaults below
  python3 loop.py --model qwen3.5:4b --turns 200 --interval 0
  python3 loop.py --think                 # comparison condition: reasoning on

Output: run_<timestamp>.jsonl (one line per turn) and live console printout.
Stop anytime with Ctrl+C; the log is written turn by turn.
"""
import argparse, json, math, time, urllib.request
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
a = p.parse_args()

URL = "http://localhost:11434/api/chat"
log_path = f"run_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
history = []

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
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)

prev = ""
print(f"model={a.model} message={a.message!r} think={a.think} log={log_path}\n")
for turn in range(1, a.turns + 1):
    history.append({"role": "user", "content": a.message})
    r = chat()
    reply = r["message"]["content"]
    history.append({"role": "assistant", "content": reply})
    row = {
        "turn": turn, "reply": reply,
        "chars": len(reply), "entropy": round(entropy(reply), 3),
        "distinct2": round(distinct2(reply), 3),
        "overlap_prev": round(overlap(reply, prev), 3),
        "prompt_tokens": r.get("prompt_eval_count"),
    }
    with open(log_path, "a") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"--- turn {turn} | {row['chars']} chars | H={row['entropy']} "
          f"d2={row['distinct2']} overlap={row['overlap_prev']} ctx={row['prompt_tokens']}")
    print(reply[:600] + ("..." if len(reply) > 600 else "") + "\n")
    if row["prompt_tokens"] and row["prompt_tokens"] > 0.9 * a.ctx:
        print("Context nearly full; stopping so old turns are not silently truncated.")
        break
    prev = reply
    time.sleep(a.interval)
