# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2010 by Elián Hanisch <lambdae2@gmail.com>
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
# Search in Weechat buffers and logs (for Weechat 0.3.*)
#
#   Inspired by xt's grep.py
#   Originally I just wanted to add some fixes in grep.py, but then
#   I got carried away and rewrote everything, so new script.
#
#   Commands:
#   * /grep
#     Search in logs or buffers, see /help grep
#   * /logs:
#     Lists logs in ~/.weechat/logs, see /help logs
#
#   Settings:
#   * plugins.var.python.grep.clear_buffer:
#     Clear the results buffer before each search. Valid values: on, off
#
#   * plugins.var.python.grep.go_to_buffer:
#     Automatically go to grep buffer when search is over. Valid values: on, off
#
#   * plugins.var.python.grep.log_filter:
#     Coma separated list of patterns that grep will use for exclude logs, e.g.
#     if you use '*server/*' any log in the 'server' folder will be excluded
#     when using the command '/grep log'
#
#   * plugins.var.python.grep.show_summary:
#     Shows summary for each log. Valid values: on, off
#
#   * plugins.var.python.grep.max_lines:
#     Grep will only print the last matched lines that don't surpass the value defined here.
#
#   * plugins.var.python.grep.size_limit:
#     Size limit in KiB, is used for decide whenever grepping should run in background or not. If
#     the logs to grep have a total size bigger than this value then grep run as a new process.
#     It can be used for force or disable background process, using '0' forces to always grep in
#     background, while using '' (empty string) will disable it.
#
#   * plugins.var.python.grep.default_tail_head:
#     Config option for define default number of lines returned when using --head or --tail options.
#     Can be overriden in the command with --number option.
#
#
#   TODO:
#   * try to figure out why hook_process chokes in long outputs (using a tempfile as a
#   workaround now)
#   * predefined regexp templates for common searches, like urls
#   * possibly add option for defining time intervals
#
#
#   History:
#   2010-01-17
#   version 0.6.1: fixed bug when grepping in grep's buffer
#
#   2010-01-14
#   version 0.6.0: implemented grep in background
#   * improved context lines presentation.
#   * grepping for big (or many) log files runs in a weechat_process.
#   * added /grep stop.
#   * added 'size_limit' option
#   * fixed a infolist leak when grepping buffers
#   * added 'default_tail_head' option
#   * results are sort by line count
#   * don't die if log is corrupted (has NULL chars in it)
#   * changed presentation of /logs
#   * log path completion doesn't suck anymore
#   * removed all tabs, because I learned how to configure Vim so that spaces aren't annoying
#   anymore. This was the script's original policy.
#
#   2010-01-05
#   version 0.5.5: rename script to 'grep.py' (FlashCode <flashcode@flashtux.org>).
#
#   2010-01-04
#   version 0.5.4.1: fix index error when using --after/before-context options.
#
#   2010-01-03
#   version 0.5.4: new features
#   * added --after-context and --before-context options.
#   * added --context as a shortcut for using both -A -B options.
#
#   2009-11-06
#   version 0.5.3: improvements for long grep output
#   * grep buffer input accepts the same flags as /grep for repeat a search with different
#     options.
#   * tweaks in grep's output.
#   * max_lines option added for limit grep's output.
#   * code in update_buffer() optimized.
#   * time stats in buffer title.
#   * added go_to_buffer config option.
#   * added --buffer for search only in buffers.
#   * refactoring.
#
#   2009-10-12, omero
#   version 0.5.2: made it python-2.4.x compliant
#
#   2009-08-17
#   version 0.5.1: some refactoring, show_summary option added.
#
#   2009-08-13
#   version 0.5: rewritten from xt's grep.py
#   * fixed searching in non weechat logs, for cases like, if you're
#     switching from irssi and rename and copy your irssi logs to %h/logs
#   * fixed "timestamp rainbow" when you /grep in grep's buffer
#   * allow to search in other buffers other than current or in logs
#     of currently closed buffers with cmd 'buffer'
#   * allow to search in any log file in %h/logs with cmd 'log'
#   * added --count for return the number of matched lines
#   * added --matchcase for case sensible search
#   * added --hilight for color matches
#   * added --head and --tail options, and --number
#   * added command /logs for list files in %h/logs
#   * added config option for clear the buffer before a search
#   * added config option for filter logs we don't want to grep
#   * added the posibility to repeat last search with another regexp by writing
#     it in grep's buffer
#   * changed spaces for tabs in the code, which is my preference
#
###

from os import path
from os import stat
import getopt, time, re

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except ImportError:
    import_ok = False

SCRIPT_NAME    = "grep"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.6.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Search in buffers and logs"
SCRIPT_COMMAND = "grep"

### Default Settings ###
settings = {
'clear_buffer'      : 'off',
'log_filter'        : '',
'go_to_buffer'      : 'on',
'max_lines'         : '4000',
'show_summary'      : 'on',
'size_limit'        : '2048',
'default_tail_head' : '10',
}

### Class definitions ###
class linesDict(dict):
    """
    Class for handling matched lines in more than one buffer.
    linesDict[buffer_name] = matched_lines_list
    """
    def __setitem__(self, key, value):
        assert isinstance(value, list)
        if key not in self:
            dict.__setitem__(self, key, value)
        else:
            dict.__getitem__(self, key).extend(value)

    def get_matches_count(self):
        """Return the sum of total matches stored."""
        if dict.__len__(self):
            return sum(map(lambda L: L.matches_count, self.itervalues()))
        else:
            return 0

    def __len__(self):
        """Return the sum of total lines stored."""
        if dict.__len__(self):
            return sum(map(len, self.itervalues()))
        else:
            return 0

    def __str__(self):
        """Returns buffer count or buffer name if there's just one stored."""
        n = len(self.keys())
        if n == 1:
            return self.keys()[0]
        elif n > 1:
            return '%s logs' %n
        else:
            return ''

    def items(self):
        """Returns a list of items sorted by line count."""
        items = dict.items(self)
        items.sort(key=lambda i: len(i[1]))
        return items

    def items_count(self):
        """Returns a list of items sorted by match count."""
        items = dict.items(self)
        items.sort(key=lambda i: i[1].matches_count)
        return items

    def strip_separator(self):
        for L in self.itervalues():
            L.strip_separator()

    def get_last_lines(self, n):
        total_lines = len(self)
        #debug('total: %s n: %s' %(total_lines, n))
        if n >= total_lines:
            # nothing to do
            return
        for k, v in reversed(self.items()):
            l = len(v)
            if n > 0:
                if l > n:
                    del v[:l-n]
                    v.stripped_lines = l-n
                n -= l
            else:
                del v[:]
                v.stripped_lines = l

