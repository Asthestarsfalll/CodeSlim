import os
from contextlib import contextmanager


@contextmanager
def cd(target):
    prev = os.getcwd()
    os.chdir(os.path.expanduser(target))
    try:
        yield
    finally:
        os.chdir(prev)
