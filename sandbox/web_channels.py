import asyncio
import itertools
import logging
import signal

import aiochan as ac
import aiohttp
import aiokafka
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def consume(out_chan: ac.Chan) -> None:
    loop = asyncio.get_running_loop()
    consumer = aiokafka.AIOKafkaConsumer('salutations',
                                         loop=loop,
                                         bootstrap_servers='kafka:9092',
                                         group_id="salutated",
                                         auto_offset_reset="earliest")
    logging.info("Starting consumer")
    await consumer.start()
    try:
        logging.info("Consumer started")
        async for msg in consumer:
            out_chan.put((msg.key, msg.value))
    except asyncio.CancelledError:
        logging.info("Consumer cancelled")
    finally:
        logging.info("Stopping consumer")
        await consumer.stop()


async def kafka_gateway(request_chan: ac.Chan) -> None:
    loop = asyncio.get_running_loop()
    producer = aiokafka.AIOKafkaProducer(loop=loop,
                                         bootstrap_servers='kafka:9092')
    await producer.start()

    response_chan = ac.Chan()
    consumer_task = ac.go(consume(response_chan))

    pending_responses = {}

    try:
        key_seq = 1
        while True:
            result, chan = await ac.select(request_chan, response_chan)
            if result is None:
                break

            key: str
            msg: str
            resp_chan: ac.Chan
            if chan is request_chan:
                msg, resp_chan = result
                key = f'msg{key_seq}'
                key_seq += 1
                logging.info(f"Requesting salutation {key}, {msg}")
                await producer.send_and_wait("salutation-requests",
                                             key=key.encode('utf8'),
                                             value=msg)
                logging.info("Message sent")
                await producer.flush()
                pending_responses[key] = resp_chan
            elif chan is response_chan:
                key_bytes, msg_bytes = result
                key, msg = key_bytes.decode('utf8'), msg_bytes.decode('utf8')
                if key in pending_responses:
                    resp_chan = pending_responses[key]
                    del pending_responses[key]
                    await resp_chan.put(msg)
                else:
                    logging.error(f"Message key '{key}' not awaiting response")
    except asyncio.CancelledError:
        logging.info("Gateway cancelled")
    finally:
        consumer_task.cancel()
        await asyncio.gather(consumer_task)

        logging.info("Stopping producer")
        await producer.stop()


async def kafka_handler(request: web.Request) -> web.StreamResponse:
    gateway_chan: ac.Chan = request.app['gateway_chan']
    response_chan = ac.Chan()
    logging.info("Kafka request received")
    await gateway_chan.put(
        ("no message for the moment".encode('utf8'), response_chan))
    return web.Response(text=await response_chan.get())


async def salutate_the_world(in_chan: ac.Chan) -> None:
    salutations = [
        "Hello, world!", "Hallo, Welt!", "Hola Mundo", "Salut Monde !",
        "Ciao mondo!"
    ]
    for i in itertools.count():
        out_chan: ac.Chan = await in_chan.get()
        if out_chan is None:
            break

        # It takes some consideration to salutate properly...
        await asyncio.sleep(0.2)
        await out_chan.put(salutations[i % len(salutations)])


async def salutation_handler(request: web.Request) -> web.StreamResponse:
    salutate_chan: ac.Chan = request.app['salutate_chan']
    salutation_chan = ac.Chan()
    await salutate_chan.put(salutation_chan)
    return web.Response(text=await salutation_chan.get())


MSG_TYPE_NAMES = {
    aiohttp.WSMsgType.BINARY: "BINARY",
    aiohttp.WSMsgType.CLOSE: "CLOSE",
    aiohttp.WSMsgType.CLOSED: "CLOSED",
    aiohttp.WSMsgType.CLOSING: "CLOSING",
    aiohttp.WSMsgType.CONTINUATION: "CONTINUATION",
    aiohttp.WSMsgType.ERROR: "ERROR",
    aiohttp.WSMsgType.PING: "PING",
    aiohttp.WSMsgType.PONG: "PONG",
    aiohttp.WSMsgType.TEXT: "TEXT",
}


async def websocket_send_from_chan(chan: ac.Chan,
                                   ws_response: web.WebSocketResponse):
    async for msg in chan:
        print(msg)
        await ws_response.send_str(msg)


async def websocket_handler(request: web.Request) -> web.StreamResponse:
    salutate_chan: ac.Chan = request.app['salutate_chan']
    salutation_chan = ac.Chan()

    response = web.WebSocketResponse()
    await response.prepare(request)

    ac.go(websocket_send_from_chan(salutation_chan, response))

    while True:
        msg = await response.receive()

        if msg.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
            break

        print(f"Message received: {MSG_TYPE_NAMES[msg.type]}")
        await salutate_chan.put(salutation_chan)

    if msg.type == aiohttp.WSMsgType.ERROR:
        print('ws connection closed with exception %s' % response.exception())

    print(f"Connection ended with message {MSG_TYPE_NAMES[msg.type]}")

    salutation_chan.close()

    return response


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get('/', salutation_handler),
        web.get('/kafka', kafka_handler),
        web.get('/ws', websocket_handler)
    ])
    return app


async def main(host: str = '0.0.0.0', port: int = 8080) -> None:
    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task(loop)
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

    def signal_handler(s):
        asyncio.create_task(shutdown(s, loop, main_task))

    for s in signals:
        loop.add_signal_handler(
            s,
            lambda s=s, loop=loop, main_task=main_task: asyncio.create_task(
                shutdown(s, loop, main_task)))

    app = create_app()

    salutate_chan = ac.Chan()
    salutate_task = ac.go(salutate_the_world(salutate_chan))
    app['salutate_chan'] = salutate_chan

    gateway_chan = ac.Chan()
    gateway_task = ac.go(kafka_gateway(gateway_chan))
    app['gateway_chan'] = gateway_chan

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info(f"Server running on {host}:{port}")

    # Wait forever. Cancelling this task will finish the application.
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()

        gateway_task.cancel()
        await asyncio.gather(gateway_task)

        salutate_chan.close()
        await asyncio.gather(salutate_task)

        await terminate_outstanding_tasks()


async def terminate_outstanding_tasks() -> None:
    outstanding_tasks = [
        t for t in asyncio.all_tasks() if t is not asyncio.current_task()
    ]
    if not outstanding_tasks:
        return

    logging.info(f"Cancelling {len(outstanding_tasks)} outstanding task(s)")
    for task in outstanding_tasks:
        task.cancel()
    await asyncio.gather(*outstanding_tasks, return_exceptions=True)


async def shutdown(signal, loop: asyncio.AbstractEventLoop,
                   main_task: asyncio.Task):
    logging.info(f"Received exit signal {signal.name}...")

    logging.info("Starting graceful shutdown")
    main_task.cancel()


def start():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    try:
        loop.run_until_complete(main())
    finally:
        logging.info("Successfully shut down service")
        loop.close()


if __name__ == "__main__":
    start()
