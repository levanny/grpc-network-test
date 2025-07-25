# grpc-network-test

Minimal async bidirectional streaming gRPC example (Python).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r server/requirements.txt
```

## Generate gRPC code

```bash
mkdir gen
touch gen/__init__.py
```
python -m grpc_tools.protoc \
  -I proto \
  --python_out=. \
  --grpc_python_out=. \
  proto/gen/stream.proto
```

This will create `proto/stream_pb2.py` and `proto/stream_pb2_grpc.py`.

## Run server

```bash
python server/server.py
```

## Run client (in another terminal)

```bash
python client/client.py
```

## Docker (optional)

Build:

```bash
docker build . -t grpc-network-test
```

Run:

```bash
docker run --rm -it -p 50051:50051 grpc-network-test
docker run --rm -it --network host grpc-network-test 
```
