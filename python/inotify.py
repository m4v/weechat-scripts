# -*- coding: utf-8 -*-
###
# Copyright (c) 2009 by Elián Hanisch <lambdae2@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###

###
# Notifycation system
#
#
#   Commands:
#   * /inotify
#     See /help inotify
#
#   Notify methods:
#
#   Settings:
#   * plugins.var.python.inotify: #TODO
#
#
#   TODO:
#   * add support for more notification methods
#
#
#   History:
#   2010-
#   version:
#
###

SCRIPT_NAME    = "inotify"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Notification system, using dbus or libnotify. Works with WeeChat in screen."
SCRIPT_COMMAND = "inotify"

DAEMON_URL = 'http://github.com/m4v/weechat-scripts/blob/m4v/python/inotify-daemon'

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import xmlrpclib, socket
from fnmatch import fnmatch

# remote daemon timeout
socket.setdefaulttimeout(3)

### messages
def debug(s, prefix=''):
    """Debug msg"""
    #return #disable debug msg
    buffer_name = 'DEBUG:' + SCRIPT_NAME
    buffer = weechat.buffer_search('python', buffer_name)
    if not buffer:
        buffer = weechat.buffer_new(buffer_name, '', '', '', '')
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

valid_methods = set(('any', 'dbus', 'libnotify'))
def get_config_valid_string(config, valid_strings=valid_methods):
    value = weechat.config_get_plugin(config)
    if value not in valid_strings:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is an invalid value, allowed: %s." %(value, ', '.join(valid_strings)))
        return default
    return value


settings = {
         'server_uri': 'http://localhost:7766',
      'server_method': 'any',
     'ignore_channel': '',
        'ignore_nick': '',
#        'ignore_text': '',
         'color_nick': 'off',
        }

color_table = (
        'teal',
        'darkmagenta',
        'darkgreen',
        'brown',
        'blue',
        'darkblue',
        'darkcyan',
        'magenta',
        'green',
        'grey',
        )

class Ignores(object):
    def __init__(self, ignore_type):
        self.ignore_type = ignore_type
        self.ignores = []
        self.exceptions = []
        self._get_ignores()

    def _get_ignores(self):
        assert self.ignore_type is not None
        ignores = weechat.config_get_plugin(self.ignore_type).split(',')
        ignores = [ s.lower() for s in ignores if s ]
        self.ignores = [ s for s in ignores if s[0] != '!' ]
        self.exceptions = [ s[1:] for s in ignores if s[0] == '!' ]

    def __contains__(self, s):
        s = s.lower()
        for p in self.ignores:
            if fnmatch(s, p):
                for e in self.exceptions:
                    if fnmatch(s, e):
                        return False
                return True
        return False

class Server(object):
    def __init__(self):
        self._reset()
        self._create_server()
        self.send_rpc('Notification script loaded')

    def _reset(self):
        self.msg = {}
        self.timer = None

    def enqueue(self, msg, channel):
        self._enqueue(msg, channel)

    def _enqueue(self, msg, channel='', timeout=3000):
        if channel not in self.msg:
            self.msg[channel] = msg
        else:
            s = self.msg[channel]
            msg = '%s\n%s' %(s, msg)
            self.msg[channel] = msg
        if self.timer is None:
            self.timer = weechat.hook_timer(timeout, 0, 1, 'msg_flush', '')
            #debug('set timer: %s %s' %(self.timer, timeout))

    def flush(self):
        for channel, msg in self.msg.iteritems():
            if self.send_rpc(msg, channel):
                # daemon is restarting, try again later
                self._restart_timer()
                return
        self._reset()

    def _restart_timer(self):
        if self.timer is not None:
            #debug('reset and set timer')
            weechat.unhook(self.timer)
        self.timer = weechat.hook_timer(5000, 0, 1, 'msg_flush', '')

    def _create_server(self):
        self.error_count = 0
        self.address = weechat.config_get_plugin('server_uri')
        self.method = get_config_valid_string('server_method')
        try:
            self.server = xmlrpclib.Server(self.address)
            version = self.server.version()
            if version != '0.1':
                error('Incorrect server version, should be 0.1, but got %s' %version)
        except socket.error, e:
            self._error_connect()

    def _error(self, s):
        if self.error_count < 5: # stop sending error msg after 5 errors in a row
            error(s)
        self.error_count += 1

    def _error_connect(self):
        self._error('Failed to connect to our notification daemon, check if the address'
               ' \'%s\' is correct and if it\'s running.' %self.address)

    def send_rpc(self, *args):
        try:
            rt = getattr(self.server, self.method)(*args)
            if rt == 'OK':
                self.error_count = 0 
                #debug('Success: %s' % rt)
            elif rt.startswith('warning:'):
                self._error(rt[8:])
                if self.error_count < 10: # don't requeue after 10 errors
                    #debug('repeating queue')
                    # returning True will cause flush() to try to send msgs again later
                    return True
            else:
                error(rt)
        except xmlrpclib.Fault, e:
            self._error(e.faultString.split(':', 1)[1])
        except socket.error, e:
            self._error_connect()

    def quit(self):
        self.server.quit()

    def restart(self):
        self.server.restart()


