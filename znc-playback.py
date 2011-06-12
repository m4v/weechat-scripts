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

import re
import time
import datetime

SCRIPT_NAME    = "znc-playback"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "I'm a script!"

# -------------------------------------------------------------------------
# Config 

settings = {
        'send_signals' : 'off',
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

buffer_playback = {}
signal_playback = set()

_hostmaskRe = re.compile(r':?\S+!\S+@\S+') # poor but good enough
def is_hostmask(s):
    """Returns whether or not the string s starts with something like a hostmask."""
    return _hostmaskRe.match(s) is not None

def playback_cb(data, modifier, modifier_data, string):
    global COLOR_RESET, COLOR_CHAT_DELIMITERS, COLOR_CHAT_NICK, COLOR_CHAT_HOST, \
           COLOR_CHAT_CHANNEL, COLOR_CHAT, COLOR_MESSAGE_JOIN, COLOR_MESSAGE_QUIT, \
           COLOR_REASON_QUIT, SMART_FILTER
    global send_signals, znc_timestamp
    global signal_playback

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
            debug("* buffer playback for %s", buffer_name)
            if not buffer_playback:
                get_config_options()
                signal_playback.clear()
            buffer_playback[buffer_name] = True
        elif line == 'Playback Complete.':
            debug("* end of playback for %s", buffer_name)
            del buffer_playback[buffer_name]
            if not buffer_playback:
                if send_signals:
                    do_signal_playback()
        return string

    elif buffer_name not in buffer_playback:
        return string

    buffer = weechat.buffer_search(plugin, buffer_name)
    if not buffer:
        return string

    prefix, s, line = string.partition('\t')
    if 'irc_action' in tags or 'irc_notice' in tags:
        _prefix, s, line = line.partition(' ')
        timestamp, s, line = line.partition(' ')
        line = '%s %s' % (_prefix, line)
    else:
        timestamp, s, line = line.partition(' ')

    if ' ' in znc_timestamp:
        error("configured timestamp is '%s', it can't have spaces." % znc_timestamp)
        #error_unhook_all()
        return string

    try:
        t = time.strptime(timestamp, znc_timestamp)
    except ValueError, e:
        # bad time format.
        error(e)
        debug("%s\n%s" % (modifier_data, string))
        #error_unhook_all()
        return string
    else:
        if t[0] == 1900:
            # only hour information, complete year, month and day with today's date
            # might be incorrect though if day changed during playback.
            t = datetime.time(*t[3:6])
            d = datetime.datetime.combine(datetime.date.today(), t)
        else:
            d = datetime.datetime(*t[:6])
        time_epoch = int(time.mktime(d.timetuple()))


    if 'nick_*buffextras' not in tags:
        # not a line coming from ZNC buffextras module.
        prnt_date_tags(buffer, time_epoch, tags, "%s\t%s" %(prefix, line))
        return ''
    else:
        # don't highlight me when I join a channel.
        tags += ',no_highlight'

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

        if send_signals:
            signal_playback.add((time_epoch, server + ",irc_in_JOIN", 
                                 ":%s JOIN :%s" % (hostmask, channel)))

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

        if send_signals:
            signal_playback.add((time_epoch, server + ",irc_in_PART", 
                                 ":%s PART %s" % (hostmask, channel)))

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

        # QUIT messages should be sent only once per channel.
        if send_signals:
            signal_playback.add((time_epoch, server + ",irc_in_QUIT", 
                                 ":%s QUIT :%s" % (hostmask, reason)))

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

        # NICK messages should be sent only once per channel.
        if send_signals:
            signal_playback.add((time_epoch, server + ",irc_in_NICK", 
                                 ":%s NICK :%s" % (hostmask, new_nick)))

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
        
        if send_signals:
            # buffextras can send an invalid hostmask "nick!@" sometimes
            # fix it so at least is valid.
            if not is_hostmask(hostmask):
                nick = hostmask[:hostmask.find('!')]
                hostmask = nick + '!unknow@unknow'
            signal_playback.add((time_epoch, server + ",irc_in_MODE", 
                                 ":%s MODE %s %s" % (hostmask, channel, modes)))

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

        if send_signals:
            signal_playback.add((time_epoch, server + ",irc_in_KICK", 
                                 ":%s KICK %s %s :%s" % (hostmask, channel, nick_kicked, reason)))


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

def do_signal_playback():
    global signal_playback
    L = list(signal_playback)
    for t, signal, string in sorted(L, key=lambda x: x[0]):
        debug('%s %s %s', t, signal, string)
        weechat.hook_signal_send(signal, WEECHAT_HOOK_SIGNAL_STRING, string)
    signal_playback.clear()

def get_config_options():
    global COLOR_RESET, COLOR_CHAT_DELIMITERS, COLOR_CHAT_NICK, COLOR_CHAT_HOST, \
           COLOR_CHAT_CHANNEL, COLOR_CHAT, COLOR_MESSAGE_JOIN, COLOR_MESSAGE_QUIT, \
           COLOR_REASON_QUIT
    global send_signals, znc_timestamp 

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
        
    send_signals = get_config_boolean('send_signals')
    znc_timestamp = weechat.config_get_plugin('znc_timestamp')

def error_unhook_all():
    global print_hook
    if print_hook:
        error("script disabled, fix date format and reload.")
        weechat.unhook(print_hook)

# -----------------------------------------------------------------------------
# Main

print_hook = ''
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    get_config_options()

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

    print_hook = weechat.hook_modifier('weechat_print', 'playback_cb', '')

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
