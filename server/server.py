import asyncio
import grpc
from concurrent import futures

import proto.stream_pb2 as stream_pb2
import proto.stream_pb2_grpc as stream_pb2_grpc

class StreamService(stream_pb2_grpc.StreamServiceServicer):
    async def Chat(self, request_iterator, context):
        async for msg in request_iterator:
            yield stream_pb2.ChatMessage(msg=f"Echo: {msg.msg}")

async def serve():
    server = grpc.aio.server()
    stream_pb2_grpc.add_StreamServiceServicer_to_server(StreamService(), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    print("Server started on :50051")
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
