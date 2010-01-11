# -*- coding: utf-8 -*-
###
# Copyright (c) 2009 by Elián Hanisch <lambdae2@gmail.com>
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
#   Settings:
#   * plugins.var.python.automode.auto_op/auto_voice:
#     comma separated list of patterns. When a user joins and if its hostmask matches any pattern in
#     these options the user is auto-op'd/voiced.
#   hostmaks format is like <nick>!<user>@<host>
#
###

SCRIPT_NAME    = "automode"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "simple script for auto op/voice other users"

try:
	import weechat
	WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
	import_ok = True
except ImportError:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://weechat.flashtux.org/"
	import_ok = False

import fnmatch

# settings
settings = (
		('auto_op', ''),
		('auto_voice', ''))

def join_cb(data, signal, signal_data):
	host, cmd, channel = signal_data.split() 
	host = host.lstrip(':')
	channel = channel.lstrip(':')
	user = '%s:%s' %(host, channel)
	auto_op = weechat.config_get_plugin('auto_op').split(',')
	for pattern in auto_op:
		if fnmatch.fnmatch(user, pattern):
			server = signal[:signal.find(',')]
			buffer = weechat.buffer_search('', '%s.%s' %(server, channel))
			if buffer:
				weechat.command(buffer, '/op %s' %user[:user.find('!')])
				return WEECHAT_RC_OK
	auto_voice = weechat.config_get_plugin('auto_voice').split(',')
	for pattern in auto_voice:
		if fnmatch.fnmatch(user, pattern):
			server = signal[:signal.find(',')]
			buffer = weechat.buffer_search('', '%s.%s' %(server, channel))
			if buffer:
				weechat.command(buffer, '/voice %s' %user[:user.find('!')])
				return WEECHAT_RC_OK
	return WEECHAT_RC_OK

if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
		SCRIPT_DESC, '', ''):
	weechat.hook_signal('*,irc_in_join', 'join_cb', '') 
	for opt, val in settings:
		if not weechat.config_is_set_plugin(opt):
				weechat.config_set_plugin(opt, val)
