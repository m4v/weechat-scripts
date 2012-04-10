# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2011 by Elián Hanisch <lambdae2@gmail.com>
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
#   * plugins.var.python.warn.warning_buffer:
#     Defines where to print warnings.
#     Valid values: 'core', 'channel', 'current', 'warn_buffer'
#     Default: 'core'
#     
#     core:    print in core buffer.
#     channel: print in channel buffer (where the matching user joined)
#     current: print in whatever buffer you're currently looking at.
#     warn_buffer: create a new buffer and print there.
#
#   * plugins.var.python.warn.autowarn_bans:
#     Enable automatically setting warns for bans. When a ban is set, the
#     banmask is used for a new warning. This feature depends of chanop.py
#     script and if the channel is in chanop's watchlist.
#
#   * plugins.var.python.warn.ignore_channels:
#     Comma separated list of patterns for ignore joins in matching channels.
#     Wildcards '*', '?' can be used.
#     An ignore exception can be added by prefixing '!' in the pattern.
#
#   * plugins.var.python.warn.ignore_autowarn_forwards:
#     (only for patterns set from bans when autowarn_bans is enabled)
#     Comma separated list of patterns for ignore bans with a matching channel
#     forward. Wildcards '*', '?' can be used.
#     An ignore exception can be added by prefixing '!' in the pattern.
#
###

SCRIPT_NAME    = "warn"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Monitor join messages and warn about known users."

settings = {
        'warning_buffer'             : 'core',
        'autowarn_bans'              : 'on',
        'ignore_channels'            : '',
        'ignore_autowarn_forwards'   : '##fix_your_connection',
        } 

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt, prnt_date_tags
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import re
import csv
import time
import string

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
    return '%s%s%s(%s%s%s)%s' % (COLOR_CHAT_NICK,
                                 nick,
                                 COLOR_CHAT_DELIMITERS,
                                 COLOR_CHAT_HOST,
                                 host,
                                 COLOR_CHAT_DELIMITERS,
                                 COLOR_RESET)

def format_color(s, color):
    return '%s%s%s' % (color, s, COLOR_RESET)

def time_elapsed(elapsed, ret=None, level=2):
    time_hour = 3600
    time_day  = 86400
    time_year = 31536000

    if ret is None:
        ret = []

    if not elapsed:
        return ''

    if elapsed > time_year:
        years, elapsed = elapsed // time_year, elapsed % time_year
        ret.append('%s%s' %(years, 'y'))
    elif elapsed > time_day:
        days, elapsed = elapsed // time_day, elapsed % time_day
        ret.append('%s%s' %(days, 'd'))
    elif elapsed > time_hour:
        hours, elapsed = elapsed // time_hour, elapsed % time_hour
        ret.append('%s%s' %(hours, 'h'))
    elif elapsed > 60:
        mins, elapsed = elapsed // 60, elapsed % 60
        ret.append('%s%s' %(mins, 'm'))
    else:
        secs, elapsed = elapsed, 0
        ret.append('%s%s' %(secs, 's'))

    if len(ret) >= level or not elapsed:
        return ' '.join(ret)

    ret = time_elapsed(elapsed, ret, level)
    return ret

# -----------------------------------------------------------------------------
# IRC String

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

valid_strings = set(('core', 'channel', 'current', 'warn_buffer'))
def get_config_valid_string(config, valid_strings=valid_strings):
    value = weechat.config_get_plugin(config)
    if value not in valid_strings:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." % (config, default))
        error("'%s' is an invalid value, allowed: %s." % (value, ', '.join(valid_strings)))
        return default
    return value

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

def get_dir(filename):
    import os
    basedir = weechat.info_get('weechat_dir', '')
    return os.path.join(basedir, filename.lower())

# -----------------------------------------------------------------------------
# WeeChat classes

def catchExceptions(f):
    def function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
            error('%s %s' % (e, args))
    function.func_name = f.func_name
    return function

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
    method = catchExceptions(method)
    setattr(__main__, name, method)
    return name

class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'name'        :'string',
            'option_name' :'string',
            'value'       :'string',
            'host'        :'string',
            'prefixes'    :'string',
            'is_connected':'integer',
            }

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
        value = getattr(weechat, 'infolist_%s' %self.fields[name])(self.pointer, name)
        return value

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

