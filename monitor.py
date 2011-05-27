# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2010 by Elián Hanisch <lambdae2@gmail.com>
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
#
#   Monitor join messages for warn about known users.
#   This is mostly intended for get an early warning of known trolls.
#
#   If using chanop.py script, any bans set in chanop's tracked
#   channels will be added to the warning list automatically.
#
#   Commands (see detailed help with /help in WeeChat):
#   * /warn: Manages warning patterns.
#
#   Settings:
#   * plugins.var.python.monitor.warning_buffer:
#     Defines where to print monitor warnings.
#     Valid values: 'core', 'channel', 'current' Default: 'core'
#     
#     core:    print in core buffer.
#     channel: print in channel buffer (where the matching user joined)
#     current: print in whatever buffer you're currently looking at.
#
#   * plugins.var.python.monitor.mask.*:
#     Patterns.
#
###

SCRIPT_NAME    = "monitor"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Monitor join messages and warn about known users."


try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt, prnt_date_tags
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import re
import time

# -----------------------------------------------------------------------------
# Print Utils

script_nick = SCRIPT_NAME
def error(s, buffer=''):
    """Error msg"""
    prnt(buffer, '%s%s %s' %(weechat.prefix('error'), script_nick, s))
    if weechat.config_get_plugin('debug'):
        import traceback
        if traceback.sys.exc_type:
            trace = traceback.format_exc()
            prnt('', trace)

def say(s, buffer=''):
    """normal msg"""
    prnt(buffer, '%s\t%s' %(script_nick, s))

def format_hostmask(hostmask):
    nick, host = hostmask.split('!', 1)
    return '%s%s%s(%s%s%s)%s' % (color_chat_nick,
                                 nick,
                                 color_chat_delimiter,
                                 color_chat_host,
                                 host,
                                 color_chat_delimiter,
                                 color_reset)

def format_color(s, color):
    return '%s%s%s' % (color, s, color_reset)

# -----------------------------------------------------------------------------
# IRC String

import string

_rfc1459trans = string.maketrans(string.ascii_uppercase + r'\[]',
                                 string.ascii_lowercase + r'|{}')
def IRClower(s):
    return s.translate(_rfc1459trans)

class CaseInsensibleString(str):
    def __init__(self, s=''):
        self.lowered = IRClower(s)

    lower    = lambda self: self.lowered
    translate = lambda self, trans: self.lowered
    __eq__   = lambda self, s: self.lowered == IRClower(s)
    __ne__   = lambda self, s: not self == s
    __hash__ = lambda self: hash(self.lowered)


def caseInsensibleKey(k):
    if isinstance(k, str):
        return CaseInsensibleString(k)
    elif isinstance(k, tuple):
        return tuple(map(caseInsensibleKey, k))
    return k


class CaseInsensibleSet(set):
    normalize = staticmethod(caseInsensibleKey)

    def __init__(self, iterable=()):
        iterable = map(self.normalize, iterable)
        set.__init__(self, iterable)

    def __contains__(self, v):
        return set.__contains__(self, self.normalize(v))

    def update(self, L):
        set.update(self, map(self.normalize, L))

    def add(self, v):
        set.add(self, self.normalize(v))

    def remove(self, v):
        set.remove(self, self.normalize(v))

# -----------------------------------------------------------------------------
# Regexp matching
 
_reCache = {}
def cachedPattern(f):
    """Use cached regexp object or compile a new one from pattern."""
    def getRegexp(pattern, *arg):
        try:
            regexp = _reCache[pattern]
        except KeyError:
            s = '^'
            for c in pattern:
                if c == '*':
                    s += '.*'
                elif c == '?':
                    s += '.'
                elif c in '[{':
                    s += r'[\[{]'
                elif c in ']}':
                    s += r'[\]}]'
                elif c in '|\\':
                    s += r'[|\\]'
                else:
                    s += re.escape(c)
            s += '$'
            regexp = re.compile(s, re.I)
            _reCache[pattern] = regexp
        return f(regexp, *arg)
    return getRegexp

@cachedPattern
def pattern_match(regexp, string):
    return regexp.match(string) is not None

# -----------------------------------------------------------------------------
# Config Settings

settings = {'warning_buffer': 'core'} 


valid_strings = set(('core', 'channel', 'current'))
def get_config_valid_string(config, valid_strings=valid_strings):
    value = weechat.config_get_plugin(config)
    if value not in valid_strings:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." % (config, default))
        error("'%s' is an invalid value, allowed: %s." % (value, ', '.join(valid_strings)))
        return default
    return value

# -----------------------------------------------------------------------------
# WeeChat classes

def callback(method):
    """This function will take a bound method or function and make it a callback."""
    # try to create a descriptive and unique name.
    func = method.func_name
    try:
        im_self = method.im_self
        try:
            inst = im_self.__name__
        except AttributeError:
            try:
                inst = im_self.name
            except AttributeError:
                raise Exception("Instance of %s has no __name__ attribute" %type(im_self))
        cls = type(im_self).__name__
        name = '_'.join((cls, inst, func))
    except AttributeError:
        # not a bound method
        name = func
    # set our callback
    import __main__
    setattr(__main__, name, method)
    return name

