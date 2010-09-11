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
    from weechat import WEECHAT_RC_OK, WEECHAT_HOOK_SIGNAL_STRING
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

SCRIPT_NAME    = "znc-buffextras"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "I'm a script!"

### Config ###
settings = {}

### Messages ###
script_nick = SCRIPT_NAME
def error(s, buffer='', trace=''):
    """Error msg"""
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), script_nick, s))
    if weechat.config_get_plugin('debug'):
        if not trace:
            import traceback
            if traceback.sys.exc_type:
                trace = traceback.format_exc()
        not trace or weechat.prnt('', trace)

def say(s, buffer=''):
    """normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(script_nick, s))

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


def buffextras_cb(data, modifier, modifier_data, string):
    if 'irc_privmsg' not in modifier_data:
        return string
    prefix, _, line = string.partition('\t')
    prefix = weechat.string_remove_color(prefix, '')
    if prefix != '*buffextras':
        return string

    IRC_COLOR_CHAT_DELIMITERS = weechat.color('chat_delimiters')
    IRC_COLOR_CHAT_NICK       = weechat.color('chat_nick')
    IRC_COLOR_CHAT_HOST       = weechat.color('chat_host')
    IRC_COLOR_CHAT_CHANNEL    = weechat.color('chat_channel')
    IRC_COLOR_CHAT            = weechat.color('chat')

    time, hostmask, action = line.split(None, 2)
    nick = hostmask[:hostmask.find('!')]
    hostname = hostmask[len(nick)+1:]
    server, channel = modifier_data.split(';')[1].split('.', 1)
    #debug('%s - %s - %s' %(time, host, action))

    if action == 'joined':
        IRC_COLOR_MESSAGE_JOIN = weechat.color(weechat.config_string(weechat.config_get(
            'irc.color.message_join')))

        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has joined %s%s%s")
        s = s %(weechat.prefix('join'),
                IRC_COLOR_CHAT_NICK, # TODO there's a function for use nick's color
                nick,
                IRC_COLOR_CHAT_DELIMITERS,
                ' (',
                IRC_COLOR_CHAT_HOST, # TODO host can be hidden in config
                hostname,
                IRC_COLOR_CHAT_DELIMITERS,
                ')',
                IRC_COLOR_MESSAGE_JOIN,
                IRC_COLOR_CHAT_CHANNEL,
                channel,
                IRC_COLOR_MESSAGE_JOIN)
        weechat.hook_signal_send("%s,irc_in_JOIN" %server, WEECHAT_HOOK_SIGNAL_STRING,
                ":%s JOIN :%s" %(hostmask, channel))
        #debug(repr(s))
        return s
    elif action == 'parted':
        IRC_COLOR_MESSAGE_QUIT = weechat.color(weechat.config_string(weechat.config_get(
            'irc.color.message_quit')))

        # there's another part string
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has left %s%s%s")
        s = s %(weechat.prefix('quit'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_CHAT_DELIMITERS,
                ' (',
                IRC_COLOR_CHAT_HOST,
                hostname,
                IRC_COLOR_CHAT_DELIMITERS,
                ')',
                IRC_COLOR_MESSAGE_QUIT,
                IRC_COLOR_CHAT_CHANNEL,
                channel,
                IRC_COLOR_MESSAGE_QUIT)
        weechat.hook_signal_send("%s,irc_in_PART" %server, WEECHAT_HOOK_SIGNAL_STRING,
                ":%s PART %s" %(hostmask, channel))
        return s
    elif action.startswith('quit with message:'):
        IRC_COLOR_MESSAGE_QUIT = weechat.color(weechat.config_string(weechat.config_get(
            'irc.color.message_quit')))
        IRC_COLOR_REASON_QUIT = weechat.color(weechat.config_string(weechat.config_get(
            'irc.color.reason_quit')))

        reason = action[20:-1]
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has quit %s(%s%s%s)")
        s = s %(weechat.prefix('quit'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_CHAT_DELIMITERS,
                ' (',
                IRC_COLOR_CHAT_HOST,
                hostname,
                IRC_COLOR_CHAT_DELIMITERS,
                ')',
                IRC_COLOR_MESSAGE_QUIT,
                IRC_COLOR_CHAT_DELIMITERS,
                IRC_COLOR_REASON_QUIT,
                reason,
                IRC_COLOR_CHAT_DELIMITERS)
        weechat.hook_signal_send("%s,irc_in_QUIT" %server, WEECHAT_HOOK_SIGNAL_STRING,
                ":%s QUIT :%s" %(hostmask, reason))
        return s
    elif action.startswith('is now known as'):
        new_nick = action[16:]
        s = weechat.gettext("%s%s%s%s is now known as %s%s%s")
        s = s %(weechat.prefix('network'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_CHAT,
                IRC_COLOR_CHAT_NICK,
                new_nick,
                IRC_COLOR_CHAT)
        return s
    elif action.startswith('set mode:'):
        modes = action[10:] # len('set mode: ') => 10
        s = weechat.gettext("%sMode %s%s %s[%s%s%s]%s by %s%s")
        s = s %(weechat.prefix('network'),
                IRC_COLOR_CHAT_CHANNEL,
                channel,
                IRC_COLOR_CHAT_DELIMITERS,
                IRC_COLOR_CHAT,
                modes,
                IRC_COLOR_CHAT_DELIMITERS,
                IRC_COLOR_CHAT,
                IRC_COLOR_CHAT_NICK,
                nick)
        return s
    elif action.startswith('kicked'):
        IRC_COLOR_MESSAGE_QUIT = weechat.color(weechat.config_string(weechat.config_get(
            'irc.color.message_quit')))

        _, nick_kicked, reason = action.split(None, 2)
        reason = reason[9:-1]

        s = weechat.gettext("%s%s%s%s has kicked %s%s%s %s(%s%s%s)")
        s = s %(weechat.prefix('quit'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_MESSAGE_QUIT,
                IRC_COLOR_CHAT_NICK,
                nick_kicked,
                IRC_COLOR_MESSAGE_QUIT,
                IRC_COLOR_CHAT_DELIMITERS,
                IRC_COLOR_CHAT,
                reason,
                IRC_COLOR_CHAT_DELIMITERS)
        return s
    elif action.startswith('changed the topic to:'):
        topic = action[22:]
        # TODO there's other topic string
        s = weechat.gettext("%s%s%s%s has changed topic for %s%s%s to \"%s%s\"")
        s = s %(weechat.prefix('network'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_CHAT,
                IRC_COLOR_CHAT_CHANNEL,
                channel,
                IRC_COLOR_CHAT,
                topic,
                IRC_COLOR_CHAT)
        return s


    debug('CB: %s' %' '.join((data, modifier, modifier_data)))
    debug(repr(string))
    return string

### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    from weeutils import DebugBuffer
    debug = DebugBuffer('znc_debugging', globals())

    # colors
    color_delimiter   = weechat.color('chat_delimiters')
    color_script_nick = weechat.color('chat_nick')
    color_reset   = weechat.color('reset')

    # pretty [SCRIPT_NAME]
    script_nick = '%s[%s%s%s]%s' %(color_delimiter, color_script_nick, SCRIPT_NAME, color_delimiter,
            color_reset)

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    weechat.hook_modifier('weechat_print', 'buffextras_cb', '')

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
