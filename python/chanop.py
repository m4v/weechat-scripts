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
#   Helper script for IRC operators
#
#   Inspired by auto_bleh.pl (irssi) and chanserv.py (xchat) scripts
#
#   Networks like Freenode and some channels encourage operators to not stay permanently with +o
#   privileges and only use it when needed. This script works along those lines, requesting op,
#   kick/ban/etc and deop automatically with a single command.
#   Still this script is very configurable and its behaviour can be configured in a per server or per
#   channel basis so it can fit most needs without changing its code.
#
#   Features several completions for ban/mute masks and a memory for channel masks and users (so
#   users that parted are still bannable).
#
#   Commands (see detailed help with /help in WeeChat):
#   *      /oop: Request op
#   *    /odeop: Drop op
#   *    /okick: Kick user (or users)
#   *     /oban: Apply bans
#   *   /ounban: Remove bans
#   *    /omute: Apply mutes
#   *  /ounmute: Remove mutes
#   *    /okban: Kick and bans user (or users)
#   *   /otopic: Change channel topic
#   *    /omode: Change channel modes
#   *    /olist: List cached masks (bans or mutes)
#   *   /ovoice: Give voice to user
#   * /odevoice: Remove voice from user
#
#
#   Settings:
#   Most configs (unless noted otherwise) can be defined for a server or a channel in particular, so
#   it is possible to request op in different networks, stay always op'ed in one channel while
#   auto-deop in another.
#
#   For define the option 'option' in server 'server_name' use:
#   /set plugins.var.python.chanop.option.server_name "value"
#   For define it in the channel '#channel_name':
#   /set plugins.var.python.chanop.option.server_name.#channel_name "value"
#
#   * plugins.var.python.chanop.op_command:
#     Here you define the command the script must run for request op, normally
#     is a /msg to a bot, like chanserv in freenode or Q in quakenet.
#     It accepts the special vars $server, $channel and $nick
#
#     By default it ask op to chanserv, if your network doesn't use chanserv, then you must change
#     it.
#
#     Examples:
#     /set plugins.var.python.chanop.op_command "/msg chanserv op $channel $nick"
#     (globally for all servers, like freenode and oftc)
#     /set plugins.var.python.chanop.op_command.quakenet "/msg q op $channel $nick"
#     (for quakenet only)
#
#   * plugins.var.python.chanop.deop_command:
#     Same as op_command but for deop.
#     It accepts the special vars $server, $channel and $nick
#
#   * plugins.var.python.chanop.autodeop:
#     Enables auto-deop'ing after using any of the ban or kick commands.
#     Note that if you got op manually (like with /oop) then the script won't deop you
#     Valid values 'on', 'off'
#
#   * plugins.var.python.chanop.autodeop_delay:
#     Time it must pass (without using any commands) before auto-deop, in seconds.
#     Using zero causes to deop immediately.
#
#   * plugins.var.python.chanop.default_banmask:
#     List of keywords separated by comas. Defines default banmask, when using /oban, /okban or
#     /omute
#     You can use several keywords for build a banmask, each keyword defines how the banmask will be
#     generated for a given hostmask, see /help oban
#     Valid keywords are: nick, user, host, exact and webchat
#
#     Examples:
#     /set plugins.var.python.chanop.default_banmask host (bans with *!*@host)
#     /set plugins.var.python.chanop.default_banmask host,user (bans with *!user@host)
#
#   * plugins.var.python.chanop.kick_reason:
#     Default kick reason if none was given in the command.
#
#   * plugins.var.python.chanop.enable_remove:
#     If enabled, it will use "/quote remove" command instead of /kick, enable it only in
#     networks that support it, like freenode.
#     Valid values 'on', 'off'
#
#   * plugins.var.python.chanop.invert_kickban_order:
#     /okban kicks first, then bans, this inverts the order.
#     Valid values 'on', 'off'
#
#   * plugins.var.python.chanop.display_affected:
#
#
#   The following configs can't be defined per channel.
#
#   * plugins.var.python.chanop.channels:
#
#   * plugins.var.python.chanop.fetch_bans:
#
#   * plugins.var.python.chanop.modes:
#
#   * plugins.var.python.chanop.chanmodes:
#
#
#   The following configs are global and can't be defined per server or channel.
#
#   * plugins.var.python.chanop.enable_multi_kick:
#     Enables kicking multiple users with /okick command.
#     Be careful with this as you can kick somebody by accident if
#     you're not careful when writting the kick reason.
#
#     This also applies to /okban command, multiple kickbans would be enabled.
#     Valid values 'on', 'off'
#
#
#  TODO
#  * use dedicated config file like in urlgrab.py
#   (win free config value validation by WeeChat)
#  * ban expire time
#  * save ban.mask and ban.hostmask across reloads
#  * allow to override mute command (for quiet with ChanServ)
#  * rewrite the queue message stuff
#  * support for bans with channel forward
#  * support for extbans (?)
#  * multiple-channel ban (?)
#
#
#   History:
#   2010-
#   version 0.2: major updates
#   * fixed mutes for ircd-seven
#   * added commands: /ovoice /odevoice /ounmute /omode /olist
#   * config options removed:
#     - merge_bans: replaced by 'modes' option
#     - enable_mute: replaced by 'chanmodes' option
#
#   2009-11-9
#   version 0.1.1: fixes
#   * script renamed to 'chanop' because it was causing conflicts with python
#   'operator' module
#   * added /otopic command
#
#   2009-10-31
#   version 0.1: Initial release
###

SCRIPT_NAME    = "chanop"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.2-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Helper script for IRC operators"

### default settings ###
settings = {
'op_command'            :'/msg chanserv op $channel $nick',
'deop_command'          :'/msg chanserv deop $channel $nick',
'autodeop'              :'on',
'autodeop_delay'        :'180',
'default_banmask'       :'host',
'enable_remove'         :'off',
'kick_reason'           :'kthxbye!',
'enable_multi_kick'     :'off',
'invert_kickban_order'  :'off',
'display_affected'      :'off', # FIXME make configurable per channel
'chanmodes'             :'bq',
'modes'                 :'4',
'fetch_bans'            :'on', # FIXME make per server
}


try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import getopt, re
from time import time

now = lambda : int(time())


### Messages ###
def error(s, prefix=None, buffer='', trace=''):
    """Error msg"""
    prefix = prefix or script_nick
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), prefix, s))
    if weechat.config_get_plugin('debug'):
        if not trace:
            import traceback
            if traceback.sys.exc_type:
                trace = traceback.format_exc()
        not trace or weechat.prnt('', trace)

def say(s, prefix=None, buffer=''):
    """normal msg"""
    prefix = prefix or script_nick
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

def print_affected_users(buffer, *hostmasks):
    """Print a list of users, max 8 hostmasks"""
    def format_user(hostmask):
        nick, host = hostmask.split('!', 1)
        return '%s%s%s(%s%s%s)' %(color_chat_nick, nick, color_delimiter, color_chat_host,
                host, color_delimiter)

    max = 8
    count = len(hostmasks)
    if count > max:
        hostmasks = hostmasks[:max]
    say('Affected users (%s): %s%s' %(count, ' '.join(map(format_user,
        hostmasks)), count > max and ' %s...' %color_reset or ''), buffer=buffer)


### Debug functions and decorators ###
def debug_time_stamp(f):
    start = now()
    def setprefix(s, prefix='', **kwargs):
        if not prefix:
            prefix = now() - start
        f(s, prefix=prefix, **kwargs)
    return setprefix

@debug_time_stamp
def debug(s, prefix='', buffer_name=None):
    """Debug msg"""
    if not weechat.config_get_plugin('debug'): return
    if not buffer_name:
        buffer_name = SCRIPT_NAME + '_debug'
    buffer = weechat.buffer_search('python', buffer_name)
    if not buffer:
        buffer = weechat.buffer_new(buffer_name, '', '', '', '')
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

