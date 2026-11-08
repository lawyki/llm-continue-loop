#!/usr/bin/env python3
"""
Overnight runner for ~/Downloads/loop.py (15 seed runs, sequential).

- Resumable: a run whose meta.json has "end_time" is skipped. A run that stopped
  early (no end_time) is redone; its partial files are moved to _failed/ first.
- Cooldown between runs (default 4 min; a restart waits out the rest of it).
  If the projected finish passes the
  deadline (default 08:00), the cooldown shrinks, never below --min-cooldown.
- Unloads the previous model on a model switch, holds caffeinate -dimsu for the
  whole job, logs to progress.log. One extra attempt for failed runs at the end
  if it still fits before the deadline.

Start detached:  ./start.sh          Stop:  kill $(cat runner.pid)
Smoke test:      python3 run_all.py --smoke --root <scratch folder>
"""
import argparse, glob, json, os, re, shutil, signal, subprocess, sys, threading, time, urllib.request
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
LOOP = os.path.expanduser("~/Downloads/loop.py")
OLLAMA = shutil.which("ollama") or "/usr/local/bin/ollama"
M9, M2 = "qwen3.5:latest", "qwen3.5:2b"
REF_SEC = {M9: 32 * 60, M2: 16 * 60}   # reference duration per run
FIXED = ["--temperature", "1.0", "--ctx", "65536"]
CTX = 65536

def item(model, sub, name, seed, message=None, vary=False):
    return dict(model=model, sub=sub, name=name, seed=seed, message=message, vary=vary)

PLAN = (
    [item(M9, "9b", f"continue_seed{s}", s, "Continue.") for s in range(1, 6)]
    + [item(M2, "2b", f"continue_seed{s}", s, "Continue.") for s in range(1, 6)]
    + [item(M2, "2b", "next_seed6", 6, "Next."),
       item(M2, "2b", "ok_seed7", 7, "Ok."),
       item(M2, "2b", "go_on_seed8", 8, "Go on."),
       item(M2, "2b", "vary_seed9", 9, vary=True),
       item(M2, "2b", "vary_seed10", 10, vary=True)]
)
SMOKE_PLAN = [item(M9, "9b", "continue_seed1", 1, "Continue."),
              item(M2, "2b", "vary_seed9", 9, vary=True)]

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=HERE)
ap.add_argument("--turns", type=int, default=400)
ap.add_argument("--cooldown", type=float, default=None, help="seconds between runs (default 240)")
ap.add_argument("--min-cooldown", type=float, default=120)
ap.add_argument("--deadline", default="08:00")
ap.add_argument("--smoke", action="store_true", help="2 turns per model, no cooldown")
args = ap.parse_args()
if args.smoke:
    args.turns, args.min_cooldown = 2, 0
    if args.cooldown is None: args.cooldown = 0
if args.cooldown is None:
    args.cooldown = 240
plan = SMOKE_PLAN if args.smoke else PLAN
root = os.path.abspath(args.root)
os.makedirs(root, exist_ok=True)
LOG = os.path.join(root, "progress.log")
PIDFILE = os.path.join(root, "runner.pid")

start = datetime.now()
hh, mm = map(int, args.deadline.split(":"))
deadline = start.replace(hour=hh, minute=mm, second=0, microsecond=0)
if deadline <= start:
    deadline += timedelta(days=1)

def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    with open(LOG, "a") as f: f.write(line + "\n")
    print(line, flush=True)

def rdir(it): return os.path.join(root, it["sub"], it["name"])
def label(it): return f"{it['sub']}/{it['name']}"

def read_meta(d):
    try:
        with open(os.path.join(d, "meta.json")) as f: return json.load(f)
    except (OSError, ValueError):
        return None

def is_done(it):
    m = read_meta(rdir(it))
    return bool(m and m.get("end_time"))

# ---- single instance -------------------------------------------------------
def alive(pid):
    try:
        out = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
        return "run_all.py" in out
    except Exception:
        return False

