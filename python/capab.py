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
    import_ok = True
except ImportError:
    import_ok = False

SCRIPT_NAME    = "capab"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Format for Freenode's CAPAB"
SCRIPT_COMMAND = "capab"

script_nick    = "[%s]" %SCRIPT_NAME

### Config ###
settings = {}

### Messages ###
def debug(s, prefix='', buffer=None):
    """Debug msg"""
    if not weechat.config_get_plugin('debug'): return
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

### Config functions and value validation ###
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

def get_config_int(config, allow_empty_string=False):
    value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        if value == '' and allow_empty_string:
            return value
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)

valid_methods = set(())
def get_config_valid_string(config, valid_strings=valid_methods):
    value = weechat.config_get_plugin(config)
    if value not in valid_strings:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is an invalid value, allowed: %s." %(value, ', '.join(valid_strings)))
        return default
    return value

ident_nick = {}
def privmsg_print_cb(server_name, modifier, modifier_data, string):
    plugin, buffer, tags = modifier_data.split(';', 2)
    if plugin != 'irc' \
            or buffer[:buffer.find('.')] != server_name \
            or 'irc_privmsg' not in tags:
        return string

    #debug("print data: %s" %modifier_data)
    #debug("print string: %s" %repr(string))
    nick = string[:string.find('\t')]
    nick_key = weechat.string_remove_color(nick, '').lstrip('@+')
    #debug('print nick: %s' %_nick)
    try:
        ident = ident_nick[nick_key]
        if not ident:
            msg = string[string.find('\t'):]
            return '%s~%s%s' %(ident_color, nick, msg)
            #return '%s%s+%s' %(nick, ident_color, msg)
    except KeyError:
        pass
    return string

def privmsg_signal_cb(server_name, modifier, modifier_data, string):
    if modifier_data != server_name:
        return string

    #debug('signal data: %s' %modifier_data)
    #debug('signal string: %s' %string)
    head, sep, msg = string.partition(' :')
    char = msg[0]
    if char in '+-':
        msg = msg[1:]
        nick = head[1:head.find('!')]
        #debug('print nick: %s' %nick)
        ident_nick[nick] = char == '+'
        return '%s :%s' %(head, msg)
    else:
        return string

def cmd_capab(data, buffer, args):
    if not args:
        return WEECHAT_RC_OK

    server = args.split()[0]
    server_buffer = weechat.buffer_search('irc', 'server.%s' %server)
    if server_buffer:
        say('Enabling IDENFITY-MSG capability on %s' %server)
        weechat.command(server_buffer, '/quote capab identify-msg')
        weechat.hook_modifier('irc_in_PRIVMSG', 'privmsg_signal_cb', server)
        weechat.hook_modifier('irc_in_NOTICE', 'privmsg_signal_cb', server)
        weechat.hook_modifier('weechat_print', 'privmsg_print_cb', server)

    return WEECHAT_RC_OK

### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    weechat.hook_command(SCRIPT_COMMAND, '', '', '', '', 'cmd_capab', '')

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    ident_color = weechat.color('chat_nick')

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
