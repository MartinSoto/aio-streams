import quart_trio
import trio
from hypercorn.config import Config
from hypercorn.trio import serve

app = quart_trio.QuartTrio(__name__)


@app.route('/')
async def hello():
    return 'Hola!'


def start():
    config = Config()
    config.bind = ["localhost:8080"]
    trio.run(serve, app, config)


if __name__ == '__main__':
    start()
