from __future__ import unicode_literals
import uuid

import sqlalchemy
from sqlalchemy.schema import Column

from drafts_as_a_service import config
from sideboard.lib.sa import declarative_base, SessionManager, UUID


@declarative_base
class Base(object):
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)


class Session(SessionManager):
    engine = sqlalchemy.create_engine(config['sqlalchemy.url'])
