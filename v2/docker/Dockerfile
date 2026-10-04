# The 2.x serving image: TensorFold (the BIZ release of the engine, pinned by TENSORFOLD_REF) on NVIDIA's
# PyTorch container. Build from the checkout root, where the licences are:
#   docker build -f v2/docker/Dockerfile -t glm53-tf:2.0.0 .
# The engine compiles its CUDA extensions on the GPU host into TORCH_EXTENSIONS_DIR (scripts/build_ext.sh).
ARG BASE_IMAGE=nvcr.io/nvidia/pytorch:26.07-py3
# cc-defer: pinned by tag; the measured image ID was sha256:2140e699… (2026-10-03). Pin by registry digest once
# F5 records `docker image inspect --format '{{index .RepoDigests 0}}'` on the hosts that pass acceptance.
FROM ${BASE_IMAGE}

ARG TENSORFOLD_REPO=https://github.com/Bizuayeu/TensorFold.git
# The one place the engine version is set: a full commit SHA of the fork's release branch (release/2.0.0).
# cc-defer: the published head of release/2.0.0 with the prefill heat wait and its printed lines (2026-10-04); drop
# this note once F5 accepts the image built from it (decode check hashes, prefill, 1M at TP=3).
ARG TENSORFOLD_REF=b44c2f197863f889659874e9be4b8e318768a828
RUN echo "$TENSORFOLD_REF" | grep -Eqx '[0-9a-f]{40}' \
 || { echo "TENSORFOLD_REF must be a full commit SHA, not '$TENSORFOLD_REF'" >&2; exit 1; }

# Beyond the base image, exactly the packages and versions of the measured containers (2026-10-03, identical on
# all three hosts). xgrammar serves structured output: without it the server answered 400 to those requests.
RUN pip install --no-cache-dir --no-deps transformers==5.18.0 xgrammar==0.2.8 huggingface_hub==1.33.0 \
    hf-xet==1.6.0 typer==0.27.2 shellingham==1.5.4 annotated-doc==0.0.5

RUN git clone "$TENSORFOLD_REPO" /opt/tensorfold \
 && git -C /opt/tensorfold checkout --detach "$TENSORFOLD_REF" \
 && test "$(git -C /opt/tensorfold rev-parse HEAD)" = "$TENSORFOLD_REF" \
 && pip install --no-cache-dir --no-deps -e /opt/tensorfold \
 && python3 -c "import tensorfold, xgrammar, transformers.models.glm5_next"

COPY v2/scripts/serve.sh v2/scripts/build_ext.sh /opt/glm53-tf/
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /opt/glm53-tf/
COPY LICENSES /opt/glm53-tf/LICENSES
ENV TORCH_EXTENSIONS_DIR=/work/ext
WORKDIR /work
LABEL glm53.line="2.x" glm53.tensorfold.ref="${TENSORFOLD_REF}"