def msg_flush(*args):
    server.flush()
    return WEECHAT_RC_OK

def color_tag(nick):
    n = len(color_table)
    #generic_nick = nick.strip('_`').lower()
    id = (sum(map(ord, nick))%n)
    #debug('%s:%s' %(nick, id))
    return '<font color=%s>%s</font>' %(color_table[id], nick)

def format(s, nick=''):
    if '<' in s:
        s = s.replace('<', '&lt;')
    if '>' in s:
        s = s.replace('>', '&gt;')
    if nick:
        if get_config_boolean('color_nick'):
            nick_color = color_tag(nick)
            nick = nick_color.replace(nick, '&lt;%s&gt;' %nick) #put the <> inside the color tag
        else:
            nick = '&lt;%s&gt;' %nick
        s = '<b>%s</b> %s' %(nick, s)
    return s

def send_notify(s, channel='', nick=''):
    #command = getattr(server, 'kde4')
    s = format(s, nick)
    server.enqueue(s, channel)

class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'buffer':'pointer',
            }

    def __init__(self, name, args=''):
        self.cursor = 0
        self.pointer = weechat.infolist_get(name, '', args)
        if self.pointer == '':
            raise Exception('Infolist initialising failed')

    def __del__(self):
        """Purge infolist if is no longer referenced."""
        self.free()

    def __getitem__(self, name):
        """Implement the evaluation of self[name]."""
        type = self.fields[name]
        return getattr(self, 'get_%s' %type)(name)

    def get_pointer(self, name):
        return weechat.infolist_pointer(self.pointer, name)

    def next(self):
        self.cursor = weechat.infolist_next(self.pointer)
        return self.cursor

    def free(self):
        if self.pointer:
            #debug('Freeing Infolist')
            weechat.infolist_free(self.pointer)
            self.pointer = ''


def in_window(buffer):
    """Returns True if buffer is in a window and the user is active. This is for not show
    notifications of a visible buffer while the user is doing something and wouldn't need to be
    notified."""
    windows = Infolist('window')
    while windows.next():
        if windows['buffer'] == buffer:
            #debug('in current window')
            return not inactive()
    return False

def inactive():
    inactivity = int(weechat.info_get('inactivity', ''))
    #debug('user inactivity: %s' %inactivity)
    if inactivity > 20:
        return True
    else:
        return False

def notify_msg(data, buffer, time, tags, display, hilight, prefix, msg):
    if data and 'notify_message' not in tags:
        # weechat 0.3.0 bug
        #debug('Got bad tags, wanted "notify_message" got "%s"' %tags)
        return WEECHAT_RC_OK
    #debug('  '.join((data, buffer, time, tags, display, hilight, prefix, 'msg_len:%s' %len(msg))),
    #        prefix='MESSAGE')
    if hilight == '1' and display == '1':
        channel = weechat.buffer_get_string(buffer, 'short_name')
        if prefix[0] in '@+#!': # strip user modes
            prefix = prefix[1:]
        if weechat.info_get('irc_is_channel', channel) \
                and channel not in ignore_channel \
                and prefix not in ignore_nick \
                and not in_window(buffer):
            #debug('%sSending notification: %s' %(weechat.color('lightgreen'), channel), prefix='NOTIFY')
            send_notify(msg, channel=channel, nick=prefix)
    return WEECHAT_RC_OK

