#!/bin/bash
# From a control machine with SSH to every host: cluster.sh CLUSTER_ENV start LABEL [more tensorfold serve arguments]
#                                                 cluster.sh CLUSTER_ENV stop
#                                                 cluster.sh CLUSTER_ENV status
# CLUSTER_ENV (examples/cluster.tp*.env) sets TP, HOSTS (SSH names in rank order), CHECKOUT (this repository on
# each host, for the memory guard) and optionally SSH, CONTAINER and WORK (each host's directory at /work).
# start: the highest rank first and rank 0 last, each `serve.sh TP RANK /work/rank.env` in its container, then the
#        memory guard (hostwatch.sh) on every host; waits for rank 0's "serving" line, and stops at the first
#        Traceback or a rank whose engine is gone. Logs: WORK/logs/serve-rRANK-LABEL.log, hostwatch-LABEL.log.
# stop:  rank 0 first, then the others; waits until no engine runs and prints each host's MemAvailable.
set -u
if [ $# -lt 2 ]; then
  echo "usage: cluster.sh CLUSTER_ENV start LABEL [serve args...] | stop | status" >&2
  exit 2
fi
. "$1"
cmd=$2
shift 2
: "${TP:?CLUSTER_ENV must set TP}" "${HOSTS:?CLUSTER_ENV must set HOSTS}" "${CHECKOUT:?CLUSTER_ENV must set CHECKOUT}"
SSH=${SSH:-ssh -o ConnectTimeout=20}
CONTAINER=${CONTAINER:-glm53-tf}
WORK=${WORK:-'$HOME/glm53-tf'}
read -r -a H <<<"$HOSTS"
if [ "${#H[@]}" != "$TP" ]; then
  echo "HOSTS names ${#H[@]} hosts for TP=$TP" >&2
  exit 2
fi
count() { $SSH "${H[$1]}" "docker exec $CONTAINER ps -eo args | grep -c '[t]ensorfold serve'" 2>/dev/null; }

case $cmd in
status)
  for r in "${!H[@]}"; do echo "rank $r ${H[$r]}: $(count "$r") engine process(es)"; done ;;
start)
  label=${1:?start needs a LABEL for the logs}
  shift
  for ((r = TP - 1; r >= 0; r--)); do
    $SSH "${H[$r]}" "docker exec -d $CONTAINER bash -c 'bash /opt/glm53-tf/serve.sh $TP $r /work/rank.env $* \
      > /work/logs/serve-r$r-$label.log 2>&1'"
    sleep 3
  done
  for r in "${!H[@]}"; do
    $SSH "${H[$r]}" "(setsid nohup bash $CHECKOUT/v2/scripts/hostwatch.sh $WORK/logs/hostwatch-$label.log $CONTAINER \
      >/dev/null 2>&1 </dev/null &)"
  done
  t0=$(date +%s)
  for _ in $(seq 1 90); do
    sleep 10
    if $SSH "${H[0]}" "grep -q '^\[tensorfold\] serving ' $WORK/logs/serve-r0-$label.log"; then
      echo "READY after $(($(date +%s) - t0)) s"
      $SSH "${H[0]}" "grep '^\[tensorfold\]' $WORK/logs/serve-r0-$label.log | tail -n 8"
      exit 0
    fi
    for r in "${!H[@]}"; do
      if $SSH "${H[$r]}" "grep -q Traceback $WORK/logs/serve-r$r-$label.log" || [ "$(count "$r")" = 0 ]; then
        echo "FAILED on rank $r"
        for q in "${!H[@]}"; do
          echo "== rank $q"
          $SSH "${H[$q]}" "tail -n 25 $WORK/logs/serve-r$q-$label.log"
        done
        exit 1
      fi
    done
  done
  echo "TIMEOUT: no serving line after 15 minutes"
  exit 1 ;;
stop)
  for r in "${!H[@]}"; do
    $SSH "${H[$r]}" "docker exec $CONTAINER pkill -f 'tensorfold serve'"
    for _ in $(seq 1 30); do [ "$(count "$r")" = 0 ] && break; sleep 2; done
  done
  for r in "${!H[@]}"; do
    m=$($SSH "${H[$r]}" "awk '/MemAvailable/{print int(\$2/1048576)}' /proc/meminfo")
    echo "rank $r ${H[$r]}: $(count "$r") engine process(es), MemAvailable $m GiB"
  done ;;
*)
  echo "unknown command '$cmd': start, stop or status" >&2
  exit 2 ;;
esac
