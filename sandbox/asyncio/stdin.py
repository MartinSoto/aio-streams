import asyncio
import os
import fcntl


def read_cb(loop: asyncio.BaseEventLoop, fd: int, nbytes: int,
            fut: asyncio.Future) -> None:
    fut.set_result(os.read(fd, nbytes))
    loop.remove_reader(fd)


def read(fd: int, nbytes: int) -> asyncio.Future:
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    loop.add_reader(fd, read_cb, loop, fd, nbytes, fut)
    return fut


async def tick() -> None:
    while True:
        print("Tick")
        await asyncio.sleep(1)


async def read_stdin():
    while True:
        data = await read(0, 1024)
        if len(data) == 0:
            break
        print("Data:", data)
    asyncio.get_running_loop().stop()


def start() -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(tick())

    flags = fcntl.fcntl(0, fcntl.F_GETFL)
    fcntl.fcntl(0, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    loop.create_task(read_stdin())

    loop.run_forever()


if __name__ == '__main__':
    start()
