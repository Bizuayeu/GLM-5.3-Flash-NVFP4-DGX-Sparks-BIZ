#!/bin/bash
# On each host: create_container.sh IMAGE [WORK_DIR]
# The serving container as measured (2026-10-03): host network and IPC, every GPU, the RDMA devices with locked
# memory unlimited, the Hugging Face cache read-only at /hub, and WORK_DIR (default ~/glm53-tf) at /work for the
# rank file (/work/rank.env), the compiled extensions (/work/ext) and the logs (/work/logs). It sleeps until
# serve.sh is started in it. CONTAINER names it (default glm53-tf); HF_HUB is the cache (default ~/.cache/huggingface/hub).
set -eu
if [ $# -lt 1 ]; then
  echo "usage: create_container.sh IMAGE [WORK_DIR]" >&2
  exit 2
fi
image=$1
work=${2:-$HOME/glm53-tf}
hub=${HF_HUB:-$HOME/.cache/huggingface/hub}
if [ ! -e /dev/infiniband ]; then
  echo "/dev/infiniband is missing: NCCL would fall back to sockets" >&2
  exit 1
fi
mkdir -p "$work/ext" "$work/logs"
docker run -d --name "${CONTAINER:-glm53-tf}" --net=host --ipc=host --gpus all --device /dev/infiniband \
  --cap-add IPC_LOCK --ulimit memlock=-1:-1 --shm-size 64m -v "$hub:/hub:ro" -v "$work:/work" -w /work \
  "$image" sleep infinity
