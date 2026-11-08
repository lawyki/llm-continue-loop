#!/bin/sh
# One-shot (2026-11-09): at the next cooldown (no run in progress), restart the
# runner so it picks up the new 4-min default. The restarted runner waits out the
# rest of the 4 min. Gives up after 2 h or if the job ends.
cd "$(dirname "$0")" || exit 1
n=$(grep -c ' cooldown ' progress.log)
end=$(( $(date +%s) + 7200 ))
while :; do
  grep -q 'JOB END' progress.log && exit 0
  [ "$(date +%s)" -gt "$end" ] && exit 0
  [ "$(grep -c ' cooldown ' progress.log)" -gt "$n" ] && break
  sleep 5
done
pid=$(cat runner.pid)
echo "$(date '+%Y-%m-%d %H:%M:%S') switching to 4-min cooldown: restarting runner (pid $pid) between runs" >> progress.log
kill -TERM "$pid"
while kill -0 "$pid" 2>/dev/null; do sleep 1; done
./start.sh >> runner.out 2>&1
