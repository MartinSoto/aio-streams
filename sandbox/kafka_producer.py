from aiokafka import AIOKafkaProducer
import asyncio

loop = asyncio.get_event_loop()


async def send_one():
    producer = AIOKafkaProducer(loop=loop, bootstrap_servers='kafka:9092')
    await producer.start()
    try:
        await producer.send_and_wait("salutations", b"Hello, world!")
    finally:
        await producer.stop()


loop.run_until_complete(send_one())
