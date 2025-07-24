import logging
import time
from datetime import datetime, timezone

import grpc
from prometheus_client import start_http_server, Counter
from google.protobuf import timestamp_pb2

import stream_pb2
import stream_pb2_grpc

def now_timestamp():
    return datetime.now(timezone.utc).isoformat()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

MESSAGES_SENT = Counter("client_messages_sent_total", "Total messages sent by client")
MESSAGES_RECEIVED = Counter("client_messages_received_total", "Total messages received by client")
ERRORS = Counter("client_errors_total", "Total client errors")

def generate_messages(duration=60):
    """Generate messages every second for the given duration (seconds)."""
    seq = 0
    start_time = time.time()
    while time.time() - start_time < duration:
        seq += 1
        msg = stream_pb2.StreamMessage(
            timestamp=now_timestamp(),  # We can leave None or use current time
            seq_number=seq,
            payload=f"Hello {seq}"
        )
        logging.info(f"Sending message: seq={seq} payload={msg.payload}")
        MESSAGES_SENT.inc()
        yield msg
        time.sleep(1)

def run():
    # Start Prometheus metrics on port 8001
    start_http_server(8001)

    with grpc.insecure_channel("localhost:50051") as channel:
        stub = stream_pb2_grpc.StreamServiceStub(channel)
        try:
            responses = stub.streamMessages(generate_messages(duration=30))
            for response in responses:
                MESSAGES_RECEIVED.inc()
                logging.info(f"Received from server: seq={response.seq_number} payload={response.payload}")
        except Exception as e:
            ERRORS.inc()
            logging.error(f"Client error: {e}")

if __name__ == "__main__":
    run()

