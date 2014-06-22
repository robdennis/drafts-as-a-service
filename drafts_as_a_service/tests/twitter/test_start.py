# coding=utf-8
from __future__ import unicode_literals

import mock

def test_sanity(bot, mocked_client):
    """
    did we correctly mock the client?
    """
    assert bot.client is mocked_client


@mock.patch('drafts_as_a_service.draft.Pod')
def test_new_draft_created_from_message(mock_pod, bot, start_message,
                                        mocked_pool):
    bot.process(start_message)
    mock_pod.assert_called_once_with({'cuesbey', 'EliCourtwright'})


