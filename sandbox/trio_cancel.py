import trio


async def main():
    print("starting...")
    with trio.move_on_after(1):
        try:
            with trio.move_on_after(2):
                await trio.sleep(5)
                print("sleep finished without error")
            print("move_on_after(5) finished without error")
        finally:
            print("Cleaning up")
            with trio.move_on_after(2) as cleanup_scope:
                cleanup_scope.shield = True
                await trio.sleep(1.5)
                print("Thoroughly cleaned up")
            if cleanup_scope.cancelled_caught:
                print("Thorough cleaning interrupted!")
    print("move_on_after(10) finished without error")


def start() -> None:
    trio.run(main)


if __name__ == '__main__':
    start()
