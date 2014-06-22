# coding=utf-8
from __future__ import unicode_literals
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


def test_pod_and_players():
    with sa.Session() as session:
        players = [sa.Player(handle='Player %s' % idx)
                   for idx in xrange(8)]
        pod = sa.Pod()
        pod.players = players
        session.add(pod)

    with sa.Session() as session:
        pod = session.query(sa.Pod).one()
        assert len(pod.player_queues) == len(players)
        assert len(pod.players) == len(players)
        assert all(pod in player.pods
                   for player in session.query(sa.Player).all())