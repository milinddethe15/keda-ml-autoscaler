#!/bin/bash

python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    externalscaler.proto

# No need to modify imports - keep them as absolute imports
