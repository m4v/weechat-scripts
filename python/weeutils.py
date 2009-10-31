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
#   Python Classes and Functions for WeeChat 0.3
#
#   This is only for import some common functions while writting a new script
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
def debug(s, prefix='', buffer=''):
    """Debug msg"""
    weechat.prnt(buffer, 'debug:\t%s %s' %(prefix, s))

def error(s, prefix='', buffer=''):
    """Error msg"""
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), prefix, s))

def say(s, prefix='', buffer=''):
    """Normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

### config
def get_config_boolean(config):
    """Gets our config value, returns False if value is wrong."""
    return boolDict[weechat.config_get_plugin(config)]

def get_config_valid_values(config, values, default=None):
    s = weechat.config_get_plugin(config)
    if s in values:
        return s
    else:
        error("'%s' is an invalid option value, allowed: %s. Defaulting to '%s'" \
                %(s, ', '.join(map(repr, values)), default))
        return default


### irc utils
def is_hostmask(s):
    """Returns whether or not the string s is a valid User hostmask."""
    n = s.find('!')
    m = s.find('@')
    if n < m-1 and n >= 1 and m >= 3 and len(s) > m+1:
        return True
    else:
        return False

### class definition
class ValidValuesDict(dict):
    """
    Dict that returns the default value defined by 'defaultKey' key if __getitem__ raises
    KeyError. 'defaultKey' must be in the supplied dict.
    """
    def _error_msg(self, key):
        error("'%s' is an invalid option value, allowed: %s. Defaulting to '%s'" \
                %(key, ', '.join(map(repr, self.keys())), self.default))

    def __init__(self, dict, defaultKey):
        self.update(dict)
        assert defaultKey in self
        self.default = defaultKey

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            # user set a bad value
            self._error_msg(key)
            return dict.__getitem__(self, self.default)


boolDict = ValidValuesDict({'on':True, 'off':False}, 'off')


class Infolist(object):
    """
    Wrapper class for reading WeeChat's infolists.

    I wrote this class because I wanted a more simpler way of dealing with infolists in my scripts,
    it passes the responsibility of freeing the infolist to python, and it allows me to use a more
    python like coding style, some examples:

    - request variables without worrying about its type, and automatically go to the first item
      if needed

    infolist = Infolist('buffer')
    buffer_name = infolist['name']
    buffer_type = infolist['type']
    buffer_pointer = infolist['pointer']

    get_string, get_integer, get_pointer and get_time methods are still available in the class

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

    def __init__(self, name, pointer='', args=''):
        """
        Gets the infolist to read, if fails so raises exception.
        Infolist(infolist_name, item_pointer, arguments) -> infolist object
        """
        self.name = name
        self.args = (pointer, args)
        self.pointer = weechat.infolist_get(name, pointer, args)
        self.fields = {}
        self.cursor = 0
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
            while self.next():
                yield self

        return generator()

    def __reversed__(self):
        """Returns iterator object for reversed loops."""
        def generator():
            while self.prev():
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
        """Not implemented in script API, declared only for avoid AttributeError exception in
        __getitem__"""
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
    """
    WeeChat command class.

    [define usage template]

    detailed help here
    """
    pointer = ''
    __slots__ = ('command', 'callback', 'completion', 'buffer', 'args')
    def __init__(self, command, callback, completion=''):
        self.command = command
        self.callback = callback
        self.completion = completion
        self.hook()

    def __call__(self, *args):
        self._parse(*args)
        self.cmd(self, *args)
        return WEECHAT_RC_OK

    def __repr__(self):
        return "<command('/%s', '%s') at %s>" \
                %(self.command, self.callback,self.pointer)

    __str__ = __repr__

    def __del__(self):
        self.unhook()

    def _parse(self, data, buffer, args):
        self.buffer = buffer
        self.args = args

    def _parse_doc(self):
        desc, usage, help = self.help()
        help = help.strip('\n')
        # strip leading tabs
        help = '\n'.join(map(lambda s: s.lstrip('\t'), help.splitlines()))
        return desc, usage, help

    def cmd(self, data, buffer, args):
        """This method is called when the command is run, override this in your script."""
        pass

    def help(self):
        return "WeeChat command class.", "[define usage template]", "detailed help here"

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

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
