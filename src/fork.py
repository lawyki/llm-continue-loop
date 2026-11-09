#!/usr/bin/env python3
"""Fork a finished run: replay its history up to turn N, then send your own message.
Interactive: python3 fork.py --log 2b/go_on_seed8/run_*.jsonl --upto 12
Automatic: python3 fork.py --log 2b/go_on_seed8/run_*.jsonl --upto 12 --message "I choose A." --then "Go on." --turns 5
"""
import argparse, glob, json, os, urllib.request
from datetime import datetime
p = argparse.ArgumentParser()
p.add_argument("--log", required=True); p.add_argument("--upto", type=int, required=True)
p.add_argument("--message", default=None); p.add_argument("--then", default=None)
p.add_argument("--turns", type=int, default=1); p.add_argument("--model", default=None)
p.add_argument("--temperature", type=float, default=1.0); p.add_argument("--ctx", type=int, default=65536)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--system", default=None, help="optional system prompt placed before the replayed history")
a = p.parse_args()
log = glob.glob(a.log)[0]
meta = json.load(open(os.path.join(os.path.dirname(log), "meta.json")))
model = a.model or meta["model"]; orig_msg = meta.get("message", "Continue.")
rows = [json.loads(l) for l in open(log)][:a.upto]
history = [{"role": "system", "content": a.system}] if a.system else []
for r in rows:
    history += [{"role": "user", "content": r.get("message", orig_msg)}, {"role": "assistant", "content": r["reply"]}]
out = os.path.join(os.path.dirname(log), f"fork_t{a.upto}_{datetime.now():%H%M%S}.md")
def chat():
    body = json.dumps({"model": model, "messages": history, "stream": False, "think": False,
        "options": {"num_ctx": a.ctx, "temperature": a.temperature, "seed": a.seed}}).encode()
    with urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat", body,
            {"Content-Type": "application/json"}), timeout=900) as r: return json.load(r)["message"]["content"]
with open(out, "w") as f:
    f.write(f"# Fork of {log} after turn {a.upto}\n\n")
    i = 0
    while True:
        if a.message is None:
            msg = input(f"\nYour message for turn {a.upto+1+i} (empty = quit): ").strip()
            if not msg: break
        else:
            if i >= a.turns: break
            msg = a.message if i == 0 else (a.then or a.message)
        history.append({"role": "user", "content": msg}); reply = chat()
        history.append({"role": "assistant", "content": reply})
        f.write(f"## Fork turn {a.upto+1+i}\n\n> Message: {msg}\n\n{reply}\n\n"); f.flush()
        print(f"--- fork turn {a.upto+1+i} ({msg})\n{reply}\n", flush=True)
        i += 1
print("saved", out)