def debug_print_cache(data, buffer, args):
    """Prints stuff stored in cache"""
    _debug = lambda s: debug(s, buffer_name = 'chanop_cache')
    for key, users in userCache.iteritems():
        _debug('\n')
        for nick, host in users.iteritems():
            _debug('%s.%s %10s => %s' %(key[0], key[1], nick, host))
        _debug('--')
        for nick, when in users._temp_users.iteritems():
            _debug('%s.%s %10s => %s' %(key[0], key[1], nick, when))
    _debug('\n')
    for pattern in _regexp_cache:
        _debug('regexp for %s' %pattern)
    return WEECHAT_RC_OK

def debug_garbage_collector(data, buffer, args):
    """Runs garbage collector"""
    return garbage_collector_cb('', 0)

def debug_result(f):
    """Prints args and result of a function"""
    def log(*args, **kwargs):
        rt = f(*args, **kwargs)
        debug('%s(%s %s) => %s' %(f.func_name, str(args), str(kwargs), rt))
        return rt
    return log

def human_readable_time(t):
    units = {0:'s', 1:'ms', 2:'us'}
    p = 0
    while t < 1 and p < 2:
        p += 1
        t *= 1000.0
    return '%6.2f %s' %(t, units[p])

def debug_print_time_avg(data, buffer, args):
    """Prints timeit avegare"""
    _debug = lambda s: debug(s, buffer_name = 'chanop_timeavg')
    _debug('')
    for k, v in _time_avg.items():
        avg = v[0]/v[1]
        _debug('f: %20s t: %s' %(k, human_readable_time(avg)))
    return WEECHAT_RC_OK

_time_avg = {}
def timeit(f):
    """Times a function and prints the result in a buffer."""
    # NOTE: after some use, I found out that timing functions this way to be *very* unrealiable :(
    # It only helps to give an idea of the time a function takes to complete, for profiling is
    # useless
    from time import time
    units = {0:'s', 1:'ms', 2:'us'}
    def timed_function(*args, **kwargs):
        t = time()
        rt = f(*args, **kwargs)
        d = time() - t
        debug('f: %20s t: %s' %(f.func_name, human_readable_time(d)), buffer_name='Chanop_timeit')
        try:
            v, n = _time_avg[f.func_name]
            v += d
            n += 1
            _time_avg[f.func_name] = (v, n)
        except KeyError:
            _time_avg[f.func_name] = (d, 1)
        return rt
    return timed_function


### Config and value validation ###
# TODO to make a class for this
boolDict = {'on':True, 'off':False}
def get_config_boolean(config, get_function=None):
    if get_function and callable(get_function):
        value = get_function(config)
    else:
        value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_int(config, get_function=None):
    if get_function and callable(get_function):
        value = get_function(config)
    else:
        value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)

valid_banmask = set(('nick', 'user', 'host', 'exact', 'webchat'))
def get_config_banmask(config='default_banmask', get_function=None):
    if get_function and callable(get_function):
        value = get_function(config)
    else:
        value = weechat.config_get_plugin(config)
    values = value.split(',')
    for value in values:
        if value not in valid_banmask:
            default = settings[config]
            error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
            error("'%s' is an invalid value, allowed: %s." %(value, ', '.join(valid_banmask)))
            return default
    #debug("default banmask: %s" %values)
    return values

def get_config_list(config):
    value = weechat.config_get_plugin(config)
    if value:
        return value.split(',')
    else:
        return []


### irc utils ###
def is_hostmask(s):
    """Returns whether or not the string s is a valid User hostmask."""
    n = s.find('!')
    m = s.find('@')
    if n < m-1 and n >= 1 and m >= 3 and len(s) > m+1:
        return True
    else:
        return False

def is_ip(s):
    """Returns whether or not a given string is an IPV4 address."""
    import socket
    try:
        return bool(socket.inet_aton(s))
    except socket.error:
        return False

_regexp_cache = {}
def hostmask_pattern_match(pattern, strings):
    if is_hostmask(pattern):
        return pattern_match(pattern, strings)
    return []

def pattern_match(pattern, strings):
    # we will take the trouble of using regexps, since they match faster than fnmatch once compiled
    if pattern in _regexp_cache:
        regexp = _regexp_cache[pattern]
    else:
        s = '^'
        for c in pattern:
            if c == '*':
                s += '.*'
            elif c == '?':
                s += '.'
            else:
                s += re.escape(c)
        s += '$'
        regexp = re.compile(s, re.I)
        _regexp_cache[pattern] = regexp

    if isinstance(strings, str):
        strings = [strings]
    return [ s for s in strings if regexp.search(s) ]

def get_nick(s):
    """
    'nick!user@host' => 'nick'
    ':nick!user@host' => 'nick'"""
    n = s.find('!')
    if n < 1:
        return ''
    if s[0] == ':':
        return s[1:n]
    return s[:n]

def get_user(s, trim=False):
    """
    'nick!user@host' => 'user'"""
    n = s.find('!')
    m = s.find('@')
    if n > 0 and m > 2 and m > n:
        s = s[n+1:m]
        if trim:
            if s[0] == '~':
                return s[1:]
            elif len(s) > 2 and s[1] == '=':
                return s[2:]
        else:
            return s
    return ''

def get_host(s):
    """
    'nick!user@host' => 'host'"""
    n = s.find('@')
    if n < 3:
        # not a valid hostmask
        return ''
    m = s.find(' ')
    if m > 0 and m > n:
        return s[n+1:m]
    return s[n+1:]

def hex_to_ip(s):
    """
    '7f000001' => '127.0.0.1'"""
    if not len(s) == 8:
        return ''
    try:
        ip = map(lambda n: s[n:n+2], range(0, len(s), 2))
        ip = map(lambda n: int(n, 16), ip)
        return '.'.join(map(str, ip))
    except:
        return ''

def supported_modes(server, mode=None):
    """
    Checks if server supports a specific chanmode. If <mode> is None returns all modes supported
    by server."""
    modes = weechat.config_get_plugin('chanmodes.%s' %server)
    if not modes:
        modes = weechat.config_get_plugin('chanmodes')
    if not modes:
        modes = 'b'
    if mode:
        return mode in modes
    else:
        return modes

def irc_buffer(buffer):
    """Returns pair (server, channel) or None if buffer isn't an irc channel"""
    buffer_get_string = weechat.buffer_get_string
    if buffer_get_string(buffer, 'plugin') == 'irc' \
            and buffer_get_string(buffer, 'localvar_type') == 'channel':
        channel = buffer_get_string(buffer, 'localvar_channel')
        server = buffer_get_string(buffer, 'localvar_server')
        return (server, channel)


### WeeChat classes ###
class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'name':'string',
            'host':'string',
            'flags':'integer',
            'is_connected':'integer',
            }

    def __init__(self, name, args=''):
        self.cursor = 0
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
        type = self.fields[name]
        return getattr(self, 'get_%s' %type)(name)

    def get_string(self, name):
        return weechat.infolist_string(self.pointer, name)

    def get_integer(self, name):
        return weechat.infolist_integer(self.pointer, name)

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


class Command(object):
    """Class for hook WeeChat commands."""
    help = ("WeeChat command.", "[define usage template]", "detailed help here")

    command = ''
    completion = ''
    callback = ''
    def __init__(self, command='', callback='', completion=''):
        if command:
            self.command = command
        if callback:
            self.callback = callback
        elif not self.callback:
            self.callback = 'chanop_%s' %self.command
        if completion:
            self.completion = completion
        self.pointer = ''

    def __call__(self, *args):
        """Called by WeeChat when /command is used."""
        self.parse_args(*args)
        self.execute()
        return WEECHAT_RC_OK

    def parse_args(self, data, buffer, args):
        """Do argument parsing here."""
        self.buffer = buffer
        self.args = args

    def _parse_doc(self):
        """Parsing of the command help strings."""
        desc, usage, help = self.help
        # format fix for help
        help = help.strip('\n').splitlines()
        if help:
            n = 0
            for c in help[0]:
                if c in ' \t':
                    n += 1
                else:
                    break

            def trim(s):
                return s[n:]

            help = '\n'.join(map(trim, help))
        else:
            help = ''
        return desc, usage, help

    def execute(self):
        """This method is called when the command is run, override this."""
        pass

    def hook(self):
        import __main__
        assert self.command and self.callback, "command: '%s' callback: '%s'" %(self.command,
                self.callback)
        assert not self.pointer, "There's already a hook pointer, unhook first (%s)" %self.command
        assert not hasattr(__main__, self.callback), "Callback already in __main__ (%s)" %self.callback
        desc, usage, help = self._parse_doc()
        self.pointer = weechat.hook_command(self.command, desc, usage, help, self.completion,
                self.callback, '')
        if self.pointer == '':
            raise Exception, "hook_command failed"
        # add self to the global namespace
        setattr(__main__, self.callback, self)

    def unhook(self):
        import __main__
        delattr(__main__, self.callback)
        if self.pointer:
            weechat.unhook(self.pointer)
            self.pointer = ''


