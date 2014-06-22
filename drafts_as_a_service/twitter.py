# coding=utf-8
from __future__ import unicode_literals
import twython


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

    def _process_start_message(self, message):
        pass
        # pod = draft.Pod(message.involved - {self.screen_name})


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