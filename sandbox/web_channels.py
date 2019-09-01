import asyncio
import itertools
import logging
import signal

import aiochan as ac
import aiohttp
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


async def salutate_the_world(in_chan):
    salutations = [
        "Hello, world!", "Hallo, Welt!", "Hola Mundo", "Salut Monde !",
        "Ciao mondo!"
    ]
    for i in itertools.count():
        out_chan: ac.Chan = await in_chan.get()
        if out_chan is None:
            break

        await out_chan.put(salutations[i % len(salutations)])


async def hello(request: web.Request) -> web.StreamResponse:
    salutate_chan: ac.Chan = request.app['salutate_chan']
    salutation_chan = ac.Chan()
    await salutate_chan.put(salutation_chan)
    return web.Response(text=await salutation_chan.get())


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

    salutate_chan = ac.Chan()
    salutate_task = ac.go(salutate_the_world(salutate_chan))

    app = create_app()
    app['salutate_chan'] = salutate_chan

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
        salutate_chan.close()
        await asyncio.gather(salutate_task)
        await terminate_outstanding_tasks()


async def terminate_outstanding_tasks():
    outstanding_tasks = [
        t for t in asyncio.all_tasks() if t is not asyncio.current_task()
    ]
    if not outstanding_tasks:
        return

    logging.info(f"Cancelling {len(outstanding_tasks)} outstanding task(s)")
    for task in outstanding_tasks:
        task.cancel()
    await asyncio.gather(*outstanding_tasks, return_exceptions=True)


async def shutdown(signal, loop: asyncio.BaseEventLoop,
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
