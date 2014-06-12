from __future__ import unicode_literals

# underscore-prefixed functions are not exposed
def _greeting_impl(s):
    return 'Hello {}!'.format(s)

# all other methods are public
def greeting():
    return _greeting_impl('World')
