# coding=utf-8
import copy

import pytest

from drafts_as_a_service import draft


@pytest.fixture
def player_count():
    return 8


@pytest.fixture
def players(player_count):
    return ['@player{}'.format(c) for c in xrange(player_count)]


@pytest.fixture
def player0(players):
    return players[0]


@pytest.fixture
def pod(players):
    return draft.Pod(players)


@pytest.fixture
def the_draft(pod, mocked_pool):
    return draft.Draft(pod, mocked_pool)


@pytest.fixture
def card_count():
    return 360


@pytest.fixture
def cards(card_count):
    return ['Card {}'.format(c) for c in xrange(card_count)]


@pytest.fixture
def pool(cards):
    return draft.Pool(cards)


@pytest.fixture
def mocked_pool(pool, packs, monkeypatch):
    def return_expected_packs(*args, **kwargs):
        return copy.deepcopy(packs)
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
