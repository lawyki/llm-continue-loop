#!/bin/sh
# Start (or resume) the overnight seed runs, detached from the terminal.
# Run from anywhere: sh src/start.sh --root runs/rerun
# Finished runs are skipped. Stop with:  kill $(cat <root>/runner.pid)
cd "$(dirname "$0")/.." || exit 1
nohup /usr/bin/env python3 -u src/run_all.py "$@" >> runner.out 2>&1 < /dev/null &
echo "runner started, pid $!"
echo "watch:  tail -f <root>/progress.log"