class linesList(list):
    """Class for list of matches, since sometimes I need to add lines that aren't matches, I need an
    independent counter."""
    _sep = '...'
    def __init__(self, *args):
        list.__init__(self, *args)
        self.matches_count = 0
        self.stripped_lines = 0

    def append_separator(self):
        """adds a separator into the list, makes sure it doen't add two together."""
        s = self._sep
        if (self and self[-1] != s) or not self:
            self.append(s)

    def count_match(self):
        self.matches_count += 1

    def strip_separator(self):
        """removes separators if there are first or/and last in the list."""
        if self:
            s = self._sep
            if self[0] == s:
                del self[0]
            if self[-1] == s:
                del self[-1]

### Misc functions ###
now = time.time
get_size = lambda x: stat(x).st_size

sizeDict = {0:'b', 1:'KiB', 2:'MiB', 3:'GiB', 4:'TiB'}
def human_readable_size(size):
    power = 0
    while size > 1024:
        power += 1
        size /= 1024.0
    return '%.2f %s' %(size, sizeDict.get(power, ''))

def color_nick(nick):
    """Returns coloured nick, with coloured mode if any."""
    if not nick: return ''
    wcolor = weechat.color
    config_string = lambda s : weechat.config_string(weechat.config_get(s))
    config_int = lambda s : weechat.config_integer(weechat.config_get(s))
    # prefix and suffix
    prefix = config_string('irc.look.nick_prefix')
    suffix = config_string('irc.look.nick_suffix')
    prefix_c = suffix_c = wcolor(config_string('weechat.color.chat_delimiters'))
    if nick[0] == prefix:
        nick = nick[1:]
    else:
        prefix = prefix_c = ''
    if nick[-1] == suffix:
        nick = nick[:-1]
        suffix = wcolor(color_delimiter) + suffix
    else:
        suffix = suffix_c = ''
    # nick mode
    modes = '@!+%'
    if nick[0] in modes:
        mode, nick = nick[0], nick[1:]
        mode_color = wcolor(config_string('weechat.color.nicklist_prefix%d' \
            %(modes.find(mode) + 1)))
    else:
        mode = mode_color = ''
    color_nicks_number = config_int('weechat.look.color_nicks_number')
    idx = (sum(map(ord, nick))%color_nicks_number) + 1
    nick_color = wcolor(config_string('weechat.color.chat_nick_color%02d' %idx))
    return ''.join((prefix_c, prefix, mode_color, mode, nick_color, nick, suffix_c, suffix))

### Config and value validation ###
boolDict = {'on':True, 'off':False}
def get_config_boolean(config):
    value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_int(config, allow_empty_string=False):
    value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        if value == '' and allow_empty_string:
            return value
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)

def get_config_log_filter():
    filter = weechat.config_get_plugin('log_filter')
    if filter:
        return filter.split(',')
    else:
        return []

def get_home():
    home = weechat.config_string(weechat.config_get('logger.file.path'))
    return home.replace('%h', weechat.info_get('weechat_dir', ''))

def strip_home(s, dir=''):
    """Strips home dir from the begging of the log path, this makes them sorter."""
    if not dir:
        global home_dir
        dir = home_dir
    l = len(dir)
    if s[:l] == dir:
        return s[l:]
    return s

### Messages ###
def debug(s, prefix='', buffer=None):
    """Debug msg"""
    if not weechat.config_get_plugin('debug'): return
    if buffer is None:
        buffer_name = 'DEBUG_' + SCRIPT_NAME
        buffer = weechat.buffer_search('python', buffer_name)
        if not buffer:
            buffer = weechat.buffer_new(buffer_name, '', '', '', '')
            weechat.buffer_set(buffer, 'nicklist', '0')
            weechat.buffer_set(buffer, 'time_for_each_line', '0')
            weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

def error(s, prefix=None, buffer='', trace=''):
    """Error msg"""
    prefix = prefix or script_nick
    weechat.prnt(buffer, '%s%s %s' %(weechat.prefix('error'), prefix, s))
    if weechat.config_get_plugin('debug'):
        if not trace:
            import traceback
            if traceback.sys.exc_type:
                trace = traceback.format_exc()
        not trace or weechat.prnt('', trace)

def say(s, prefix=None, buffer=''):
    """normal msg"""
    prefix = prefix or script_nick
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

### Log files and buffers ###
cache_dir = {} # note: don't remove, needed for completion if the script was loaded recently
def dir_list(dir, filter_list=(), filter_excludes=True, include_dir=False):
    """Returns a list of files in 'dir' and its subdirs."""
    global cache_dir
    from os import walk
    from fnmatch import fnmatch
    #debug('dir_list: listing in %s' %dir)
    key = (dir, include_dir)
    try:
        return cache_dir[key]
    except KeyError:
        pass
    
    filter_list = filter_list or get_config_log_filter()
    dir_len = len(dir)
    if filter_list:
        def filter(file):
            file = file[dir_len:] # pattern shouldn't match home dir
            for pattern in filter_list:
                if fnmatch(file, pattern):
                    return filter_excludes
            return not filter_excludes
    else:
        filter = lambda f : not filter_excludes

    file_list = []
    extend = file_list.extend
    join = path.join
    def walk_path():
        for basedir, subdirs, files in walk(dir):
            if include_dir: 
                subdirs = map(lambda s : join(s, ''), subdirs)
                files.extend(subdirs)
            files_path = map(lambda f : join(basedir, f), files)
            files_path = [ file for file in files_path if not filter(file) ]
            extend(files_path)

    walk_path()
    cache_dir[key] = file_list
    #debug('dir_list: got %s' %str(file_list))
    return file_list

