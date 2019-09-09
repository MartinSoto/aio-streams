import asyncio
import logging
from datetime import datetime

import trio_asyncio
from aiokafka import AIOKafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def consume() -> None:
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
            print("consumed: ", msg.topic, msg.partition, msg.offset, msg.key,
                  msg.value, datetime.utcfromtimestamp(msg.timestamp / 1000))
    except asyncio.CancelledError:
        pass
    finally:
        logging.info("Stopping consumer")
        await consumer.stop()


async def main() -> None:
    await trio_asyncio.run_asyncio(consume)


if __name__ == '__main__':
    try:
        trio_asyncio.run(main)
    except KeyboardInterrupt:
        pass
