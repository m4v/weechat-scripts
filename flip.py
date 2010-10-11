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
#   History:
#   2010-01-14
#   version 0.1: new script!
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
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Flips text upside down."
SCRIPT_COMMAND = "flip"

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
#u'P' : u'\N{CYRILLIC CAPITAL LETTER KOMI DE}',
u'P' : u'd',
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


### Commands
def cmd_flip(data, buffer, args):
    """Flips text."""
    if not args:
        return WEECHAT_RC_OK

    unicode_args = args.decode('utf-8')
    L = [ fliptable[c] for c in unicode_args ]
    L.reverse()
    u = u''.join(L)
    s = u.encode('utf-8')

    weechat.buffer_set(buffer, 'input', s)

    return WEECHAT_RC_OK


### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):

    weechat.hook_command(SCRIPT_COMMAND, cmd_flip.__doc__, "text", "", '', 'cmd_flip', '')

    #for test all chars, change False to True
    if False:
        L = []
        for k, v in fliptable.iteritems():
            L.append(u'%s %s' %(k, v))
        u = u' '.join(L)
        s = u.encode('utf-8')
        weechat.prnt('', s)

    fliptable = TwoWayDict(fliptable)


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
