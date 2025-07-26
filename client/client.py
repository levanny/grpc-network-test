import logging
import random
import time
import signal
import threading
from datetime import datetime, timezone
import os
import multiprocessing as mp

import grpc
from prometheus_client import start_http_server, Counter

from gen import stream_pb2, stream_pb2_grpc

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

STREAM_START = 30
STREAM_END = 300
BREAK_TIME_SECONDS = 10

SERVER_ADDR = os.getenv("SERVER_ADDR", "localhost:50051")

# Metrics
MESSAGES_SENT = Counter("client_messages_sent_total", "Total messages sent by client")
MESSAGES_RECEIVED = Counter("client_messages_received_total", "Total messages received by client")
ERRORS = Counter("client_errors_total", "Total client errors")

STOP = threading.Event()


def handle_signal(signum, frame):
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    STOP.set()


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def now_timestamp():
    return datetime.now(timezone.utc).isoformat()


def generate_messages(duration: int):
    """Generate messages every second for the given duration (seconds)."""
    seq = 0
    end_at = time.time() + duration

    while not STOP.is_set() and time.time() < end_at:
        seq += 1
        msg = stream_pb2.StreamMessage(
            timestamp=now_timestamp(),
            seq_number=seq,
            payload=f"Hello {seq}",
            payload_bytes=os.urandom(1024),
        )
        logging.info(
            f"Sending message: seq={seq} payload={msg.payload} "
            f"bytes_sample={(msg.payload_bytes[:10].hex() if msg.payload_bytes else 'None')} "
            f"(length={len(msg.payload_bytes) if msg.payload_bytes else 0})"
        )
        MESSAGES_SENT.inc()
        yield msg


def run(metrics_port: int = 8001):
    # Start Prometheus metrics on a (possibly unique) port
    start_http_server(metrics_port)

    while not STOP.is_set():
        channel = None
        stub = None
        responses = None

        try:
            # Open a fresh connection
            channel = grpc.insecure_channel(SERVER_ADDR)
            stub = stream_pb2_grpc.StreamServiceStub(channel)

            duration = random.randint(STREAM_START, STREAM_END)
            logging.info(f"Starting new message stream for {duration} seconds")

            responses = stub.streamMessages(generate_messages(duration))

            for response in responses:
                MESSAGES_RECEIVED.inc()
                logging.info(
                    f"Received from server: seq={response.seq_number} payload={response.payload} "
                    f"bytes_sample={(response.payload_bytes[:10].hex() if response.payload_bytes else 'None')} "
                    f"(length={len(response.payload_bytes) if response.payload_bytes else 0})"
                )

        except grpc.RpcError as e:
            if e.code() != grpc.StatusCode.CANCELLED:
                ERRORS.inc()
                logging.error(f"Client error: {e}")
        except Exception:
            ERRORS.inc()
            logging.exception("Client Error")
        finally:
            # Explicitly cancel the stream & close the channel
            if responses is not None:
                try:
                    responses.cancel()
                except Exception:
                    pass
            if channel is not None:
                try:
                    channel.close()
                except Exception:
                    pass

            if STOP.is_set():
                break

            logging.info(f"Closed connection. Waiting {BREAK_TIME_SECONDS} seconds before reopening...")
            for _ in range(BREAK_TIME_SECONDS):
                if STOP.is_set():
                    break
                time.sleep(1)

    logging.info("Client shutdown complete!")


if __name__ == "__main__":
    # Spawn 5 parallel clients, each with its own Prometheus port to avoid clashes
    procs = []
    base_port = 8001
    for i in range(5):
        p = mp.Process(target=run, kwargs={"metrics_port": base_port + i})
        p.start()
        procs.append(p)

    for p in procs:
        p.join()
