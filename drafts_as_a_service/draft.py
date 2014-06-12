# coding=utf-8
from __future__ import unicode_literals

import copy
import random


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

    def deal_packs(self, packs, cards_per_pack=15):
        """
        a naive booster-draft implementation
        """
        if packs * cards_per_pack > len(self.cards):
            raise DraftError('require {} cards ({} x {}), have {}'.format(
                packs * cards_per_pack, packs, cards_per_pack, len(self.cards)
            ))
        random.shuffle(self.cards)

        return [
            self.cards[x:x + cards_per_pack]
            for x in xrange(0, packs * cards_per_pack, cards_per_pack)
        ]