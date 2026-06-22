FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    ripgrep git curl ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*
RUN adduser --uid 1000 --disabled-password aede
USER aede
WORKDIR /workspace
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sleep", "infinity"]
