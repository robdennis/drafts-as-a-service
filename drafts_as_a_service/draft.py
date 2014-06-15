# coding=utf-8
from __future__ import unicode_literals

import copy
import random

from collections import deque
from itertools import cycle


class DraftError(Exception):
    """
    generic error with the draft
    """


class Pool(object):
    """
    A set of all possible cards that could be randomly selected for the draft
    """
    def __init__(self, cards=None):
        self.cards = copy.copy(list(cards or []))

    def deal_packs(self, packs, cards_per_pack=15, randomize=True):
        """
        a naive booster-draft implementation
        """
        if packs * cards_per_pack > len(self.cards):
            raise DraftError('require {} cards ({} x {}), have {}'.format(
                packs * cards_per_pack, packs, cards_per_pack, len(self.cards)
            ))

        if randomize:
            random.shuffle(self.cards)

        return deque([
            self.cards[x:x + cards_per_pack]
            for x in xrange(0, packs * cards_per_pack, cards_per_pack)
        ])


class Pod(object):
    def __init__(self, players=None):
        self.players = copy.copy(list(players or []))
        self.num_players = len(self.players)
        self.player_queues = {
            player: dict(opened=[], unopened=[])
            for player in self.players
        }

    def seat_players(self, players=None, randomize=True):
        players = players or self.players

        if randomize:
            random.shuffle(players)

        return players


class Draft(object):
    def __init__(self, pod, pool):
        self.pod = pod
        self.pool = pool

    def distribute(self):
        packs = self.pool.deal_packs(3 * self.pod.num_players)
        assert packs
        for idx in xrange(3):
            for player in self.pod.players:
                unopened = self.pod.player_queues[player]['unopened']
                unopened.append(packs.popleft())

