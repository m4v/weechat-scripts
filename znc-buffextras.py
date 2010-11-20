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
    from weechat import WEECHAT_RC_OK, WEECHAT_HOOK_SIGNAL_STRING, prnt_date_tags, prnt
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import datetime, time

SCRIPT_NAME    = "znc-buffextras"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "I'm a script!"

# -------------------------------------------------------------------------
# Config 

settings = {
        'send_signals' : 'on',
        'znc_timestamp': '[%H:%M]',
        }

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

# -----------------------------------------------------------------------------
# Print Utils

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

# -----------------------------------------------------------------------------
# Script Callbacks

global buffer_playback
buffer_playback = False

def buffextras_cb(data, modifier, modifier_data, string):
# old weechat 0.3.3
#    if 'irc_privmsg' not in modifier_data:
#        return string
#    prefix, _, line = string.partition('\t')
#    prefix = weechat.string_remove_color(prefix, '')
#    if prefix != '*buffextras':
#        # not a line coming from ZNC module.
#        return string
    plugin, buffer_name, tags = modifier_data.split(';')
    if plugin != 'irc' or buffer_name == 'irc_raw':
        return string

    global buffer_playback
    if 'nick_***' in tags:
        line = string.partition('\t')[2]
        if line == 'Buffer Playback...':
            # TODO load here all config options.
            buffer_playback = True
        elif line == 'Playback Complete.':
            buffer_playback = False
        return string

    elif not buffer_playback:
        return string

    buffer = weechat.buffer_search(plugin, buffer_name)
    if not buffer:
        return string

    debug(modifier_data)
    debug(string)

    prefix, s, line = string.partition('\t')
    timestamp, s, line = line.partition(' ')

    try:
        t = time.strptime(timestamp, '[%H:%M]') # XXX this should be configurable
    except ValueError, e:
        # bad time format.
        error(e)
        return string
    else:
        t = datetime.time(t[3], t[4], t[5])
        d = datetime.datetime.combine(datetime.date.today(), t)
        time_epoch = int(time.mktime(d.timetuple()))

    if 'nick_*buffextras' not in tags:
        # not a line coming from ZNC buffextras module.
        prnt_date_tags(buffer, time_epoch, tags, "%s\t%s" %(prefix, line))
        return ''

    hostmask, s, line = line.partition(' ')
    nick = hostmask[:hostmask.find('!')]
    host = hostmask[len(nick) + 1:]
    server, channel = buffer_name.split('.', 1)
    
    s = None
    if line == 'joined':
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has joined %s%s%s")
        s = s %(weechat.prefix('join'),
                COLOR_CHAT_NICK, # TODO there's a function for use nick's color
                nick,
                COLOR_CHAT_DELIMITERS,
                ' (',
                COLOR_CHAT_HOST, # TODO host can be hidden in config
                host,
                COLOR_CHAT_DELIMITERS,
                ')',
                COLOR_MESSAGE_JOIN,
                COLOR_CHAT_CHANNEL,
                channel,
                COLOR_MESSAGE_JOIN)

        weechat.hook_signal_send("%s,irc_in_JOIN" %server, WEECHAT_HOOK_SIGNAL_STRING,
                ":%s JOIN :%s" %(hostmask, channel))

    elif line == 'parted':
        # buffextras doesn't seem to send the part's reason.
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has left %s%s%s")
        s = s %(weechat.prefix('quit'),
                COLOR_CHAT_NICK,
                nick,
                COLOR_CHAT_DELIMITERS,
                ' (',
                COLOR_CHAT_HOST,
                host,
                COLOR_CHAT_DELIMITERS,
                ')',
                COLOR_MESSAGE_QUIT,
                COLOR_CHAT_CHANNEL,
                channel,
                COLOR_MESSAGE_QUIT)

        weechat.hook_signal_send("%s,irc_in_PART" %server, WEECHAT_HOOK_SIGNAL_STRING,
                ":%s PART %s" %(hostmask, channel))

    elif line.startswith('quit with message:'):
        reason = line[line.find('[') + 1:-1]
        s = weechat.gettext("%s%s%s%s%s%s%s%s%s%s has quit %s(%s%s%s)")
        s = s %(weechat.prefix('quit'),
                COLOR_CHAT_NICK,
                nick,
                COLOR_CHAT_DELIMITERS,
                ' (',
                COLOR_CHAT_HOST,
                host,
                COLOR_CHAT_DELIMITERS,
                ')',
                COLOR_MESSAGE_QUIT,
                COLOR_CHAT_DELIMITERS,
                COLOR_REASON_QUIT,
                reason,
                COLOR_CHAT_DELIMITERS)

        weechat.hook_signal_send("%s,irc_in_QUIT" %server, WEECHAT_HOOK_SIGNAL_STRING,
                ":%s QUIT :%s" %(hostmask, reason))

    elif line.startswith('is now known as '):
        new_nick = line.rpartition(' ')[-1]
        s = weechat.gettext("%s%s%s%s is now known as %s%s%s")
        s = s %(weechat.prefix('network'),
                COLOR_CHAT_NICK,
                nick,
                COLOR_CHAT,
                COLOR_CHAT_NICK,
                new_nick,
                COLOR_CHAT)

    elif line.startswith('set mode: '):
        modes = line[line.find(':') + 2:]
        s = weechat.gettext("%sMode %s%s %s[%s%s%s]%s by %s%s")
        s = s %(weechat.prefix('network'),
                COLOR_CHAT_CHANNEL,
                channel,
                COLOR_CHAT_DELIMITERS,
                COLOR_CHAT,
                modes,
                COLOR_CHAT_DELIMITERS,
                COLOR_CHAT,
                COLOR_CHAT_NICK,
                nick)

    elif line.startswith('kicked'):
        _, nick_kicked, reason = line.split(None, 2)
        reason = reason[reason.find('[') + 1:-1]
        s = weechat.gettext("%s%s%s%s has kicked %s%s%s %s(%s%s%s)")
        s = s %(weechat.prefix('quit'),
                COLOR_CHAT_NICK,
                nick,
                COLOR_MESSAGE_QUIT,
                COLOR_CHAT_NICK,
                nick_kicked,
                COLOR_MESSAGE_QUIT,
                COLOR_CHAT_DELIMITERS,
                COLOR_CHAT,
                reason,
                COLOR_CHAT_DELIMITERS)

    elif line.startswith('changed the topic to: '):
        topic = line[line.find(':') + 2:]
        s = weechat.gettext("%s%s%s%s has changed topic for %s%s%s to \"%s%s\"")
        s = s %(weechat.prefix('network'),
                COLOR_CHAT_NICK,
                nick,
                COLOR_CHAT,
                COLOR_CHAT_CHANNEL,
                channel,
                COLOR_CHAT,
                topic,
                COLOR_CHAT)
    
    if s is None:
        error('Unknown message from ZNC: %r' % string)
        return string
    else:
        prnt_date_tags(buffer, time_epoch, tags, s)
        return ''

### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    # colors
    config_get_string = lambda s: weechat.config_string(weechat.config_get(s))

    COLOR_RESET           = weechat.color('reset')
    COLOR_CHAT_DELIMITERS = weechat.color('chat_delimiters')
    COLOR_CHAT_NICK       = weechat.color('chat_nick')
    COLOR_CHAT_HOST       = weechat.color('chat_host')
    COLOR_CHAT_CHANNEL    = weechat.color('chat_channel')
    COLOR_CHAT            = weechat.color('chat')
    COLOR_MESSAGE_JOIN    = weechat.color(config_get_string('irc.color.message_join'))
    COLOR_MESSAGE_QUIT    = weechat.color(config_get_string('irc.color.message_quit'))
    COLOR_REASON_QUIT     = weechat.color(config_get_string('irc.color.reason_quit'))


    # pretty [SCRIPT_NAME]
    script_nick = '%s[%s%s%s]%s' % (COLOR_CHAT_DELIMITERS, 
                                    COLOR_CHAT_NICK,
                                    SCRIPT_NAME, 
                                    COLOR_CHAT_DELIMITERS,
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
