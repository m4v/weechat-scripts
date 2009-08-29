# -*- coding: utf-8 -*-
SCRIPT_NAME    = "dbusnotify"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = ""
#SCRIPT_COMMAND = "egrep"

try:
	import weechat
	from weechat import WEECHAT_RC_OK
	import_ok = True
except:
	import_ok = False
import dbus, time#, fnmatch

now = time.time

def debug(s, prefix='debug'):
	"""Debug msg"""
	weechat.prnt('', '%s: %s'  %(prefix,s))

def error(s, prefix=SCRIPT_NAME, buffer=''):
	weechat.prnt(buffer, '%s%s: %s' %(weechat.prefix('error'), prefix, s))

settings = (('ignore_private', ''),)
#		('ignore_hilight', ''))

def get_config_ignores(config):
	ignores = weechat.config_get_plugin(config)
	if ignores:
		return ignores.split(',')
	else:
		return []

#def match_host(pattern, host):
#	return fnmatch.fnmatch(host, pattern)

def format_tags(s):
	s = s.replace('<', '&lt;')
	s = s.replace('>', '&gt;')
	return s

def notify_hilight(data, buffer, time, tags, display, hilight, prefix, msg ):
	#debug(';'.join((data, buffer, time, tags, display, hilight, prefix, msg)))
	if hilight is '1':
		channel = weechat.buffer_get_string(buffer, 'short_name')
		if not channel:
			channel = weechat.buffer_get_string(buffer, 'name')
		msg = format_tags(msg)
		dbus_notify(channel, '<b>%s</b>: %s' %(prefix, msg))
	return WEECHAT_RC_OK

def notify_priv(data, signal, msg):
	#debug(','.join((data, signal, message)))
	ignore = get_config_ignores('ignore_private')
	for pattern in ignore:
		if msg.startswith(pattern):
			return WEECHAT_RC_OK
	msg = format_tags(msg)
	dbus_notify(*msg.split('\t', 1))
	return WEECHAT_RC_OK

timestamp = 0
notify_id = ''
notify_msg = ''
notify_title = ''
def dbus_notify(channel, msg):
	global notify_id, notify_title, notify_msg, timestamp
	try:
		bus = dbus.SessionBus()
		notify_object = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		notify = dbus.Interface(notify_object, 'org.freedesktop.Notifications')
		if ((now() - timestamp) < 10) and (channel == notify_title):
			id = notify_id
			msg = '%s<br>%s' %(notify_msg, msg)
		else:
			id = 0
		notify_id = notify.Notify('', id, '', channel, msg, '', {}, 50000)
		notify_title = channel
		notify_msg = msg
		timestamp = now()
	except:
		weechat # force exception if we aren't in weechat
		dbus_lost()


# If you use weechat with screen, dbusnotify will lose dbus when you close your X session and later
# reattach, this is because the local dbus daemon was restarted and it has now a different address,
# which is exported in the DBUS_SESSION_BUS_ADDRESS env var, this is a hack for allow me to update
# that address, this is ugly, but I don't know enough python-dbus-fu for write a better way
#################################################
### Ugly hack for get dbus back if we lost it ###

def dbus_lost():
	global hook_dbus_update, notify_hooks
	if notify_hooks:
		error('Looks like we lost the dbus daemon, disabling notices...')
		error('See /help dbus_update_address for update dbus address.')
		hook_dbus_update = weechat.hook_command('dbus_update_address',
				'Temporal command for update dbus address', '',
				'First find the address of you dbus daemon, "echo $DBUS_SESSION_BUS_ADDRESS" in a'
				' new shell should be enough.\n'
				'The pass it as an argument.\n\n'
				'Example: /dbus_update_address '
				'unix:abstract=/tmp/dbus-kVLRzw8Bke,guid=6aeebd17c1264df1f21377314a932099',
				'', 'cmd_dbus_update', '')
		disable()

dbus_address = ''
def dbus_notify_process(channel, msg):
	global dbus_address
	assert dbus_address
	weechat.hook_process("export DBUS_SESSION_BUS_ADDRESS=%(dbus_address)s; python -c \""
			"import sys\n"
			"sys.path.append('/home/m4v/dev/weechat/scripts-git/python')\n"
			"import dbusnotify\n"
			"dbusnotify.dbus_notify('%(channel)s', '%(msg)s')\"" \
					%{'dbus_address':dbus_address, 'channel':channel, 'msg':msg},
			10000, 'dbus_notify_process_cb', '')

def dbus_notify_process_cb(data, command, rc, stdout, stderr):
	global notify_hooks
	#debug("%s @ stderr: '%s', stdout: '%s'" %(rc, stderr.strip('\n'), stdout.strip('\n')))
	if rc is not '0' and notify_hooks:
		# dbus lost, again ...
		dbus_lost()
	return WEECHAT_RC_OK

def cmd_dbus_update(data, buffer, args):
	global hook_dbus_update
	global dbus_notify, dbus_address
	dbus_address = args
	enable()
	weechat.unhook(hook_dbus_update)
	dbus_notify = dbus_notify_process
	dbus_notify('dbusnotify', 'Address update successful.')
	return WEECHAT_RC_OK

###             End of ugly hack              ###
#################################################

def cmd_test(data, buffer, args):
	dbus_notify('test', 'test')
	return WEECHAT_RC_OK

notify_hooks = []
def enable():
	global notify_hooks
	if notify_hooks:
		disable()
	notify_hooks = [
			weechat.hook_print('', '', '', 1, 'notify_hilight', ''),
			weechat.hook_signal('weechat_pv', 'notify_priv', ''),
			]
	debug(notify_hooks)

def disable():
	global notify_hooks
	for hook in notify_hooks:
		weechat.unhook(hook)
	notify_hooks = []

if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
		'', ''):
	for opt, val in settings:
		if not weechat.config_is_set_plugin(opt):
			weechat.config_set_plugin(opt, val)
	weechat.hook_command('dbus_test', 'desc', 'help', 'help', '', 'cmd_test', '')
	enable()

# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
