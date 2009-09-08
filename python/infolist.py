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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###

###
#	WeeChat infolist inspector
#	
#	This is a tool I wrote for help me with WeeChat scripting and infolists,
#	I hope it can be usefull to anyone writing scripts in Weechat.
#	
###

SCRIPT_NAME    = "infolist"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "WeeChat infolist inspector"
SCRIPT_COMMAND = "infolist"


try:
	import weechat
	from weechat import WEECHAT_RC_OK
	import_ok = True
except ImportError:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://weechat.flashtux.org/"
	import_ok = False

try:
	from weeutils import *
except ImportError:
	import_ok = False
	print "This script requires weeutils.py module."

### function definition
def buffer_create():
	"""Returns our buffer pointer, creates the buffer if needed."""
	buffer = weechat.buffer_search('python', SCRIPT_NAME)
	if not buffer:
		buffer = weechat.buffer_new(SCRIPT_NAME, '', '', '', '')
		weechat.buffer_set(buffer, 'time_for_each_line', '0')
		weechat.buffer_set(buffer, 'nicklist', '0')
		weechat.buffer_set(buffer, 'title', SCRIPT_DESC)
		weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
		weechat.buffer_set(buffer, 'display', '1')
	return buffer

def script_init():
	global script_infolist, script_buffer
	script_infolist = None
	script_buffer = None

def script_unload():
	global script_infolist
	del script_infolist
	return WEECHAT_RC_OK

### command
def cmd_infolist(data, buffer, args):
	"""/infolist command"""
	global script_infolist, script_buffer
	#debug(args)
	if not args and script_infolist is None:
		weechat.command('', '/help %s' %SCRIPT_COMMAND)
		return WEECHAT_RC_OK
	script_buffer = buffer_create()
	if not args:
		say(script_infolist)
		return WEECHAT_RC_OK
	# argument parsing
	args = args.split()
	try:
		cmd = args.pop(0)
		if cmd not in ('get', 'free', 'next', 'prev', 'fields', 'read', 'list'):
			raise Exception("'%s' not a valid command." %cmd)
		if cmd == 'get':
			try:
				infolist_name = args.pop(0)
			except:
				raise Exception("command 'get' requires at least one argument.")
			infolist_args = infolist_pointer = ''
			if args:
				infolist_pointer = args.pop(0)
				if infolist_pointer in ('NULL', "''"):
					infolist_pointer = ''
				if args:
					infolist_args = args.pop(0)
					if infolist_args in ('NULL', "''"):
						infolist_args = ''
				else:
					# just one arg for get, lets check if infolist_pointer is really a pointer
					if not infolist_pointer.startswith('0x'):
						# doesn't look like a pointer
						infolist_args = infolist_pointer
						infolist_pointer = ''
		elif cmd == 'read':
			all_items = False
			variable_name = None
			if '--all' in args:
				all_items = True
				del args[args.index('--all')]
			if args:
				variable_name = args[0]
	except Exception, e:
		error("Bad argument, %s" %e, buffer=script_buffer)
		return WEECHAT_RC_OK
	# arguments look good
	if cmd == 'get':
		try:
			infolist = Infolist(infolist_name, pointer=infolist_pointer, args=infolist_args)
			script_infolist = infolist	# the previously open infolist (if there was one) is freed
										# by python
			say('Success, %s' %script_infolist, buffer=script_buffer)
		except Exception, e:
			error(e, buffer=script_buffer)
			return WEECHAT_RC_OK
	# needs an infolist 
	elif script_infolist is not None: 
		if cmd == 'free':
			if script_infolist:
				say('pointer %s freed' %script_infolist.pointer, buffer=script_buffer)
				script_infolist.free()
			else:
				say("'%s' already purged" %script_infolist.name, buffer=script_buffer)
		# needs an open infolist
		elif script_infolist:
			if cmd == 'next':
				if script_infolist.next():
					say("Moved the cursor to the next item of '%s'" %script_infolist.name,
							buffer=script_buffer)
				else:
					error('End of list reached.', buffer=script_buffer)
			elif cmd == 'prev':
				if script_infolist.prev():
					say("Moved the cursor to the previous item of '%s'" %script_infolist.name,
							buffer=script_buffer)
				else:
					error('At the beginning of list.', buffer=script_buffer)
			elif cmd == 'fields':
				fields = script_infolist.get_fields()
				if fields:
					if args:
						name = args[0]
						try:
							say(fields[name], name + ':', buffer=script_buffer)
						except KeyError:
							error("variable '%s' doesn't exist in %s." %(name, script_infolist),
									buffer=script_buffer)
							return WEECHAT_RC_OK
					else:
						say('--', buffer=script_buffer)
						for name, type in fields.iteritems():
							say(type, name + ':', buffer=script_buffer)
			elif cmd == 'read':
				id = ''
				if all_items:
					id = 1
					script_infolist.reset() # list them from the beginning
				for item in script_infolist:
					if not all_items:
						# we're going to show just current item and break, but when the loop
						# started 
						# we're already in the next item, so go back one
						item.prev()
					if variable_name:
						try:
							say(item[variable_name], variable_name + ':', buffer=script_buffer)
						except KeyError:
							error("variable '%s' doesn't exist in %s."\
									%(variable_name, script_infolist), buffer=script_buffer)
							return WEECHAT_RC_OK
					else:
						say('-- #%s --' %id, buffer=script_buffer)
						for name in item.variables():
							say(item[name], name + ':', buffer=script_buffer)
					if not all_items:
						break
					else:
						id += 1
		else:
			error("Can't do that with a purged infolist.", buffer=script_buffer)
	else:
		error("Got no infolist.", buffer=script_buffer)
	return WEECHAT_RC_OK