def get_file_by_pattern(pattern, all=False):
    """Returns the first log whose path matches 'pattern',
    if all is True returns all logs that matches."""
    if not pattern: return []
    #debug('get_file_by_filename: searching for %s.' %pattern)
    # do envvar expandsion and check file
    file = path.expanduser(pattern)
    file = path.expandvars(file)
    if path.isfile(file):
        return [file]
    # lets see if there's a matching log
    global home_dir
    file = path.join(home_dir, pattern)
    if path.isfile(file):
        return [file]
    else:
        import fnmatch
        file = []
        file_list = dir_list(home_dir)
        n = len(home_dir)
        for log in file_list:
            basename = log[n:]
            if fnmatch.fnmatch(basename, pattern):
                file.append(log)
                if not all: break
        #debug('get_file_by_filename: got %s.' %file)
        return file

def get_file_by_buffer(buffer):
    """Given buffer pointer, finds log's path or returns None."""
    #debug('get_file_by_buffer: searching for %s' %buffer)
    infolist = weechat.infolist_get('logger_buffer', '', '')
    if not infolist: return
    try:
        while weechat.infolist_next(infolist):
            pointer = weechat.infolist_pointer(infolist, 'buffer')
            if pointer == buffer:
                file = weechat.infolist_string(infolist, 'log_filename')
                if weechat.infolist_integer(infolist, 'log_enabled'):
                    #debug('get_file_by_buffer: got %s' %file)
                    return file
                #else:
                #    debug('get_file_by_buffer: got %s but log not enabled' %file)
    finally:
        #debug('infolist gets freed')
        weechat.infolist_free(infolist)

def get_file_by_name(buffer_name):
    """Given a buffer name, returns its log path or None. buffer_name should be in 'server.#channel'
    or '#channel' format."""
    #debug('get_file_by_name: searching for %s' %buffer_name)
    # common mask options
    config_masks = ('logger.mask.irc', 'logger.file.mask')
    # since there's no buffer pointer, we try to replace some local vars in mask, like $channel and
    # $server, then replace the local vars left with '*', and use it as a mask for get the path with
    # get_file_by_pattern
    for config in config_masks:
        mask = weechat.config_string(weechat.config_get(config))
        #debug('get_file_by_name: mask: %s' %mask)
        if '$name' in mask:
            mask = mask.replace('$name', buffer_name)
        elif '$channel' in mask or '$server' in mask:
            if '.' in buffer_name and \
                    '#' not in buffer_name[:buffer_name.find('.')]: # the dot isn't part of the channel name
                #    ^ I'm asuming channel starts with #, i'm lazy.
                server, channel = buffer_name.split('.', 1)
            else:
                server, channel = '*', buffer_name
            if '$channel' in mask:
                mask = mask.replace('$channel', channel)
            if '$server' in mask:
                mask = mask.replace('$server', server)
        # change the unreplaced vars by '*'
        if '$' in mask:
            chars = 'abcdefghijklmnopqrstuvwxyz_'
            masks = mask.split('$')
            masks = map(lambda s: s.lstrip(chars), masks)
            mask = '*'.join(masks)
            if mask[0] != '*':
                mask = '*' + mask
        #debug('get_file_by_name: using mask %s' %mask)
        file = get_file_by_pattern(mask)
        #debug('get_file_by_name: got file %s' %file)
        if file:
            return file
    return None

def get_buffer_by_name(buffer_name):
    """Given a buffer name returns its buffer pointer or None."""
    #debug('get_buffer_by_name: searching for %s' %buffer_name)
    pointer = weechat.buffer_search('', buffer_name)
    if not pointer:
        try:
            infolist = weechat.infolist_get('buffer', '', '')
            while weechat.infolist_next(infolist):
                short_name = weechat.infolist_string(infolist, 'short_name')
                name = weechat.infolist_string(infolist, 'name')
                if buffer_name in (short_name, name):
                    #debug('get_buffer_by_name: found %s' %name)
                    pointer = weechat.buffer_search('', name)
                    return pointer
        finally:
            weechat.infolist_free(infolist)
    #debug('get_buffer_by_name: got %s' %pointer)
    return pointer

def get_all_buffers():
    """Returns list with pointers of all open buffers."""
    buffers = []
    infolist = weechat.infolist_get('buffer', '', '')
    while weechat.infolist_next(infolist):
        buffers.append(weechat.infolist_pointer(infolist, 'pointer'))
    weechat.infolist_free(infolist)
    grep_buffer = weechat.buffer_search('python', SCRIPT_NAME)
    if grep_buffer and grep_buffer in buffers:
        # remove it from list
        del buffers[buffers.index(grep_buffer)]
    return buffers

### Grep ###
def make_regexp(pattern, matchcase=False):
    """Returns a compiled regexp."""
    if pattern in ('.', '.*', '.?', '.+'):
        # because I don't need to use a regexp if we're going to match all lines
        return None
    try:
        import re
        if not matchcase:
            regexp = re.compile(pattern, re.IGNORECASE)
        else:
            regexp = re.compile(pattern)
    except Exception, e:
        raise Exception, 'Bad pattern, %s' %e
    return regexp

def check_string(s, regexp, hilight='', exact=False):
    """Checks 's' with a regexp and returns it if is a match."""
    if not regexp:
        return s
    elif exact:
        matchlist = regexp.findall(s)
        if matchlist:
            return ' '.join(matchlist)
    elif hilight:
        matchlist = regexp.findall(s)
        if matchlist:
            matchlist = list(set(matchlist)) # remove duplicates if any
            # apply hilight
            color_hilight, color_reset = hilight.split(',', 1)
            for m in matchlist:
                s = s.replace(m, '%s%s%s' %(color_hilight, m, color_reset))
            return s
    # no need for findall() here
    elif regexp.search(s):
        return s

