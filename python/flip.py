# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2010 by Elián Hanisch <lambdae2@gmail.com>
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

SCRIPT_NAME    = "flip"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1-dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "I'm a script!"
SCRIPT_COMMAND = "flip"

script_nick    = "[%s]" %SCRIPT_NAME

### Config ###
settings = {}

fliptable = {
# Upper case
u'A' : u'\N{FOR ALL}',
u'B' : u'\N{GREEK SMALL LETTER XI}',
u'C' : u'\N{ROMAN NUMERAL REVERSED ONE HUNDRED}',
u'D' : u'\N{LEFT HALF BLACK CIRCLE}',
u'E' : u'\N{LATIN CAPITAL LETTER REVERSED E}',
u'F' : u'\N{TURNED CAPITAL F}',
u'G' : u'\N{TURNED SANS-SERIF CAPITAL G}',
u'J' : u'\N{LATIN SMALL LETTER LONG S}',
u'K' : u'\N{RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT}',
u'L' : u'\N{LATIN CAPITAL LETTER TURNED L}',
u'M' : u'W',
u'N' : u'\N{LATIN LETTER SMALL CAPITAL REVERSED N}',
u'P' : u'\N{CYRILLIC CAPITAL LETTER KOMI DE}',
u'Q' : u'\N{GREEK CAPITAL LETTER OMICRON WITH TONOS}',
u'R' : u'\N{LATIN LETTER SMALL CAPITAL TURNED R}',
u'T' : u'\N{UP TACK}',
u'U' : u'\N{INTERSECTION}',
u'V' : u'\N{LATIN CAPITAL LETTER TURNED V}',
u'Y' : u'\N{TURNED SANS-SERIF CAPITAL Y}',
# Lower case
u'a' : u'\N{LATIN SMALL LETTER TURNED A}',
u'b' : u'q',
u'c' : u'\N{LATIN SMALL LETTER OPEN O}',
u'd' : u'p',
u'e' : u'\N{LATIN SMALL LETTER TURNED E}',
u'f' : u'\N{LATIN SMALL LETTER DOTLESS J WITH STROKE}',
u'g' : u'\N{LATIN SMALL LETTER B WITH TOPBAR}',
u'h' : u'\N{LATIN SMALL LETTER TURNED H}',
u'i' : u'\N{LATIN SMALL LETTER DOTLESS I}',
u'j' : u'\N{LATIN SMALL LETTER R WITH FISHHOOK}',
u'k' : u'\N{LATIN SMALL LETTER TURNED K}',
u'l' : u'\N{LATIN SMALL LETTER ESH}',
u'm' : u'\N{LATIN SMALL LETTER TURNED M}',
u'n' : u'u',
u'r' : u'\N{LATIN SMALL LETTER TURNED R}',
u't' : u'\N{LATIN SMALL LETTER TURNED T}',
u'v' : u'\N{LATIN SMALL LETTER TURNED V}',
u'w' : u'\N{LATIN SMALL LETTER TURNED W}',
u'y' : u'\N{LATIN SMALL LETTER TURNED Y}',
# Numbers
u'3' : u'\N{LATIN CAPITAL LETTER OPEN E}',
u'4' : u'\N{CANADIAN SYLLABICS YA}',
u'6' : u'9',
u'7' : u'\N{LATIN CAPITAL LETTER L WITH MIDDLE TILDE}',
# Misc
u'!' : u'\N{INVERTED EXCLAMATION MARK}',
u'"' : u'\N{DOUBLE LOW-9 QUOTATION MARK}',
u'&' : u'\N{TURNED AMPERSAND}',
u'\'': u',',
u'(' : u')',
u'.' : u'\N{DOT ABOVE}',
u'/' : u'\\',
u';' : u'\N{ARABIC SEMICOLON}',
u'<' : u'>',
u'?' : u'\N{INVERTED QUESTION MARK}',
u'[' : u']',
u'_' : u'\N{OVERLINE}',
u'{' : u'}',
u'\N{UNDERTIE}'                       : u'\N{CHARACTER TIE}',
u'\N{LEFT SQUARE BRACKET WITH QUILL}' : u'\N{RIGHT SQUARE BRACKET WITH QUILL}',
u'\N{THEREFORE}'                      : u'\N{BECAUSE}',
# Spanish
u'\N{LATIN SMALL LETTER N WITH TILDE}' : u'\N{LATIN SMALL LETTER U WITH TILDE BELOW}',
}


### Classes ###
class TwoWayDict(dict):
    def __init__(self, d):
        dict.__init__(self, d)
        keys = d.keys()
        for k, v in d.iteritems():
            if v not in keys:
                self[v] = k

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return key

fliptable = TwoWayDict(fliptable)


### Messages ###
def debug(s, prefix='debug'):
    """Debug msg"""
    if not weechat.config_get_plugin('debug'): return
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

def say_unicode(s, prefix=None, buffer=''):
    """normal msg for unicode strings"""
    prefix = prefix or script_nick
    u = u'%s\t%s' %(prefix, s)
    weechat.prnt(buffer, u.encode('utf-8'))


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


### Commands
def cmd_flip(data, buffer, args):
    """ """
    if not args:
        return WEECHAT_RC_OK

    L = [ fliptable[c] for c in args ]
    L.reverse()
    u = u''.join(L)
    s = u.encode('utf-8')
    weechat.prnt(buffer, s)
    
    return WEECHAT_RC_OK


### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)
    
    weechat.hook_command(SCRIPT_COMMAND, cmd_flip.__doc__, "",
            "", '', 'cmd_flip', '')


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
