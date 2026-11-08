#!/bin/sh
# Start (or resume) the overnight seed runs, detached from the terminal.
# Finished runs are skipped. Stop with:  kill $(cat ~/Downloads/seed_runs/runner.pid)
cd "$(dirname "$0")" || exit 1
nohup /usr/bin/env python3 -u run_all.py "$@" >> runner.out 2>&1 < /dev/null &
echo "runner started, pid $!"
echo "watch:  tail -f ~/Downloads/seed_runs/progress.log"
