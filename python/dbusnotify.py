# -*- coding: utf-8 -*-
SCRIPT_NAME    = "dbusnotify"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = ""

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except:
    import_ok = False

import xmlrpclib, socket, fnmatch

### messages
def debug(s, prefix=''):
    """Debug msg"""
    buffer = weechat.buffer_search('python', 'debug ' + SCRIPT_NAME)
    if not buffer:
        buffer = weechat.buffer_new('debug ' + SCRIPT_NAME, '', '', '', '')
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'time_for_each_line', '0')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

def error(s, prefix=SCRIPT_NAME, buffer=''):
    """Error msg"""
    weechat.prnt(buffer, '%s%s: %s' %(weechat.prefix('error'), prefix, s))

def say(s, prefix='', buffer=''):
    """Normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

### config and value validation
boolDict = {'on':True, 'off':False}
def get_config_boolean(config):
    value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_int(config):
    value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)

settings = {
           'server_host': 'localhost',
           'server_port': '7766',
         'server_method': 'kde4',
        'ignore_channel': '',
           'ignore_nick': '',
        }

class Ignores(object):
    ignore_type = None
    def __init__(self):
        self.ignores = []
        self._get_ignores()

    def _get_ignores(self):
        assert self.ignore_type is not None
        ignores = weechat.config_get_plugin(self.ignore_type).split(',')
        self.ignores = [ s.lower() for s in ignores if s ]

    def __contains__(self, s):
        s = s.lower()
        for p in self.ignores:
            if fnmatch.fnmatch(s, p):
                return True
        return False

class IgnoreChannel(Ignores):
    ignore_type = 'ignore_channel'

class IgnoreNick(Ignores):
    ignore_type = 'ignore_nick'

class Server(object):
    def __init__(self):
        self._create_server()
        self.send_rpc('Notification script loaded')

    def _create_server(self):
        address = weechat.config_get_plugin('host')
        port = get_config_int('port')
        self.server = xmlrpclib.Server('http://%s:%s' %(address, port))
        self.method = weechat.config_get_plugin('method')

    def send_rpc(self, *args):
        try:
            rt = self.server.notify(self.method, *args)
            debug('Success: %s' % rt)
        except xmlrpclib.Fault, e:
            debug('Error: %s' % e.faultString.split(':', 1)[1])


def send_notify(s, channel='', nick='', raw=False):
    #command = getattr(server, 'kde4')
    server.send_rpc(s, channel, nick, raw)

def notify_msg(data, buffer, time, tags, display, hilight, prefix, msg):
    if 'notify_message' not in tags:
        # XXX weechat bug?
        debug('Got bad tags: %s' %tags)
        return WEECHAT_RC_OK
    debug('  '.join((data, buffer, time, tags, display, hilight, prefix, 'msg_len:%s' %len(msg))),
            prefix='MESSAGE')
    if hilight == '1' and display == '1':
        channel = weechat.buffer_get_string(buffer, 'short_name')
        if prefix[0] in '@+#!': # strip user modes
            _prefix = prefix[1:]
        else:
            _prefix = prefix
        if weechat.info_get('irc_is_channel', channel) \
                and channel not in ignore_channel \
                and _prefix not in ignore_nick:
            debug('%sSending notification: %s' %(weechat.color('lightgreen'), channel), prefix='NOTIFY')
            send_notify(msg, channel=channel, nick=prefix)
    return WEECHAT_RC_OK

def notify_priv(data, buffer, time, tags, display, hilight, prefix, msg):
    if 'notify_private' not in tags:
        # XXX weechat bug?
        debug('Got bad tags: %s' %tags)
        return WEECHAT_RC_OK
    debug('  '.join((data, buffer, time, tags, display, hilight, prefix, 'msg_len:%s' %len(msg))),
            prefix='PRIVATE')
    if display == '1':
        if prefix not in ignore_nick:
            debug('%sSending notification: %s' %(weechat.color('lightgreen'), nick), prefix='NOTIFY')
            send_notify(msg, channel=prefix)
        else:
            debug('private ignored')
    return WEECHAT_RC_OK

def cmd_test(data, buffer, args):
    if not args:
        send_notify('test', channel='#test')
    else:
        send_notify(args, channel='#test', raw=True)
    return WEECHAT_RC_OK

def ignore_update(*args):
    ignore_channel._get_ignores()
    ignore_nick._get_ignores()
    return WEECHAT_RC_OK

def server_update(*args):
    server._create_server()
    return WEECHAT_RC_OK


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
        '', ''):

    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    ignore_channel = IgnoreChannel()
    ignore_nick = IgnoreNick()
    server = Server()

    weechat.hook_command('dbus_test', 'desc', 'help', 'help', '', 'cmd_test', '')
    weechat.hook_config('plugins.var.python.%s.ignore_*' %SCRIPT_NAME, 'ignore_update', '')
    weechat.hook_config('plugins.var.python.%s.server_*' %SCRIPT_NAME, 'server_update', '')

    weechat.hook_print('', 'notify_message', '', 1, 'notify_msg', ''),
    weechat.hook_print('', 'notify_private', '', 1, 'notify_priv', ''),

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
