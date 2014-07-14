# coding=utf-8
from __future__ import unicode_literals
import json
import os
from os.path import join

import mock
import pytest

from drafts_as_a_service import config
from drafts_as_a_service.twitter import DraftBot, Message

__here__ = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope='session')
def raw_start_message():
    """
    a "start message" tweet
    """
    with open(join(__here__, 'start_drafting.json')) as start:
        return json.load(start)


@pytest.fixture(scope='session')
def start_message(raw_start_message):
    """
    a "start message" tweet that's been processed
    """
    return Message(raw_start_message)


@pytest.fixture
def mocked_client():
    """
    The mock object that replaces the Twitter client
    """
    return mock.Mock()

@pytest.fixture
def bot(request, mocked_client, mocked_pool):
    """
    An initialized draft bot with a mocked client
    """
    patcher = mock.patch.object(DraftBot, 'make_client',
                                return_value=mocked_client)
    patcher.start()
    request.addfinalizer(patcher.stop)
    return DraftBot(**config['twitter'])