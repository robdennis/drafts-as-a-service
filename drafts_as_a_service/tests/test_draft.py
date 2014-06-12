# coding=utf-8
import pytest

from drafts_as_a_service import draft

@pytest.fixture
def card_count():
    return 360


@pytest.fixture
def cards(card_count):
    return ['Card {}'.format(c) for c in xrange(card_count)]


class TestPool(object):
    @pytest.fixture
    def pool(self, cards):
        return draft.Pool(cards)

    @pytest.mark.parametrize('packs, num_per_pack', [
        (1, 1),
        (2, 2),
        (8, 15),
        (24, 15),
    ])
    def test_deal(self, pool, packs, num_per_pack):
        dealt = pool.deal_packs(packs, num_per_pack)

        assert len(dealt) == packs
        assert all(len(pack) == num_per_pack for pack in dealt)

    def test_over_deal(self, pool, card_count):
        with pytest.raises(draft.DraftError):
            pool.deal_packs(card_count / 2 + 1, 2)

