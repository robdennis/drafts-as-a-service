# coding=utf-8
from __future__ import unicode_literals

import mock
import pytest

from drafts_as_a_service import sa


@pytest.mark.usefixtures('init_db')
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
        with pytest.raises(sa.DraftError):
            pool.deal_packs(card_count / 2 + 1, 2)


class TestSeating(object):
    @mock.patch('random.shuffle')
    def test_default_random_seating(self, mock_shuffle, the_draft):
        assert not mock_shuffle.called
        the_draft.seat_players()
        the_draft.distribute()
        assert mock_shuffle.called

    @mock.patch('random.shuffle')
    def test_non_random_seating(self, mock_shuffle, the_draft):
        assert not mock_shuffle.called
        the_draft.seat_players(randomize=False)
        the_draft.distribute()
        assert not mock_shuffle.called

    def test_players_start_with_with_queues(self, the_draft):
        assert all(q == dict(opened=[], unopened=[])
                   for p,q in the_draft.player_queues.iteritems())


class TestDraftSetup(object):
    def test_sanity(self, the_draft, packs):
        # we mocked this out to always deal the same packs
        assert the_draft.pool.deal_packs() == packs
        assert the_draft.pool.deal_packs(123, 'asdf') == packs

    def test_distribute(self, the_draft, packs):
        assert the_draft.player_queues == {
            'player{}'.format(idx): dict(opened=[], unopened=[])
            for idx in xrange(8)
        }
        the_draft.distribute()
        # this works thanks to the mocking we've set out
        expected = {
            'player{}'.format(idx): {
                'opened': [],
                'unopened': [packs[0 + idx],
                             packs[8 + idx],
                             packs[16 + idx]],
            }
            for idx in xrange(8)
        }
        assert the_draft.player_queues == expected

    def test_open(self, the_draft):
        the_draft.distribute()
        assert all(len(queue['opened']) == 0 and len(queue['unopened']) == 3
                   for queue in the_draft.player_queues.itervalues())

        [the_draft.open_pack(player) for player in the_draft.player_order]

        assert all(len(queue['opened']) == 1 and len(queue['unopened']) == 2
                   for queue in the_draft.player_queues.itervalues())


class TestDraftPicks(object):
    @pytest.fixture
    def pass_right_pack_order(self):
        """
        if you're in seat 0, your first pass pack is from seat 1
        """
        return [0, 1, 2, 3, 4, 5, 6, 7]

    @pytest.fixture
    def pass_left_pack_order(self):
        """
        if you're in seat 0, your first pass pack is from seat 7
        """
        return [0, 7, 6, 5, 4, 3, 2, 1]

    @pytest.fixture
    def started_draft(self, the_draft, draft_session):
        draft_session.add(the_draft)
        draft_session.commit()
        the_draft.distribute()
        [the_draft.open_pack(player) for player in the_draft.player_order]
        draft_session.commit()
        return the_draft

    @pytest.fixture
    def player0_picks(self, started_draft, player0):

        return lambda: started_draft.player_picks[player0.handle]

    @pytest.fixture
    def player0_queues(self, started_draft, player0):
        return lambda: started_draft.player_queues[player0.handle]

    @pytest.fixture
    def some_pick(self, player0_queues, packs, started_draft):
        assert all(started_draft.player_queues[name]['opened']
                   for name in started_draft.player_order)
        assert started_draft.player_order == [
            'player{}'.format(n) for n in xrange(8)
        ]
        # we know this based on the mocking and the pack distribution
        # we asserted earlier
        assert player0_queues()['opened'][0] == packs[0]
        assert player0_queues()['opened'][0][0] == 'Card 0'
        return 'Card 0'

    def test_make_pick_and_pass(self, started_draft, player0, player0_picks,
                                player0_queues, some_pick, packs):

        assert len(player0_queues()['opened']) == 1
        assert len(player0_picks()) == 0

        started_draft.make_pick(player0, some_pick)
        # we haven't passed yet
        assert len(player0_queues()['opened']) == 1
        assert len(player0_picks()) == 1
        assert player0_picks()[0] == {
            'drafted': some_pick,
            'passed': packs[0][1:]
        }

        player1_on_deck = started_draft.player_queues['player1']['opened']
        # we're passing to this person in pack 1
        assert len(player1_on_deck) == 1
        started_draft.pass_left(player0)
        assert len(player0_queues()['opened']) == 0
        assert len(player1_on_deck) == 2
        assert player1_on_deck[0] == packs[1]
        assert (player1_on_deck[1] ==
                packs[0][1:] ==
                player0_picks()[0]['passed'])

    def test_wheel_left(self, started_draft, players, player0,
                        player0_queues, player0_picks, packs,
                        pass_left_pack_order, pass_right_pack_order):

        def make_first_picks(player):
            """
            make the first pick for each pack the player has queued
            """
            name = player.handle
            on_deck = started_draft.player_queues[name]['opened']
            for _ in xrange(len(on_deck)):
                started_draft.make_pick_and_pass_left(name, on_deck[0][0])

        # "reverse" order we all the packs are now waiting for you
        for seat in pass_right_pack_order:
            make_first_picks(players[seat])

        assert len(player0_queues()['opened']) == 8
        next_pack = player0_queues()['opened'][0]
        opened_pack = player0_queues()['opened'][-1]
        # since everyone took the first pack we can assert this
        # and we are dealing out packs in a pattern, we can
        # guarantee these
        assert next_pack == packs[7][1:]
        assert opened_pack == packs[0][8:]

        make_first_picks(player0)
        pack_order = pass_left_pack_order + [0]

        assert [p['drafted'] for p in player0_picks()] == [
            packs[p][idx] for idx, p in enumerate(pack_order)
        ]

        assert [len(p['passed']) for p in player0_picks()] == [
            15 - pack - 1 for pack in xrange(9)
        ]

    def test_wheel_right(self, started_draft, players, player0,
                        player0_queues, player0_picks, packs,
                        pass_left_pack_order, pass_right_pack_order):

        def make_first_picks(player):
            """
            make the first pick for each pack the player has queued
            """
            name = player.handle
            on_deck = started_draft.player_queues[name]['opened']
            for _ in xrange(len(on_deck)):
                started_draft.make_pick_and_pass_right(name, on_deck[0][0])

        # "reverse" order we all the packs are now waiting for you
        for seat in pass_left_pack_order:
            make_first_picks(players[seat])

        assert len(player0_queues()['opened']) == 8
        next_pack = player0_queues()['opened'][0]
        opened_pack = player0_queues()['opened'][-1]
        # since everyone took the first pack we can assert this
        # and we are dealing out packs in a pattern, we can
        # guarantee these
        assert next_pack == packs[1][1:]
        assert opened_pack == packs[0][8:]

        make_first_picks(player0)
        pack_order = pass_right_pack_order + [0]

        assert [p['drafted'] for p in player0_picks()] == [
            packs[p][idx] for idx, p in enumerate(pack_order)
        ]

        assert [len(p['passed']) for p in player0_picks()] == [
            15 - pack - 1 for pack in xrange(9)
        ]
