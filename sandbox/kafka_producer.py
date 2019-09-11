import asyncio
import sys
import warnings

import trio
import trio_asyncio
from aiokafka import AIOKafkaProducer

warnings.filterwarnings("ignore", category=trio.TrioDeprecationWarning)


@trio_asyncio.trio2aio
async def send(receive_channel: trio.abc.ReceiveChannel) -> None:
    loop = asyncio.get_event_loop()

    producer = AIOKafkaProducer(loop=loop, bootstrap_servers='kafka:9092')
    await producer.start()
    try:
        while True:
            msg = await loop.run_trio(receive_channel.receive)  # type: ignore
            await producer.send_and_wait("salutations", msg.encode('utf-8'))
    except trio.EndOfChannel:
        pass
    finally:
        await producer.stop()


async def produce_messages(send_channel: trio.abc.SendChannel) -> None:
    for msg in sys.argv[1:]:
        print("Producing messaage", msg)
        await send_channel.send(msg)
    await send_channel.aclose()


async def main() -> None:
    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(1)
        nursery.start_soon(produce_messages, send_channel)
        nursery.start_soon(send, receive_channel)


if __name__ == '__main__':
    try:
        trio_asyncio.run(main)
    except KeyboardInterrupt:
        pass
