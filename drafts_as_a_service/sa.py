# coding=utf-8
from __future__ import unicode_literals
import uuid
import random

from copy import copy, deepcopy
from collections import deque

import sqlalchemy
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import Column, Table, ForeignKey
from sqlalchemy.types import Integer, String

from drafts_as_a_service import config
from sideboard.lib.sa import declarative_base, SessionManager, UUID, JSON


class DraftError(Exception):
    """
    generic error with the draft
    """


@declarative_base
class Base(object):
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)


player_to_pod = Table(
    'player_to_pod', Base.metadata,
    Column('player_id', UUID(), ForeignKey('player.id')),
    Column('pod_id', UUID(), ForeignKey('pod.id')),
)


class Player(Base):
    """
    A player (currently a twitter user) who drafts and as a member
    of a Pool
    """
    handle = Column(String(), nullable=False, unique=True)
    pods = relationship('Pod', secondary='player_to_pod',
                        backref='players')


class Pod(Base):
    """
    A player (currently a twitter user) who drafts and as a member
    of a Pool
    """
    player_order = Column(JSON(), default=[], server_default='[]',
                          nullable=False)
    player_queues = Column(JSON(), default={}, server_default='{}',
                           nullable=False)
    # performance enhancement for not having to query the foreign keys
    num_players = Column(Integer(), nullable=False)

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.seat_players()

    def seat_players(self, randomize=False):
        self.num_players = len(self.players)
        self.player_queues = {
            player.handle: dict(opened=[], unopened=[])
            for player in self.players
        }

        if randomize:
            random.shuffle(self.players)

        return self.players

    def __setattr__(self, key, value):
        Base.__setattr__(self, key, value)
        if key == 'players':
            self.seat_players()


class Pool(Base):
    """
    A set of all possible cards that could be randomly selected for the draft
    Generally either boosters and or a set
    """
    # in practice, "boosters" or "set"
    type = Column(String(), nullable=False)
    # the contents of this pool, the structure of this will
    # depend on the type of pool it it is
    contents = Column(JSON(), nullable=False)

    def deal_packs(self, packs, cards_per_pack=15, randomize=True):
        """
        a naive booster-draft implementation
        """
        if self.type == 'set':
            cards = copy(self.contents)
        else:
            raise NotImplementedError

        if packs * cards_per_pack > len(cards):
            raise DraftError('require {} cards ({} x {}), have {}'.format(
                packs * cards_per_pack, packs, cards_per_pack, len(cards)
            ))

        if randomize:
            random.shuffle(cards)

        return deque([
            cards[x:x + cards_per_pack]
            for x in xrange(0, packs * cards_per_pack, cards_per_pack)
        ])


class Draft(Base):
    """
    A grouping of a Pod and a Pool, engaged in a number of asynchronous
    actions (making selections
    """
    pod_id = Column(UUID(), ForeignKey('pod.id'))
    pod = relationship("Pod", backref=backref('draft', uselist=False))
    pool_id = Column(UUID(), ForeignKey('pool.id'))
    pool = relationship("Pool", backref='drafts')
    player_picks = Column(JSON(), default={}, server_default='{}')

    def distribute(self):
        self.pod.seat_players()
        self.player_picks = {
            player.handle: [] for player in self.pod.players
        }
        packs = self.pool.deal_packs(3 * self.pod.num_players)
        assert packs
        for idx in xrange(3):
            for player in self.pod.players:
                unopened = self.pod.player_queues[player.handle]['unopened']
                unopened.append(packs.popleft())

    def open_pack(self, player):
        queues = self.player_queues[player.handle]
        # this isn't a deque because the tests are uglier and
        # I don't expect the performance to actually suffer
        queues['opened'].append(queues['unopened'].pop(0))

    def make_pick(self, player, pick):
        current_pack = self.player_queues[player.handle]['opened'][0]
        selection = current_pack.pop(current_pack.index(pick))
        self.player_picks[player.handle].append({
            'drafted': selection,
            'passed': copy(current_pack)
        })

    def pass_left(self, player):
        return self._pass_pack(player, 1)

    def pass_right(self, player):
        return self._pass_pack(player, -1)

    def _pass_pack(self, player, step):
        player_seat = self.player_order.index(player.handle)
        next_player = self.player_order[(player_seat + step) %
                                        self.num_players]
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
    def player_order(self):
        return self.pod.player_order

    @property
    def player_queues(self):
        return self.pod.player_queues



class Message(Base):
    """
    A twitter message directed to us
    """

    twitter_id = Column(Integer(), nullable=False, unique=True)
    content = Column(JSON(), nullable=False)


class Session(SessionManager):
    engine = sqlalchemy.create_engine(config['sqlalchemy.url'])