try:
    old = int(open(PIDFILE).read().strip())
    if old != os.getpid() and alive(old):
        sys.exit(f"runner already running (pid {old}); not starting a second one")
except (OSError, ValueError):
    pass
with open(PIDFILE, "w") as f: f.write(str(os.getpid()))
try:
    os.setsid()                      # own session: survives the launching terminal
except OSError:
    pass

caff = subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])
child = None

def on_term(signum, frame):
    log(f"runner got signal {signum}; stopping current run")
    if child and child.poll() is None:
        child.terminate()
        try: child.wait(30)
        except subprocess.TimeoutExpired: child.kill()
    sys.exit(1)
signal.signal(signal.SIGTERM, on_term)
signal.signal(signal.SIGHUP, signal.SIG_IGN)

# ---- helpers ---------------------------------------------------------------
durations = {M9: [], M2: []}

def est(model):
    d = durations[model]
    return sum(d) / len(d) if d else REF_SEC[model]

def remaining():
    return [it for it in plan if not is_done(it)]

def last_finish():
    """Latest end (or abort) time of any run, as local naive datetime."""
    ts = []
    for it in plan:
        m = read_meta(rdir(it)) or {}
        for k in ("end_time", "aborted_time"):
            if m.get(k):
                ts.append(datetime.fromisoformat(m[k]).astimezone().replace(tzinfo=None))
    return max(ts) if ts else None

def projected(cooldown, todo):
    return datetime.now() + timedelta(seconds=sum(est(i["model"]) for i in todo) + cooldown * max(len(todo) - 1, 0))

def pick_cooldown(todo):
    """Cooldown before the next run; shrinks only if the deadline is at risk."""
    c = args.cooldown
    if not todo or c <= 0:
        return c
    work = sum(est(i["model"]) for i in todo)
    left = (deadline - datetime.now()).total_seconds()
    if left - work - c * len(todo) < 0:
        new = max(args.min_cooldown, min(c, (left - work) / len(todo)))
        log(f"cooldown reduced {c/60:.1f} -> {new/60:.1f} min (projected finish would pass {deadline:%H:%M})")
        c = new
    return c

def ollama_up():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/version", timeout=10): return True
    except Exception:
        return False

def wait_for_ollama(limit=600):
    t0, tried_open = time.time(), False
    while not ollama_up():
        if time.time() - t0 > limit:
            log("ERROR Ollama not reachable for 10 min")
            return False
        if not tried_open and time.time() - t0 > 60 and os.path.isdir("/Applications/Ollama.app"):
            log("Ollama down >60 s; launching Ollama.app")
            subprocess.run(["open", "-ga", "Ollama"]); tried_open = True
        time.sleep(15)
    return True

def unload_except(model):
    for m in {i["model"] for i in PLAN} - {model}:
        subprocess.run([OLLAMA, "stop", m], capture_output=True)

def write_story(d):
    files = sorted(glob.glob(os.path.join(d, "run_*.jsonl")))
    if not files: return
    with open(files[-1]) as f, open(os.path.join(d, "story.md"), "w") as out:
        for line in f:
            r = json.loads(line)
            out.write(f"## Turn {r['turn']}\n\n> Message: {r.get('message', '')}\n\n{r['reply']}\n\n")

