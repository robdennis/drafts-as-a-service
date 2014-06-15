# coding=utf-8
from __future__ import unicode_literals

import copy
import mock
import pytest

from drafts_as_a_service import draft

@pytest.fixture
def card_count():
    return 360


@pytest.fixture
def player_count():
    return 8


@pytest.fixture
def cards(card_count):
    return ['Card {}'.format(c) for c in xrange(card_count)]


@pytest.fixture
def players(player_count):
    return ['@player{}'.format(c) for c in xrange(player_count)]


@pytest.fixture
def pool(cards):
    return draft.Pool(cards)


@pytest.fixture
def mocked_pool(pool, packs, monkeypatch):
    def return_expected_packs(*args, **kwargs):
        return copy.copy(packs)
    monkeypatch.setattr(pool, 'deal_packs', return_expected_packs)
    return pool


@pytest.fixture
def packs(pool, player_count, card_count):
    assert card_count % player_count == 0
    per_pack = card_count / player_count / 3
    packs = pool.deal_packs(player_count * 3, per_pack, randomize=False)
    assert len(packs) == player_count * 3
    assert all(len(pack) == per_pack for pack in packs)
    return packs


@pytest.fixture
def pod(players):
    return draft.Pod(players)


@pytest.fixture
def the_draft(pod, mocked_pool):
    return draft.Draft(pod, mocked_pool)


class TestPool(object):
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


class TestPod(object):
    @mock.patch('random.shuffle')
    def test_default_random_seating(self, mock_shuffle, pod):
        assert not mock_shuffle.called
        pod.seat_players()
        assert mock_shuffle.called

    @mock.patch('random.shuffle')
    def test_non_random_seating(self, mock_shuffle, pod):
        assert not mock_shuffle.called
        pod.seat_players(randomize=False)
        assert not mock_shuffle.called

    def test_players_start_with_with_queues(self, pod):
        assert all(q == dict(opened=[], unopened=[])
                   for p,q in pod.player_queues.iteritems())


class TestDraft(object):
    def test_sanity(self, the_draft, packs):
        # we mocked this out to always deal the same packs
        assert the_draft.pool.deal_packs() == packs
        assert the_draft.pool.deal_packs(123, 'asdf') == packs

    def test_distribute(self, the_draft, packs):
        the_draft.distribute()

        # this works thanks to the mocking we've set out
        expected = {
            '@player{}'.format(idx): {
                'opened': [],
                'unopened': [packs[0 + idx],
                             packs[8 + idx],
                             packs[16 + idx]],
            }
            for idx in xrange(8)
        }

        assert the_draft.pod.player_queues == expected