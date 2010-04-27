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
#
#
#   Commands:
#
#   Settings:
#
#   History:
#   <date>
#   version 0.1-dev: new script!
#
###

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    WEECHAT_RC_OK_EAT = weechat.WEECHAT_RC_OK_EAT
    import_ok = True
except ImportError:
    import_ok = False

SCRIPT_NAME    = "hexip"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "I'm a script!"

### Messages ###
def debug(s, prefix='', buffer=None):
    """Debug msg"""
#    if not weechat.config_get_plugin('debug'): return
    if buffer is None:
        buffer_name = 'DEBUG_' + SCRIPT_NAME
        buffer = weechat.buffer_search('python', buffer_name)
        if not buffer:
            buffer = weechat.buffer_new(buffer_name, '', '', '', '')
            weechat.buffer_set(buffer, 'nicklist', '0')
            weechat.buffer_set(buffer, 'time_for_each_line', '0')
            weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

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

def is_ip(s):
    """Returns whether or not a given string is an IPV4 address."""
    import socket
    try:
        return bool(socket.inet_aton(s))
    except socket.error:
        return False

def is_hexip(s):
    """Checks if 's' is a hexed ip"""
    if len(s) == 8 and all([c in '0123456789ABCDEFabcdef' for c in s]):
        return True
    return False

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

def ip_to_hex(s):
    hex = s.split('.')
    hex = map(lambda s: '%02x' %int(s), hex)
    return ''.join(hex)

def hexip_completion(data, buffer, command):
    input = weechat.buffer_get_string(buffer, 'input')
#    cmd = input.partition(' ')[0].strip('/')
#    if cmd not in weechat.config_get_plugin('commands_cmpl'):
#        # don't complete then
#        return WEECHAT_RC_OK
    pos = weechat.buffer_get_integer(buffer, 'input_pos')
    #debug('%r %s %s' %(input, len(input), pos))
    if pos >= 8 and (pos == len(input) or input[pos] == ' '):
        n = input.rfind(' ', 0, pos)
        word = input[n+1:pos]
        #debug(word)
        if not word:
            return WEECHAT_RC_OK
        replace = ''
        if is_hexip(word):
            replace = hex_to_ip(word)
        elif is_ip(word):
            replace = ip_to_hex(word)
        if replace:
            n = len(word)
            weechat.buffer_set(buffer, 'input', '%s%s%s' %(input[:pos-n], replace, input[pos:]))
            weechat.buffer_set(buffer, 'input_pos', str(pos - n + len(replace)))
            return WEECHAT_RC_OK_EAT
    return WEECHAT_RC_OK

### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    weechat.hook_command_run('/input complete_next', 'hexip_completion', '')

    
# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