def grep_file(file, head, tail, after_context, before_context, count, regexp, hilight, exact):
    """Return a list of lines that match 'regexp' in 'file', if no regexp returns all lines."""
    if count:
        tail = head = after_context = before_context = exact = False
        hilight = ''
    elif exact:
        before_context = after_context = False
    #debug(' '.join(map(str, (file, head, tail, after_context, before_context))))

    lines = linesList()
    # define these locally as it makes the loop run slightly faster
    append = lines.append
    count_match = lines.count_match
    separator = lines.append_separator
    check = lambda s: check_string(s, regexp, hilight, exact)
    
    file_object = open(file, 'r')
    if tail or before_context:
        # for these options, I need to seek in the file, but is slower and uses a good deal of
        # memory if the log is too big, so we do this *only* for these options.
        file_lines = file_object.readlines()

        if before_context:
            before_context_range = range(1, before_context + 1)
            before_context_range.reverse()

        if tail:
            # instead of searching in the whole file and later pick the last few lines, we
            # reverse the log, search until count reached and reverse it again, that way is a lot
            # faster
            file_lines.reverse()
        limit = tail or head

        line_idx = 0
        while line_idx < len(file_lines):
            line = file_lines[line_idx]
            line = check(line)
            if line:
                if before_context:
                    separator()
                    trimmed = False
                    for id in before_context_range:
                        try:
                            context_line = file_lines[line_idx - id]
                            if check(context_line):
                                # match in before context, that means we appended these same lines in a
                                # previous match, so we delete them merging both paragraphs
                                if not trimmed:
                                    del lines[id - before_context - 1:]
                                    trimmed = True
                            else:
                                append(context_line)
                        except IndexError:
                            pass
                append(line)
                count_match()
                if after_context:
                    id, offset = 0, 0
                    while id < after_context + offset:
                        id += 1
                        try:
                            context_line = file_lines[line_idx + id]
                            _context_line = check(context_line)
                            if _context_line:
                                offset = id
                                context_line = _context_line # so match is hilighted with --hilight
                                count_match()
                            append(context_line)
                        except IndexError:
                            pass
                    separator()
                    line_idx += id
                if limit and lines.matches_count >= limit:
                    break
            line_idx += 1

        if tail:
            lines.reverse()
    else:
        # do a normal grep
        limit = head

        for line in file_object:
            line = check(line)
            if line:
                count or append(line)
                count_match()
                if after_context:
                    id, offset = 0, 0
                    while id < after_context + offset:
                        id += 1
                        try:
                            context_line = file_object.next()
                            _context_line = check(context_line)
                            if _context_line:
                                offset = id
                                context_line = _context_line
                                count_match()
                            count or append(context_line)
                        except StopIteration:
                            pass
                    separator()
                if limit and lines.matches_count >= limit:
                    break

    file_object.close()
    return lines

def grep_buffer(buffer, head, tail, after_context, before_context, count, regexp, hilight, exact):
    """Return a list of lines that match 'regexp' in 'buffer', if no regexp returns all lines."""
    lines = linesList()
    if count:
        tail = head = after_context = before_context = exact = False
        hilight = ''
    elif exact:
        before_context = after_context = False
    #debug(' '.join(map(str, (tail, head, after_context, before_context, count, exact, hilight))))

    # Using /grep in grep's buffer can lead to some funny effects
    # We should take measures if that's the case
    def make_get_line_funcion():
        """Returns a function for get lines from the infolist, depending if the buffer is grep's or
        not."""
        string_remove_color = weechat.string_remove_color
        infolist_string = weechat.infolist_string
        grep_buffer = weechat.buffer_search('python', SCRIPT_NAME)
        if grep_buffer and buffer == grep_buffer:
            def function(infolist):
                prefix = infolist_string(infolist, 'prefix')
                message = infolist_string(infolist, 'message')
                if prefix: # only our messages have prefix, ignore it
                    return None
                return message
        else:
            infolist_time = weechat.infolist_time
            def function(infolist):
                prefix = string_remove_color(infolist_string(infolist, 'prefix'), '')
                message = string_remove_color(infolist_string(infolist, 'message'), '')
                date = infolist_time(infolist, 'date')
                return '%s\t%s\t%s' %(date, prefix, message)
        return function
    get_line = make_get_line_funcion()

    infolist = weechat.infolist_get('buffer_lines', buffer, '')
    if tail:
        # like with grep_file() if we need the last few matching lines, we move the cursor to
        # the end and search backwards
        infolist_next = weechat.infolist_prev
        infolist_prev = weechat.infolist_next
    else:
        infolist_next = weechat.infolist_next
        infolist_prev = weechat.infolist_prev
    limit = head or tail

    # define these locally as it makes the loop run slightly faster
    append = lines.append
    count_match = lines.count_match
    separator = lines.append_separator
    check = lambda s: check_string(s, regexp, hilight, exact)

    if before_context:
        before_context_range = range(1, before_context + 1)
        before_context_range.reverse()

    while infolist_next(infolist):
        line = get_line(infolist)
        if line is None: continue
        line = check(line)
        if line:
            if before_context:
                separator()
                trimmed = False
                for id in before_context_range:
                    if not infolist_prev(infolist):
                        trimmed = True
                for id in before_context_range:
                    context_line = get_line(infolist)
                    if check(context_line):
                        if not trimmed:
                            del lines[id - before_context - 1:]
                            trimmed = True
                    else:
                        append(context_line)
                    infolist_next(infolist)
            count or append(line)
            count_match()
            if after_context:
                id, offset = 0, 0
                while id < after_context + offset:
                    id += 1
                    if infolist_next(infolist):
                        context_line = get_line(infolist)
                        _context_line = check(context_line)
                        if _context_line:
                            context_line = _context_line
                            offset = id
                            count_match()
                        append(context_line)
                    else:
                        # in the main loop infolist_next will start again an cause an infinite loop
                        # this will avoid it
                        infolist_next = lambda x: 0
                separator()
            if limit and lines.matches_count >= limit:
                break
    weechat.infolist_free(infolist)

    if tail:
        lines.reverse()
    return lines