class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'name'        :'string',
            'option_name' :'string',
            'value'       :'string',
            'host'        :'string',
            'flags'       :'integer',
            'prefixes'    :'string',
            'is_connected':'integer',
            }

    _use_flags = False

    def __init__(self, name, args=''):
        self.cursor = 0
        #debug('Generating infolist %r %r', name, args)
        self.pointer = weechat.infolist_get(name, '', args)
        if self.pointer == '':
            raise Exception("Infolist initialising failed (name:'%s' args:'%s')" %(name, args))

    def __len__(self):
        """True False evaluation."""
        if self.pointer:
            return 1
        else:
            return 0

    def __del__(self):
        """Purge infolist if is no longer referenced."""
        self.free()

    def __getitem__(self, name):
        """Implement the evaluation of self[name]."""
        if self._use_flags and name == 'prefixes':
            name = 'flags'
        value = getattr(weechat, 'infolist_%s' %self.fields[name])(self.pointer, name)
        if self._use_flags and name == 'flags':
            value = self._flagsAsString(value)
        return value

    def _flagsAsString(self, n):
        s = ''
        if n & 32:
            s += '+'
        if n & 8:
            s += '@'
        return s

    def __iter__(self):
        def generator():
            while self.next():
                yield self
        return generator()

    def next(self):
        self.cursor = weechat.infolist_next(self.pointer)
        return self.cursor

    def prev(self):
        self.cursor = weechat.infolist_prev(self.pointer)
        return self.cursor

    def reset(self):
        """Moves cursor to beginning of infolist."""
        if self.cursor == 1: # only if we aren't in the beginning already
            while self.prev():
                pass

    def free(self):
        if self.pointer:
            #debug('Freeing Infolist')
            weechat.infolist_free(self.pointer)
            self.pointer = ''


def nick_infolist(server, channel):
    return Infolist('irc_nick', '%s,%s' %(server, channel))


class NoArguments(Exception):
    pass

class ArgumentError(Exception):
    pass


class Command(object):
    """Class for hook WeeChat commands."""
    description, usage, help = "WeeChat command.", "[define usage template]", "detailed help here"
    command = ''
    completion = ''

    def __init__(self):
        assert self.command, "No command defined"
        self.__name__ = self.command
        self._pointer = ''
        self._callback = ''

    def __call__(self, *args):
        return self.callback(*args)

    def callback(self, data, buffer, args):
        """Called by WeeChat when /command is used."""
        self.data, self.buffer, self.args = data, buffer, args
        try:
            self.parser(args)  # argument parsing
        except ArgumentError, e:
            error('Argument error, %s' % e)
        except NoArguments:
            pass
        else:
            self.execute()
        return WEECHAT_RC_OK

    def parser(self, args):
        """Argument parsing, override if needed."""
        pass

    def execute(self):
        """This method is called when the command is run, override this."""
        pass

    def hook(self):
        assert not self._pointer, \
                "There's already a hook pointer, unhook first (%s)" %self.command
        self._callback = callback(self.callback)
        pointer = weechat.hook_command(self.command,
                                       self.description,
                                       self.usage,
                                       self.help,
                                       self.completion,
                                       self._callback, '')
        if pointer == '':
            raise Exception, "hook_command failed: %s %s" %(SCRIPT_NAME, self.command)
        self._pointer = pointer

    def unhook(self):
        if self._pointer:
            weechat.unhook(self._pointer)
            self._pointer = ''
            self._callback = ''

# -----------------------------------------------------------------------------
# Script Classes

class MonitorPatterns(CaseInsensibleSet):
    _updated = False
    _config = 'python.%s.mask' % SCRIPT_NAME
    def __contains__(self, v):
        if not self._updated:
            self.__update()
        return CaseInsensibleSet.__contains__(self, v)

    def __iter__(self):
        if not self._updated:
            self.__update()
        return CaseInsensibleSet.__iter__(self)

    def __update(self):
        self._updated = True
        infolist = Infolist('option', 'plugins.var.%s.*' % self._config)
        n = len(self._config) + 1
        self.update([ opt['option_name'][n:] for opt in infolist ])

    def clear(self):
        CaseInsensibleSet.clear(self)
        self._updated = False

warnPatterns = MonitorPatterns()

# -----------------------------------------------------------------------------
# Script Commands

