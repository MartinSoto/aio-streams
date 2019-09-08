from quart_trio import QuartTrio

app = QuartTrio(__name__)


@app.route('/')
async def hello():
    return 'hello'


app.run()
