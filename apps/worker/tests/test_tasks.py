import asyncio

from worker.tasks import echo


def test_echo_returns_message():
    result = asyncio.run(echo({}, "hello"))
    assert result == "hello"
