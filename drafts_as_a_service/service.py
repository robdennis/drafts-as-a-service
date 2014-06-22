# coding=utf-8
from __future__ import unicode_literals

from sideboard.lib import subscribes, notifies, DaemonTask

from drafts_as_a_service import sa, config
from drafts_as_a_service.twitter import DraftBot


bot = None

def _get_or_initalize_bot():
    global bot
    if bot is None:
        bot = DraftBot(**config['twitter'])


def check_for_messages():
    draft_bot = _get_or_initalize_bot()

    for message in draft_bot.client.get_mentions_timeline():
        pass