### this is our main grep function
hook_file_grep = None
def show_matching_lines():
    """
    Greps buffers in search_in_buffers or files in search_in_files and updates grep buffer with the
    result.
    """
    global pattern, matchcase, number, count, exact, hilight
    global tail, head, after_context, before_context
    global search_in_files, search_in_buffers, matched_lines, home_dir
    global time_start
    matched_lines = linesDict()
    #debug('buffers:%s \nlogs:%s' %(search_in_buffers, search_in_files))
    time_start = now()

    # buffers
    if search_in_buffers:
        regexp = make_regexp(pattern, matchcase)
        for buffer in search_in_buffers:
            buffer_name = weechat.buffer_get_string(buffer, 'name')
            matched_lines[buffer_name] = grep_buffer(buffer, head, tail, after_context,
                    before_context, count, regexp, hilight, exact)

    # logs
    if search_in_files:
        size_limit = get_config_int('size_limit', allow_empty_string=True)
        background = False
        if size_limit or size_limit == 0:
            size = sum(map(get_size, search_in_files))
            if size > size_limit * 1024:
                background = True
        elif size_limit == '':
            background = False

        if not background:
            # run grep normally
            regexp = make_regexp(pattern, matchcase)
            for log in search_in_files:
                log_name = strip_home(log)
                matched_lines[log_name] = grep_file(log, head, tail, after_context, before_context,
                        count, regexp, hilight, exact)
            buffer_update()
        else:
            # we hook a process so grepping runs in background.
            #debug('on background')
            global hook_file_grep
            timeout = 1000*60*10 # 10 min

            def shell_escapes(s):
                # nicks might have ` characters, must be escaped
                if '`' in s:
                    s = s.replace('`', '\`')
                return "'%s'" %s

            files_string = ', '.join(map(shell_escapes, search_in_files))

            cmd = grep_proccess_cmd %dict(logs=files_string, head=head, pattern=pattern, tail=tail,
                    hilight=hilight, after_context=after_context, before_context=before_context,
                    exact=exact, matchcase=matchcase, home_dir=home_dir, version=SCRIPT_VERSION,
                    home=weechat.info_get('weechat_dir', ''), count=count)

            #debug(cmd)
            hook_file_grep = weechat.hook_process(cmd, timeout, 'grep_file_callback', '')
            global pattern_tmpl
            if hook_file_grep:
                buffer_create("Searching for '%s' in %s worth of data..." %(pattern_tmpl,
                    human_readable_size(size)))
    else:
        buffer_update()

# defined here for commodity
grep_proccess_cmd = """python -c "
import sys, tempfile, cPickle
sys.path.append('%(home)s/python/dev') # add WeeChat script dir so we can import grep
from grep import make_regexp, grep_file, strip_home, SCRIPT_VERSION
logs = (%(logs)s, )
try:
    if '%(version)s' != SCRIPT_VERSION:
        raise Exception, 'Can\\'t spawn new process, script version mismatch'
    regexp = make_regexp('%(pattern)s', %(matchcase)s)
    d = {}
    for log in logs:
        log_name = strip_home(log, '%(home_dir)s')
        lines = grep_file(log, %(head)s, %(tail)s, %(after_context)s, %(before_context)s,
        %(count)s, regexp, '%(hilight)s', %(exact)s)
        d[log_name] = lines
    fd = tempfile.NamedTemporaryFile('wb', delete=False)
    print fd.name
    cPickle.dump(d, fd, -1)
    fd.close()
except Exception, e:
    print >> sys.stderr, e"
"""

grep_stdout = grep_stderr = ''
def grep_file_callback(data, command, rc, stdout, stderr):
    global hook_file_grep, grep_stderr,  grep_stdout
    global matched_lines
    #debug("rc: %s\nstderr: %s\nstdout: %s" %(rc, repr(stderr), repr(stdout)))
    if stdout:
        grep_stdout += stdout
    if stderr:
        grep_stderr += stderr
    if int(rc) >= 0:
  
        def set_buffer_error():
            grep_buffer = buffer_create()
            title = weechat.buffer_get_string(grep_buffer, 'title')
            title = title + ' %serror' %color_title
            weechat.buffer_set(grep_buffer, 'title', title)

        try:
            if grep_stderr:
                error(grep_stderr)
                set_buffer_error()
            elif grep_stdout:
                #debug(grep_stdout)
                file = grep_stdout.strip()
                if file:
                    try:
                        import cPickle, os
                        #debug(file)
                        fd = open(file, 'rb')
                        d = cPickle.load(fd)
                        matched_lines.update(d)
                        fd.close()
                    except Exception, e:
                        error(e)
                        set_buffer_error()
                    else:
                        os.remove(file)
                        buffer_update()
        finally:
            grep_stdout = grep_stderr = ''
            hook_file_grep = None
    return WEECHAT_RC_OK

def get_grep_file_status():
    global search_in_files, matched_lines, time_start
    elapsed = now() - time_start
    if len(search_in_files) == 1:
        log = '%s (%s)' %(strip_home(search_in_files[0]),
                human_readable_size(get_size(search_in_files[0])))
    else:
        size = sum(map(get_size, search_in_files))
        log = '%s log files (%s)' %(len(search_in_files), human_readable_size(size))
    return 'Searching in %s, running for %.4f seconds. Interrupt it with "/grep stop" or "stop"' \
        ' in grep buffer.' %(log, elapsed)