### completion
infolist_list = (
	'alias',
	'irc_channel',
	'irc_ignore',
	'irc_nick',
	'irc_server',
	'logger_buffer',
	'lua_script',
	'perl_script',
	'python_script',
	'relay',
	'ruby_script',
	'tcl_script',
	'bar',
	'bar_item',
	'bar_window',
	'buffer',
	'buffer_lines',
	'filter',
	'history',
	'hook',
	'hotlist',
	'key',
	'nicklist',
	'option',
	'plugin',
	'window',
	'xfer',
	)

def completion_infolist(data, completion_item, buffer, completion):
	"""Complete with standard infolist names."""
	for name in infolist_list:
		weechat.hook_completion_list_add(completion, name, 0, weechat.WEECHAT_LIST_POS_SORT)
	return WEECHAT_RC_OK

def completion_infolist_variables(data, completion_item, buffer, completion):
	"""Complete with the variable names of current infolist."""	
	global script_infolist
	if script_infolist:
		for name in script_infolist.variables():
			weechat.hook_completion_list_add(completion, name, 0, weechat.WEECHAT_LIST_POS_SORT)
	return WEECHAT_RC_OK


### main
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
			'script_unload', ''):
		script_init()
		weechat.hook_command(SCRIPT_COMMAND, SCRIPT_DESC,
				"[get <infolist name> [<item pointer>] [<arguments>] | fields [<variable>] "
				"| read [<variable>] [--all] | next | prev | free]",
				"   get: get the requested infolist, arguments if not given default to NULL\n"
				"fields: show the type of all variables (or one if name given) of current "
				"infolist item.\n"
				"  read: show the value of all variables (or one if name given) of current "
				"infolist item. If --all flag given it reads the variable(s) for all items.\n"
				"  next: move to next item of current infolist.\n"
				"  prev: move to previous item of current infolist.\n"
				"  free: purge current infolist.\n\n"
				"If no commands given, shows current infolist (or /help is there's none). "
				"The commands 'fields' and 'read' will automatically switch to the first "
				"item if needed.\n\n"
				"Examples:\n"
				"  /infolist get buffer -> gets infolist 'buffer'\n"
				"  /infolist fields -> list fields of 'buffer'\n"
				"  /infolist get irc_nicks freenode,#weechat -> gets infolist 'irc_nicks' for "
				"freenode.#weechat\n"
				"  /infolist read name --all -> list 'name' for all items", 
				"get %(weeutils_infolist)"
				"|| fields %(weeutils_infolist_vars)"
				"|| read %(weeutils_infolist_vars) --all"
				"|| next"
				"|| prev"
				"|| free",
				'cmd_infolist', '')
		weechat.hook_completion('weeutils_infolist', "list of standard infolist names",
				'completion_infolist', '')
		weechat.hook_completion('weeutils_infolist_vars', "list of variables of current infolist",
				'completion_infolist_variables', '')


# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