### Command queue classes ###
# TODO I need to refactor this
class Message(object):
    """Class that stores the command for scheduling in CommandQueue."""
    def __init__(self, cmd, buffer='', wait=0):
        assert cmd
        self.command = cmd
        self.wait = wait
        self.buffer = buffer

    def __call__(self):
        #debug('Message: wait %s' %self.wait)
        if self.wait:
            if isinstance(self.wait, float):
               command = '/wait %sms %s' %(int(self.wait*1000), self.command)
            else:
               command = '/wait %s %s' %(self.wait, self.command)
        else:
            command = self.command
        debug('sending: %r' %command)
        if weechat.config_get_plugin('debug') == '2':
            # don't run commands
            return True
        weechat.command(self.buffer, command)
        return True


class CommandQueue(object):
    """Class that manages and sends the script's commands to WeeChat."""
    commands = []
    wait = 0

    class Normal(Message):
        """Normal message"""
        def __str__(self):
            return "<Normal %s >" \
                    %', '.join((self.command, self.buffer, str(self.wait)))


    class WaitForOp(Message):
        """This message interrupts the command queue until user is op'ed."""
        def __init__(self, cmd, server='*', channel='', nick='', **kwargs):
            Message.__init__(self, cmd, **kwargs)
            self.server = server
            self.channel = channel
            self.nick = nick

        def __call__(self):
            """Interrupt queue and wait until our user gets op."""
            global hook_timeout, hook_signal
            if hook_timeout:
                weechat.unhook(hook_timeout)
            if hook_signal:
                weechat.unhook(hook_signal)

            data = 'MODE %s +o %s' %(self.channel, self.nick)
            hook_signal = weechat.hook_signal('%s,irc_in2_MODE' %self.server,
                    'queue_continue_cb', data)

            data = '%s.%s' %(self.server, self.channel)
            hook_timeout = weechat.hook_timer(5000, 0, 1, 'queue_timeout_cb', data)

            Message.__call__(self)
            if weechat.config_get_plugin('debug') == '2':
                return True
            return False # returning false interrupts the queue execution

        def __str__(self):
            return "<WaitForOp %s >" \
                    %', '.join((self.command, self.buffer, self.server, self.channel, self.nick,
                        str(self.wait)))


    class AddChannel(Message):
        """This message only adds a channel into chanop channel list."""
        def __init__(self, cmd, server='', channel='', **kwargs):
            self.server = server
            self.channel = channel

        def __call__(self):
            config = 'channels.%s' %self.server
            channels = get_config_list(config)
            if not channels:
                weechat.config_set_plugin(config, self.channel)
            elif self.channel not in channels:
                channels.append(self.channel)
                value = ','.join(channels)
                weechat.config_set_plugin(config, value)
            return True


    class DisableAntiFlood(Message):
        def __init__(self, cmd, instance=None, **kwargs):
            assert instance
            self.commandQueueInstance = instance

        def __call__(self):
            """Chanop sends one message per second, except some cases (like kickbans) where it sends
            them without delay. WeeChat's antiflood interferes with this, so we have to disable it
            temporally."""
            opt_low = weechat.config_get('irc.network.anti_flood_prio_low')
            opt_high = weechat.config_get('irc.network.anti_flood_prio_high')
            value_low = weechat.config_integer(opt_low)
            value_high = weechat.config_integer(opt_high)
            #debug('disabling antiflood')
            wait = self.commandQueueInstance.wait + 1
            if value_low:
                weechat.config_option_set(opt_low, '0', 0)
                # set hook for re-enable antiflood
                weechat.hook_timer(wait*1000, 0, 1, 'enable_anti_flood_cb', '%s,%s' %(opt_low,
                    value_low))
            if value_high:
                weechat.config_option_set(opt_high, '0', 0)
                # set hook for re-enable antiflood
                weechat.hook_timer((wait+1)*1000, 0, 1, 'enable_anti_flood_cb', '%s,%s' %(opt_high,
                    value_high))
            return True


    def queue(self, cmd, type='Normal', wait=1, **kwargs):
        #debug('queue: wait %s self.wait %s' %(wait, self.wait))
        pack = getattr(self, type)(cmd, wait=self.wait, **kwargs)
        self.wait += wait
        #debug('queue: wait %s %s' %(self.wait, pack))
        self.commands.append(pack)

    # it happened once and it wasn't pretty
    def safe_check(f):
        def abort_if_too_many_commands(self):
            if len(self.commands) > 20:
                error("Limit of 20 commands in queue reached, aborting.")
                self.clear()
            else:
                f(self)
        return abort_if_too_many_commands

    @safe_check
    def run(self):
        while self.commands:
            pack = self.commands.pop(0)
            #debug('running: %s' %pack)
            rt = pack()
            assert rt in (True, False), '%s must return either True or False' %pack
            if not rt:
                return
        self.wait = 0

    def clear(self):
        self.commands = []
        self.wait = 0


weechat_queue = CommandQueue()
hook_signal = hook_timeout = None

def queue_continue_cb(data, signal, signal_data):
    global hook_timeout, hook_signal
    signal = signal_data.split(' ', 1)[1].strip()
    if signal == data:
        # we got op'ed
        #debug("We got op")
        weechat.unhook(hook_signal)
        weechat.unhook(hook_timeout)
        hook_signal = hook_timeout = None
        weechat_queue.run()
    return WEECHAT_RC_OK

def queue_timeout_cb(channel, count):
    global hook_timeout, hook_signal
    error("Couldn't get op in '%s', purging command queue..." %channel)
    weechat.unhook(hook_signal)
    hook_signal = hook_timeout = None
    weechat_queue.clear()
    return WEECHAT_RC_OK

def enable_anti_flood_cb(data, count):
    #debug('enabling antiflood: %s' %data)
    option, value = data.split(',')
    weechat.config_option_set(option, value, 0)
    return WEECHAT_RC_OK


