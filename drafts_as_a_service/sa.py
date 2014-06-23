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
from sqlalchemy.ext.mutable import Mutable

from drafts_as_a_service import config
from sideboard.lib.sa import declarative_base, SessionManager, UUID, JSON


class DraftError(Exception):
    """
    generic error with the draft
    """


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()


class MutableList(Mutable, list):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect list set events and emit change events."

        list.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect list del events and emit change events."

        list.__delitem__(self, key)
        self.changed()


@declarative_base
class Base(object):
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)


player_to_draft = Table(
    'player_to_draft', Base.metadata,
    Column('player_id', UUID(), ForeignKey('player.id')),
    Column('draft_id', UUID(), ForeignKey('draft.id')),
)


class Player(Base):
    """
    A player (currently a twitter user) who drafts and as a member
    of a Pool
    """
    handle = Column(String(), nullable=False, unique=True)
    drafts = relationship('Draft', secondary='player_to_draft',
                          backref='players')


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
    default_cards_per_pack = 15

    def deal_packs(self, packs, cards_per_pack=None, randomize=True):
        """
        a naive booster-draft implementation
        """
        if cards_per_pack is None:
            cards_per_pack = self.default_cards_per_pack

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
    pool_id = Column(UUID(), ForeignKey('pool.id'), nullable=False)
    pool = relationship("Pool", backref='drafts')
    player_picks = Column(MutableDict.as_mutable(JSON), default={},
                          server_default='{}', nullable=False)
    player_order = Column(MutableList.as_mutable(JSON), default=[], server_default='[]',
                          nullable=False)
    player_queues = Column(MutableDict.as_mutable(JSON), default={},
                           server_default='{}', nullable=False)
    # performance enhancement for not having to query the foreign keys
    num_players = Column(Integer(), nullable=False)

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.seat_players(randomize=False)

    def distribute(self):
        """
        Hand out all the packs
        """
        packs = self.pool.deal_packs(3 * self.num_players)

        assert packs
        for idx in xrange(3):
            for player in self.player_order:
                self.player_queues[player]['unopened'].\
                    append(packs.popleft())
        # http://docs.sqlalchemy.org/en/rel_0_8/orm/extensions/mutable.html
        # the mutable dict approach doesn't work for sub-dictionaries
        self.player_queues.changed()

    def open_pack(self, player):
        queues = self.player_queues[self._get_name(player)]
        # this isn't a deque because the tests are uglier and
        # I don't expect the performance to actually suffer
        queues['opened'].append(queues['unopened'].pop(0))
        self.player_queues.changed()

    def make_pick(self, player, pick):
        name = self._get_name(player)
        current_pack = self.player_queues[name]['opened'][0]
        selection = current_pack.pop(current_pack.index(pick))
        self.player_picks[name].append({
            'drafted': selection,
            'passed': copy(current_pack)
        })
        self.player_queues.changed()
        self.player_picks.changed()

    def pass_left(self, player):
        return self._pass_pack(player, 1)

    def pass_right(self, player):
        return self._pass_pack(player, -1)

    def _pass_pack(self, player, step):
        name = self._get_name(player)
        player_seat = self.player_order.index(name)
        next_player = self.player_order[(player_seat + step) %
                                        self.num_players]
        self.player_queues[next_player]['opened'].append(
            self.player_queues[name]['opened'].pop(0)
        )
        self.player_queues.changed()

    def make_pick_and_pass_left(self, player, pick):
        self.make_pick(player, pick)
        self.pass_left(player)

    def make_pick_and_pass_right(self, player, pick):
        self.make_pick(player, pick)
        self.pass_right(player)

    def _get_name(self, player):
        """
        Utility method for getting the name of the player
        """
        if isinstance(player, basestring):
            return player
        else:
            return player.handle

    def randomize_seating(self):
        random.shuffle(self.player_order)

    def seat_players(self, randomize=True):
        self.num_players = len(self.players)
        self.player_queues = {
            player.handle: dict(opened=[], unopened=[])
            for player in self.players
        }
        self.player_picks = {
            player.handle: [] for player in self.players
        }

        self.player_order = [p.handle for p in self.players]

        if randomize:
            self.randomize_seating()

        self.player_queues.changed()
        self.player_picks.changed()
        return self.player_order

    def __setattr__(self, key, value):
        Base.__setattr__(self, key, value)
        if key == 'players':
            self.seat_players()


class Message(Base):
    """
    A twitter message directed to us
    """

    twitter_id = Column(Integer(), nullable=False, unique=True)
    content = Column(JSON(), nullable=False)


class Session(SessionManager):
    engine = sqlalchemy.create_engine(config['sqlalchemy.url'])
