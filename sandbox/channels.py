import aiochan as ac
import asyncio

c = ac.Chan()


async def producer(c):
    i = 0
    while True:
        await asyncio.sleep(0.1)  # producing stuff takes time
        i += 1
        still_open = await c.put('product ' + str(i))
        if not still_open:
            await asyncio.sleep(0.5)
            print(
                f'product {i} produced but never delivered, producer goes home now'
            )
            break
        else:
            print(f"product {i} delivered")


async def consumer(c):
    while True:
        product = await c.get()
        if product is not None:
            print('obtained:', product)
        else:
            print('consumer goes home')
            break


async def main():
    c = ac.Chan()
    prod = ac.go(producer(c))
    cons = ac.go(consumer(c))
    await asyncio.sleep(0.6)
    print('It is late, let us call it a day.')
    c.close()
    await asyncio.wait({prod, cons})


ac.run(main())