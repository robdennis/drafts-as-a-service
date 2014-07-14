# coding=utf-8
from __future__ import unicode_literals

import mock
import pytest
from drafts_as_a_service import sa


def test_sanity(bot, mocked_client):
    """
    did we correctly mock the client?
    """
    assert bot.client is mocked_client


@mock.patch('drafts_as_a_service.twitter.DraftBot._process_start_message')
def test_message_is_a_start_message(mock_process_start, bot,
                                    raw_start_message,
                                    start_message):
    """
    do we know when something is start message?
    """
    assert not mock_process_start.called
    bot.process(start_message)
    mock_process_start.assert_called_once_with(start_message)


class TestSettingUpDraft(object):
    """
    Tests that we set up the draft correctly
    """

    def test_sanity(self, bot, start_message):
        with sa.Session() as session:
            assert session.query(sa.Player).count() == 0
            assert session.query(sa.Draft).count() == 0
        bot._process_start_message(start_message)
        with sa.Session() as session:
            assert session.query(sa.Player).count() == 2
            assert session.query(sa.Draft).count() == 1