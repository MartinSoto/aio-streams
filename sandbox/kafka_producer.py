import asyncio
import sys
import warnings

import trio
import trio_asyncio
from aiokafka import AIOKafkaProducer

warnings.filterwarnings("ignore", category=trio.TrioDeprecationWarning)


async def send_one(msg: str) -> None:
    loop = asyncio.get_event_loop()
    producer = AIOKafkaProducer(loop=loop, bootstrap_servers='kafka:9092')
    await producer.start()
    try:
        await producer.send_and_wait("salutations", msg.encode('utf-8'))
    finally:
        await producer.stop()


async def main() -> None:
    msg = ' '.join(sys.argv[1:])
    await trio_asyncio.run_asyncio(send_one, msg)


if __name__ == '__main__':
    trio_asyncio.run(main)
