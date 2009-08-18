# -*- coding: utf-8 -*-

SCRIPT_NAME    = "country"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"

try:
	import weechat
	from weechat import WEECHAT_RC_OK
	import_ok = True
except ImportError:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://weechat.flashtux.org/"
	import_ok = False

import os

database_url = 'http://geolite.maxmind.com/download/geoip/database/GeoIPCountryCSV.zip'
database_file = 'GeoIPCountryWhois.csv'

def say(s, prefix=SCRIPT_NAME, buffer=''):
	weechat.prnt(buffer, '%s: %s' %(prefix, s))

def error(s, prefix=SCRIPT_NAME, buffer=''):
	weechat.prnt(buffer, '%s%s: %s' %(weechat.prefix('error'), prefix, s))

def debug(s, prefix='debug', buffer=''):
	weechat.prnt(buffer, '%s: %s' %(prefix, s))

def whois(s, nick, buffer=''):
	weechat.prnt(buffer, '%s%s[%s%s%s] %s%s' %(
			weechat.prefix('network'),
			weechat.color('chat_delimiters'),
			weechat.color('chat_nick'),
			nick,
			weechat.color('chat_delimiters'),
			weechat.color('chat'),
			s))

def get_script_dir():
	script_dir = weechat.info_get('weechat_dir', '')
	script_dir = os.path.join(script_dir, 'country')
	if not os.path.isdir(script_dir):
		os.makedirs(script_dir)
	return script_dir

timeout = 1000*60
hook_download = ''
def update_database():
	global hook_download
	if hook_download:
		weechat.unhook(hook_download)
		hook_download = ''
	script_dir = get_script_dir()
	say("Downloading IP database...")
	hook_download = weechat.hook_process(
			"python -c \"\n"
			"import urllib2, zipfile, os\n"
			"try:\n"
			"	temp = os.path.join('%(script_dir)s', 'temp.zip')\n"
			"	zip = urllib2.urlopen('%(url)s')\n"
			"	fd = open(temp, 'w')\n"
			"	fd.write(zip.read())\n"
			"	fd.close()\n"
			"	zip = zipfile.ZipFile(temp)\n"
			"	zip.extractall(path='%(script_dir)s')\n"
			"	os.remove(temp)\n"
			"except Exception, e:\n"
			"	print e\n\"" %{'url':database_url, 'script_dir':script_dir},
			timeout, 'update_database_cb', '')

hook_stdout = ''
def update_database_cb(data, command, rc, stdout, stderr):
	global hook_download, hook_stdout
	if stderr:
		hook_stdout += stderr
	if stdout:
		hook_stdout += stdout
	if int(rc) >= 0:
		if hook_stdout:
			error("There was an error...")
			error(hook_stdout)
			hook_stdout = ''
		else:
			say("Success.")
		hook_download = ''
	return weechat.WEECHAT_RC_OK

def is_ip(ip):
	if ip.count('.') == 3:
		L = ip.split('.')
		try:
			for n in L:
				n = int(n)
				if not (n > 0 and n < 255):
					return False
		except:
			return False
		return True
	else:
		return False

def is_host(host):
	if '/' in host:
		return False
	elif '.' in host:
		return True
	return False

def is_nick(nick, buffer):
	pass

def get_ip(host):
	import socket
	return socket.gethostbyname(host)

def sum_ip(ip):
	L = map(int, ip.split('.'))
	return L[0]*16777216 + L[1]*65536 + L[2]*256 + L[3]

def search_in_database(n):
	import csv
	global ip_database
	try:
		fd = open(ip_database)
		reader = csv.reader(fd)
		max = os.path.getsize(ip_database)
		last_high = last_low = min = 0
		while True:
			mid = (max + min)/2
			fd.seek(mid)
			fd.readline()
			_, _, low, high, code, country = reader.next()
			if low == last_low and high == last_high:
				break
			if n < long(low):
				max = mid
			elif n > long(high):
				min = mid
			elif n > long(low) and n < long(high):
				return (code, country)
			else:
				break
			last_low, last_high = low, high
	except IOError, e:
		error(e)
	except StopIteration:
		pass
	return (None, None)

def get_country(host):
	if is_ip(host):
		ip = host
	else:
		if is_host(host):
			ip = get_ip(host)
		else:
			ip = None
	if ip:
		return search_in_database(sum_ip(ip))
	else:
		return (None, None)

### cmd
def cmd_country(data, buffer, args):
	if not args:
		return WEECHAT_RC_OK
	if ' ' in args:
		host = args[args.rfind(' '):]
	else:
		host = args
	code, country = get_country(host)
	whois('%s (%s)' %(country, code), host, buffer)
	return WEECHAT_RC_OK

### signal callback
def whois_cb(data, signal, signal_data):
	nick, user, host = signal_data.split()[3:6]
	server = signal[:signal.find(',')]
	#debug('%s | %s | %s' %(data, signal, signal_data))
	code, country = get_country(host)
	if code:
		buffer = weechat.buffer_search('irc', 'server.%s' %server)
		whois('%s (%s)' %(country, code), nick, buffer)
	return WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, '', '', '', '', ''):
	ip_database = os.path.join(get_script_dir(), database_file)
	if not os.path.isfile(ip_database):
		say("IP database not found.")
		update_database()
	else:
		say("IP database found.")
	weechat.hook_signal('*,irc_in2_311', 'whois_cb', '')
	weechat.hook_command('country', '', "nick|host", "", '', 'cmd_country', '')

# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
