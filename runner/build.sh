#!/bin/bash
set -e
docker build -t zig-runner:0.13.0 .
echo "Image built: zig-runner:0.13.0"