class SimpleBuffer(object):
    """WeeChat buffer. Only for displaying lines."""
    _title = ''
    def __init__(self, name):
        assert name, "Buffer needs a name."
        self.__name__ = name
        self._pointer = ''

    def _getBuffer(self):
        # we need to always search the buffer, since there's no close callback we can't know if the
        # buffer was closed.
        buffer = weechat.buffer_search('python', self.__name__)
        if not buffer:
            buffer = self.create()
        return buffer

    def _create(self):
        return weechat.buffer_new(self.__name__, '', '', '', '')

    def create(self):
        buffer = self._create()
        if self._title:
            weechat.buffer_set(buffer, 'title', self._title)
        self._pointer = buffer
        return buffer

    def title(self, s):
        self._title = s
        weechat.buffer_set(self._getBuffer(), 'title', s)

    def clear(self):
        weechat.buffer_clear(self._getBuffer())

    def __call__(self, s, *args, **kwargs):
        self.prnt(s, *args, **kwargs)

    def display(self):
        weechat.buffer_set(self._getBuffer(), 'display', '1')

    def error(self, s, *args):
        self.prnt(s, prefix=weechat.prefix('error'))

    def prnt(self, s, *args, **kwargs):
        """Prints messages in buffer."""
        buffer = self._getBuffer()
        if not isinstance(s, basestring):
            s = str(s)
        if args:
            s = s %args
        try:
            s = kwargs['prefix'] + s
        except KeyError:
            pass
        prnt(buffer, s)

    def prnt_lines(self, s, *args, **kwargs):
        for line in s.splitlines():
            self.prnt(line, *args, **kwargs)

# -----------------------------------------------------------------------------
# Script Classes

class WarnObject(object):
    def __init__(self, pattern='', comment='', date=0, expires=0, channels=[]):
        self.id = None
        self.pattern = pattern
        self.comment = comment
        if not date:
            self.date = int(time.time())
        else:
            self.date = date
        self.expires = expires
        self.channels = CaseInsensibleSet(channels)

    def serialize(self):
        L = [ self.id, self.pattern, self.comment, self.date, self.expires ]
        L.extend(self.channels)
        return L

    def deserialize(self, L):
        self.id, self.pattern, self.comment, self.date, self.expires = L[:5]
        self.channels = CaseInsensibleSet(L[5:])
        self.id = int(self.id)
        self.date = int(self.date)
        self.expires = int(self.expires)

    def __str__(self):
        return "%s<%s %s>" % (self.__class__.__name__, self.id, self.pattern)

    __repr__ = __str__

    def isValidChannel(self, channel):
        if not self.channels:
            return True
        return channel in self.channels


class WarnDatabase(CaseInsensibleDict):
    _updated = False
    _config = 'python.%s.mask' % SCRIPT_NAME
    _last_id = 0
    _id_dict = {}

    def updateOnDemand(f):
        def update(self, *args, **kwargs):
            if not self._updated:
                self.__update()
            return f(self, *args, **kwargs)
        return update

    __contains__ = updateOnDemand(CaseInsensibleDict.__contains__)
    __iter__     = updateOnDemand(CaseInsensibleDict.__iter__)

    @updateOnDemand
    def itervalues(self):
        return sorted(CaseInsensibleDict.itervalues(self), key=lambda x: x.id)

    def values(self):
        return list(self.itervalues())

    @updateOnDemand
    def __getitem__(self, k):
        if isinstance(k, int) or (isinstance(k, basestring) and k.isdigit()):
            return self._id_dict.__getitem__(int(k))
        return CaseInsensibleDict.__getitem__(self, k)

    def __update(self):
        self._updated = True
        self.readDB()
        # import and remove old warn configs
        infolist = Infolist('option', 'plugins.var.%s.*' % self._config)
        n = len(self._config) + 1
        for opt in infolist:
            pattern = opt['option_name'][n:]
            comment = opt['value']
            self.add(pattern, comment=comment)
            weechat.config_unset_plugin('mask.%s' % pattern)

    def writeDB(self):
        filename = get_dir('warn_patterns.csv')
        try:
            fd = open(filename, 'wb')
            writer = csv.writer(fd)
            writer.writerows(self.getrows())
            fd.close()
        except IOError:
            error('Failed to write warn database in %s' % file)

    def readDB(self):
        filename = get_dir('warn_patterns.csv')
        try:
            reader = csv.reader(open(filename, 'rb'))
        except IOError:
            return

        for row in reader:
            obj = WarnObject()
            obj.deserialize(row)
            self._add(obj)
        self._getLastId()

    def _getLastId(self):
        if self:
            self._last_id = max([ obj.id for obj in self.itervalues() ])
        return self._last_id

    _last_purge = 0
    def purge(self):
        if time.time() - self._last_purge < 60:
            return

        self._last_purge = int(time.time())
        for obj in self.values():
            if obj.expires and self._last_purge > (obj.date + obj.expires):
                debug("purging %s" % obj)
                self.rem(obj.pattern)

    def getId(self):
        self._last_id += 1
        return self._last_id

    def getrows(self):
        def generator():
            for obj in self.itervalues():
                yield obj.serialize()

        return generator()

    def _add(self, obj):
        if obj.id in self._id_dict:
            raise Exception("Id is not unique.")
        self[obj.pattern] = obj
        self._id_dict[obj.id] = obj

    def add(self, pattern, **kwargs):
        if pattern not in self:
            obj = WarnObject(pattern, **kwargs)
            id = kwargs.get('id', None)
            if id is None:
                obj.id = self.getId()
            else:
                obj.id = id
            self._add(obj)
        else:
            obj = self[pattern]
            debug("add args: %s", kwargs)
            # FIXME update new values

    def rem(self, k):
        if isinstance(k, int) or (isinstance(k, basestring) and k.isdigit()):
            pattern = self._id_dict[int(k)].pattern
        else:
            pattern = k
        if pattern in self:
            obj = self[pattern]
            del self[pattern]
            del self._id_dict[obj.id]

    def clear(self):
        CaseInsensibleDict.clear(self)
        self._id_dict.clear()
        self._updated = False
        self._last_id = 0

