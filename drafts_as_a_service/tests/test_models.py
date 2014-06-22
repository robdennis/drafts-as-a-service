# coding=utf-8
from __future__ import unicode_literals
from copy import deepcopy
import pytest

from drafts_as_a_service import sa

pytestmark = pytest.mark.usefixtures('init_db')

@pytest.mark.parametrize('model, kwargs', [
    (sa.Message, dict(twitter_id=1, content={})),
    (sa.Player, dict(handle='test'))
])
def test_create_things(model, kwargs):
    with sa.Session() as session:
        assert session.query(model).count() == 0

    with sa.Session() as session:
        session.add(model(**kwargs))

    with sa.Session() as session:
        assert session.query(model).count() == 1


def test_draft_and_players():
    with sa.Session() as session:
        players = [sa.Player(handle='Player %s' % idx)
                   for idx in xrange(8)]
        draft = sa.Draft(pool=sa.Pool(type='set', contents=[]))
        draft.players = players
        session.add(draft)

    with sa.Session() as session:
        draft = session.query(sa.Draft).one()
        assert len(draft.player_queues) == len(players)
        assert len(draft.players) == len(players)
        assert all(draft in player.drafts
                   for player in session.query(sa.Player).all())

@pytest.mark.parametrize('value', [
    {'test': 'key'},
    {'test': []},
    {'test': {'key1':[], 'key2':[]}},
])
def test_json_column_saving(value):
    with sa.Session() as session:
        msg = sa.Message(twitter_id=1, content=deepcopy(value))
        assert msg.content == deepcopy(value)
        session.add(msg)
        session.commit()
        assert msg.content == deepcopy(value)
        assert session.query(sa.Message).one().content == deepcopy(value)


def test_json_column_after_commit(pool, players):

    def _queue_lengths(queue, length):
        return all(len(the_draft.player_queues[name][queue]) == length
                   for name in the_draft.player_order)

    with sa.Session() as session:
        the_draft = sa.Draft(pool=pool, players=players)
        session.add(the_draft)

        assert the_draft.player_order
        assert len(the_draft.player_picks) == 8
        session.commit()
        assert the_draft.player_order
        assert len(the_draft.player_picks) == 8

        assert _queue_lengths('opened', 0)
        assert _queue_lengths('unopened', 0)
        assert not session.dirty
        the_draft.distribute()
        assert session.dirty

        assert _queue_lengths('opened', 0)
        assert _queue_lengths('unopened', 3)
        session.commit()
        assert _queue_lengths('opened', 0)
        assert _queue_lengths('unopened', 3)
        assert not session.dirty
        [the_draft.open_pack(player) for player in the_draft.player_order]
        assert session.dirty
        assert _queue_lengths('opened', 1)
        assert _queue_lengths('unopened', 2)
        session.commit()
        assert not session.dirty
        assert _queue_lengths('opened', 1)
        assert _queue_lengths('unopened', 2)

        fetched_draft = session.query(sa.Draft).one()

        assert fetched_draft.player_order == the_draft.player_order
        assert fetched_draft.player_queues == the_draft.player_queues
        assert fetched_draft.player_picks == fetched_draft.player_picks