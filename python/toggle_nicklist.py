# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
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
#
#
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-06-23, FlashCode
#     version 0.4: use modifier to show/hide nicklist on a buffer
# 2009-06-23, xt
#     version 0.3: use hiding/showing instead of disabling nicklist
# 2009-06-23, xt
#     version 0.2: use better check if buffer has nicklist
# 2009-06-22, xt <xt@bash.no>
#     version 0.1: initial release

import weechat as w

SCRIPT_NAME    = "toggle_nicklist"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.4+m4v"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Auto show and hide nicklist depending on buffer name"

SCRIPT_COMMAND = "toggle_nicklist"

settings = {
    'action'  : 'hide', # show or hide nicklist in buffers list (next option)
    'buffers' : '',     # comma separated list
    'nick_limit': '0',  # hide/show nicklist bigger than this limit (zero disables it)
}

def display_action():
    w.prnt('', '%s: action = "%s"' % (SCRIPT_NAME, w.config_get_plugin("action")))

def display_buffers():
    w.prnt('', '%s: buffers:\n%s' % (SCRIPT_NAME, 
        w.config_get_plugin("buffers").replace(',', '\n')))

def get_buffers_list():
    buffers = w.config_get_plugin('buffers')
    if buffers == '':
        return []
    else:
        return buffers.split(',')

def nicklist_cmd_cb(data, buffer, args):
    ''' Command /nicklist '''
    if args == '':
        display_action()
        display_buffers()
    else:
        try:
            del toggle_memory[buffer]
        except:
            pass
        current_buffer_name = w.buffer_get_string(buffer, 'plugin') + '.' + w.buffer_get_string(buffer, 'name')
        if args == 'show':
            w.config_set_plugin('action', 'show')
            #display_action()
            w.command('', '/window refresh')
        elif args == 'hide':
            w.config_set_plugin('action', 'hide')
            #display_action()
            w.command('', '/window refresh')
        elif args == 'add':
            list = get_buffers_list()
            if current_buffer_name not in list:
                list.append(current_buffer_name)
                w.config_set_plugin('buffers', ','.join(list))
                #display_buffers()
                w.command('', '/window refresh')
            else:
                w.prnt('', '%s: buffer "%s" is already in list' % (SCRIPT_NAME, current_buffer_name))
        elif args == 'remove':
            list = get_buffers_list()
            if current_buffer_name in list:
                list.remove(current_buffer_name)
                w.config_set_plugin('buffers', ','.join(list))
                #display_buffers()
                w.command('', '/window refresh')
            else:
                w.prnt('', '%s: buffer "%s" is not in list' % (SCRIPT_NAME, current_buffer_name))
        elif args.split()[0] == 'limit':
            try:
                n = int(args.split()[1])
                w.config_set_plugin('nick_limit', str(n))
                w.command('', '/window refresh')
            except:
                w.prnt('', '%s: missing argument or not a number' % SCRIPT_NAME)
    return w.WEECHAT_RC_OK

toggle_memory = {}
def check_nicklist_cb(data, modifier, modifier_data, string):
    ''' The callback that checks if nicklist should be displayed '''
    
    def result(b):
        if w.config_get_plugin('action') == 'show':
            b = not b
        if b:
            return "0"
        return "1"

    buffer = w.window_get_pointer(modifier_data, "buffer")
    if buffer:
        try:
            # check_nicklist_cb is called several times if using split windows, using a dict for store
            # the result save us from checking the nicklist hide/show condition over and over again.
            return result(toggle_memory[buffer])
        except:
            pass

        current_buffer_name = '%s.%s' % (w.buffer_get_string(buffer, 'plugin'),
                w.buffer_get_string(buffer, 'name'))
        buffers_list = w.config_get_plugin('buffers').split(',')
        if current_buffer_name in buffers_list:
            toggle_memory[buffer] = True
            return result(True)

        try:
            limit = int(w.config_get_plugin('nick_limit'))
        except:
            limit = 0
        if limit:
            server = w.buffer_get_string(buffer, 'localvar_server')
            channel = w.buffer_get_string(buffer, 'localvar_channel')
            irc_buffer_name = '%s.%s' % (server, channel)
            irc_channel = w.infolist_get('irc_channel', '', server)
            while w.infolist_next(irc_channel):
                if w.infolist_string(irc_channel, 'buffer_name') == irc_buffer_name:
                    nicks_count = w.infolist_integer(irc_channel, 'nicks_count')
                    break
            w.infolist_free(irc_channel)
            if nicks_count > limit:
                toggle_memory[buffer] = True
                return result(True)

        toggle_memory[buffer] = False
    return "1"

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    
    w.hook_command(SCRIPT_COMMAND,
                   "Show or hide nicklist on some buffers",
                   "[show|hide|add|remove|limit <number>]",
                   "  show: show nicklist for buffers in list (hide nicklist for other buffers by default)\n"
                   "  hide: hide nicklist for buffers in list (show nicklist for other buffers by default)\n"
                   "   add: add current buffer to list\n"
                   "remove: remove current buffer from list\n"
                   " limit: set a nick count limit (buffers with more nicks than this number will\n"
                   "        be added to the list) (0 disables it)\n\n"
                   "Instead of using add/remove, you can set buffers list with: "
                   "/set plugins.var.python.%s.buffers \"xxx\""
                   % SCRIPT_NAME,
                   "show|hide|add|remove|limit",
                   "nicklist_cmd_cb", "")
    w.hook_modifier('bar_condition_nicklist', 'check_nicklist_cb', '')
