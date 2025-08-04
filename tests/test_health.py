import pytest
from aiogram.types import Message
from src.bot import cmd_health

class DummyMessage:
    def __init__(self):
        self.text = "/health"
        self.answer_called = False
        self.answer_text = None
    async def answer(self, text):
        self.answer_called = True
        self.answer_text = text

@pytest.mark.asyncio
async def test_cmd_health():
    msg = DummyMessage()
    await cmd_health(msg)
    assert msg.answer_called
    assert "alive" in msg.answer_text 