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
SCRIPT_COMMAND = ""

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

nick_dict = {}
def privmsg_print_cb(data, modifier, modifier_data, string):
    plugin, buffer, tags = modifier_data.split(';', 2)
    if plugin != 'irc' or 'irc_privmsg' not in tags:
        return string
    #debug("print data: %s" %modifier_data)
    #debug("print string: %s" %repr(string))
    nick = string[:string.find('\t')]
    nick_key = weechat.string_remove_color(nick, '').lstrip('@+')
    #debug('print nick: %s' %_nick)
    try:
        ident = nick_dict[nick_key]
        if not ident:
            msg = string[string.find('\t'):]
            return '%s~%s%s' %(ident_color, nick, msg)
            #return '%s%s+%s' %(nick, ident_color, msg)
    except KeyError:
        pass
    return string

def privmsg_signal_cb(data, modifier, modifier_data, string):
    #debug('signal data: %s' %modifier_data)
    #debug('signal string: %s' %string)
    head, sep, msg = string.partition(' :')
    char = msg[0]
    if char in '+-':
        msg = msg[1:]
        nick = head[1:head.find('!')]
        #debug('print nick: %s' %nick)
        nick_dict[nick] = char == '+' 
        return '%s :%s' %(head, msg)
    else:
        return string

### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    ident_color = weechat.color('chat_nick')

    weechat.hook_modifier('irc_in_PRIVMSG', 'privmsg_signal_cb', '')
    weechat.hook_modifier('irc_in_NOTICE', 'privmsg_signal_cb', '')
    weechat.hook_modifier('weechat_print', 'privmsg_print_cb', '')

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
