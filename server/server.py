import logging
import time
from concurrent import futures

import grpc
from prometheus_client import start_http_server, Gauge, Histogram, Counter

from gen import stream_pb2, stream_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Metrics
MESSAGES_RECEIVED = Counter("messages_received_total", "Total messages received")
MESSAGES_SENT = Counter("messages_sent_total", "Total messages sent")
CONNECTIONS_OPEN = Gauge("connections_open", "Currently open streaming connections")
ERRORS = Counter("errors_total", "Total errors")
CONNECTION_DURATION = Histogram("connection_duration_seconds", "Duration of a streaming connection in seconds")


class StreamServiceServicer(stream_pb2_grpc.StreamServiceServicer):
    def streamMessages(self, request_iterator, context):
        """Bidirectional streaming RPC to echo received messages."""
        CONNECTIONS_OPEN.inc()
        start_time = time.time()
        try:
            for msg in request_iterator:
                MESSAGES_RECEIVED.inc()
                logger.info(f"Received message: seq={msg.seq_number} payload={msg.payload}")

                response = stream_pb2.StreamMessage(
                    timestamp=msg.timestamp,
                    seq_number=msg.seq_number,
                    payload=f"Echo: {msg.payload}",
                    payload_bytes=msg.payload_bytes,  # echo the bytes back
                )
                MESSAGES_SENT.inc()
                logger.info(f"Sending message: seq={response.seq_number} payload={response.payload}")

                yield response

        except Exception as e:
            ERRORS.inc()
            logger.error(f"Error in streamMessages: {e}")
            raise
        finally:
            CONNECTIONS_OPEN.dec()
            CONNECTION_DURATION.observe(time.time() - start_time)


def serve():
    """Start gRPC server and Prometheus metrics HTTP server."""
    start_http_server(8000)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    stream_pb2_grpc.add_StreamServiceServicer_to_server(StreamServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("Server started on port 50051, metrics on 8000")

    try:
        while True:
            time.sleep(86400)  # Sleep one day in a loop
    except KeyboardInterrupt:
        logger.info("Server stopping...")
        server.stop(0)


if __name__ == '__main__':
    serve()
