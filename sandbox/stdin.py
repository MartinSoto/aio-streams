import asyncio
import os
import fcntl


async def tick():
    while True:
        print("Tick")
        await asyncio.sleep(1)


def read_stdin():
    print("Data:", os.read(0, 1024 * 4))


def start():
    loop = asyncio.get_event_loop()
    loop.create_task(tick())

    flags = fcntl.fcntl(0, fcntl.F_GETFL)
    fcntl.fcntl(0, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    loop.add_reader(0, read_stdin)

    loop.run_forever()


if __name__ == '__main__':
    start()
