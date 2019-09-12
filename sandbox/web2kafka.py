import asyncio
import logging
import warnings

import quart_trio
import trio
import trio_asyncio
from aiokafka import AIOKafkaProducer
from hypercorn.config import Config
from hypercorn.trio import serve
import quart

warnings.filterwarnings("ignore", category=trio.TrioDeprecationWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = quart_trio.QuartTrio(__name__)
send_channel: trio.abc.SendChannel = None


@app.route('/<salutation>')
async def hello(salutation: str) -> quart.Response:
    await trio.sleep(10.0)
    await send_channel.send(f"I send an S.O.S. to the world: {salutation}")
    logging.info("Writing message")

    response = await quart.make_response(f'S.O.S.: {salutation}')
    response.timeout = None
    return response


@trio_asyncio.trio2aio
async def send_to_kafka(receive_channel: trio.abc.ReceiveChannel) -> None:
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
        logging.info("Stopping Kafka client")
        await producer.stop()


async def serve_web():
    config = Config()
    config.use_reloader = True
    config.bind = ["localhost:8080"]
    config.keep_alive_timeout = 3600
    await serve(app, config)


async def main() -> None:
    global send_channel

    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(1)

        nursery.start_soon(serve_web)
        nursery.start_soon(send_to_kafka, receive_channel)


if __name__ == '__main__':
    try:
        trio_asyncio.run(main)
    except KeyboardInterrupt:
        pass
