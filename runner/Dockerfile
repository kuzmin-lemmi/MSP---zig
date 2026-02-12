ARG ZIG_VERSION=0.13.0
FROM debian:bookworm-slim

ARG ZIG_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L "https://ziglang.org/download/${ZIG_VERSION}/zig-linux-x86_64-${ZIG_VERSION}.tar.xz" -o /tmp/zig.tar.xz \
    && mkdir -p /opt/zig \
    && tar -xf /tmp/zig.tar.xz -C /opt/zig --strip-components=1 \
    && rm /tmp/zig.tar.xz

ENV PATH="/opt/zig:${PATH}"

RUN useradd -m -u 1000 zig \
    && mkdir -p /workspace \
    && chown zig:zig /workspace

USER zig
WORKDIR /workspace