def clear_partial(d):
    """Move leftovers of an aborted run to _failed/ (nothing is deleted)."""
    if os.path.isdir(d) and os.listdir(d):
        dest = os.path.join(root, "_failed", f"{os.path.relpath(d, root).replace(os.sep, '_')}_{datetime.now():%Y%m%d_%H%M%S}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(d, dest)
        log(f"moved partial files of {os.path.relpath(d, root)} to {os.path.relpath(dest, root)}")

def run(it):
    global child
    d = rdir(it)
    if not wait_for_ollama():
        return False
    clear_partial(d)
    cmd = [sys.executable, "-u", LOOP, "--model", it["model"], "--seed", str(it["seed"]),
           "--turns", str(args.turns), "--outdir", d, *FIXED]
    cmd += ["--vary"] if it["vary"] else ["--message", it["message"]]
    log(f"START {label(it)}  model={it['model']} seed={it['seed']} "
        f"message={'(vary)' if it['vary'] else repr(it['message'])}")
    t0 = time.time()
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    def pump_err():
        for line in child.stderr:
            if line.strip(): log(f"  [{label(it)}] {line.rstrip()}")
    th = threading.Thread(target=pump_err, daemon=True); th.start()
    pat = re.compile(r"^--- turn (\d+) .* ctx=(\S+)")
    for line in child.stdout:
        m = pat.match(line)
        if m:
            n, ctx = int(m.group(1)), m.group(2)
            if n % 10 == 0 or n == 1:
                pct = f" ({int(ctx) / CTX:.0%})" if ctx.isdigit() else ""
                log(f"  {label(it)} turn {n}, ctx {ctx}{pct}, {(time.time() - t0) / 60:.1f} min")
    rc = child.wait(); th.join(5)
    dur = time.time() - t0
    meta = read_meta(d) or {}
    write_story(d)
    if meta.get("end_time"):
        durations[it["model"]].append(dur)
        log(f"FINISH {label(it)}  {meta.get('turns')} turns, stop={meta.get('stop_reason')}, {dur / 60:.1f} min")
        return True
    log(f"ERROR {label(it)} failed: exit {rc}, stop={meta.get('stop_reason')}, "
        f"{meta.get('turns', 0)} turns, {dur / 60:.1f} min (redone on restart)")
    return False

# ---- main ------------------------------------------------------------------
todo = remaining()
skipped = [label(i) for i in plan if i not in todo]
log(f"JOB START pid={os.getpid()} root={root} turns={args.turns} cooldown={args.cooldown/60:.0f} min "
    f"deadline={deadline:%Y-%m-%d %H:%M}")
if skipped: log(f"skipping {len(skipped)} finished: {', '.join(skipped)}")
log(f"{len(todo)} runs to do; projected finish {projected(args.cooldown, todo):%H:%M}")

last_model, ran_any, failed = None, False, []
for pass_no in (1, 2):
    queue = remaining()
    if pass_no == 2:
        if not queue: break
        log(f"retry pass for {len(queue)} failed run(s)")
    for idx, it in enumerate(queue):
        if pass_no == 2:
            c = args.cooldown if ran_any else 0
            if datetime.now() + timedelta(seconds=c + est(it["model"])) > deadline:
                log(f"skip retry of {label(it)}: would end after {deadline:%H:%M}")
                continue
        if ran_any:
            c = pick_cooldown(queue[idx:])
            if c > 0:
                log(f"cooldown {c / 60:.1f} min")
                time.sleep(c)
        elif args.cooldown > 0 and (lf := last_finish()):
            # fresh start or restart: still honor the cooldown since the last run ended
            c = pick_cooldown(queue[idx:])
            wait = c - (datetime.now() - lf).total_seconds()
            if wait > 0:
                log(f"cooldown {wait / 60:.1f} min (rest of {c / 60:.1f} min after last run ended {lf:%H:%M:%S})")
                time.sleep(wait)
        if it["model"] != last_model:
            unload_except(it["model"])
            if last_model: log(f"unloaded {last_model}")
            last_model = it["model"]
        run(it); ran_any = True
        left = remaining()
        if left and pass_no == 1:
            log(f"{len(plan) - len(left)}/{len(plan)} done; projected finish "
                f"{projected(args.cooldown, [i for i in queue[idx + 1:] if i in left]):%H:%M}")

if last_model:
    subprocess.run([OLLAMA, "stop", last_model], capture_output=True)
left = remaining()
log(f"JOB END {len(plan) - len(left)}/{len(plan)} complete"
    + (f"; not complete: {', '.join(label(i) for i in left)}" if left else ""))
try: os.remove(PIDFILE)
except OSError: pass
