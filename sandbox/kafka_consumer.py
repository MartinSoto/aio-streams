import asyncio
import logging
import signal
from datetime import datetime

from aiokafka import AIOKafkaConsumer

loop = asyncio.get_event_loop()


async def consume():
    main_task = asyncio.current_task(loop)
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

    def signal_handler(s):
        asyncio.create_task(shutdown(s, loop, main_task))

    for s in signals:
        loop.add_signal_handler(
            s,
            lambda s=s, loop=loop, main_task=main_task: asyncio.create_task(
                shutdown(s, loop, main_task)))
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


async def shutdown(signal, loop: asyncio.AbstractEventLoop,
                   main_task: asyncio.Task):
    logging.info(f"Received exit signal {signal.name}...")

    logging.info("Starting graceful shutdown")
    main_task.cancel()


loop.run_until_complete(consume())