warnDB = WarnDatabase()


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
            if pattern_match(p, s):
                for e in self.exceptions:
                    if pattern_match(e, s):
                        return False
                return True
        return False


# -----------------------------------------------------------------------------
# Script Commands

class Warn(Command):
    description, help = "Manages the list of warning patterns.", ""
    usage = "add <pattern> [<comment>] || del <pattern> [<pattern> ..] || list <word>\n"\
            "\n"\
            "Without arguments list all patterns.\n"\
            " add: adds a new pattern, with an optional comment. Anyone joining with "\
            "an usermask matching a pattern will raise a warning.\n"\
            "      Patterns accept ?, * as wildcards.\n"\
            " del: deletes one or several patterns.\n"\
            "list: list current patterns with <word> (either in pattern or comment)."
    command = 'warn'
    completion = 'add %(chanop_ban_mask)||del %(warn_patterns)|%*||list'

    def parser(self, args):
        if not args:
            self.printAll()
            raise NoArguments

        args = args.split()
        try:
            cmd = args.pop(0)
            if cmd not in ('add', 'del', 'list'):
                raise Exception
            if cmd in ('add', 'del') and len(args) < 1:
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

    def printAll(self):
        for obj in warnDB.itervalues():
            self.printWarn(obj)

        if not warnDB:
            say("No patterns set.")

    def printWarn(self, obj):
        say("%s[%s%s%s] %s %s%s" % (COLOR_CHAT_DELIMITERS,
                                  COLOR_CHAT_BUFFER,
                                  obj.id,
                                  COLOR_CHAT_DELIMITERS,
                                  obj.pattern,
                                  COLOR_RESET,
                                  obj.comment))

    def printWarnFull(self, obj):
        say("%s[%s%s%s] %s" % (COLOR_CHAT_DELIMITERS,
                               COLOR_CHAT_BUFFER,
                               obj.id,
                               COLOR_CHAT_DELIMITERS,
                               obj.pattern))
        say("comment: %s" % obj.comment)
        if obj.expires:
            expires = (obj.date + obj.expires) - int(time.time())
            expires = time_elapsed(expires)
        else:
            expires = "never"
        say("added: %s expires: %s" % (time.strftime("%Y-%m-%d", time.localtime(obj.date)),
                                       expires))

    def execute(self):
        if self.cmd == 'add':
            warnDB.add(self.mask, comment=self.comment)
            warnDB.writeDB()
        elif self.cmd == 'del':
            for mask in self.mask:
                warnDB.rem(mask)
            warnDB.writeDB()
        elif self.cmd == 'list':
            try:
                if self.mask:
                    self.printWarnFull(warnDB[self.mask[0]])
                else:
                    self.printAll()
            except KeyError:
                say("Wrong id or pattern.")


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
        debug('%s %s %s', data, signal, signal_data)
        return f(server, channel, hostmask, signal_data)
    decorator.func_name = f.func_name
    return decorator