### Base classes for chanop commands ###
class CommandChanop(Command):
    """Base class for our commands, with config and general functions."""
    infolist = None
    def __call__(self, *args):
        """Called by WeeChat when /command is used."""
        #debug("command __call__ args: %s" %(args, ))
        try:
            self.parse_args(*args)  # argument parsing
        except Exception, e:
            error('Argument error, %s' %e)
            return WEECHAT_RC_OK
        self.execute()          # call our command and queue messages for WeeChat
        weechat_queue.run()     # run queued messages
        self.infolist = None    # free irc_nick infolist
        return WEECHAT_RC_OK    # make WeeChat happy

    def parse_args(self, data, buffer, args):
        self.buffer = buffer
        self.args = args
        self.server = weechat.buffer_get_string(self.buffer, 'localvar_server')
        self.channel = weechat.buffer_get_string(self.buffer, 'localvar_channel')
        self.nick = weechat.info_get('irc_nick', self.server)
        self.users = userCache.get(self.server, self.channel)

    def replace_vars(self, s):
        try:
            return weechat.buffer_string_replace_local_var(self.buffer, s)
        except AttributeError:
            if '$channel' in s:
                s = s.replace('$channel', self.channel)
            if '$nick' in s:
                s = s.replace('$nick', self.nick)
            if '$server' in s:
                s = s.replace('$server', self.server)
            return s

    def get_config(self, config):
        string = '%s.%s.%s' %(config, self.server, self.channel)
        value = weechat.config_get_plugin(string)
        if not value:
            string = '%s.%s' %(config, self.server)
            value = weechat.config_get_plugin(string)
            if not value:
                value = weechat.config_get_plugin(config)
        return value

    def get_config_boolean(self, config):
        return get_config_boolean(config, self.get_config)

    def get_config_int(self, config):
        return get_config_int(config, self.get_config)

    def _nick_infolist(self):
        # reuse the same infolist instead of creating it many times
        # per __call__() (like with MultiKick)
        if not self.infolist:
            #debug('Creating Infolist')
            self.infolist = Infolist('irc_nick', '%s,%s' %(self.server, self.channel))
            return self.infolist
        else:
            self.infolist.reset()
            return self.infolist

    def has_op(self, nick=None):
        if not nick:
            nick = self.nick
        try:
            nicks = self._nick_infolist()
            while nicks.next():
                if nicks['name'] == nick:
                    if nicks['flags'] & 8:
                        return True
                    else:
                        return False
        except:
            error('Not in a IRC channel.')

    def has_voice(self, nick=None):
        if not nick:
            nick = self.nick
        try:
            nicks = self._nick_infolist()
            while nicks.next():
                if nicks['name'] == nick:
                    if nicks['flags'] & 32:
                        return True
                    else:
                        return False
        except:
            error('Not in a IRC channel.')

    def is_nick(self, nick):
        return nick in self.users

    def get_host(self, name=None):
        try:
            if name is None:
                return self.users[self.nick]
            host = self.users[name]
            return host
        except KeyError:
            pass

    def queue(self, cmd, **kwargs):
        weechat_queue.queue(cmd, buffer=self.buffer, **kwargs)

    def queue_clear(self):
        weechat_queue.clear()

    def get_op(self):
        op = self.has_op()
        if op is False:
            value = self.get_config('op_command')
            if not value:
                raise Exception, "No command defined for get op."
            self.queue(self.replace_vars(value), type='WaitForOp', server=self.server,
                    channel=self.channel, nick=self.nick)
        self.queue('', type='AddChannel', wait=0, server=self.server, channel=self.channel)
        self.queue('', type='DisableAntiFlood', wait=0, instance=weechat_queue)
        return op

    def drop_op(self):
        op = self.has_op()
        if op is True:
            value = self.get_config('deop_command')
            if not value:
                value = '/deop'
            self.queue(self.replace_vars(value))

    def voice(self, args):
        cmd = '/voice %s' %args
        self.queue(cmd)

    def devoice(self, args):
        cmd = '/devoice %s' %args
        self.queue(cmd)


deop_hook = {}
manual_op = False
class CommandNeedsOp(CommandChanop):
    """Base class for all the commands that requires op status for work."""

    def parse_args(self, data, buffer, args):
        """Show help if nothing to parse."""
        CommandChanop.parse_args(self, data, buffer, args)
        if not self.args:
            weechat.command('', '/help %s' %self.command)

    def execute(self, *args):
        global deop_hook, manual_op
        buffer = self.buffer
        if not self.args:
            return # don't pointless op and deop it no arguments given
        op = self.get_op()
        if op is None:
            return WEECHAT_RC_OK # not a channel
        elif op is False or buffer in deop_hook:
            # we're going to autoop or already did
            manual_op = False
        else:
            manual_op = True
        self.execute_op(*args)
        if not manual_op and self.get_config_boolean('autodeop'):
            delay = self.get_config_int('autodeop_delay')
            if delay > 0:
                if buffer in deop_hook:
                    weechat.unhook(deop_hook[buffer])
                deop_hook[buffer] = weechat.hook_timer(delay * 1000, 0, 1, 'deop_callback', buffer)
            else:
                self.drop_op()

    def execute_op(self, *args):
        """Commands in this method will be run with op privileges."""
        pass

def deop_callback(buffer, count):
    global deop_hook, cmd_deop
    cmd_deop('', buffer, '')
    del deop_hook[buffer]
    return WEECHAT_RC_OK


### User and masks classes ###
class CaseInsensibleString(str):
    def __init__(self, s=''):
        self.lowered = s.lower()

    def __eq__(self, s):
        try:
            return self.lowered == s.lower()
        except:
            return False

    def __ne__(self, s):
        return not self == s

    def __hash__(self):
        return hash(self.lowered)

def caseInsensibleKey(k):
    if isinstance(k, str):
        return CaseInsensibleString(k)
    elif isinstance(k, tuple):
        return tuple([ caseInsensibleKey(v) for v in k ])
    return k


class CaseInsensibleDict(dict):
    key = staticmethod(caseInsensibleKey)

    def __setitem__(self, k, v):
        dict.__setitem__(self, self.key(k), v)

    def __getitem__(self, k):
        return dict.__getitem__(self, self.key(k))

    def __delitem__(self, k):
        dict.__delitem__(self, self.key(k))

    def __contains__(self, k):
        return dict.__contains__(self, self.key(k))


class CaseInsensibleSet(set):
    normalize = staticmethod(caseInsensibleKey)

    def __init__(self, iterable=()):
        iterable = map(self.normalize, iterable)
        set.__init__(self, iterable)

    def __contains__(self, v):
        return set.__contains__(self, self.normalize(v))

    def add(self, v):
        set.add(self, self.normalize(v))

    def remove(self, v):
        set.remove(self, self.normalize(v))


class ServerChannelDict(CaseInsensibleDict):
    def getKeys(self, server, item=None):
        """Return a list of keys that match server and has item if given"""
        if item:
            return [ key for key in self if key[0] == server and item in self[key] ]
        else:
            return [ key for key in self if key[0] == server ]

    def purge(self):
        for key in self.keys():
            if not is_tracked(*key):
                debug('Removing not tracked %s.%s list (%s items)' %(key[0], key[1], len(self[key])))
                del self[key]
        for data in self.itervalues():
            data.purge()



class MaskObject(object):
    __slots__ = ('mask', 'hostmask', 'operator', 'date', 'expires')
    def __init__(self, mask, hostmask=None, operator=None, date=None, expires=None):
        self.mask = mask
        self.hostmask = hostmask
        self.operator = operator
        self.date = date or now()
        self.expires = expires

    def __repr__(self):
        return "<MaskObject %s %s >" %(self.mask, self.date)


class MaskList(CaseInsensibleDict):
    def __init__(self):
        self.fetch_time = 0

    def __setitem__(self, mask, d):
        if mask in self:
            # mask exists, update it
            ban = self[mask]
            for attr, value in d.iteritems():
                if value:
                    setattr(ban, attr, value)
        else:
            CaseInsensibleDict.__setitem__(self, mask, MaskObject(mask, **d))

    def searchByHostmask(self, hostmask):
        L = []
        for mask in self:
            if hostmask_pattern_match(mask, hostmask):
                L.append(mask)
        return L

    def searchByPattern(self, pattern):
        return pattern_match(pattern, self.iterkeys())

    def purge(self):
        pass


