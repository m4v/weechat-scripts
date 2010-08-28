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
    from weechat import WEECHAT_RC_OK, prnt
except ImportError:
    print "This must be imported by a script under WeeChat."

import __main__
import traceback

def callback(method):
    """This function will take a bound method and create a callback for it."""
    # try to create a descriptive and unique name.
    func = method.__name__
    inst = method.im_self.__name__
    name = '%s_%s' %(inst, func)
    # set our callback
    setattr(__main__, name, method)
    return name


class SimpleBuffer(object):
    """WeeChat buffer."""
    def __init__(self, name):
        assert name
        self.__name__ = name
        buffer = weechat.buffer_search('python', name)
        if buffer:
            self.pointer = buffer
        else:
            self._createBuffer()

    def _createBuffer(self):
        buffer = weechat.buffer_new(self.__name__, '', '', '', '')
        self.pointer = buffer

    def __call__(self, s, *args):
        self.prnt(s, *args)

    def prnt(self, s, *args):
        """Prints messages in buffer."""
        if not isinstance(s, basestring):
            s = str(s)
        if args:
            s = s %args
        prnt(self.pointer, s)


class Buffer(SimpleBuffer):
    """WeeChat buffer. With input and close methods."""
    def _createBuffer(self):
        buffer = weechat.buffer_new(self.__name__, callback(self.input), '', callback(self.close), '')
        self.pointer = buffer

    def input(self, data, buffer, input):
        return WEECHAT_RC_OK

    def close(self, data, buffer):
        return WEECHAT_RC_OK


class DebugBuffer(Buffer):
    def __init__(self, name, globals={}):
        Buffer.__init__(self, name)
        self.globals = globals
        weechat.buffer_set(self.pointer, 'nicklist', '0')
        weechat.buffer_set(self.pointer, 'time_for_each_line', '0')
        weechat.buffer_set(self.pointer, 'localvar_set_no_log', '1')

    def input(self, data, buffer, input):
        """Python code evaluation."""
        try:
            s = eval(input, self.globals)
            self.prnt(s)
        except:
            trace = traceback.format_exc()
            self.prnt(trace)
        return WEECHAT_RC_OK


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
