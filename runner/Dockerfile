ARG ZIG_VERSION=0.13.0
FROM ziglang/zig:${ZIG_VERSION}

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 zig && \
    mkdir -p /workspace && \
    chown zig:zig /workspace

USER zig
WORKDIR /workspace