### Grep buffer ###
def buffer_update():
    """Updates our buffer with new lines."""
    global matched_lines, pattern_tmpl, count, hilight
    pattern = pattern_tmpl
    time_grep = now()

    buffer = buffer_create()
    if get_config_boolean('clear_buffer'):
        weechat.buffer_clear(buffer)
    matched_lines.strip_separator() # remove first and last separators of each list
    len_total_lines = len(matched_lines)
    max_lines = get_config_int('max_lines')
    if not count and len_total_lines > max_lines:
        weechat.buffer_clear(buffer)

    def _make_summary(log, lines, note):
        return "%s matches \"%s%s%s\" in %s%s%s%s" \
                %(lines.matches_count, color_summary, pattern, color_info, color_summary, log,
                  color_reset, note)

    if count:
        make_summary = lambda log, lines : _make_summary(log, lines, ' (not shown)')
    else:
        def make_summary(log, lines):
            if lines.stripped_lines:
                if lines:
                    note = ' (last %s lines shown)' %len(lines)
                else:
                    note = ' (not shown)'
            else:
                note = ''
            return _make_summary(log, lines, note)

    global weechat_format
    if hilight:
        # we don't want colors if there's match highlighting
        format_line = lambda s : '%s %s %s' %split_line(s)
    else:
        def format_line(s):
            global nick_dict, weechat_format
            date, nick, msg = split_line(s)
            if weechat_format:
                try:
                    nick = nick_dict[nick]
                except KeyError:
                    # cache nick
                    nick_c = color_nick(nick)
                    nick_dict[nick] = nick_c
                    nick = nick_c
                return '%s%s %s%s %s' %(color_date, date, nick, color_reset, msg)
            else:
                #no formatting
                return msg

    prnt = weechat.prnt
    prnt(buffer, '\n')
    print_line('Search for "%s" in %s%s%s.' %(pattern, color_summary, matched_lines, color_reset),
            buffer)
    # print last <max_lines> lines
    if matched_lines.get_matches_count():
        if count:
            # with count we sort by matches lines instead of just lines.
            matched_lines_items = matched_lines.items_count()
        else:
            matched_lines_items = matched_lines.items()

        matched_lines.get_last_lines(max_lines)
        for log, lines in matched_lines_items:
            if lines.matches_count:
                # matched lines
                if not count:
                    # print lines
                    weechat_format = True
                    for line in lines:
                        #debug(repr(line))
                        if line == linesList._sep:
                            # separator
                            prnt(buffer, context_sep)
                        else:
                            if '\x00' in line:
                                # log was corrupted
                                error("Found garbage in log '%s', maybe it's corrupted" %log,
                                        trace=repr(line))
                                line = line.replace('\x00', '')
                            prnt(buffer, format_line(line))

                # summary
                if count or get_config_boolean('show_summary'):
                    summary = make_summary(log, lines)
                    print_line(summary, buffer)

            # separator
            if not count and lines:
                prnt(buffer, '\n')
    else:
        print_line('No matches found.', buffer)

    # set title
    global time_start
    time_end = now()
    # total time
    time_total = time_end - time_start
    # percent of the total time used for grepping
    time_grep_pct = (time_grep - time_start)/time_total*100
    #debug('time: %.4f seconds (%.2f%%)' %(time_total, time_grep_pct))
    if not count and len_total_lines > max_lines:
        note = ' (last %s lines shown)' %len(matched_lines)
    else:
        note = ''
    title = "Search in %s%s%s | %s matches%s | pattern \"%s%s%s\" | %.4f seconds (%.2f%%)" \
            %(color_title, matched_lines, color_reset, matched_lines.get_matches_count(), note,
              color_title, pattern, color_reset, time_total, time_grep_pct)
    weechat.buffer_set(buffer, 'title', title)

    if get_config_boolean('go_to_buffer'):
        weechat.buffer_set(buffer, 'display', '1')

    # free matched_lines so it can be removed from memory
    del matched_lines
    
def split_line(s):
    """Splits log's line 's' in 3 parts, date, nick and msg."""
    global weechat_format
    if weechat_format and s.count('\t') >= 2:
        date, nick, msg = s.split('\t', 2) # date, nick, message
    else:
        # looks like log isn't in weechat's format
        weechat_format = False # incoming lines won't be formatted
        date, nick, msg = '', '', s
    # remove tabs
    if '\t' in msg:
        msg = msg.replace('\t', '    ')
    return date, nick, msg

def print_line(s, buffer=None, display=False):
    """Prints 's' in script's buffer as 'script_nick'. For displaying search summaries."""
    if buffer is None:
        buffer = buffer_create()
    say('%s%s' %(color_info, s), buffer=buffer)
    if display and get_config_boolean('go_to_buffer'):
        weechat.buffer_set(buffer, 'display', '1')

def buffer_create(title=None):
    """Returns our buffer pointer, creates and cleans the buffer if needed."""
    buffer = weechat.buffer_search('python', SCRIPT_NAME)
    if not buffer:
        buffer = weechat.buffer_new(SCRIPT_NAME, 'buffer_input', '', '', '')
        weechat.buffer_set(buffer, 'time_for_each_line', '0')
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'title', title or 'grep output buffer')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
    elif title:
        weechat.buffer_set(buffer, 'title', title)
    return buffer

def buffer_input(data, buffer, input_data):
    """Repeats last search with 'input_data' as regexp."""
    try:
        cmd_grep_stop(buffer, input_data)
    except:
        return WEECHAT_RC_OK

    global search_in_buffers, search_in_files
    global pattern
    try:
        if pattern and (search_in_files or search_in_buffers):
            # check if the buffer pointers are still valid
            for pointer in search_in_buffers:
                infolist = weechat.infolist_get('buffer', pointer, '')
                if not infolist:
                    del search_in_buffers[search_in_buffers.index(pointer)]
                weechat.infolist_free(infolist)
            try:
                cmd_grep_parsing(input_data)
            except Exception, e:
                error('Argument error, %s' %e, buffer=buffer)
                return WEECHAT_RC_OK
            try:
                show_matching_lines()
            except Exception, e:
                error(e)
    except NameError:
        error("There isn't any previous search to repeat.", buffer=buffer)
    return WEECHAT_RC_OK

### Commands ###
def cmd_init():
    """Resets global vars."""
    global home_dir, cache_dir, nick_dict
    global pattern_tmpl, pattern, matchcase, number, count, exact, hilight
    global tail, head, after_context, before_context
    hilight = ''
    head = tail = after_context = before_context = False
    matchcase = count = exact = False
    pattern_tmpl = pattern = number = None
    home_dir = get_home()
    cache_dir = {} # for avoid walking the dir tree more than once per command
    nick_dict = {} # nick cache for don't calculate nick color every time

