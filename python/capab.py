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
settings = {
'servers':  '',
'bouncer_prefix': r'\[\d\d:\d\d\]\s',
}

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

def get_config_list(config):
    value = weechat.config_get_plugin(config)
    if value:
        return value.split(',')
    else:
        return []

def set_config_list(config, value):
    old_value = get_config_list(config)
    if isinstance(value, list):
        old_value.extend(value)
    else:
        old_value.append(value)
    value = set(old_value)
    str_value = ','.join(value)
    weechat.config_set_plugin(config, str_value)


def update_nicklist(buffer_name):
    buffer_pointer = weechat.buffer_search('irc', buffer_name)
    if not buffer_pointer:
        return

    group_pointers = {}

    infolist = weechat.infolist_get('nicklist', buffer_pointer, '')
    infolist_string = weechat.infolist_string
    infolist_next = weechat.infolist_next
    while infolist_next(infolist):
        if not infolist_string(infolist, 'type') == 'nick':
            continue

        nick = infolist_string(infolist, 'name')
        if nick not in ident_nick:
            continue
        
        group = infolist_string(infolist, 'group_name')
        color = infolist_string(infolist, 'color')
        prefix = infolist_string(infolist, 'prefix')
        prefix_color = infolist_string(infolist, 'prefix_color')

        if ident_nick[nick]:
            prefix_new = ' '
            group_new = '080|ident'
            color_new = 'green'
        else:
            prefix_new = '~'
            group_new = '081|unident'
            color_new = 'brown'
            prefix_color = 'cyan'

        if prefix[0] != prefix_new[0]:
            if prefix == ' ':
                prefix = prefix_new
                prefix_new = ''
            elif prefix_new != ' ':
                prefix = prefix_new + prefix
                prefix_new = ''

        if color == 'bar_fg':
            color = color_new
            color_new = ''

        if group[:2] == '08':
            group = group_new
            group_new = ''
            try:
                group_pointer = group_pointers[group]
            except KeyError:
                group_pointer = weechat.nicklist_search_group(buffer_pointer, '', group)
                if not group_pointer:
                    group_pointer = weechat.nicklist_add_group(buffer_pointer, '', group,
                            'weechat.color.nicklist_group', 1)
                group_pointers[group] = group_pointer
        else:
            group_pointer = weechat.nicklist_search_group(buffer_pointer, '', group)

        if prefix_new and group_new and color_new:
            # nothing to change
            continue

        #debug('adding nick: %s%s to %s' %(prefix, nick, group))
        nick_pointer = weechat.nicklist_search_nick(buffer_pointer, '', nick)
        if nick_pointer:
            weechat.nicklist_remove_nick(buffer_pointer, nick_pointer)
        nick_pointer = weechat.nicklist_add_nick(buffer_pointer, group_pointer, nick, color,
                prefix, prefix_color, 1)
        nicklist[buffer_name, nick] = (buffer_pointer, nick_pointer)
    weechat.infolist_free(infolist)


ident_nick = {}
nicklist = {}
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
        #if (buffer, nick_key) not in nicklist:
            #debug('updating nicklist for %s %s' %(buffer, nick))
            #update_nicklist(buffer)
            #debug('added! %s' %str((buffer, nick_key)))
            #nicklist.add((buffer, nick_key))
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
    elif bouncerRe:
        #debug('msg: %s' %msg)
        m = bouncerRe.search(msg)
        if m:
            prefix = m.group()
            #debug('prefix: %s' %prefix)
            msg = msg[len(prefix):]
            char = msg[0]
            if char in '+-':
                msg = msg[1:]
                nick = head[1:head.find('!')]
                #debug('print nick: %s' %nick)
                ident_nick[nick] = char == '+'
                return '%s :%s%s' %(head, prefix, msg)
        return string
    else:
        return string

def part_signal_cb(server_name, signal, signal_data):
    #debug('signal: %s' %signal)
    #debug('signal data: %s' %signal_data)
    signal_data = signal_data.split()
    host = signal_data[0]
    channel = signal_data[2]
    nick = host[1:host.find('!')]
    buffer = '%s.%s' %(server_name, channel)
    key = (buffer, nick)
    if key in nicklist:
        weechat.nicklist_remove_nick(*nicklist[key])
        del nicklist[key]
    elif nick == weechat.info_get('irc_nick', server_name):
        for b, n in nicklist.keys():
            if b == buffer:
                weechat.nicklist_remove_nick(*nicklist[b, n])
                del nicklist[b, n]
    return WEECHAT_RC_OK

def quit_signal_cb(server_name, signal, signal_data):
    #debug('signal: %s' %signal)
    #debug('signal data: %s' %signal_data)
    nick = signal_data[1:signal_data.find('!')]
    if nick in ident_nick:
        del ident_nick[nick]
    for b, n in nicklist.keys():
        if n == nick:
            weechat.nicklist_remove_nick(*nicklist[b, n])
            del nicklist[b, n]
    return WEECHAT_RC_OK

def enable_capab(server):
    server_buffer = weechat.buffer_search('irc', 'server.%s' %server)
    if server_buffer:
        weechat.command(server_buffer, '/quote capab identify-msg')
        weechat.hook_modifier('irc_in_PRIVMSG', 'privmsg_signal_cb', server)
        weechat.hook_modifier('irc_in_NOTICE', 'privmsg_signal_cb', server)
        #weechat.hook_signal('%s,irc_in_PART' %server, 'part_signal_cb', server)
        #weechat.hook_signal('%s,irc_in_QUIT' %server, 'quit_signal_cb', server)
        weechat.hook_modifier('weechat_print', 'privmsg_print_cb', server)
        return True

def cmd_capab(data, buffer, args):
    if not args:
        return WEECHAT_RC_OK

    server = args.split()[0]
    say('Enabling IDENFITY-MSG capability on %s' %server)
    if enable_capab(server):
        set_config_list('servers', server)
    return WEECHAT_RC_OK

### Main ###
def script_unload():
    for b, n in nicklist.keys():
        weechat.nicklist_remove_nick(*nicklist[b, n])
    return WEECHAT_RC_OK

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, 'script_unload', ''):

    ident_color = weechat.color('chat_nick')
    r = weechat.config_get_plugin('bouncer_prefix')
    bouncerRe = None
    if r:
        try:
            import re
            if r[0] != '^':
                r = '^' + r
            bouncerRe = re.compile(r)
        except:
            bouncerRe = None
            error('bad regexp %s' %r)

    weechat.hook_command(SCRIPT_COMMAND, '', '', '', '', 'cmd_capab', '')

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    servers = get_config_list('servers')
    for server in servers:
        enable_capab(server)


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
