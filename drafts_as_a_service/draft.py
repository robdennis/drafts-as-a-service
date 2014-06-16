# coding=utf-8
from __future__ import unicode_literals

from copy import copy, deepcopy
import random

from collections import deque


class DraftError(Exception):
    """
    generic error with the draft
    """


class Pool(object):
    """
    A set of all possible cards that could be randomly selected for the draft
    """
    def __init__(self, cards=None):
        self.cards = copy(list(cards or []))

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
        self.players = copy(list(players or []))
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
        self.player_picks = {
            player: [] for player in self.pod.players
        }

    def distribute(self):
        packs = self.pool.deal_packs(3 * self.pod.num_players)
        assert packs
        for idx in xrange(3):
            for player in self.pod.players:
                unopened = self.pod.player_queues[player]['unopened']
                unopened.append(packs.popleft())

    def open_pack(self, player):
        queues = self.player_queues[player]
        # this isn't a deque because the tests are uglier and
        # I don't expect the performance to actually suffer
        queues['opened'].append(queues['unopened'].pop(0))

    def make_pick(self, player, pick):
        current_pack = self.player_queues[player]['opened'][0]
        selection = current_pack.pop(current_pack.index(pick))
        self.player_picks[player].append({
            'drafted': selection,
            'passed': copy(current_pack)
        })

    def pass_left(self, player):
        return self._pass_pack(player, 1)

    def pass_right(self, player):
        return self._pass_pack(player, -1)

    def _pass_pack(self, player, step):
        player_seat = self.players.index(player)
        next_player = self.players[(player_seat + step) % self.num_players]
        self.player_queues[next_player]['opened'].append(
            self.player_queues[player]['opened'].pop(0)
        )

    def make_pick_and_pass_left(self, player, pick):
        self.make_pick(player, pick)
        self.pass_left(player)

    def make_pick_and_pass_right(self, player, pick):
        self.make_pick(player, pick)
        self.pass_right(player)

    @property
    def num_players(self):
        return self.pod.num_players

    @property
    def players(self):
        return self.pod.players

    @property
    def player_queues(self):
        return self.pod.player_queues
