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
###

SCRIPT_NAME    = "operator"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = ""

try:
	import weechat
	WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
	#WEECHAT_RC_ERROR = weechat.WEECHAT_RC_ERROR
	import_ok = True
except ImportError:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://weechat.flashtux.org/"
	import_ok = False

try:
	from weeutils import *
	weeutils_module = True
except:
	weeutils_module = False


class Infos(object):
	def get(self, key, arg=''):
		return weechat.info_get(key, arg)


class Buffer(object):
	def __init__(self, pointer):
		self.pointer = pointer

	def __getitem__(self, key):
		return weechat.buffer_get_string(self.pointer, key)


class Command(object):
	"""
	WeeChat command class.
	
	[define usage template]

	detailed help here
	"""
	command = None
	completion = ''
	callback = None
	hook_pointer = None
#	def __call__(self, data, buffer, args):
#		pass

	def __init__(self, command=None, callback=None):
		if command:
			self.command = command
		if callback:
			self.callback = callback
	
	def __call__(self, *args):
		self._parse(*args)
		self.cmd(self, *args)
		return WEECHAT_RC_OK

	def _parse(self, data, buffer, args):
		self.buffer = buffer
		self.data = data
		self.args = args

	def cmd(self, data, buffer, args):
		pass

	def hook(self, command=None, callback=None):
		command = command or self.command
		callback = callback or self.callback
		assert command, callback
		assert not self.hook_pointer
		description, usage, help = '', '', '' #[ s for s in map(str.strip, self.__doc__.split("\n")) if s ]
		self.hook_pointer = weechat.hook_command(command, description, usage, help, self.completion, callback, '')
		if self.hook_pointer == '':
			raise Exception, "hook_command failed"

class CommandOperator(Command):
	def __init__(self, *args):
		self.infos = Infos()
		Command.__init__(self, *args)

	def _parse(self, *args):
		Command._parse(self, *args)
		buffer = Buffer(self.buffer)
		self.server = buffer['localvar_server']
		self.channel = buffer['localvar_channel']
		self.nick = self.infos.get('irc_nick', self.server)

	def replace_vars(self, s):
		if '$channel' in s:
			s = s.replace('$channel', self.channel)
		if '$nick' in s:
			s = s.replace('$nick', self.nick)
		return s

	def get_config(self, config):
		string = '%s_%s' %(self.server, config)
		value = weechat.config_get_plugin(string)
		if not value:
			value = weechat.config_get_plugin(config)
		return value

	def get_op_cmd(self):
		value = self.get_config('op_cmd')
		if not value:
			raise Exception, "No command defined for get op."
		return self.replace_vars(value)

	def get_deop_cmd(self):
		value = self.get_config('deop_cmd')
		if not value:
			return '/deop'
		return self.replace_vars(value)

	def is_op(self):
		try:
			infolist = Infolist('irc_nick', args='%s,%s' %(self.server, self.channel))
			for nick in infolist:
				if nick['name'] == self.nick:
					if nick['flags'] & 8:
						return True
					else:
						return False
		except:
			error('Not in a channel')

	def run_cmd(self, cmd, wait=False):
		if wait:
			if wait is True:
				wait = 1
			debug('run with wait: %s' %cmd)
			weechat.command(self.buffer, '/wait %s %s' %(wait, cmd))
		else:
			debug('run: %s' %cmd)
			weechat.command(self.buffer, cmd)

	def get_op(self, **kwargs):
		self.run_cmd(self.get_op_cmd(), **kwargs)

	def drop_op(self, **kwargs):
		self.run_cmd(self.get_deop_cmd(), **kwargs)

	def kick(self, nick, reason, **kwargs):
		cmd = '/kick %s %s' %(nick, reason)
		self.run_cmd(cmd, **kwargs)

	def ban(self, nick, **kwargs):
		cmd = '/ban %s' %nick
		self.run_cmd(cmd, **kwargs)

	
class Op(CommandOperator):
	def cmd(self, *args):
		op = self.is_op()
		if op is False:
			self.get_op()
		return op


class Deop(CommandOperator):
	def cmd(self, *args):
		op = self.is_op()
		if op is True:
			self.drop_op()
		return op


class CmdOp(Op):
	op = None
	def __call__(self, *args):
		self._parse(*args)
		self.op = Op.cmd(self, *args)
		if self.op is None:
			return WEECHAT_RC_OK
		self.cmd(self, *args)
		self.drop_op(wait=2)
		return WEECHAT_RC_OK


class Kick(CmdOp):
	def cmd(self, *args):
		if ' ' in self.args:
			nick, reason = self.args.split(' ', 1)
		else:
			nick, reason = self.args, 'Adiós'
		self.kick(nick, reason, wait=not self.op)


class Ban(CmdOp):
	def cmd(self, *args):
		if ' ' in self.args:
			nick = self.args[:self.args.find(' ')]
		else:
			nick = self.args
		self.ban(nick, wait=not self.op)


class KickBan(CmdOp):
	def cmd(self, *args):
		if ' ' in self.args:
			nick, reason = self.args.split(' ', 1)
		else:
			nick, reason = self.args, 'Adiós'
		self.ban(nick, wait=not self.op)
		self.kick(nick, reason, wait=2)


# initialise commands
cmd_op = Op('oop', 'cmd_op')
cmd_deop = Deop('odeop', 'cmd_deop')
cmd_kick = Kick('okick', 'cmd_kick')
cmd_ban = Ban('oban', 'cmd_ban')
cmd_kban = KickBan('okickban', 'cmd_kban')

command_list = (cmd_op, cmd_deop, cmd_kick, cmd_ban, cmd_kban)


if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
		SCRIPT_DESC, '', ''):
	if weeutils_module:
		map(lambda x: x.hook(), command_list)
	else:
		weechat.prnt('', "%s%s: This scripts requires weeutils.py" %(weechat.prefix('error'), SCRIPT_NAME))
		weechat.prnt('', '%s%s: Load failed' %(weechat.prefix('error'), SCRIPT_NAME))

