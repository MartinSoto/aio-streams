from functools import partial

import trio
from hypercorn.config import Config
from hypercorn.trio import serve


async def app(scope, receive, send):
    if scope["type"] != "http":
        raise Exception("Only the HTTP protocol is supported")

    await send({
        'type':
        'http.response.start',
        'status':
        200,
        'headers': [
            (b'content-type', b'text/plain'),
            (b'content-length', b'5'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'hello',
    })


def start():
    config = Config()
    config.bind = ["localhost:8080"]
    trio.run(partial(serve, app, config))


if __name__ == '__main__':
    start()
