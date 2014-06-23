# coding=utf-8
from __future__ import unicode_literals

def test_sanity(bot, mocked_client):
    """
    did we correctly mock the client?
    """
    assert bot.client is mocked_client



