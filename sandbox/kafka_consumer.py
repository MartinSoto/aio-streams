import asyncio
import logging
from datetime import datetime

import trio
import trio_asyncio
from aiokafka import AIOKafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


@trio_asyncio.trio2aio
async def consume(send_channel: trio.MemorySendChannel) -> None:
    loop = asyncio.get_event_loop()

    consumer = AIOKafkaConsumer('salutations',
                                loop=loop,
                                bootstrap_servers='kafka:9092',
                                group_id="salutated",
                                auto_offset_reset="earliest")
    logging.info("Starting consumer")
    await consumer.start()
    await consumer.seek_to_beginning()
    try:
        logging.info("Consumer started")
        async for msg in consumer:
            # yapf: disable
            await loop.run_trio(lambda msg=msg: send_channel.send(msg))
            # yapf: enable
    except asyncio.CancelledError:
        pass
    finally:
        logging.info("Stopping consumer")
        await consumer.stop()


async def print_messages(receive_channel: trio.MemoryReceiveChannel) -> None:
    async for msg in receive_channel:
        print("consumed: ", msg.topic, msg.partition, msg.offset, msg.key,
              msg.value, datetime.utcfromtimestamp(msg.timestamp / 1000))


async def main() -> None:
    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(1)
        nursery.start_soon(consume, send_channel)
        nursery.start_soon(print_messages, receive_channel)


if __name__ == '__main__':
    try:
        trio_asyncio.run(main)
    except KeyboardInterrupt:
        pass
