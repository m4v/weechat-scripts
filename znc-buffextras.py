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
settings = { 'send_signals': 'on' }

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

# -----------------------------------------------------------------------------
# Print Utils

from weechat import prnt

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


def buffextras_cb(data, modifier, modifier_data, string):
    if 'irc_privmsg' not in modifier_data:
        return string
    prefix, _, line = string.partition('\t')
    prefix = weechat.string_remove_color(prefix, '')
    if prefix != '*buffextras':
        # not a line coming from ZNC module.
        return string

    debug(repr(string))

    time, hostmask, line = line.split(None, 2)
    nick = hostmask[:hostmask.find('!')]
    host = hostmask[len(nick)+1:]
    server, channel = modifier_data.split(';')[1].split('.', 1)

    if line == 'joined':
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has joined %s%s%s")
        s = s %(weechat.prefix('join'),
                IRC_COLOR_CHAT_NICK, # TODO there's a function for use nick's color
                nick,
                IRC_COLOR_CHAT_DELIMITERS,
                ' (',
                IRC_COLOR_CHAT_HOST, # TODO host can be hidden in config
                host,
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

    elif line == 'parted':
        # TODO there's another part string
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has left %s%s%s")
        s = s %(weechat.prefix('quit'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_CHAT_DELIMITERS,
                ' (',
                IRC_COLOR_CHAT_HOST,
                host,
                IRC_COLOR_CHAT_DELIMITERS,
                ')',
                IRC_COLOR_MESSAGE_QUIT,
                IRC_COLOR_CHAT_CHANNEL,
                channel,
                IRC_COLOR_MESSAGE_QUIT)
        weechat.hook_signal_send("%s,irc_in_PART" %server, WEECHAT_HOOK_SIGNAL_STRING,
                ":%s PART %s" %(hostmask, channel))
        return s

    elif line.startswith('quit with message:'):
        reason = line[line.find('['):-1]
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has quit %s(%s%s%s)")
        s = s %(weechat.prefix('quit'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_CHAT_DELIMITERS,
                ' (',
                IRC_COLOR_CHAT_HOST,
                host,
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

    elif line.startswith('is now known as '):
        new_nick = line.rpartition(' ')[-1]
        s = weechat.gettext("%s%s%s%s is now known as %s%s%s")
        s = s %(weechat.prefix('network'),
                IRC_COLOR_CHAT_NICK,
                nick,
                IRC_COLOR_CHAT,
                IRC_COLOR_CHAT_NICK,
                new_nick,
                IRC_COLOR_CHAT)
        return s

    elif line.startswith('set mode: '):
        modes = line[line.find(':') + 1:]
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

    elif line.startswith('kicked'):
        _, nick_kicked, reason = line.split(None, 2)
        reason = reason[reason.find('['):-1]
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

    elif line.startswith('changed the topic to:'):
        topic = line[line.find(':') + 1:]
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


    debug(' *** unknown msg ***')
    debug('CB: %s' %' '.join((data, modifier, modifier_data)))
    debug(repr(string))
    return string

### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    # colors
    config_get_string = lambda s: weechat.config_string(weechat.config_get(s))

    COLOR_RESET               = weechat.color('reset')
    IRC_COLOR_CHAT_DELIMITERS = weechat.color('chat_delimiters')
    IRC_COLOR_CHAT_NICK       = weechat.color('chat_nick')
    IRC_COLOR_CHAT_HOST       = weechat.color('chat_host')
    IRC_COLOR_CHAT_CHANNEL    = weechat.color('chat_channel')
    IRC_COLOR_CHAT            = weechat.color('chat')
    IRC_COLOR_MESSAGE_JOIN    = weechat.color(config_get_string('irc.color.message_join'))
    IRC_COLOR_MESSAGE_QUIT    = weechat.color(config_get_string('irc.color.message_quit'))
    IRC_COLOR_REASON_QUIT     = weechat.color(config_get_string('irc.color.reason_quit'))


    # pretty [SCRIPT_NAME]
    script_nick = '%s[%s%s%s]%s' % (IRC_COLOR_CHAT_DELIMITERS, 
                                    IRC_COLOR_CHAT_NICK,
                                    SCRIPT_NAME, 
                                    IRC_COLOR_CHAT_DELIMITERS,
                                    COLOR_RESET)

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    weechat.hook_modifier('weechat_print', 'buffextras_cb', '')

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
