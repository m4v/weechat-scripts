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
#  Helper script for IRC operators
#
#  TODO for v1.0
#  * wait until got op before sending commands
#  * implement freenode's remove and mute commands
#  * unban command
#  * command for switch channel moderation on/off
#  * implement ban with channel forward
#
#  TODO for later
#  * bans expire time
#  * bantracker (keeps a record of ban and kicks)
#  * user tracker (for ban even when they already /part)
#  * ban by gecos
#  * smart banmask (?)
###

SCRIPT_NAME    = "operator"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Helper script for IRC operators"

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    #WEECHAT_RC_ERROR = weechat.WEECHAT_RC_ERROR
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://weechat.flashtux.org/"
    import_ok = False

import getopt

def debug(s, prefix='', buffer=''):
    """Debug msg"""
    weechat.prnt(buffer, 'debug:\t%s %s' %(prefix, s))

def error(s, prefix='', buffer=''):
    """Error msg"""
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), prefix, s))

def say(s, prefix='', buffer=''):
    """Normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

class BoolDict(dict):
    def __init__(self):
        self['on'] = True
        self['off'] = False

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            error("'%s' is an invalid value, allowed: 'on', 'off'. Fix it." %key)
            raise KeyError

class ValidValues(list):
    def __init__(self, *args):
        self.extend(args)

    def __getitem__(self, key):
        if key not in self:
            error("'%s' is an invalid value, allowed: %s. Fix it." %(key, self))
            raise KeyError
        return key

boolDict = BoolDict()

def get_config_boolean(config, default=None):
    value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        error("Error while fetching config '%s'. Using default." %config)
        return settings[config]


### irc utils
def is_hostmask(s):
    """Returns whether or not the string s is a valid User hostmask."""
    n = s.find('!')
    m = s.find('@')
    if n < m-1 and n >= 1 and m >= 3 and len(s) > m+1:
        return True
    else:
        return False


### WeeChat Classes
class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'name':'string',
            'host':'string',
            'flags':'integer',
            }

    def __init__(self, name, args=''):
        self.cursor = 0
        self.pointer = weechat.infolist_get(name, '', args)
        if self.pointer == '':
            raise Exception('Infolist initialising failed')

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
            weechat.infolist_free(self.pointer)
            self.pointer = ''


class Command(object):
    """Class for hook WeeChat commands."""
    help = ("WeeChat command.", "[define usage template]", "detailed help here")

    def __init__(self, command, callback, completion=''):
        self.command = command
        self.callback = callback
        self.completion = completion
        self.pointer = ''
        self.hook()

    def __call__(self, *args):
        self.parse_args(*args)
        self.cmd()
        return WEECHAT_RC_OK

    def parse_args(self, data, buffer, args):
        """Do arg parsing here."""
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

    def cmd(self):
        """This method is called when the command is run, override this."""
        pass

    def hook(self):
        assert self.command and self.callback
        assert not self.pointer, "There's already a hook pointer, unhook first"
        desc, usage, help = self._parse_doc()
        self.pointer = weechat.hook_command(self.command, desc, usage, help, self.completion,
                self.callback, '')
        if self.pointer == '':
            raise Exception, "hook_command failed"

    def unhook(self):
        if self.pointer:
            weechat.unhook(self.pointer)
            self.pointer = ''


### Script Classes
class CommandQueue(object):
    commands = []
    wait = 0
    def queue(self, buffer, cmd, wait=1):
        cmd = (buffer, cmd, wait)
        debug('queue cmd:%s' %(cmd, ))
        self.commands.append(cmd)

    def safe_check(f):
        def abort_if_too_many_commands(self):
            if len(self.commands) > 10:
                error("Too many commands in queue, must be a bug!")
                error("last 10 commnads:")
                for cmd in self.commands[-10:]:
                    error(str(cmd))
                self.clear()
            else:
                f(self)
        return abort_if_too_many_commands

    @safe_check
    def run(self):
        for buffer, cmd, wait in self.commands:
            debug('running cmd:%s wait:%s' %(cmd, self.wait))
            if self.wait:
                weechat.command(buffer, '/wait %s %s' %(self.wait, cmd))
            else:
                weechat.command(buffer, cmd)
            self.wait += wait
        self.clear()

    def clear(self):
        self.commands = []
        self.wait = 0


weechat_commands = CommandQueue()

class CommandOperator(Command):
    infolist = None
    def __call__(self, *args):
        debug("command __call__ args: %s" %(args,))
        self.parse_args(*args)
        self.cmd()
        weechat_commands.run()
        self.infolist = None
        return WEECHAT_RC_OK

    def parse_args(self, data, buffer, args):
        self.buffer = buffer
        self.args = args
        self.server = weechat.buffer_get_string(self.buffer, 'localvar_server')
        self.channel = weechat.buffer_get_string(self.buffer, 'localvar_channel')
        self.nick = weechat.info_get('irc_nick', self.server)

    def replace_vars(self, s):
        if '$channel' in s:
            s = s.replace('$channel', self.channel)
        if '$nick' in s:
            s = s.replace('$nick', self.nick)
        if '$server' in s:
            s = s.replace('$server', self.server)
        return s

    def get_config(self, config):
        string = '%s.%s.%s' %(self.server, self.channel, config)
        value = weechat.config_get_plugin(string)
        if not value:
            string = '%s.%s' %(self.server, config)
            value = weechat.config_get_plugin(string)
            if not value:
                value = weechat.config_get_plugin(config)
        return value

    def get_config_boolean(self, config):
        value = self.get_config(config)
        try:
            return boolDict[value]
        except:
            error("Error while fetching config '%s'. Using default." %config)
            return settings[config]

    def _nick_infolist(self):
        # reuse the same infolist instead of creating it many times
        # per __call__() (like in MultiKick)
        if not self.infolist:
            self.infolist =  Infolist('irc_nick', '%s,%s' %(self.server, self.channel))
            return self.infolist
        else:
            self.infolist.reset()
            return self.infolist

    def is_op(self):
        try:
            nicks = self._nick_infolist()
            while nicks.next():
                if nicks['name'] == self.nick:
                    if nicks['flags'] & 8:
                        return True
                    else:
                        return False
        except:
            error('Not in a IRC channel.')

    def is_nick(self, nick):
        nicks = self._nick_infolist()
        while nicks.next():
            if nicks['name'] == nick:
                return True
        return False

    def get_host(self, name):
        nicks = self._nick_infolist()
        while nicks.next():
            if nicks['name'] == name:
                return '%s!%s' % (name, nicks['host'])

    def queue(self, cmd, wait=1):
        weechat_commands.queue(self.buffer, cmd, wait)

    def get_op_cmd(self):
        value = self.get_config('op_cmd')
        if not value:
            raise Exception, "No command defined for get op."
        return self.replace_vars(value)

    def get_deop_cmd(self):
        value = self.get_config('deop_cmd')
        if not value:
            return '/deop'
        return self.replace_vars(value)

    def get_op(self):
        op = self.is_op()
        if op is False:
            self.queue(self.get_op_cmd())
        return op

    def drop_op(self):
        op = self.is_op()
        if op is True:
            self.queue(self.get_deop_cmd())


deop_hook = ''
deop_callback = None
class CommandNeedsOp(CommandOperator):
    def cmd(self, *args):
        op = self.get_op()
        global manual_op
        if op is None:
            return WEECHAT_RC_OK
        elif op is False:
            manual_op = False
        self._cmd(*args)
        # don't deop if we weren't auto-op'ed
        if not manual_op and self.get_config_boolean('deop_after_use'):
            delay = int(self.get_config('deop_delay'))
            if delay > 0:
                global deop_hook, deop_callback
                if deop_hook:
                    weechat.unhook(deop_hook)

                def callback(data, count):
                    cmd_deop('', self.buffer, self.args)
                    deop_hook = ''
                    return WEECHAT_RC_OK

                deop_callback = callback
                deop_hook = weechat.hook_timer(delay * 1000, 0, 1, 'deop_callback', '')
            else:
                self.drop_op()

    def _cmd(self, *args):
        """Commands in this method will be run while user is with op status."""
        pass


### Operator Commands ###
manual_op = False
class Op(CommandOperator):
    help = ("Asks operator status.", "",
            """
            The command used for ask op is defined globally in plugins.var.python.%(name)s.op_cmd,
            it can be defined per server or per channel in:
              plugins.var.python.%(name)s.'server_name'.op_cmd
              plugins.var.python.%(name)s.'server_name'.'channel_name'.op_cmd""" %{'name':SCRIPT_NAME})

    def cmd(self):
        global manual_op
        manual_op = True
        self.get_op()


class Deop(CommandOperator):
    help = ("Drops operator status.", "", "")

    def cmd(self):
        self.drop_op()


class Kick(CommandNeedsOp):
    help = ("Kicks nick. Request operator status if needed.", "<nick> [<reason>]", "")

    def _cmd(self, args=None):
        if not args:
            args = self.args
        if ' ' in args:
            nick, reason = args.split(' ', 1)
        else:
            nick, reason = args, ''
        if not reason:
            reason = self.get_config('kick_reason')
        self.kick(nick, reason)

    def kick(self, nick, reason):
        cmd = '/kick %s %s' %(nick, reason)
        self.queue(cmd)


class MultiKick(Kick):
    help = ("Kicks nicks, can be more than one. Request operator status if needed.",
            "<nick> [<nick> ...] [:] [<reason>]",
            """
            Note: Is not needed, but use ':' as a separator between nicks and the reason.
                  Otherwise, if there's a nick in the channel matching the reason it will
                  be kicked.""")

    def _cmd(self, args=None):
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
        if not reason:
            reason = self.get_config('kick_reason')
        for nick in nicks:
            self.kick(nick, reason)


class Ban(CommandNeedsOp):
    help = ("Bans users. Request operator status if needed.",
            "<nick> [<nick> ..] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            """
            Banmask options:
                -h --host: Use *!*@hostname banmask
                -n --nick: Use nick!*@* banmask
                -u --user: Use *!user@* banmask
                -e --exact: Use exact hostmask, same as using --nick --user --host
                            simultaneously.

            If no banmask options are supplied, uses configured defaults.

            Example:
            /oban troll --user --host : will use a *!user@hostname banmask.""")

    banmask = []
    valid_banmask = ValidValues('nick', 'user', 'host', 'exact')
    def parse_args(self, *args):
        CommandNeedsOp.parse_args(self, *args)
        args = self.args.split()
        (opts, args) = getopt.gnu_getopt(args, 'hune', ('host', 'user', 'nick', 'exact'))
        self.banmask = []
        for k, v in opts:
            if k in ('-h', '--host'):
                self.banmask.append('host')
            elif k in ('-u', '--user'):
                self.banmask.append('user')
            elif k in ('-n', '--nick'):
                self.banmask.append('nick')
            elif k in ('-e', '--exact'):
                self.banmask = ['nick', 'user', 'host']
                break
        if not self.banmask:
            self.banmask = self.get_default_banmask()
        self.args = ' '.join(args)

    def get_default_banmask(self):
        value = self.get_config('default_banmask')
        values = value.split(',')
        for value in values:
            try:
                self.valid_banmask[value]
            except KeyError:
                error("Error while fetching default banmask. Using default.")
                return settings['default_banmask']
        return values

    def make_banmask(self, hostmask):
        if not self.banmask:
            # FIXME this will not be safe with MergedBan
            return hostmask[:hostmask.find('!')]
        nick = user = host = '*'
        if 'nick' in self.banmask:
            nick = hostmask[:hostmask.find('!')]
        if 'user' in self.banmask:
            user = hostmask.split('!',1)[1].split('@')[0]
        if 'host' in self.banmask:
            host = hostmask[hostmask.find('@') + 1:]
        banmask = '%s!%s@%s' %(nick, user, host)
        return banmask

    def _cmd(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            mask = arg
            if not is_hostmask(arg):
                hostmask = self.get_host(arg)
                if hostmask:
                    mask = self.make_banmask(hostmask)
            banmasks.append(mask)
        if banmasks:
            self.ban(*banmasks)

    def ban(self, *args):
        cmd = '/ban %s' %' '.join(args)
        self.queue(cmd)


class UnBan(Ban):
    def _cmd(self):
        args = self.args.split()
        self.unban(*args)

    def unban(self, *args):
        cmd = '/unban %s' %' '.join(args)
        self.queue(cmd)


class MergedBan(Ban):
    unban = False
    def ban(self, *args):
        c = self.unban and '-' or '+'
        # do 4 bans per command
        for n in range(0, len(args), 4):
            slice = args[n:n+4]
            hosts = ' '.join(slice)
            cmd = '/mode %s%s %s' %(c, 'b'*len(slice), hosts)
            self.queue(cmd)


class KickBan(Ban, Kick):
    help = ("Kickban user. Request operator status if needed.",
            "<nick> [<reason>] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            "Combines /okick and /oban commands.")

    invert = False
    def _cmd(self):
        if ' ' in self.args:
            nick, reason = self.args.split(' ', 1)
        else:
            nick, reason = self.args, ''
        hostmask = self.get_host(nick)
        if hostmask:
            banmask = self.make_banmask(hostmask)
            if self.invert:
                self.kick(nick, reason)
                self.ban(banmask)
            else:
                self.ban(banmask)
                self.kick(nick, reason)


### config callbacks ###
def enable_multiple_kick_conf_cb(data, config, value):
    global cmd_kick
    cmd_kick.unhook()
    if boolDict[value]:
        cmd_kick = MultiKick('okick', 'cmd_kick')
    else:
        cmd_kick = Kick('okick', 'cmd_kick')
    return WEECHAT_RC_OK

def merge_bans_conf_cb(data, config, value):
    global cmd_ban
    cmd_ban.unhook()
    if boolDict[value]:
        cmd_ban  = MergedBan('oban', 'cmd_ban')
    else:
        cmd_ban = Ban('okick', 'cmd_kick')
    return WEECHAT_RC_OK

def invert_kickban_order_conf_cb(data, config, value):
    global cmd_kban
    if boolDict[value]:
        cmd_kban.invert = True
    else:
        cmd_kban.invert = False
    return WEECHAT_RC_OK


### Register Script and set configs ###
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

    # settings
    settings = {
            'op_cmd': '/msg chanserv op $channel $nick',
            'deop_cmd': '/deop',
            'deop_after_use': 'on',
            'deop_delay': '300',
            'default_banmask': 'host',
            'kick_reason': 'bye.',
            'enable_multiple_kick': 'off',
            'merge_bans': 'on',
            'invert_kickban_order': 'off'}

    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
                weechat.config_set_plugin(opt, val)

    # hook our commands
    cmd_op   = Op('oop', 'cmd_op')
    cmd_deop = Deop('odeop', 'cmd_deop')

    if get_config_boolean('enable_multiple_kick'):
        cmd_kick = MultiKick('okick', 'cmd_kick')
    else:
        cmd_kick = Kick('okick', 'cmd_kick')

    if get_config_boolean('merge_bans'):
        cmd_ban  = MergedBan('oban', 'cmd_ban')
    else:
        cmd_ban  = Ban('oban', 'cmd_ban')

    # FIXME unban cmd disabled as is not very usefull atm
    #cmd_unban  = UnBan('ounban', 'cmd_unban')

    cmd_kban = KickBan('okban', 'cmd_kban')
    if get_config_boolean('invert_kickban_order'):
        cmd_kban.invert = True

    weechat.hook_config('plugins.var.python.%s.enable_multiple_kick' %SCRIPT_NAME, 'enable_multiple_kick_conf_cb', '')
    weechat.hook_config('plugins.var.python.%s.merge_bans' %SCRIPT_NAME, 'merge_bans_conf_cb', '')
    weechat.hook_config('plugins.var.python.%s.invert_kickban_order' %SCRIPT_NAME, 'invert_kickban_order_conf_cb', '')

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
