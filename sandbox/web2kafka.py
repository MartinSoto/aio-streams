import asyncio
import logging
import warnings
from typing import Dict, Optional

import quart
import quart_trio
import trio
import trio_asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from hypercorn.config import Config
from hypercorn.trio import serve

warnings.filterwarnings("ignore", category=trio.TrioDeprecationWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = quart_trio.QuartTrio(__name__)

producer_send_channel: trio.abc.SendChannel = None

pending_response_channels: Dict[str, trio.abc.SendChannel] = {}

current_key = 0


def unique_key():
    global current_key
    current_key += 1
    return f'msg{current_key}'


@app.route('/<salutation>')
async def hello(salutation: str) -> quart.Response:
    conn_key = unique_key()

    resp_send_channel, resp_receive_channel = trio.open_memory_channel(1)

    pending_response_channels[conn_key] = resp_send_channel
    try:
        await producer_send_channel.send(
            (conn_key, f"I send an S.O.S. to the world: {salutation}"))

        resp_text: Optional[str] = None
        with trio.move_on_after(15):
            resp_text = await resp_receive_channel.receive()
    finally:
        del pending_response_channels[conn_key]

    if resp_text:
        response = await quart.make_response(f'S.O.S.: {resp_text}')
    else:
        # TODO: Use an HTTP pending code.
        response = await quart.make_response(f'No response on time', 202)

    response.timeout = None
    return response


async def serve_web():
    config = Config()
    config.use_reloader = True
    config.bind = ["localhost:8080"]
    config.keep_alive_timeout = 3600
    await serve(app, config)


@trio_asyncio.trio2aio
async def send_to_kafka(receive_channel: trio.abc.ReceiveChannel) -> None:
    loop = asyncio.get_event_loop()

    producer = AIOKafkaProducer(loop=loop, bootstrap_servers='kafka:9092')
    await producer.start()
    try:
        # TODO: Use iteration to read from channel.
        while True:
            key, msg = await loop.run_trio(receive_channel.receive)
            await producer.send_and_wait("salutation-requests",
                                         key=key.encode('utf-8'),
                                         value=msg.encode('utf-8'))
    except trio.EndOfChannel:
        pass
    finally:
        logging.info("Stopping Kafka client")
        await producer.stop()


@trio_asyncio.trio2aio
async def consume_from_kafka(send_channel: trio.MemorySendChannel) -> None:
    loop = asyncio.get_event_loop()

    consumer = AIOKafkaConsumer('salutations',
                                loop=loop,
                                bootstrap_servers='kafka:9092',
                                group_id="salutated",
                                auto_offset_reset="earliest")
    logging.info("Starting consumer")
    await consumer.start()
    try:
        logging.info("Consumer started")
        async for msg in consumer:
            if msg.key is None:
                continue
            await loop.run_trio(lambda msg=msg: send_channel.send(
                (msg.key.decode('utf-8'), msg.value.decode('utf-8'))))
    except asyncio.CancelledError:
        pass
    finally:
        logging.info("Stopping consumer")
        await consumer.stop()


async def dispatch_responses(receive_channel: trio.MemoryReceiveChannel
                             ) -> None:
    async for key, msg in receive_channel:
        if key in pending_response_channels:
            await pending_response_channels[key].send(msg)
        else:
            logging.warning(f"Missed response for key {key}")


async def main() -> None:
    global producer_send_channel

    async with trio.open_nursery() as nursery:
        producer_send_channel, producer_receive_channel = trio.open_memory_channel(
            1)
        consumer_send_channel, consumer_receive_channel = trio.open_memory_channel(
            1)

        nursery.start_soon(serve_web)
        nursery.start_soon(send_to_kafka, producer_receive_channel)
        nursery.start_soon(consume_from_kafka, consumer_send_channel)
        nursery.start_soon(dispatch_responses, consumer_receive_channel)


if __name__ == '__main__':
    try:
        trio_asyncio.run(main)
    except KeyboardInterrupt:
        pass
