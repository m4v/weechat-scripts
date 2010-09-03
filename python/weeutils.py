# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by Elián Hanisch <lambdae2@gmail.com>
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
# Module for debugging scripts. Please note that this doesn't give you an interactive console, it
# can only evaluate simple statements, assignations like "myVar = True" will raise an exception.
#
# For debug a script, insert these lines after weechat.register() call.
#
#
# from weeutils import DebugBuffer
# debug = DebugBuffer("name", globals())
# debug.display()
#
#
# Then, after loading the script (not weeutils.py), try "dir()" in the buffer input, it should
# display script's global functions and variables.
# This module should be placed in your python scripts path as weeutils.py
#
# weeutils.py can be loaded as a script, you will able to call methods in weechat's
# python module only.
#
###

SCRIPT_NAME    = "weeutils"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Debug a script or test code in WeeChat."

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import __main__
import traceback

def callback(method):
    """This function will take a bound method and make it a callback."""
    # try to create a descriptive and unique name.
    func = method.__name__
    inst = method.im_self.__name__
    name = '%s_%s' %(inst, func)
    # set our callback
    setattr(__main__, name, method)
    return name


class SimpleBuffer(object):
    """WeeChat buffer. Only for displaying lines."""
    def __init__(self, name):
        assert name, "Buffer needs a name."
        self.__name__ = name
        self._pointer = ''

    def _getBuffer(self):
        buffer = weechat.buffer_search('python', self.__name__)
        if not buffer:
            buffer = self.create()
        return buffer

    def _create(self):
        return weechat.buffer_new(self.__name__, '', '', '', '')
    
    def create(self):
        buffer = self._create()
        self._pointer = buffer
        return buffer

    def __call__(self, s, *args, **kwargs):
        self.prnt(s, *args, **kwargs)

    def display(self):
        buffer = self._getBuffer()
        weechat.buffer_set(buffer, 'display', '1')
    
    def error(self, s, *args):
        self.prnt(s, prefix='error')

    def prnt(self, s, *args, **kwargs):
        """Prints messages in buffer."""
        buffer = self._getBuffer()
        if not isinstance(s, basestring):
            s = str(s)
        if args:
            s = s %args
        if 'prefix' in kwargs:
            prefix = weechat.prefix(kwargs['prefix'])
            s = prefix + s
        prnt(buffer, s)


class Buffer(SimpleBuffer):
    """WeeChat buffer. With input and close methods."""
    def _create(self):
        return weechat.buffer_new(self.__name__, callback(self.input), '', callback(self.close), '')

    def input(self, data, buffer, input):
        return WEECHAT_RC_OK

    def close(self, data, buffer):
        return WEECHAT_RC_OK


class DebugBuffer(Buffer):
    def __init__(self, name, globals={}):
        Buffer.__init__(self, name)
        self.globals = globals


    def _create(self):
        buffer = Buffer._create(self)
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'time_for_each_line', '0')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
        return buffer

    def input(self, data, buffer, input):
        """Python code evaluation."""
        try:
            s = eval(input, self.globals)
            self.prnt(s)
        except:
            trace = traceback.format_exc()
            self.prnt(trace)
        return WEECHAT_RC_OK


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

        # we're being loaded as a script.
        # import weechat functions into this namespace.
        from weechat import *

        def weechat_functions():
            return [ func for func in dir(weechat) if callable(getattr(weechat, func)) ]
        
        myBuffer = DebugBuffer('weeutils', globals())
        myBuffer("Test simple Python statements here.")
        myBuffer("Example: \"buffer_search('python', 'weeutils')\"")
        myBuffer("For a list of WeeChat functions, type 'weechat_functions()'")
        myBuffer.display()


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
