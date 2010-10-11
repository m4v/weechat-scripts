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
# along with this program.	If not, see <http://www.gnu.org/licenses/>.
###

###
#
#
###

SCRIPT_NAME    = "bufsort"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Remember buffer sorting"
SCRIPT_COMMAND = "bufsort"

script_debug = True
script_file = 'bufsort.pkl'

try:
	import weechat
	from weechat import WEECHAT_RC_OK
	import_ok = True
except ImportError:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://weechat.flashtux.org/"
	import_ok = False

# FIXME I should copy the whole class instead of importing.
from weeutils import Infolist

### messages
def debug(s, prefix='debug:'):
	"""Debug msg"""
	if script_debug:
		weechat.prnt('', '%s %s'  %(prefix,s)) 

def error(s):
	"""Error msg"""
	weechat.prnt('', '%s%s' %(weechat.prefix('error'), s))

def say(s, prefix=''):
	"""Normal msg"""
	weechat.prnt('', '%s\t%s' %(prefix, str(s)))

### functions
def get_buffers_dict():
	d = {}
	for buffer in Infolist('buffer'):
		name = buffer['name'] 
		if not name.startswith('__'):
			d[name] = str(buffer['number'])
	return d

def sort_buffers():
	global buffer_dict
	buffer_list = list(buffer_dict.iteritems())
	# sort list by number
	buffer_list.sort(key=lambda x: x[1])
	for name, number in buffer_list:
		pointer = weechat.buffer_search('', name)
		if pointer:
			weechat.buffer_set(pointer, 'number', number)
		else:
			open_empty_buffer(number)

def open_empty_buffer(number):
	name = '__%s__' %number
	if not weechat.buffer_search('', name):
		buffer = weechat.buffer_new(name, '', '', '', '')
		weechat.buffer_set(buffer, 'number', number)
		weechat.buffer_set(buffer, 'short_name', ' ')

def save_buffer_dict():
	import pickle
	global buffer_dict
	path = '%s/%s' %(weechat.info_get('weechat_dir', ''), script_file)
	debug(path)
	try:
		fd = open(path, 'wb')
		pickle.dump(buffer_dict, fd)
		fd.close()
		#debug('saved sorting in %s' %script_file)
	except IOError:
		error('Failed to save buffer sorting in %s' %path)

def script_init():
	import pickle
	global buffer_dict
	path = '%s/%s' %(weechat.info_get('weechat_dir', ''), script_file)
	try:
		fd = open(path, 'rb')
		buffer_dict = pickle.load(fd)
		fd.close()
		debug('loaded sorting from %s' %script_file)
	except IOError:
		buffer_dict = {}
	debug(buffer_dict)

def script_unload():
	# save the buffer sorting
	# save_buffer_dict()
	return WEECHAT_RC_OK

### command
def cmd_bufsort(data, buffer, args):
	global buffer_dict

	args = args.split()
	if not args:
		weechat.command('', '/help %s' %SCRIPT_COMMAND)
		return WEECHAT_RC_OK
	cmd = args[0]
	if cmd == 'save':
		buffer_dict = get_buffers_dict()
		debug(buffer_dict)
		save_buffer_dict()
		#say('saved sorting in %s' %script_file)
	elif cmd == 'sort':
		sort_buffers()
	return WEECHAT_RC_OK

### signal callbacks
def buffer_opened_cb(data, signal, signal_data):
	global buffer_dict, empty_buffer_dict
	debug('%s %s %s' %(data, signal, signal_data))
	name = weechat.buffer_get_string(signal_data, 'name')
	if name not in buffer_dict:
		number = str(weechat.buffer_get_integer(signal_data, 'number'))
		buffer_dict[name] = number
	else:
		sort_buffers()
	return WEECHAT_RC_OK

def buffer_closed_cb(data, signal, signal_data):
	global buffer_dict, empty_buffer_dict
	debug('%s %s %s' %(data, signal, signal_data))
	sort_buffers()	
	return WEECHAT_RC_OK

def buffer_moved_cb(data, signal, signal_data):
	global buffer_dict, empty_buffer_dict
	debug('%s %s %s' %(data, signal, signal_data))
	sort_buffers()	
	return WEECHAT_RC_OK

### main
if __name__ == '__main__' and import_ok:
	if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
			'script_unload', ''):
		script_init()
		weechat.hook_command(SCRIPT_COMMAND, SCRIPT_DESC, "",
				"", 
				"",
				'cmd_bufsort', '')
		#weechat.hook_signal('buffer_opened', 'buffer_opened_cb', '')
		#weechat.hook_signal('buffer_closed', 'buffer_closed_cb', '')
		#weechat.hook_signal('buffer_closing', 'buffer_closing_cb', '')
		#weechat.hook_signal('buffer_moved', 'buffer_moved_cb', '')


# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