def cmd_grep_parsing(args, buffer=''):
    """Parses args for /grep and grep input buffer."""
    global pattern_tmpl, pattern, matchcase, number, count, exact, hilight
    global tail, head, after_context, before_context
    global log_name, buffer_name, only_buffers, all
    opts, args = getopt.gnu_getopt(args.split(), 'cmHeahtin:bA:B:C:', ['count', 'matchcase', 'hilight',
        'exact', 'all', 'head', 'tail', 'number=', 'buffer', 'after-context=', 'before-context=',
        'context='])
    debug(opts, 'opts: '); debug(args, 'args: ')
    if len(args) >= 2:
        if args[0] == 'log':
            del args[0]
            log_name = args.pop(0)
        elif args[0] == 'buffer':
            del args[0]
            buffer_name = args.pop(0)
    
    def tmplReplacer(match):
        """This function will replace templates with regexps"""
        s = match.groups()[0]
        debug(s)
        tmpl_args = s.split()
        tmpl_key = tmpl_args[0]
        del tmpl_args[0]
        try:
            template = templates[tmpl_key]
            if callable(template):
                return template(buffer, *tmpl_args)
            else:
                return template
        except:
            return '%%{%s}' %s

    args = ' '.join(args) # join pattern for keep spaces
    if args:
        pattern_tmpl = args  
        pattern = _tmplRe.sub(tmplReplacer, args)
        debug('Using regexp: %s' %pattern, buffer='', prefix=script_nick)
    if not pattern:
        raise Exception, 'No pattern for grep the logs.'

    def positive_number(opt, val):
        try:
            number = int(val)
            if number < 0:
                raise ValueError
            return number
        except ValueError:
            if len(opt) == 1:
                opt = '-' + opt
            else:
                opt = '--' + opt
            raise Exception, "argument for %s must be a positive integer." %opt

    for opt, val in opts:
        opt = opt.strip('-')
        if opt in ('c', 'count'):
            count = not count
        elif opt in ('m', 'matchcase'):
            matchcase = not matchcase
        elif opt in ('H', 'hilight'):
            # hilight must be always a string!
            if hilight:
                hilight = ''
            else:
                hilight = '%s,%s' %(color_hilight, color_reset)
            # we pass the colors in the variable itself because check_string() must not use
            # weechat's module when applying the colors (this is for grep in a hooked process)
            count = False
        elif opt in ('e', 'exact'):
            exact = not exact
            count = False
        elif opt in ('a', 'all'):
            all = not all
        elif opt in ('h', 'head'):
            head = not head
            tail = False
            count = False
        elif opt in ('t', 'tail'):
            tail = not tail
            head = False
            count = False
        elif opt in ('b', 'buffer'):
            only_buffers = True
        elif opt in ('n', 'number'):
            number = positive_number(opt, val)
        elif opt in ('C', 'context'):
            n = positive_number(opt, val)
            after_context = n
            before_context = n
            count = False
        elif opt in ('A', 'after-context'):
            after_context = positive_number(opt, val)
            before_context = False
            count = False
        elif opt in ('B', 'before-context'):
            before_context = positive_number(opt, val)
            after_context = False
            count = False
    # number check
    if number is not None:
        if number == 0:
            head = tail = False
            number = None
        elif head:
            head = number
        elif tail:
            tail = number
    else:
        n = get_config_int('default_tail_head')
        if head:
            head = n
        elif tail:
            tail = n

def cmd_grep_stop(buffer, args):
    global hook_file_grep, pattern, matched_lines
    if hook_file_grep:
        if args == 'stop':
            weechat.unhook(hook_file_grep)
            hook_file_grep = None
            s = 'Search for \'%s\' stopped.' %pattern
            say(s, buffer=buffer)
            grep_buffer = weechat.buffer_search('python', SCRIPT_NAME)
            if grep_buffer:
                weechat.buffer_set(buffer, 'title', s)
            del matched_lines
        else:
            say(get_grep_file_status(), buffer=buffer)
        raise Exception

def cmd_grep(data, buffer, args):
    """Search in buffers and logs."""
    global pattern, matchcase, head, tail, number, count, exact, hilight
    try:
        cmd_grep_stop(buffer, args)
    except:
        return WEECHAT_RC_OK

    if not args:
        weechat.command('', '/help %s' %SCRIPT_COMMAND)
        return WEECHAT_RC_OK

    cmd_init()
    global log_name, buffer_name, only_buffers, all
    log_name = buffer_name = ''
    only_buffers = all = False

    # parse
    try:
        cmd_grep_parsing(args, buffer=buffer)
    except Exception, e:
        error('Argument error, %s' %e)
        return WEECHAT_RC_OK

    # find logs
    log_file = search_buffer = None
    if log_name:
        log_file = get_file_by_pattern(log_name, all)
        if not log_file:
            error("Couldn't find any log for %s. Try /logs" %log_name)
            return WEECHAT_RC_OK
    elif all:
        search_buffer = get_all_buffers()
    elif buffer_name:
        search_buffer = get_buffer_by_name(buffer_name)
        if not search_buffer:
            # there's no buffer, try in the logs
            log_file = get_file_by_name(buffer_name)
            if not log_file:
                error("Logs or buffer for '%s' not found." %buffer_name)
                return WEECHAT_RC_OK
        else:
            search_buffer = [search_buffer]
    else:
        search_buffer = [buffer]

    # make the log list
    global search_in_files, search_in_buffers
    search_in_files = []
    search_in_buffers = []
    if log_file:
        search_in_files = log_file
    elif not only_buffers:
        #debug(search_buffer)
        for pointer in search_buffer:
            log = get_file_by_buffer(pointer)
            #debug('buffer %s log %s' %(pointer, log))
            if log:
                search_in_files.append(log)
            else:
                search_in_buffers.append(pointer)
    else:
        search_in_buffers = search_buffer

    # grepping
    try:
        show_matching_lines()
    except Exception, e:
        error(e)
    return WEECHAT_RC_OK

def cmd_logs(data, buffer, args):
    """List files in Weechat's log dir."""
    cmd_init()
    global home_dir
    sort_by_size = False
    filter = []

    try:
        opts, args = getopt.gnu_getopt(args.split(), 's', ['size'])
        if args:
            filter = args
        for opt, var in opts:
            opt = opt.strip('-')
            if opt in ('size', 's'):
                sort_by_size = True
    except Exception, e:
        error('Argument error, %s' %e)
        return WEECHAT_RC_OK

    # is there's a filter, filter_excludes should be False
    file_list = dir_list(home_dir, filter, filter_excludes=not filter)
    if sort_by_size:
        file_list.sort(key=get_size)
    else:
        file_list.sort()

    file_sizes = map(lambda x: human_readable_size(get_size(x)), file_list)
    # calculate column lenght
    if file_list:
        L = file_list[:]
        L.sort(key=len)
        bigest = L[-1]
        column_len = len(bigest) + 3
    else:
        column_len = ''

    buffer = buffer_create()
    if get_config_boolean('clear_buffer'):
        weechat.buffer_clear(buffer)
    file_list = zip(file_list, file_sizes)
    msg = 'Found %s logs.' %len(file_list)

    print_line(msg, buffer, display=True)
    for file, size in file_list:
        separator = column_len and '.'*(column_len - len(file))
        weechat.prnt(buffer, '%s %s %s' %(strip_home(file), separator, size))
    if file_list:
        print_line(msg, buffer)
    return WEECHAT_RC_OK

