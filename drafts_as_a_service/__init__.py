from __future__ import unicode_literals

import cherrypy


from sideboard.lib import log, parse_config, render_with_templates, services
from drafts_as_a_service._version import __version__

config = parse_config(__file__)


from drafts_as_a_service import service
services.register(service, 'drafts_as_a_service')



from drafts_as_a_service import sa
services.register(sa.Session.crud, 'drafts_as_a_service_crud')



@render_with_templates(config['template_dir'])
class Root(object):
    def index(self):
        log.debug('this data will be used to render a template')
        return {
            'plugin': 'drafts-as-a-service',
            'header': True
        }

cherrypy.tree.mount(Root(), '/drafts_as_a_service')

