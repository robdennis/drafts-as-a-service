# coding=utf-8
from __future__ import unicode_literals
import json
import os

import twython
from drafts_as_a_service import sa


__here__ = os.path.dirname(__file__)


class DraftBot(object):
    start_draft_hashtag = 'StartBoosterDrafting'

    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret,
                 user_id, screen_name):
        self.client = self.make_client(app_key=app_key, app_secret=app_secret,
                                       oauth_token=oauth_token,
                                       oauth_token_secret=oauth_token_secret)
        self.user_id = user_id
        self.screen_name = screen_name

    def make_client(self, **kwargs):
        return twython.Twython(**kwargs)

    def process(self, raw_message_to_process):
        message = Message(raw_message_to_process)

        if (message.is_in_reply_to(self.user_id) and
            message.has_hashtag(self.start_draft_hashtag)):
            self._process_start_message(message)

    def get_pool(self, message):
        #TODO: different kinds of pools
        #TODO: sometimes we can fetch an existing pool
        contents = json.load(open(os.path.join(__here__, 'cuesbey.json')))
        return sa.Pool(contents=contents, type='set')


    def _process_start_message(self, message):
        with sa.Session() as session:
            players = sa.Player.bulk_get_or_create(
                session, message.involved - {self.screen_name})
            pool = self.get_pool(message)
            draft = sa.Draft(players=players, pool=pool)
            session.add_all([pool, draft])


class Message(dict):
    def is_in_reply_to(self, id):
        return self.get('in_reply_to_user_id') == id

    @property
    def mentions(self):
        return self.get('entities', {}).get('user_mentions', [])

    @property
    def hashtags(self):
        return self.get('entities', {}).get('hashtags', [])

    def has_hashtag(self, hashtag):
        return hashtag in [tag['text'] for tag in self.hashtags]

    @property
    def tweeter(self):
        return self['user']['screen_name']

    @property
    def tweeter_id(self):
        return self['user']['id']

    @property
    def involved(self):
        return {self.tweeter} | {m['screen_name'] for m in self.mentions}