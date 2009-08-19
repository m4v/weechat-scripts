# -*- coding: utf-8 -*-

SCRIPT_NAME    = "country"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = ""
SCRIPT_COMMAND = "country"

try:
	import weechat
	from weechat import WEECHAT_RC_OK
	import_ok = True
except ImportError:
	print "This script must be run under WeeChat."
	print "Get WeeChat now at: http://weechat.flashtux.org/"
	import_ok = False

import os

### ip database
database_url = 'http://geolite.maxmind.com/download/geoip/database/GeoIPCountryCSV.zip'
database_file = 'GeoIPCountryWhois.csv'

### messages
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

### functions
def get_script_dir():
	script_dir = weechat.info_get('weechat_dir', '')
	script_dir = os.path.join(script_dir, 'country')
	if not os.path.isdir(script_dir):
		os.makedirs(script_dir)
	return script_dir

ip_database = ''
def check_database():
	global ip_database
	ip_database = os.path.join(get_script_dir(), database_file)
	return os.path.isfile(ip_database)

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
			"from sys import stderr\n"
			"try:\n"
			"	temp = os.path.join('%(script_dir)s', 'temp.zip')\n"
			"	zip = urllib2.urlopen('%(url)s', timeout=1)\n"
			"	fd = open(temp, 'w')\n"
			"	fd.write(zip.read())\n"
			"	fd.close()\n"
			"	print 'Download complete, uncompressing...'\n"
			"	zip = zipfile.ZipFile(temp)\n"
			"	zip.extractall(path='%(script_dir)s')\n"
			"	os.remove(temp)\n"
			"except Exception, e:\n"
			"	print >>stderr, e\n\"" %{'url':database_url, 'script_dir':script_dir},
			timeout, 'update_database_cb', '')

process_stderr = ''
def update_database_cb(data, command, rc, stdout, stderr):
	global hook_download, process_stderr
	#debug("%s @ stderr: '%s', stdout: '%s'" %(rc, stderr.strip('\n'), stdout.strip('\n')))
	if stdout:
		say(stdout)
	if stderr:
		process_stderr += stderr
	if int(rc) >= 0:
		if process_stderr:
			error(process_stderr)
			process_stderr = ''
		else:
			say('Success.')
		hook_download = ''
	return WEECHAT_RC_OK

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

def get_host_by_nick(nick, buffer):
	channel = weechat.buffer_get_string(buffer, 'localvar_channel')
	server = weechat.buffer_get_string(buffer, 'localvar_server')
	if channel and server:
		infolist = weechat.infolist_get('irc_nick', '', '%s,%s' %(server, channel))
		if infolist:
			while weechat.infolist_next(infolist):
				name = weechat.infolist_string(infolist, 'name')
				if nick == name:
					host = weechat.infolist_string(infolist, 'host')
					return host[host.find('@')+1:] # strip everything in front of '@'
			weechat.infolist_free(infolist)
	return ''

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
			fd.readline() # move cursor to next line
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
		# picks the first argument only
		args = args[:args.find(' ')]
	if args == 'update':
		update_database()
		return WEECHAT_RC_OK
	#debug('args: %s' %args)
	try:
		if not is_host(args):
			# maybe a nick
			host = get_host_by_nick(args, buffer)
			#debug('host: %s' %host)
		else:
			host = args
		code, country = get_country(host)
		whois('%s (%s)' %(country, code), args, buffer)
	except IOError:
		error("IP database not found. You must download a database with '/country update' before "
				"using this script.", buffer=buffer)
	return WEECHAT_RC_OK

### signal callback
def whois_cb(data, signal, signal_data):
	nick, user, host = signal_data.split()[3:6]
	server = signal[:signal.find(',')]
	#debug('%s | %s | %s' %(data, signal, signal_data))
	try:
		code, country = get_country(host)
		if code:
			buffer = weechat.buffer_search('irc', 'server.%s' %server)
			whois('%s (%s)' %(country, code), nick, buffer)
	except IOError:
		pass # no database installed
	return WEECHAT_RC_OK

### main
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
		SCRIPT_DESC, '', ''):
	weechat.hook_signal('*,irc_in2_311', 'whois_cb', '')
	weechat.hook_command('country', '', "nick|ip|uri", "", 'update||%(nick)', 'cmd_country', '')
	if not check_database():
		say("IP database not found. You must download a database with '/country update' before "
				"using this script.")
	else:
		say("IP database found.")

# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
