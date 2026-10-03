#!/bin/bash
# On each host, while the engine serves: hostwatch.sh LOG
# Reads MemAvailable every 2 s and stops `tensorfold serve` when it falls below 5 GiB, before the unified memory
# runs out (the guard 1.x and the 2.x measurements used); exits when the engine is gone. cluster.sh starts it.
log=$1
sleep 5
while pgrep -f "tensorfold serve" >/dev/null; do
  available=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
  echo "$(date +%T) $available" >>"$log"
  if [ "$available" -lt 5 ]; then
    pkill -9 -f "tensorfold serve"
    echo KILLED >>"$log"
  fi
  sleep 2
done
echo "$(date +%T) done" >>"$log"
