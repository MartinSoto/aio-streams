import aiohttp
from aiohttp import web


async def hello(request: web.Request) -> web.StreamResponse:
    return web.Response(text="Hello, world")


async def websocket_handler(request: web.Request) -> web.StreamResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            print(f"Message received: {msg.type}")
            if msg.data == 'close':
                await ws.close()
            else:
                await ws.send_str(msg.data + '/answer')
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())

    print('websocket connection closed')

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes([web.get('/', hello), web.get('/ws', websocket_handler)])
    return app


if __name__ == '__main__':
    web.run_app(create_app())