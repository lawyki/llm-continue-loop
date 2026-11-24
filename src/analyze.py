#!/usr/bin/env python3
"""Summarize every run: one CSV row per run plus per-turn charts.

  python3 src/analyze.py

Reads runs/pilot/run_*.jsonl and runs/seed/<model>/<run>/run_*.jsonl (+ meta.json).
Writes results/summary.csv, results/reply_length.png and results/overlap.png.
Charts need matplotlib; the CSV needs only the standard library.
"""
import csv, glob, json, os, re, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")


def norm(t):
    return re.sub(r"\s+", " ", t.strip().lower())


def runs():
    """Yield (label, rows, meta) in a fixed order: pilots, 9B, 2B."""
    for i, f in enumerate(sorted(glob.glob(f"{ROOT}/runs/pilot/run_*.jsonl")), 1):
        yield f"Pilot {i}", [json.loads(l) for l in open(f)], {}
    order = ["continue_seed1", "continue_seed2", "continue_seed3", "continue_seed4", "continue_seed5",
             "next_seed6", "ok_seed7", "go_on_seed8", "vary_seed9", "vary_seed10"]
    for sub in ("9b", "2b"):
        for name in order:
            d = f"{ROOT}/runs/seed/{sub}/{name}"
            logs = glob.glob(f"{d}/run_*.jsonl")
            if not logs:
                continue
            meta = json.load(open(f"{d}/meta.json"))
            seed = re.search(r"seed(\d+)", name).group(1)
            yield f"{sub.upper()} seed {seed}", [json.loads(l) for l in open(logs[0])], meta


def summarize(label, R, meta):
    n = len(R)
    k = max(1, n // 10)
    first, last = R[:k], R[-k:]
    replies = [norm(r["reply"]) for r in R]
    streak = best = 1
    for a, b in zip(replies, replies[1:]):
        streak = streak + 1 if a == b else 1
        best = max(best, streak)
    msg = "random pool" if meta.get("vary") else (meta.get("message") or "not logged")
    return {
        "run": label,
        "model": meta.get("model", "not recorded"),
        "message": msg,
        "turns": n,
        "stop_reason": meta.get("stop_reason", "not recorded"),
        "chars_first_tenth": round(st.mean(r["chars"] for r in first)),
        "chars_last_tenth": round(st.mean(r["chars"] for r in last)),
        "entropy_first_tenth": round(st.mean(r["entropy"] for r in first), 2),
        "entropy_last_tenth": round(st.mean(r["entropy"] for r in last), 2),
        "distinct2_first_tenth": round(st.mean(r["distinct2"] for r in first), 2),
        "distinct2_last_tenth": round(st.mean(r["distinct2"] for r in last), 2),
        # turn 1 has no previous reply, so the first window starts at turn 2
        "overlap_first_tenth": round(st.mean(r["overlap_prev"] for r in R[1:k + 1]), 2),
        "overlap_last_tenth": round(st.mean(r["overlap_prev"] for r in last), 2),
        "unique_replies": len(set(replies)),
        "verbatim_repeats": n - len(set(replies)),
        "longest_identical_streak": best,
    }


def title(label, meta):
    msg = "random pool" if meta.get("vary") else (meta.get("message") or "model not recorded")
    return f"{label}, {msg}"


def charts(data):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping charts")
        return
    ink, muted, line, grid = "#1f2328", "#59636e", "#2f6fb0", "#d8dee4"
    specs = [("reply_length.png", "chars", "Reply length per turn (characters)", None),
             ("overlap.png", "overlap_prev", "Word overlap with the previous reply per turn (Jaccard)", (0, 1.02))]
    for fname, key, suptitle, ylim in specs:
        cols, rows = 3, -(-len(data) // 3)
        fig, axes = plt.subplots(rows, cols, figsize=(12, 2.1 * rows), sharey=True, facecolor="white")
        for ax in axes.flat[len(data):]:
            ax.set_visible(False)
        for ax, (label, R, meta) in zip(axes.flat, data):
            xs = [r["turn"] for r in R]
            ys = [r[key] for r in R]
            if key == "overlap_prev":
                xs, ys = xs[1:], ys[1:]
            ax.plot(xs, ys, color=line, linewidth=1.4)
            ax.set_title(title(label, meta), fontsize=9, color=ink, loc="left")
            ax.grid(True, color=grid, linewidth=0.6)
            ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(grid)
            ax.tick_params(colors=muted, labelsize=8)
            if ylim:
                ax.set_ylim(*ylim)
        fig.suptitle(suptitle + ". x axis: turn", fontsize=11, color=ink, x=0.01, ha="left")
        fig.tight_layout(rect=(0, 0, 1, 0.98))
        fig.savefig(os.path.join(OUT, fname), dpi=130, facecolor="white")
        plt.close(fig)
        print("wrote", os.path.relpath(os.path.join(OUT, fname), ROOT))


def main():
    os.makedirs(OUT, exist_ok=True)
    data = list(runs())
    rows = [summarize(*d) for d in data]
    path = os.path.join(OUT, "summary.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", os.path.relpath(path, ROOT), f"({len(rows)} runs)")
    charts(data)


if __name__ == "__main__":
    main()
