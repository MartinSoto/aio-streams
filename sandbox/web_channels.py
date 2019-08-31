import asyncio
import logging
import signal

import aiohttp
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def hello(request: web.Request) -> web.StreamResponse:
    return web.Response(text="Hola mundo!")


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes([web.get('/', hello)])
    return app


async def main(host='0.0.0.0', port=8080):
    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task(loop)
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop, main_task)))

    runner = web.AppRunner(create_app())
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info(f"Server running on {host}:{port}")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


async def shutdown(signal, loop: asyncio.BaseEventLoop,
                   main_task: asyncio.Task):
    logging.info(f"Received exit signal {signal.name}...")

    logging.info("Starting graceful shutdown")
    main_task.cancel()
    await asyncio.gather(main_task, return_exceptions=True)

    outstanding_tasks = [
        t for t in asyncio.all_tasks() if t is not asyncio.current_task()
    ]
    if outstanding_tasks:
        logging.info("Cancelling outstanding tasks")
        for task in outstanding_tasks:
            task.cancel()
        await asyncio.gather(*outstanding_tasks, return_exceptions=True)

    loop.stop()


def start():
    loop = asyncio.get_event_loop()

    try:
        loop.create_task(main())
        loop.run_forever()
    finally:
        logging.info("Successfully shut down service")
        loop.close()


if __name__ == "__main__":
    start()