class Monitor(Command):
    description, help = "Manages the list of warning patterns.", ""
    usage = "[ ( add <pattern> [<comment>] | del <pattern> [<pattern> ..]) ]"
    command = 'warn'
    completion = 'add %(chanop_ban_mask)||del %(monitor_patterns)|%*'

    def parser(self, args):
        if not args:
            self.print_pattern_list()
            raise NoArguments
        args = args.split()
        try:
            cmd = args.pop(0)
            if cmd not in ('add', 'del') or len(args) < 1:
                raise Exception
        except:
            raise ArgumentError("please see /help warn.")

        self.cmd = cmd
        if cmd == 'add':
            self.mask = args.pop(0)
            if args:
                self.comment = ' '.join(args)
            else:
                self.comment = ''
        else:
            self.mask = args

    def print_pattern_list(self):
        for mask in warnPatterns:
            say("%s (%s)" % (format_color(mask, color_chat_delimiter),
                            weechat.config_get_plugin('mask.%s' % mask)))

    def execute(self):
        if self.cmd == 'add':
            weechat.config_set_plugin('mask.%s' % self.mask, self.comment)
            # config_set_plugin doesn't trigger hook_config callback, bug?
            warnPatterns.add(self.mask)
        elif self.cmd == 'del':
            for mask in self.mask:
                weechat.config_unset_plugin('mask.%s' % mask)

# -----------------------------------------------------------------------------
# Script Callbacks

# Decorators
def signal_parse(f):
    def decorator(data, signal, signal_data):
        server = signal[:signal.find(',')]
        channel = signal_data.split()[2]
        if channel[0] == ':':
            channel = channel[1:]
        hostmask = signal_data[1:signal_data.find(' ')]
        #debug('%s %s %s', data, signal, signal_data)
        return f(server, channel, hostmask, signal_data)
    decorator.func_name = f.func_name
    return decorator

@signal_parse
def join_cb(server, channel, hostmask, signal_data):
    for mask in warnPatterns:
        match = pattern_match(mask, hostmask)
        if match:
            value = get_config_valid_string('warning_buffer')
            buffer = ''
            if value == 'channel':
                buffer = weechat.buffer_search('irc', '%s.%s' % (server, channel))
            elif value == 'current':
                buffer = weechat.current_buffer()
            prnt_date_tags(buffer, 0, 'notify_highlight', 
                "%s\t%s joined %s (%s \"%s\")" % (script_nick, 
                                                 format_hostmask(hostmask),
                                                 format_color(channel, color_chat_channel),
                                                 format_color(mask, color_chat_delimiter),
                                                 weechat.config_get_plugin('mask.%s' % mask)))
            break
    return WEECHAT_RC_OK

def banmask_cb(data, signal, signal_data):
    #debug('BAN: %s %s', signal, signal_data)
    args = signal_data.split()
    # sanity check
    if not len(args) == 4:
        return WEECHAT_RC_OK

    op, channel, mask, users = args
    mode = signal[-1]
    if mode == 'b' and mask not in warnPatterns:
        s = ' '.join(map(format_hostmask, users.split(',')))
        op_nick = weechat.info_get('irc_nick_from_host', op)
        comment = "Ban in %s by %s, affected %s Date: %s" % (channel, op_nick, s, time.asctime())
        comment = weechat.string_remove_color(comment, '')
        weechat.config_set_plugin('mask.%s' % mask, comment)
        warnPatterns.add(mask)
    return WEECHAT_RC_OK

def clear_warn_pattern(data, config, value):
    #debug('CONFIG: %s %s %s' % (data, config, value))
    warnPatterns.clear()
    return WEECHAT_RC_OK

def monitor_cmpl(data, completion_item, buffer, completion):
    for mask in warnPatterns:
        weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_END)
    return WEECHAT_RC_OK

# -----------------------------------------------------------------------------
# Register script

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

    # colors
    color_chat_delimiter = weechat.color('chat_delimiters')
    color_chat_nick      = weechat.color('chat_nick')
    color_chat_host      = weechat.color('chat_host')
    color_chat_channel   = weechat.color('chat_channel')
    color_reset          = weechat.color('reset')

    # pretty SCRIPT_NAME
    script_nick = '%s[%s%s%s]%s' % (color_chat_delimiter,
                                    color_chat_nick,
                                    SCRIPT_NAME,
                                    color_chat_delimiter,
                                    color_reset)

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    # hook signals
    weechat.hook_signal('*,irc_in_join', 'join_cb', '')
    weechat.hook_signal('*,irc_in_join_znc', 'join_cb', '')
    weechat.hook_signal('*,chanop_mode_*', 'banmask_cb', '')

    # hook config
    weechat.hook_config('plugins.var.python.%s.mask.*' % SCRIPT_NAME, 'clear_warn_pattern', '')

    # hook completer
    weechat.hook_completion('monitor_patterns', '', 'monitor_cmpl', '')

    # hook commands
    Monitor().hook()

    # -------------------------------------------------------------------------
    # Debug

    if weechat.config_get_plugin('debug'):
        try:
            # custom debug module I use, allows me to inspect script's objects.
            import pybuffer
            debug = pybuffer.debugBuffer(globals(), '%s_debug' % SCRIPT_NAME)
        except:
            def debug(s, *args):
                if not isinstance(s, basestring):
                    s = str(s)
                if args:
                    s = s %args
                prnt('', '%s\t%s' %(script_nick, s))
    else:
        def debug(*args):
            pass



# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