@catchExceptions
@signal_parse
def join_cb(server, channel, hostmask, signal_data):
    if channel in ignoreJoins:
        return WEECHAT_RC_OK

    warnDB.purge()
    for mask in warnDB:
        match = pattern_match(mask, hostmask)
        if match:
            obj = warnDB[mask]
            if not obj.isValidChannel(channel):
                continue

            value = get_config_valid_string('warning_buffer')
            buffer = ''
            if value == 'channel':
                buffer = weechat.buffer_search('irc', '%s.%s' % (server, channel))
            elif value == 'current':
                buffer = weechat.current_buffer()
            elif value == 'warn_buffer':
                buffer = weechat.buffer_search('python', SCRIPT_NAME) 
                if not buffer:
                    buffer = weechat.buffer_new(SCRIPT_NAME, '', '', '', '')
            prnt_date_tags(buffer, 0, 'notify_highlight', 
                "%s\t%s joined %s%s %s[%s%s%s] %s%s \"%s\"" % (script_nick,
                                        format_hostmask(hostmask),
                                        COLOR_CHAT_CHANNEL,
                                        channel,
                                            COLOR_CHAT_DELIMITERS,
                                            COLOR_CHAT_BUFFER,
                                            obj.id,
                                            COLOR_CHAT_DELIMITERS,
                                            mask,
                                            COLOR_RESET,
                                            obj.comment))
            break
    return WEECHAT_RC_OK

def banmask_cb(data, signal, signal_data):
    if not get_config_boolean('autowarn_bans'):
        return WEECHAT_RC_OK

    #debug('BAN: %s %s', signal, signal_data)
    args = signal_data.split()
    # sanity check
    if not len(args) == 4:
        return WEECHAT_RC_OK

    op, channel, mask, users = args
    mode = signal[-1]
    if '$' in mask:
        mask, forward = mask.split('$', 1)
        if forward in ignoreForwards:
            return WEECHAT_RC_OK

    if mode == 'b' and mask not in warnDB:
        s = ' '.join(users.split(','))
        op_nick = weechat.info_get('irc_nick_from_host', op)
        comment = "Ban in %s by %s: %s" % (channel, op_nick, s)
        comment = weechat.string_remove_color(comment, '')
        # FIXME make expire time configurable
        warnDB.add(mask, comment=comment, expires=3600*24*7)
    return WEECHAT_RC_OK

def ignore_update(*args):
    ignoreForwards._get_ignores()
    ignoreJoins._get_ignores()
    return WEECHAT_RC_OK

def warn_cmpl(data, completion_item, buffer, completion):
    for mask in warnDB:
        weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_END)
    return WEECHAT_RC_OK

@catchExceptions
def script_unload():
    warnDB.writeDB()
    return WEECHAT_RC_OK

# -----------------------------------------------------------------------------
# Register script

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, 'script_unload', ''):

    # colors
    COLOR_CHAT_DELIMITERS = weechat.color('chat_delimiters')
    COLOR_CHAT_NICK       = weechat.color('chat_nick')
    COLOR_CHAT_HOST       = weechat.color('chat_host')
    COLOR_CHAT_BUFFER     = weechat.color('chat_buffer')
    COLOR_CHAT_CHANNEL    = weechat.color('chat_channel')
    COLOR_RESET           = weechat.color('reset')

    # pretty SCRIPT_NAME
    script_nick = '%s[%s%s%s]%s' % (COLOR_CHAT_DELIMITERS,
                                    COLOR_CHAT_NICK,
                                    SCRIPT_NAME,
                                    COLOR_CHAT_DELIMITERS,
                                    COLOR_RESET)

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    # hook signals
    weechat.hook_signal('*,irc_in_join', 'join_cb', '')
    if get_config_boolean('autowarn_bans'):
        weechat.hook_signal('*,chanop_mode_*', 'banmask_cb', '')

    ignoreForwards = Ignores('ignore_autowarn_forwards')
    ignoreJoins = Ignores('ignore_channels')

    # hook config
    weechat.hook_config('plugins.var.python.%s.ignore_*' % SCRIPT_NAME, 'ignore_update', '')

    # hook completer
    weechat.hook_completion('warn_patterns', '', 'warn_cmpl', '')

    # hook commands
    Warn().hook()

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
