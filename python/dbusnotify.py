# -*- coding: utf-8 -*-
SCRIPT_NAME    = "dbusnotify"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = ""
#SCRIPT_COMMAND = "egrep"

import weechat
from weechat import WEECHAT_RC_OK
import dbus#, fnmatch

def debug(s, prefix='debug'):
	"""Debug msg"""
	weechat.prnt('', '%s: %s'  %(prefix,s))

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

def notify_hilight(data, buffer, time, tags, display, hilight, prefix, msg ):
	#debug(';'.join((data, buffer, time, tags, display, hilight, prefix, msg)))
	if hilight is '1':
		channel = weechat.buffer_get_string(buffer, 'short_name')
		if not channel:
			channel = weechat.buffer_get_string(buffer, 'name')
		#FIXME replace < > by their html codes
		dbus_notify(channel, '<b>%s</b>:%s' %(prefix, msg))
	return WEECHAT_RC_OK

def notify_priv(data, signal, message):
	#debug(','.join((data, signal, message)))
	ignore = get_config_ignores('ignore_private')
	for pattern in ignore:
		if message.startswith(pattern):
			return WEECHAT_RC_OK
	dbus_notify(*message.split(' ', 1))
	return WEECHAT_RC_OK

def dbus_notify(channel, msg):
	try:
		bus = dbus.SessionBus()
		notify_object = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
		notify = dbus.Interface(notify_object, 'org.freedesktop.Notifications')
		notificar = notify.Notify('', 0, '', channel, msg, '', {}, 50000)
	except:
		weechat.prnt('', '%sLooks like we lost the dbus daemon, disabling notices...'\
				%weechat.prefix('error'))
		def dbus_disabled(*args):
			pass
		global dbus_notify
		dbus_notify = dbus_disabled

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
	for opt, val in settings:
		if not weechat.config_is_set_plugin(opt):
			weechat.config_set_plugin(opt, val)
	weechat.hook_print('', '', '', 1, 'notify_hilight', '')
	weechat.hook_signal('weechat_pv', 'notify_priv', '')

# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