class MaskCache(ServerChannelDict):
    """Keeps a list of our bans for quick look up."""
    # DONT reassign these lists, should be shared across MaskCache instances
    hook_queue = [] # use deque object
    hook_fetch = []

    def __init__(self, mode='b'):
        self.mode = mode

    def initList(self, server, channel):
        self[server, channel] = MaskList()

    def add(self, server, channel, mask, **kwargs):
        """Adds a ban to (server, channel) banlist."""
        key = (server, channel)
        if key not in self:
            self.initList(*key)
        self[key][mask] = kwargs

    def remove(self, server, channel, mask=None):#, hostmask=None):
        key = (server, channel)
        try:
            if mask is None:
                del self[key]
            else:
                del self[key][mask]
                #debug("removing ban: %s" %banmask)
        except KeyError:
            pass

    def searchByHostmask(self, hostmask, server, channel):
        if hostmask:
            try:
                return self[server, channel].searchByHostmask(hostmask)
            except KeyError:
                pass
        return []

    def searchByPattern(self, pattern, server, channel):
        if pattern:
            try:
                return self[server, channel].searchByPattern(pattern)
            except KeyError:
                pass
        return []

    def searchByNick(self, nick, server, channel):
        hostmask = userCache.hostFromNick(nick, server, channel)
        return self.searchByHostmask(hostmask, server, channel)

    def search(self, s, server, channel):
        if is_nick(s):
            masks = self.searchByNick(s, server, channel)
        elif is_hostmask(s):
            masks = self.searchByHostmask(s, server, channel)
        else:
            masks = self.searchByPattern(s, server, channel)
        return masks

    def fetch(self, server, channel):
        """Fetches masks for a given server and channel."""
        # check modes
        if not supported_modes(server, self.mode):
            return
        # check the last time we did this
        try:
            if (now() - self[server, channel].fetch_time) < 60:
                # don't fetch again
                return
        except KeyError:
            pass
        if not self.hook_fetch:
            # only need to hook once
            self.hook_fetch.append(weechat.hook_modifier('irc_in_367', 'masklist_add_cb', ''))
            self.hook_fetch.append(weechat.hook_modifier('irc_in_368', 'masklist_end_cb', ''))
        # The server will send all messages together sequentially, so is easy to tell for which channel
        # and mode the mask is if we keep a queue list in self.hook_queue
        key = (server, channel, self.mode)
        if key in self.hook_queue:
            # already in queue
            return
        cmd = '/mode %s %s' %(channel, self.mode)
        #weechat_queue.queue(cmd, buffer=buffer)
        debug('fetching masks: %r' %cmd)
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        weechat.command(buffer, cmd)
        self.hook_queue.append(key)



banlist = MaskCache('b')
mutelist = MaskCache('q')
maskModes = { 'b':banlist, 'q': mutelist }

def masklist_add_cb(data, modifier, modifier_data, string):
    """Adds ban to the list."""
    #debug(string)
    channel, banmask, op, date = string.split()[-4:]
    server = modifier_data
    mode = MaskCache.hook_queue[0][2]
    maskModes[mode].add(server, channel, banmask, operator=op, date=date)
    return ''

def masklist_end_cb(data, modifier, modifier_data, string):
    """Ban listing over."""
    #debug(string)
    global waiting_for_completion, cmpl_mask_args
    server, channel, mode = MaskCache.hook_queue.pop(0)
    masklist = maskModes[mode]
    key = (server, channel)
    if key not in masklist:
        masklist.initList(*key)
    else:
        debug('got masks for %s.%s %r' %(server, channel, mode))
    if not MaskCache.hook_queue:
        # fetch is over
        for hook in MaskCache.hook_fetch:
            weechat.unhook(hook)
        del MaskCache.hook_fetch[:]
        debug('fetch over')
    # check if there is a completion waiting for the fetch to finish
    if waiting_for_completion:
        buffer, completion  = waiting_for_completion
        input = weechat.buffer_get_string(buffer, 'input')
        input = input[:input.find(' fetching masks')] # remove this bit
        weechat.buffer_set(buffer, 'input', '%s ' %input)
        cmpl_unban(buffer, server, channel, completion, masklist, input, cmpl_mask_args)
        waiting_for_completion = cmpl_mask_args = None
    return ''


class UserList(CaseInsensibleDict):
    def __init__(self):
        self._temp_users = CaseInsensibleDict()

    def __setitem__(self, nick, hostname):
        CaseInsensibleDict.__setitem__(self, nick, hostname)
        # remove from temp list, in case if user did a cycle
        if nick in self._temp_users:
            del self._temp_users[nick]

    def remove(self, nick):
        """Place nick in queue for deletion"""
        self._temp_users[nick] = now()

    def purge(self):
        """Purge 1 hour old nicks"""
        _now = now()
        for nick, when in self._temp_users.items():
            if (_now - when) > 3600:
                try:
                    del self._temp_users[nick]
                    del self[nick]
                except KeyError:
                    pass


class UserCache(ServerChannelDict):
    def generate_cache(self, server, channel):
        users = UserList()
        try:
            infolist = Infolist('irc_nick', '%s,%s' %(server, channel))
        except:
            error('Not in a IRC channel.')
            return users
        while infolist.next():
            name = infolist['name']
            users[name] = '%s!%s' %(name, infolist['host'])
        self[(server, channel)] = users
        return users

    def get(self, server, channel):
        """Return list of users"""
        try:
            return self[server, channel]
        except KeyError:
            return self.generate_cache(server, channel)


        for users in self.itervalues():
            users.purge()

    def hostFromNick(self, nick, server, channel=None):
        """Returns hostmask of nick, searching in all or one channel"""
        if channel:
            users = self.get(server, channel)
            if nick in users:
                return users[nick]
        for key in self.getKeys(server, nick):
            return self[key][nick]


userCache = UserCache()

##############################
### Chanop Command Classes ###

class Op(CommandChanop):
    help = ("Request operator privileges.", "",
            """
            The command used for ask op is defined globally in plugins.var.python.%(name)s.op_command,
            it can be defined per server or per channel in:
              plugins.var.python.%(name)s.op_command.server_name
              plugins.var.python.%(name)s.op_command.server_name.#channel_name""" %{'name':SCRIPT_NAME})
    command = 'oop'

    def execute(self):
        self.get_op()


class Deop(CommandChanop):
    help = ("Drops operator privileges.", "", "")
    command = 'odeop'

    def execute(self):
        self.drop_op()


class Kick(CommandNeedsOp):
    help = ("Kick nick.", "<nick> [<reason>]", "")
    command = 'okick'
    completion = '%(nicks)'

    def execute_op(self, args=None):
        if not args:
            args = self.args
        nick, s, reason = args.partition(' ')
        if not reason:
            reason = self.get_config('kick_reason')
        self.kick(nick, reason)

    def kick(self, nick, reason, **kwargs):
        if self.get_config_boolean('enable_remove'):
            cmd = '/quote remove %s %s :%s' %(self.channel, nick, reason)
        else:
            cmd = '/kick %s %s' %(nick, reason)
        self.queue(cmd, **kwargs)


class MultiKick(Kick):
    help = ("Kick one or more nicks.",
            "<nick> [<nick> ..] [:] [<reason>]",
            """
            Note: Is not needed, but use ':' as a separator between nicks and the reason.
                  Otherwise, if there's a nick in the channel matching the first word in
                  reason it will be kicked.""")
    completion = '%(nicks)|%*'

    def execute_op(self, args=None):
        if not args:
            args = self.args
        args = args.split()
        nicks = []
        #debug('multikick: %s' %str(args))
        while(args):
            nick = args[0]
            if nick[0] == ':' or not self.is_nick(nick):
                break
            nicks.append(args.pop(0))
        #debug('multikick: %s, %s' %(nicks, args))
        reason = ' '.join(args).lstrip(':')
        if nicks:
            if not reason:
                reason = self.get_config('kick_reason')
            for nick in nicks:
                self.kick(nick, reason)
        else:
            say("Sorry, found nothing to kick.", buffer=self.buffer)
            self.queue_clear()