### Completion ###
def completion_log_files(data, completion_item, buffer, completion):
    #debug('completion: %s' %', '.join((data, completion_item, buffer, completion)))
    global home_dir
    for log in dir_list(home_dir, include_dir=True):
        weechat.hook_completion_list_add(completion, strip_home(log), 0, weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK

def completion_grep_args(data, completion_item, buffer, completion):
    for arg in ('count', 'all', 'matchcase', 'hilight', 'exact', 'head', 'tail', 'number', 'buffer',
            'after-context', 'before-context', 'context'):
        weechat.hook_completion_list_add(completion, '--' + arg, 0, weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK

def completion_grep_tmpl(data, completion_item, buffer, completion):
    pass

### Templates ###
_tmplRe = re.compile(r'%\{(\w+.*?)\}')
def make_url_regexp(buffer, *args):
    if args:
        words = r'(?:%s)' %'|'.join(args)
        return r'((?:\w+://|www\.)[^\s]*%s[^\s]*(?:/[^\])>\s]*)?)' %words
    else:
        return url

def make_host_regexp(buffer, *args):
    debug('make host: %s' %str(args))
    if not buffer:
        return ''
    regexp = []
    for nick in args:
        host = get_host(buffer, nick)
        if not host:
            continue
        host = host[host.find('@')+1:].replace('.', '\\.')
        regexp.append(host)
    if regexp:
        return '|'.join(regexp)
    return ''

def make_username_regexp(buffer, *args):
    debug('make username: %s' %str(args))
    if not buffer:
        return ''
    regexp = []
    for nick in args:
        host = get_host(buffer, nick)
        if not host:
            continue
        user = host[host.find('=')+1:host.find('@')] # FIXME this is too freenode specific
        regexp.append(user)
    if regexp:
        return '|'.join(regexp)
    return ''

def get_host(buffer, nick):
    channel = weechat.buffer_get_string(buffer, 'localvar_channel')
    server = weechat.buffer_get_string(buffer, 'localvar_server')
    nick_infolist = weechat.infolist_get('irc_nick', '', '%s,%s' %(server, channel))
    if not nick_infolist:
        return None
    host = None
    while weechat.infolist_next(nick_infolist):
        if nick == weechat.infolist_string(nick_infolist, 'name'):
            host = weechat.infolist_string(nick_infolist, 'host')
            break
    weechat.infolist_free(nick_infolist)
    return host

# stolen from urlbar
octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
ipAddr = r'%s(?:\.%s){3}' % (octet, octet)
label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (label, label)
url = r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (domain, ipAddr)

templates = {
        'ip'   :ipAddr,
        'url'  :make_url_regexp,
        'host' :make_host_regexp,
        'user' :make_username_regexp,
        }

### Main ###
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
        SCRIPT_DESC, '', ''):
    home_dir = get_home()

    weechat.hook_command(SCRIPT_COMMAND, cmd_grep.__doc__,
            "[log <file> | buffer <name> | stop] [-a|--all] [-b|--buffer] [-c|--count] [-m|--matchcase] "
            "[-H|--hilight] [-e|--exact] [(-h|--head)|(-t|--tail) [-n|--number <n>]] "
            "[-A|--after-context <n>] [-B|--before-context <n>] [-C|--context <n> ] <expression>",
            # help
            "    log <file>: Search in one log that matches <file> in the logger path.\n"
            "                 Use '*' and '?' as wildcards.\n"
            " buffer <name>: Search in buffer <name>, if there's no buffer with <name> it will\n"
            "                try to search for a log file.\n"
            "          stop: Stops a currently running search.\n"
            "      -a --all: Search in all open buffers.\n"
            "                If used with 'log <file>' search in all logs that matches <file>.\n"
            "   -b --buffer: Search only in buffers, not in file logs.\n"
            "    -c --count: Just count the number of matched lines instead of showing them.\n"
            "-m --matchcase: Don't do case insensible search.\n"
            "  -H --hilight: Colour exact matches in output buffer.\n"
            "    -e --exact: Print exact matches only.\n"
            "     -t --tail: Print the last 10 matching lines.\n"
            "     -h --head: Print the first 10 matching lines.\n"
            "-n --number <n>: Overrides default number of lines for --tail or --head.\n"
            "-A --after-context <n>: Shows <n> lines of trailing context after matching lines.\n"
            "-B --before-context <n>: Shows <n> lines of leading context before matching lines.\n"
            "-C --context <n>: Same as using both --after-context and --before-context simultaneously.\n"
            "  <expression>: Expression to search.\n\n"
            "Grep buffer:\n"
            "  Input line accepts most arguemnts of /grep, it'll repeat last search using the new \n"
            "  arguments provided. You can't search in different logs from the buffer's input.\n"
            "  Boolean arguments like --count, --tail, --head, --hilight, ... are toggleable\n\n"
            "Python regular expression syntax:\n"
            "See http://docs.python.org/lib/re-syntax.html\n",
            # completion template
            "buffer %(buffers_names) %(grep_arguments)|%*"
            "||log %(grep_log_files)|%(filename) %(grep_arguments)|%*"
            "||stop"
            "||%(grep_arguments)|%*",
            'cmd_grep' ,'')
    weechat.hook_command('logs', cmd_logs.__doc__, "[-s|--size] [<filter>]",
            "-s --size: Sort logs by size.\n"
            " <filter>: Only show logs that match <filter>. Use '*' and '?' as wildcards.", '--size', 'cmd_logs', '')

    weechat.hook_completion('grep_log_files', "list of log files",
            'completion_log_files', '')
    weechat.hook_completion('grep_arguments', "list of arguments",
            'completion_grep_args', '')

    # settings
    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    # colors
    color_date        = weechat.color('brown')
    color_info        = weechat.color('cyan')
    color_hilight     = weechat.color('lightred')
    color_reset       = weechat.color('reset')
    color_title       = weechat.color('yellow')
    color_summary     = weechat.color('lightcyan')
    color_delimiter   = weechat.color('chat_delimiters')
    color_script_nick = weechat.color('chat_nick')
    
    # pretty [grep]
    script_nick = '%s[%s%s%s]%s' %(color_delimiter, color_script_nick, SCRIPT_NAME, color_delimiter,
            color_reset)
    script_nick_nocolor = '[%s]' %SCRIPT_NAME
    # paragraph separator when using context options
    context_sep = '%s\t%s--' %(script_nick, color_info)

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
