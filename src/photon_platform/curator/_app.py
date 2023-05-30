"""
run the main app
"""
from .curator import Curator


def run() -> None:
    reply = Curator().run()
    print(reply)
