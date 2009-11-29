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
#
#
###

__version__ = "0.1"
__author__  = "Elián Hanisch <lambdae2@gmail.com>"

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://weechat.flashtux.org/"

### messages
def debug(s, prefix=''):
    """Debug msg, displays in its own buffer."""
    buffer = weechat.buffer_search('python', 'script debug')
    if not buffer:
        buffer = weechat.buffer_new('script debug', '', '', '', '')
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'time_for_each_line', '0')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

def error(s, prefix='', buffer=''):
    """Error msg"""
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), prefix, s))

def say(s, prefix='', buffer=''):
    """Normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))


### irc utils
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


### config fetch
boolDict = {'on':True, 'off':False}
def get_config_boolean(config, default=None):
    value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        if not default:
            raise Exception("Error while fetching config '%s'. '%s' is a invalid value." %(config, value))
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_int(config, default=None):
    value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        if not default:
            raise Exception("Error while fetching config '%s'. '%s' is a invalid value." %(config, value))
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)


### WeeChat classes
class Infolist(object):
    """
    Class for reading WeeChat's infolists.

    I wrote this class because I wanted a more simpler way of dealing with infolists in my scripts,
    it passes the responsibility of freeing the infolist to python, and it allows me to use a more
    python like coding style, some examples:

    - request variables without worrying about its type, and automatically go to the first item
      if needed

    infolist = Infolist('buffer')
    buffer_name = infolist['name']
    buffer_type = infolist['type']
    buffer_pointer = infolist['pointer']

    get_string, get_integer, get_pointer and get_time methods are still available in the class or a
    fields dict can be passed on initialization for avoid the infolist_fields call if wanted.

    - 'for' loops

    buffer_list = []
    for buffer in Infolist('buffer'):
        buffer_list.append(buffer['name'])

    the traditional while loop still can be used

    buffer_list = []
    infolist = Infolist('buffer')
    while infolist.next():
        buffer_list.append(infolist['name'])

    - 'with' code blocks

    with Infolist('buffer_lines', buffer_pointer) as infolist:
        for line in infolist:
            msg = line['message']
            break
    """
    __slots__ = ('name', 'args', 'pointer', 'fields', 'cursor')
    typeDict = {'i': 'integer', 's': 'string', 'p': 'pointer', 'b': 'buffer', 't': 'time'}

    def __init__(self, name, pointer='', args='', fields=None):
        """
        Gets the infolist to read, if fails so raises exception.
        Infolist(infolist_name, item_pointer, arguments) -> infolist object
        """
        self.name = name
        self.args = (pointer, args)
        if fields is not None:
            assert isinstance(fields, dict)
            self.fields = fields
        else:
            self.fields = {}
        self.cursor = 0
        self.pointer = weechat.infolist_get(name, pointer, args)
        if self.pointer == '':
            raise Exception('Infolist initialising failed %s' %self)

    def __repr__(self):
        return "<infolist('%s', '%s', '%s') at %s>" \
                %(self.name, self.args[0], self.args[1], self.pointer)

    __str__ = __repr__

    def __del__(self):
        """Purge infolist if is no longer referenced."""
        self.free()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.free()

    def __len__(self):
        """True False evaluation, returns 1 if there's a pointer, 0 if the infolist was freed."""
        if self.pointer:
            return 1
        else:
            return 0

    def __iter__(self):
        """Returns iterator object."""
        def generator():
            next = self.next
            while next():
                yield self

        return generator()

    def __reversed__(self):
        """Returns iterator object for reversed loops."""
        def generator():
            prev = self.prev
            while prev():
                yield self

        return generator()

    def __getitem__(self, name):
        """Implement the evaluation of self[name]."""
        type = self.get_fields()[name]
        if self.cursor == 0:
            self.next()
        return getattr(self, 'get_%s' %type)(name)

    def get_string(self, name):
        """Returns value of a string type variable."""
        return weechat.infolist_string(self.pointer, name)

    def get_integer(self, name):
        """Returns value of a integer type variable."""
        return weechat.infolist_integer(self.pointer, name)

    def get_pointer(self, name):
        """Returns value of a pointer type variable."""
        return weechat.infolist_pointer(self.pointer, name)

    def get_time(self, name):
        """Returns value of a time type variable."""
        return weechat.infolist_time(self.pointer, name)

    def get_buffer(self, name):
        """Not implemented in script API, declared only for avoid AttributeError exception."""
        return ''

    def set_fields(self):
        """Store the fields list in self.fields dictionary."""
        s = weechat.infolist_fields(self.pointer)
        if s:
            fields = s.split(',')
            d = {}
            for field in fields:
                type, name = field.split(':')
                d[name] = self.typeDict[type]
            self.fields = d

    def get_fields(self):
        """Returns fields dictionary, move cursor to the next item if needed."""
        if not self.fields:
            if self.cursor == 0:
                self.next()
            self.set_fields()
        return self.fields

    def variables(self):
        """Returns iterator over the variables of infolist."""
        return self.get_fields().iterkeys()

    def next(self):
        """Moves cursor to the next item, returns 0 if end of list reached,
        otherwise always 1."""
        self.cursor = weechat.infolist_next(self.pointer)
        return self.cursor

    def prev(self):
        """Moves cursor to the previous item, returns 0 if beginning of list reached,
        otherwise always 1."""
        self.cursor = weechat.infolist_prev(self.pointer)
        return self.cursor

    def reset(self):
        """Moves cursor to beginning of infolist."""
        if self.cursor == 1: # only if we aren't in the beginning already
            while self.prev():
                pass

    def free(self):
        """Purge the infolist. Automatically called by python when
        the infolist is no longer referenced."""
        if self.pointer:
            weechat.infolist_free(self.pointer)
            self.pointer = ''
            self.fields = {}


class Command(object):
    """TODO"""
    help = ("WeeChat command.", "[define usage template]", "detailed help here")

    def __init__(self, command, callback, completion=''):
        self._command = command
        self.callback = callback
        self.completion = completion
        self.pointer = ''
        self.hook()

    def __call__(self, *args):
        """Called by WeeChat when /command is used."""
        self.parse_args(*args)
        self.command()
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

    def command(self):
        """This method is called when the command is run, override this."""
        pass

    def hook(self):
        assert self._command and self.callback
        assert not self.pointer, "There's already a hook pointer, unhook first"
        desc, usage, help = self._parse_doc()
        self.pointer = weechat.hook_command(self._command, desc, usage, help, self.completion,
                self.callback, '')
        if self.pointer == '':
            raise Exception, "hook_command failed"

    def unhook(self):
        if self.pointer:
            weechat.unhook(self.pointer)
            self.pointer = ''


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