class Ban(CommandNeedsOp):
    help = ("Ban user or hostmask.",
            "<nick|banmask> [<nick|banmask> ..] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            """
            Banmask options:
                -h --host: Use *!*@hostname banmask
                -n --nick: Use nick!*@* banmask
                -u --user: Use *!user@* banmask
                -e --exact: Use exact hostmask, same as using --nick --user --host
                            simultaneously.

            If no banmask options are supplied, configured defaults are used.

            Example:
            /oban somebody --user --host : will use a *!user@hostname banmask.""")
    command = 'oban'
    completion = '%(chanop_nicks)|%(chanop_ban_mask)|%*'
    masklist = banlist
    banmask = []
    _mode = 'b'
    _prefix = '+'

    def parse_args(self, *args):
        CommandNeedsOp.parse_args(self, *args)
        self._parse_args(self, *args)

    def _parse_args(self, *args):
        args = self.args.split()
        try:
            (opts, args) = getopt.gnu_getopt(args, 'hunew', ('host', 'user', 'nick', 'exact',
                'webchat'))
        except getopt.GetoptError, e:
            raise Exception, e
        self.banmask = []
        for k, v in opts:
            if k in ('-h', '--host'):
                self.banmask.append('host')
            elif k == '--host2':
                self.banmask.append('host2')
            elif k == '--host1':
                self.banmask.append('host1')
            elif k in ('-u', '--user'):
                self.banmask.append('user')
            elif k in ('-n', '--nick'):
                self.banmask.append('nick')
            elif k in ('-w', '--webchat'):
                self.banmask.append('webchat')
            elif k in ('-e', '--exact'):
                self.banmask = ['exact']
                break
        if not self.banmask:
            self.banmask = self.get_default_banmask()
        self.args = ' '.join(args)

    def get_default_banmask(self):
        return get_config_banmask(get_function=self.get_config)

    def make_banmask(self, hostmask):
        assert self.banmask # really, if there isn't any banmask by now there's something wrong
        if 'exact' in self.banmask:
            return hostmask
        elif 'webchat' in self.banmask:
            user = get_user(hostmask, trim=True)
            if is_ip(hex_to_ip(user)):
                return '*!%s@*' %get_user(hostmask)
            else:
                return '*!*@%s' %get_host(hostmask)
        nick = user = host = '*'
        if 'nick' in self.banmask:
            nick = get_nick(hostmask)
        if 'user' in self.banmask:
            user = get_user(hostmask)
        if 'host' in self.banmask:
            host = get_host(hostmask)
        banmask = '%s!%s@%s' %(nick, user, host)
        return banmask

    def execute_op(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            mask = arg
            if not is_hostmask(arg):
                hostmask = self.get_host(arg)
                if hostmask:
                    mask = self.make_banmask(hostmask)
                    if self.has_voice(arg):
                        self.devoice(arg)
            banmasks.append(mask)
        if banmasks:
            banmasks = set(banmasks) # remove duplicates
            self.ban(*banmasks)
        else:
            say("Sorry, found nothing to ban.", buffer=self.buffer)
            self.queue_clear()

    def mode_is_supported(self):
        return supported_modes(self.server, self._mode)

    def ban(self, *banmasks, **kwargs):
        if self._mode != 'b' and not self.mode_is_supported():
            error("%s doesn't seem to support channel mode '%s', using regular ban." %(self.server,
                self._mode))
            mode = 'b'
        else:
            mode = self._mode
        max_modes = self.get_config_int('modes')
        for n in range(0, len(banmasks), max_modes):
            slice = banmasks[n:n+max_modes]
            bans = ' '.join(slice)
            cmd = '/mode %s%s %s' %(self._prefix, mode*len(slice), bans)
            self.queue(cmd, **kwargs)


class UnBan(Ban):
    help = ("Remove bans.",
            "<nick|banmask> [<nick|banmask> ..]",
            """
            Note: Unbaning with <nick> is not very useful at the momment, only the bans known by the
                  script (bans that were applied with this script) will be removed and only *if*
                  <nick> is present in the channel.""")
    command = 'ounban'
    completion = '%(chanop_nicks)|%(chanop_unban_mask)|%*'
    _prefix = '-'

    def search_masks(self, s):
        if is_nick(s):
            return self.masklist.searchByNick(s, self.server, self.channel)
        elif is_hostmask(s):
            return self.masklist.searchByHostmask(s, self.server, self.channel)
        return []

    def execute_op(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            masks = self.search_masks(arg)
            if masks:
                banmasks.extend(masks)
            else:
                banmasks.append(arg)
        if banmasks:
            self.unban(*banmasks)
        else:
            say("Couldn't find any mask for remove with '%s'" %self.args, buffer=self.buffer)
            self.queue_clear()

    unban = Ban.ban


class Mute(Ban):
    help = ("Silence user or hostmask.",
            Ban.help[1],
            """
            Use /ounban <nick> for remove the mute.

            Note: This command is disabled by default and should be enabled for networks that
                  support "/mode +q hostmask", use:
                  /set plugins.var.python.%s.enable_mute.your_server_name on""" %SCRIPT_NAME)
    command = 'omute'
    completion = '%(chanop_nicks)|%(chanop_ban_mask)|%*'
    _mode = 'q'
    masklist = mutelist


class UnMute(UnBan):
    command = 'ounmute'
    completion = '%(chanop_nicks)|%(chanop_unmute_mask)|%*'
    _mode = 'q'
    masklist = mutelist


class KickBan(Ban, Kick):
    help = ("Kickban nick.",
            "<nick> [<reason>] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            "Combines /okick and /oban commands.")
    command = 'okban'
    completion = '%(chanop_nicks)'

    def execute_op(self):
        nick, s, reason = self.args.partition(' ')
        hostmask = self.get_host(nick)
        if hostmask:
            if not reason:
                reason = self.get_config('kick_reason')
            banmask = self.make_banmask(hostmask)
            if not self.get_config_boolean('invert_kickban_order'):
                self.kick(nick, reason, wait=0)
                self.ban(banmask)
            else:
                self.ban(banmask, wait=0)
                self.kick(nick, reason)
        else:
            say("Sorry, found nothing to kickban.", buffer=self.buffer)
            self.queue_clear()


class MultiKickBan(KickBan):
    help = ("Kickban one or more nicks.",
            "<nick> [<nick> ..] [:] [<reason>] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            KickBan.help[2])
    completion = '%(chanop_nicks)|%*'

    def execute_op(self):
        args = self.args.split()
        nicks = []
        while(args):
            nick = args[0]
            if nick[0] == ':' or not self.is_nick(nick):
                break
            nicks.append(args.pop(0))
        reason = ' '.join(args).lstrip(':')
        if nicks:
            if not reason:
                reason = self.get_config('kick_reason')
            for nick in nicks:
                hostmask = self.get_host(nick)
                if hostmask:
                    banmask = self.make_banmask(hostmask)
                    if not self.get_config_boolean('invert_kickban_order'):
                        self.kick(nick, reason, wait=0)
                        self.ban(banmask)
                    else:
                        self.ban(banmask, wait=0)
                        self.kick(nick, reason)
        else:
            say("Sorry, found nothing to kickban.", buffer=self.buffer)
            self.queue_clear()


class Topic(CommandNeedsOp):
    help = ("Changes channel topic.", "[-delete | topic]",
            "Clear topic if '-delete' is the new topic.")
    command = 'otopic'
    completion = '%(irc_channel_topic)||-delete'

    def execute_op(self):
        self.topic(self.args)

    def topic(self, topic):
        cmd = '/topic %s' %topic
        self.queue(cmd)


class Voice(CommandNeedsOp):
    help = ("Gives voice to somebody.", "nick", "")
    command = 'ovoice'
    completion = '%(nicks)'

    def execute_op(self):
        self.voice(self.args)


class DeVoice(Voice):
    help = ("Removes voice from somebody.", "nick", "")
    command = 'odevoice'

    def execute_op(self):
        self.devoice(self.args)


class Mode(CommandNeedsOp):
    help = ("Changes channel modes.", "",
            "")
    command = 'omode'

    def execute_op(self):
        self.mode(self.args)

    def mode(self, modes):
        cmd = '/mode %s' %modes
        self.queue(cmd)


class ShowBans(CommandChanop):
    command = 'olist'
    completion = 'bans|mutes %(irc_server_channels)'
    showbuffer = ''

    def parse_args(self, data, buffer, args):
        self.buffer = buffer
        self.server = weechat.buffer_get_string(self.buffer, 'localvar_server')
        self.channel = weechat.buffer_get_string(self.buffer, 'localvar_channel')
        type, _, args = args.partition(' ')
        if not type:
            raise ValueError, 'missing argument'
        if type == 'bans':
            self.mode = 'b'
        elif type == 'mutes':
            self.mode = 'q'
        else:
            raise ValueError, 'incorrect argument'
        self.type = type
        self.args = args.strip()

    def get_buffer(self):
        if self.showbuffer:
            return self.showbuffer
        buffer = weechat.buffer_search('python', SCRIPT_NAME)
        if not buffer:
            buffer = weechat.buffer_new(SCRIPT_NAME, '', '', '', '')
            weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
            weechat.buffer_set(buffer, 'time_for_each_line', '0')
        self.showbuffer = buffer
        return buffer

    def prnt(self, s):
        weechat.prnt(self.get_buffer(), s)

    def prnt_ban(self, banmask, op, when, hostmask=None):
        padding = self.padding - len(banmask)
        if padding < 0:
            padding = 0
        padding = '.'*padding
        self.prnt('%s%s%s %sset by %s%s%s at %s' %(color_mask, banmask, color_reset,
                padding, color_chat_nick, op, color_reset, when))
        if hostmask:
            if not isinstance(hostmask, str):
                hostmask = ' '.join(hostmask)
            self.prnt('  %s%s' %(color_chat_host, hostmask))

    def clear(self):
        b = self.get_buffer()
        weechat.buffer_clear(b)
        weechat.buffer_set(b, 'display', '1')

    def set_title(self, s):
        weechat.buffer_set(self.get_buffer(), 'title', s)

    def execute(self):
        try:
            self.padding = int(weechat.config_get_plugin('padding'))
        except:
            self.padding = 40
        self.clear()
        masklist = maskModes[self.mode]
        if not masklist:
            self.prnt("No %s known." %self.type)
            return
        # XXX fails if used in a non irc buffer, display message or something
        if self.args:
            key = (self.server, self.args)
        else:
            key = (self.server, self.channel)
        try:
            masks = masklist[key]
        except KeyError:
            masks = None
        mask_count = 0
        if masks:
            mask_count = len(masks)
            self.prnt('\n%s[%s %s]' %(color_channel, key[0], key[1]))
            masks = [ m for m in masks.itervalues() ]
            masks.sort(key=lambda x: x.date)
            for ban in masks:
                op = ban.operator and get_nick(ban.operator) or self.server
                self.prnt_ban(ban.mask, op, ban.date, ban.hostmask)
        else:
            self.prnt('Not known %s for %s.%s' %(self.type, key[0], key[1]))
        self.set_title('List of %s known by chanop in %s.%s (total: %s)' %(self.type, key[0],
            key[1], mask_count))


#########################
### WeeChat callbacks ###

### Init stuff ###
global chanop_channels
chanop_channels = CaseInsensibleSet()
def chanop_init():
    global chanop_channels
    servers = Infolist('irc_server')
    fetch_bans = get_config_boolean('fetch_bans')
    while servers.next():
        if servers['is_connected']:
            server = servers['name']
            channels = get_config_list('channels.%s' %server)
            chanop_channels.update([ (server, channel) for channel in channels ])
            for channel in channels:
                userCache.generate_cache(server, channel)
                if fetch_bans:
                    for mode in supported_modes(server):
                        maskModes[mode].fetch(server, channel)

def is_tracked(server, channel):
    """Check if a server channel pair should be tracked by script"""
    global chanop_channels
    return (server, channel) in chanop_channels


### Ban list ###
def signal_parse(f):
    def decorator(data, signal, signal_data):
        server = signal[:signal.find(',')]
        channel = signal_data.split()[2].lstrip(':')
        nick = get_nick(signal_data)
        return f(server, channel, nick, data, signal, signal_data)
    decorator.func_name = f.func_name
    return decorator

def signal_parse_no_channel(f):
    def decorator(data, signal, signal_data):
        server = signal[:signal.find(',')]
        nick = get_nick(signal_data)
        keys = userCache.getKeys(server, nick)
        if keys:
            return f(keys, nick, data, signal, signal_data)
        return WEECHAT_RC_OK
    decorator.func_name = f.func_name
    return decorator

@signal_parse
def mode_cb(server, channel, nick, data, signal, signal_data):
    """Keep the banmask list updated when somebody changes modes"""
    #debug('MODE: %s' %' '.join((server, channel, nick, data, signal, signal_data)))
    #:m4v!~znc@unaffiliated/m4v MODE #test -bo+v asd!*@* m4v dude
    modes, args = signal_data.split(' ', 4)[3:]
    if len(modes) == 2 and modes[1] in 'ovjml':
        # return for these modes fairly used but not useful to us
        return WEECHAT_RC_OK
    key = (server, channel)
    allkeys = CaseInsensibleSet()
    for masklist in maskModes.itervalues():
        allkeys.update(masklist)
        if key not in allkeys and not is_tracked(server, channel):
            # from a channel we're not tracking
            return WEECHAT_RC_OK
    servermodes = set(supported_modes(server))
    if servermodes.intersection(set(modes)):
        # split chanmodes into tuples like ('+', 'b', 'asd!*@*')
        action = ''
        L = []
        args = args.split()
        op = signal_data[1:signal_data.find(' ')]
        for c in modes:
            if c in '+-':
                action = c
            elif c in servermodes:
                L.append((action, c, args.pop(0)))
            elif c in 'ov': # these have an argument, drop it
                del args[0]
        affected_users = []
        # update masklist
        for action, mode, mask in L:
            masklist = maskModes[mode]
            #debug('MODE: %s%s %s %s' %(action, mode, mask, op))
            if action == '+':
                hostmask = hostmask_pattern_match(mask, userCache.get(*key).itervalues())
                if hostmask:
                    affected_users.extend(hostmask)
                masklist.add(server, channel, mask, operator=op, hostmask=hostmask)
            elif action == '-':
                masklist.remove(server, channel, mask)
        if affected_users and get_config_boolean('display_affected'):
            buffer = weechat.buffer_search('irc', '%s.%s' %key)
            print_affected_users(buffer, *set(affected_users))
    return WEECHAT_RC_OK


### User list ###
@signal_parse
def join_cb(server, channel, nick, data, signal, signal_data):
    #debug('JOIN: %s' %' '.join((server, channel, nick, data, signal, signal_data)))
    key = (server, channel)
    if nick == weechat.info_get('irc_nick', server):
        if is_tracked(server, channel):
            # joined a channel that we should track
            userCache.generate_cache(server, channel)
            for mode in supported_modes(server):
                maskModes[mode].fetch(server, channel)
    elif key in userCache:
        hostname = signal_data[1:signal_data.find(' ')]
        userCache[key][nick] = hostname
    return WEECHAT_RC_OK

@signal_parse
def part_cb(server, channel, nick, data, signal, signal_data):
    #debug('PART: %s' %' '.join((server, channel, nick, data, signal, signal_data)))
    key = (server, channel)
    if key in userCache:
        userCache[key].remove(nick)
    return WEECHAT_RC_OK

@signal_parse_no_channel
def quit_cb(keys, nick, data, signal, signal_data):
    for key in keys:
        userCache[key].remove(nick)
    return WEECHAT_RC_OK

@signal_parse_no_channel
def nick_cb(keys, nick, data, signal, signal_data):
    #debug('NICK: %s' %' '.join((data, signal, signal_data)))
    hostname = signal_data[1:signal_data.find(' ')]
    newnick = signal_data[signal_data.rfind(' ')+2:]
    newhostname = '%s!%s' %(newnick, hostname[hostname.find('!')+1:])
    for key in keys:
        userCache[key].remove(nick)
        userCache[key][newnick] = newhostname
    return WEECHAT_RC_OK


### Garbage collector ###
def garbage_collector_cb(data, counter):
    for masklist in maskModes.itervalues():
        masklist.purge()

    userCache.purge()

    if weechat.config_get_plugin('debug'):
        user_count = sum(map(len, userCache.itervalues()))
        temp_user_count = sum(map(lambda x: len(x._temp_users), userCache.itervalues()))
        for mode, masklist in maskModes.iteritems():
            mask_count = sum(map(len, masklist.itervalues()))
            mask_chan = len(masklist)
            debug("collector: %s '%s' cached masks in %s channels" %(mask_count, mode, mask_chan))
        debug('collector: %s cached users in %s channels' %(user_count, len(userCache)))
        debug('collector: %s users about to be purged' %temp_user_count)
        debug('collector: %s cached regexps' %len(_regexp_cache))
    return WEECHAT_RC_OK


### Config callbacks ###
def enable_multi_kick_conf_cb(data, config, value):
    global cmd_kick, cmd_kban
    cmd_kick.unhook()
    cmd_kban.unhook()
    if boolDict[value]:
        cmd_kick = MultiKick()
        cmd_kban = MultiKickBan()
    else:
        cmd_kick = Kick()
        cmd_kban = KickBan()
    cmd_kick.hook()
    cmd_kban.hook()
    return WEECHAT_RC_OK

def update_chanop_channels_cb(data, config, value):
    #debug('CONFIG: %s' %(' '.join((data, config, value))))
    global chanop_channels
    server = config[config.rfind('.')+1:]
    if value:
        L = value.split(',')
    else:
        L = []
    chanop_channels[server] = CaseInsensibleSet(L)
    return WEECHAT_RC_OK


###########################
### WeeChat completions ###

def cmpl_get_irc_users(f):
    """
    Decorator for check if completion is done in a irc channel, and pass the buffer's user list
    if so."""
    def decorator(data, completion_item, buffer, completion):
        key = irc_buffer(buffer)
        if not key:
            return WEECHAT_RC_OK
        users = userCache.get(*key)
        return f(users, data, completion_item, buffer, completion)
    return decorator

global waiting_for_completion, cmpl_mask_args
waiting_for_completion = None
cmpl_mask_args = None
def unban_mask_cmpl(mode, completion_item, buffer, completion):
    """Completion for applied banmasks, for commands like /ounban /ounmute"""
    masklist = maskModes[mode]
    key = irc_buffer(buffer)
    if not key:
        return WEECHAT_RC_OK
    server, channel = key
    if key not in masklist:
        # do completion in masklist_end_cb function
        global waiting_for_completion, cmpl_mask_args
        input = weechat.buffer_get_string(buffer, 'input')
        if input[-1] != ' ':
            input, _, cmpl_mask_args = input.rpartition(' ')
        input = input.strip()
        masklist.fetch(server, channel)
        # check if it's fetching a banlist or nothing (due to fetching too soon)
        if MaskCache.hook_fetch:
            waiting_for_completion = (buffer, completion)
            if 'fetching masks' not in input:
                weechat.buffer_set(buffer, 'input', '%s fetching masks...' %input)
        else:
            weechat.buffer_set(buffer, 'input', '%s nothing.' %input)
    else:
        # mask list updated, do completion
        input = weechat.buffer_get_string(buffer, 'input')
        input, _, pattern = input.rpartition(' ')
        cmpl_unban(buffer, server, channel, completion, masklist, input, pattern)
    return WEECHAT_RC_OK

def cmpl_unban(buffer, server, channel, completion, masklist, input, pattern):
    """Updates input with masks if pattern given or feeds the completion list"""
    masks = masklist[server, channel]
    if pattern:
        L = masklist.search(pattern, server, channel)
        if L:
            weechat.buffer_set(buffer, 'input', '%s %s ' %(input, ' '.join(L)))
            return
    elif not masks:
            weechat.buffer_set(buffer, 'input', '%s nothing.' %input)
            return
    for mask in masks.iterkeys():
        weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_SORT)

@cmpl_get_irc_users
def ban_mask_cmpl(users, data, completion_item, buffer, completion):
    """Completion for banmasks, for commands like /oban /omute"""
    input = weechat.buffer_get_string(buffer, 'input')
    if input[-1] == ' ':
        # no pattern, return
        return WEECHAT_RC_OK

    input, _, pattern = input.rpartition(' ')
    if pattern[-1] != '*':
        search_pattern = pattern + '*'
    else:
        search_pattern = pattern

    if '@' in pattern:
        # complete *!*@hostname
        prefix = pattern[:pattern.find('@')]
        make_mask = lambda mask : '%s@%s' %(prefix, mask[mask.find('@')+1:])
    elif '!' in pattern:
        # complete *!username@*
        prefix = pattern[:pattern.find('!')]
        make_mask = lambda mask : '%s!%s@*' %(prefix, mask[mask.find('!')+1:mask.find('@')])
    else:
        # complete nick!*@*
        make_mask = lambda mask : '%s!*@*' %get_nick(mask)

    masks = pattern_match(search_pattern, users.itervalues())
    for mask in masks:
        mask = make_mask(mask)
        weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK

### Completions for nick, user and host parts of a usermask ###
@cmpl_get_irc_users
def nicks_cmpl(users, data, completion_item, buffer, completion):
    for nick in users:
        weechat.hook_completion_list_add(completion, nick, 0, weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK

@cmpl_get_irc_users
def hosts_cmpl(users, data, completion_item, buffer, completion):
    for hostmask in users.itervalues():
        weechat.hook_completion_list_add(completion, get_host(hostmask), 0, weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK

@cmpl_get_irc_users
def users_cmpl(users, data, completion_item, buffer, completion):
    for hostmask in users.itervalues():
        user = get_user(hostmask, trim=True)
        weechat.hook_completion_list_add(completion, user, 0, weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK


### Register Script and set configs ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

    # colors
    color_delimiter = weechat.color('chat_delimiters')
    color_chat_nick = weechat.color('chat_nick')
    color_chat_host = weechat.color('chat_host')
    color_mask      = weechat.color('white')
    color_channel   = weechat.color('lightred')
    color_reset     = weechat.color('reset')

    # pretty [chanop]
    script_nick = '%s[%s%s%s]%s' %(color_delimiter, color_chat_nick, SCRIPT_NAME, color_delimiter,
            color_reset)

    # valid nick, use weechat's api if available
    version = weechat.info_get('version_number', '')
    if not version or version < 0x30200:
        _nickchars = r'[]\`_^{|}'
        _nickRe = re.compile(r'^[A-Za-z%s][-0-9A-Za-z%s]*$' %(re.escape(_nickchars), re.escape(_nickchars)))
        is_nick = lambda s: bool(_nickRe.match(s))
    else:
        is_nick = lambda s: weechat.info_get('irc_is_nick', s)

    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    chanop_init()

    # hook /oop /odeop
    Op().hook()
    cmd_deop = Deop()
    cmd_deop.hook()
    # hook /okick /okban
    if get_config_boolean('enable_multi_kick'):
        cmd_kick = MultiKick()
        cmd_kban = MultiKickBan()
    else:
        cmd_kick = Kick()
        cmd_kban = KickBan()
    cmd_kick.hook()
    cmd_kban.hook()
    # hook /oban /ounban /olist
    Ban().hook()
    UnBan().hook()
    ShowBans().hook()
    # hook /omute /ounmute
    Mute().hook()
    UnMute().hook()
    # hook /otopic /omode /ovoive /odevoice
    Topic().hook()
    Mode().hook()
    Voice().hook()
    DeVoice().hook()

    weechat.hook_config('plugins.var.python.%s.enable_multi_kick' %SCRIPT_NAME,
            'enable_multi_kick_conf_cb', '')
    weechat.hook_config('plugins.var.python.%s.channels.*' %SCRIPT_NAME,
            'update_chanop_channels_cb', '')

    weechat.hook_completion('chanop_unban_mask', '', 'unban_mask_cmpl', 'b')
    weechat.hook_completion('chanop_unmute_mask', '', 'unban_mask_cmpl', 'q')
    weechat.hook_completion('chanop_ban_mask', '', 'ban_mask_cmpl', '')
    weechat.hook_completion('chanop_nicks', '', 'nicks_cmpl', '')
    weechat.hook_completion('chanop_users', '', 'users_cmpl', '')
    weechat.hook_completion('chanop_hosts', '', 'hosts_cmpl', '')

    weechat.hook_signal('*,irc_in_join', 'join_cb', '')
    weechat.hook_signal('*,irc_in_part', 'part_cb', '')
    weechat.hook_signal('*,irc_in_quit', 'quit_cb', '')
    weechat.hook_signal('*,irc_in_nick', 'nick_cb', '')
    weechat.hook_signal('*,irc_in_mode', 'mode_cb', '')

    weechat.hook_timer(30*60*1000, 0, 0, 'garbage_collector_cb', '')

    # debug commands
    #weechat.hook_command('ocaches', '', '', '', '', 'debug_print_cache', '')
    #weechat.hook_command('ocollect', '', '', '', '', 'debug_garbage_collector', '')
    #weechat.hook_command('otime', '', '', '', '', 'debug_print_time_avg', '')



# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
