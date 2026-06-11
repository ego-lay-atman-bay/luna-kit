import time
from contextlib import contextmanager

@contextmanager
def time_it(message: str | None = None):
    tic: float = time.perf_counter()
    try:
        if message:
            print(message)
        yield
    finally:
        toc: float = time.perf_counter()
        print(f"Finished in: {1000*(toc - tic):.3f}ms")