def notify_priv(data, buffer, time, tags, display, hilight, prefix, msg):
    if data and 'notify_private' not in tags:
        # weechat 0.3.0 bug
        #debug('Got bad tags, wanted "notify_private" got "%s"' %tags)
        return WEECHAT_RC_OK
    #debug('  '.join((data, buffer, time, tags, display, hilight, prefix, 'msg_len:%s' %len(msg))),
    #        prefix='PRIVATE')
    if display == '1' \
            and prefix not in ignore_nick \
            and not in_window(buffer):
        #debug('%sSending notification: %s' %(weechat.color('lightgreen'), prefix), prefix='NOTIFY')
        send_notify(msg, channel=prefix)
    return WEECHAT_RC_OK

def cmd_notify(data, buffer, args):
    if args:
        args = args.split()
        cmd = args[0]
        if cmd in ('test', 'quit', 'restart'):
            if cmd == 'test':
                server.send_rpc(' '.join(args[1:]) or 'This is a test.', '#test')
                #send_notify(' '.join(args[1:]) or 'This is a test.', '#test')
            elif cmd == 'quit':
                server.send_rpc('Shutting down notification daemon...')
                server.quit()
            elif cmd == 'restart':
                server.send_rpc('Restarting notification daemon...')
                server.restart()
            return WEECHAT_RC_OK

    weechat.command('', '/help %s' %SCRIPT_COMMAND)
    return WEECHAT_RC_OK

def ignore_update(*args):
    ignore_channel._get_ignores()
    ignore_nick._get_ignores()
    #ignore_text._get_ignores()
    return WEECHAT_RC_OK

def server_update(*args):
    server._create_server()
    return WEECHAT_RC_OK


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
        '', ''):

    # check if we need to workaround a bug in 0.3.0
    workaround = ''
    version = weechat.info_get('version', '')
    if version == '0.3.0':
        workaround = '1'
        #debug('workaround enabled')

    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    ignore_channel = Ignores('ignore_channel')
    ignore_nick = Ignores('ignore_nick')
    #ignore_text = Ignores('ignore_text')

    server = Server()

    weechat.hook_command(SCRIPT_COMMAND, SCRIPT_DESC, '[test [text] | quit ]', 
            "test: sends a test notification, with 'text' if provided.\n"
            "quit: forces remote daemon to shutdown, after this notifications won't be available"
            " and the daemon should be started again manually.\n\n"
            "Setting notification ignores:\n"
            "  It's possible to filter notification by channel or by nick, with the config options\n"
            "   'ignore_channel' and 'ignore_nick' in plugins.var.python.%s\n"
            "  Each config option accepts a comma separated list of patterns that should be\n"
            "   ignored. Wildcards '*', '?' and char groups [..] can be used.\n"
            "  An ignore exception can be added by prefixing '!' in the pattern.\n\n"
            "Examples:\n"
            "  Setting 'ignore_nick' to 'troll,b[0o]t':\n"
            "   will ignore notifications from troll, bot and b0t.\n"
            "  Setting 'ignore_channel' to '*ubuntu*,!#ubuntu-es':\n"
            "   will ignore notifications from any channel with the word 'ubuntu' except from\n"
            "   #ubuntu-es.\n" %SCRIPT_NAME
            ,'test|restart|quit', 'cmd_notify', '')
    weechat.hook_config('plugins.var.python.%s.ignore_*' %SCRIPT_NAME, 'ignore_update', '')
    weechat.hook_config('plugins.var.python.%s.server_*' %SCRIPT_NAME, 'server_update', '')

    weechat.hook_print('', 'notify_message', '', 1, 'notify_msg', workaround)
    weechat.hook_print('', 'notify_private', '', 1, 'notify_priv', workaround)

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
