import asyncio
import grpc
import proto.stream_pb2 as stream_pb2
import proto.stream_pb2_grpc as stream_pb2_grpc

async def generate_messages():
    for i in range(3):
        yield stream_pb2.ChatMessage(msg=f"Hello {i} from client")
        await asyncio.sleep(0.5)

async def run():
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = stream_pb2_grpc.StreamServiceStub(channel)
        async for response in stub.Chat(generate_messages()):
            print("Server:", response.msg)

if __name__ == "__main__":
    asyncio.run(run())
