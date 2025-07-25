import logging
import random
import time
import signal
import threading
from datetime import datetime, timezone

import grpc
from prometheus_client import start_http_server, Gauge

import stream_pb2
import stream_pb2_grpc

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

#Metrics
MESSAGES_SENT = Gauge("client_messages_sent_total", "Total messages sent by client")
MESSAGES_RECEIVED = Gauge("client_messages_received_total", "Total messages received by client")
ERRORS = Gauge("client_errors_total", "Total client errors")

STOP = threading.Event()

def handle_signal(signum,frame):
    logging.info(f"Received signal {signum}, shutting down grafecully...")
    STOP.set()

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def now_timestamp():
    return datetime.now(timezone.utc).isoformat()

global duration

def generate_messages(duration: int):
    """Generate messages every second for the given duration (seconds)."""
    seq = 0
    end_at = time.time() + duration
    duration = random.randint(1, 10)
    start_time = time.time()
    while not STOP.is_set() and time.time() <end_at:
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
        break_time = 3
        responses = None
        stream_start = 30
        stream_end = 300
        try:
            while not STOP.is_set():
                duration = random.randint(stream_start, stream_end)
                logging.info(f"Starting new message stream for {duration} seconds")
                responses = stub.streamMessages(generate_messages(duration))

                for response in responses:
                    MESSAGES_RECEIVED.inc()
                    logging.info(f"Received from server: seq={response.seq_number} payload={response.payload}")

                if STOP.is_set():
                    break

                logging.info(f"Pausing {break_time} seconds before next stream... ")
                for _ in range(break_time * 10):
                    if STOP.is_set():
                        break
                    time.sleep(0.1)

        except grpc.RpcError as e:
            if e.code() != grpc.StatusCode.CANCELLED:
                ERRORS.inc()
                logging.error(f"Client error: {e}")
        except Exception:
            ERRORS.inc()
            logging.exception("Client Error")
        finally:
            if responses is not None:
                try:
                    responses.cancel()
                except Exception:
                    pass
            logging.info("Client shutdown complete!")

if __name__ == "__main__":
    run()

