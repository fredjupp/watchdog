#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

''' -----------------------------------------------------
    WatchDog UX module

    module name: wdlib.py
    purpose    : watchdog library
    created    : 2006-07-04
    last change: 2007-11-29
    
    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg
    -----------------------------------------------------
'''
''' history:
    2006-08-24
        initial release
    2006-08-28
        add: standardized error messages in 'try:' statements
        fix: convEOL: open -> createfile
        fix: convEOL: destdir was appended to file path; this works for
             absolute paths only! now destdir replaces file path
        chg: countlines: call with filename, not handle; open file status
             will not be changed
        chg: openfile: call open, not file
        add: abspath replaces multiple os.path calls
        chg: myversion returns basename only
        chg: printTopN: 2 more spaces between count and value columns
             for better legibility
    2006-08-30
        add: boolfromconf()
        add: open_out, open_tmp: construct filename in report dir (very often
             used; meant to keep the folder logic locally)
        add: rmdir()
        fix: myversion: mtime needs absolute pathname
        add: convEOL: add/remove filename extension
    2006-08-31
        add: set_configfile: default folder is folder where script is run from
    2006-09-25
        add: clearfolder(), use instead of rmdir()
        add: out_path, tmp_path companions to open_out, open_tmp
        add: is_IPaddr, IP2host (not yet used)                
    2006-09-26
        add: center()
        chg: myversion: format changes
        chg: write_header: do not print file modify date (is always current)
        chg: write_header: include timefilter period info
        chg: set_timefilter: introduce upper bound on time filter interval
        add: period_str (timefilter period info)
    2006-09-28
        fix: convEOL: do not convert to DOS if already in DOS mode
    2006-10-16
        add: invdict()
    2006-10-24
        chg: convEOL: more verbose output; output file is created even if no
             conversion is necessary
    2007-07-11
        chg: elapsedstr() replaced
    2007-07-13
        chg: printTopN rewritten, saved in old_printTopN
        chg: skip_header: return empty header if second separator is not found
        fix: pr: corrected output for (arg < 0) and floats
    2007-07-30
        chg: redirect_stdout: changed logic to toggle stdout; 2nd parameter
             is unnecessary; no sys.exit() call
        add: convEOL: error handler for os.stat() call
        chg: check_conf: return None if IOError occurs, do not use sys.exit()
    2007-08-08
        chg: period_str: show time interval without seconds
        chg: period_str: 'events from..only' instead of 'time filter:'
        chg: global variable __file__ sometimes undefined; wrapped
        add: redirect_stdout: changed logic whether stdout is redirected
             or not; robust if called more than once
        chg: (various fcts): use global separator line variable (sepln)
    2007-08-10
        fix: various: if return False is used to signal a failure, an explicit
             return True must be coded when successful!
        chg: printTopN: 'events' instead of 'entries'
        fix: some err() statements without trailing newline
    2007-11-19
        add: get_path()
        chg: out_path, tmp_path, open_out, open_tmp call get_path
        chg: convEOL: mkdir of destination dir is already handled by
             createfile()
        add: opens(): open() replacement supporting filename
             pattern(s); recursive if wildcard in path
        chg: openfile() uses opens() now (multi-file input)
    2007-11-21
        chg: has_wildcards new
        chg: opens() non-wildcard file is opened by regular open()
    2007-11-24
        chg: _months initialized statically
        chg: opens: if there is only 1 file to open (even if wildcards are used)
             then a regular open() is used
        fix: open_out, open_tmp: test for write mode now includes append mode
        fix: createfile: file was created without path
    2007-11-29
        fix: redirect_stdout: accept UNIX style '-' to direct output to stdout
        add: opens(): sorts filename list
        del: deleted old_printTopN()
'''

import sys, os.path, time, shutil
import platform
# WDUX specific modules
import wdux_configfile



# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

IPcache = {}

WDUX_CONF = 'wdux.conf'  # name of config file
#   this might be changed later under program control
#   using set_confpath()

# <verbose> controls info messages to the screen
# if stderr is redirected, verbose if False
verbose = False
    

nDashes = 70             # length of separator line in output
sepln = '-' *nDashes     # output separator line

_saved_stdout = 0        # saved stdout file handle
_new_stdout = 0
one_day = 24. * 60. * 60.# in seconds

# vars for time filtering:
_curdate = time.localtime()          # at module load time; 9-tuple
_curserial = time.mktime(_curdate)
# we need to translate month names to numbers
_months = dict(
    (['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct',
      'Nov','Dec'][i],i+1) for i in range(12)
)
    
    
# some time.strftime() formats:
DATE_LONG  = '%Y-%m-%d %H:%M'  # '2006-11-29 13:55'
DATE_SHORT = '%y-%m-%d'        # '06-11-29'
DATE_WEEKDAYNUM = '%w-%a'      # '1-MON'


# -----------------
# std: output functions
err = sys.stderr.write


def info(s=''):
    '''Print string <s> on stderr only if wdlib.verbose is True.'''
    if verbose:
       err(s + '\n')


# ------------------
# date/time routines


def now(fmt='%Y-%m-%d %H:%M:%S'):
    '''Current date/time as string.
    <fmt> optional custom format string.'''
    return datestr(time.mktime(time.localtime()),fmt)


def elapsedstr(serdiff):
    '''Return difference in seconds as '[-][dd]HH:MM' string.'''
    # minutes are rounded up
    # fixed output length of 10 chars
    
    rediv = lambda alist,b : list(divmod(alist[0],b)) + alist[1:]

    # remove sign, round up to next minute
    t = abs(serdiff) + 30
    # divide repeatedly; res=(days,hours,mins,secs)
    res = tuple(reduce(rediv,[[t,],60,60,24]))
    
    # output (secs are not used)
    if res[0] == 0:   # no days
        s = '-%02d:%02d' % res[1:-1]
    else:
        s = '-%02dd%02d:%02d' % res[:-1]
    return '%10s' % s[(serdiff >= 0):]  # skip sign if positive


def datestr(serial,fmt='%Y-%m-%d %H:%M:%S'):
    '''Convert date serial (seconds since epoch) to string.
    May supply custom format string.'''
    return time.strftime(fmt,time.localtime(serial))


def set_timefilter(logstatus_str, filterOnTime=True):
    '''Return (lower bound,upper bound) (serial times) as filter period.
    Lower bound is either the previous day, midnight, or the last successful
    run if that is longer ago. Upper bound is either yesterday at 23:59:59 plus
    1 second (upper bound is left out, i.e. low_b <= valid < upp_b)
    or "now" (_curserial) if no time filter is selected.
    <logstatus_str>: keyname of log entry in wdux.conf.'''
    
    last_run, was_OK = get_status(logstatus_str)
    if not filterOnTime:
        oldest = 0
        youngest = _curserial
    elif not was_OK:  # this check not yet run
        oldest = 0
        youngest = yesterday_midnight(_curserial) + one_day
    else:
        yesterday = yesterday_midnight(_curserial) # current day
        if yesterday < last_run:                   # '<' == 'older than'
            oldest = yesterday
        else:
            oldest = last_run
        youngest = yesterday + one_day
    return (oldest, youngest)


def period_str(period):
    '''Return info on time filter period for display.'''

    period_fmt = '%Y-%m-%d %H:%M'
    if period[0] == 0:
        lb = 'beginning'
    else:
        lb = datestr(period[0],period_fmt)
    return 'events from %s to %s only' % (lb,datestr(period[1],period_fmt))

  
# ------------------

def convEOL(filename, toDOS=True, destdir='', DOSext='', noaction=False):
    '''Convert text file line ends between DOS and UNIX.
    Keeps file mode, access and modify time stamps.
    if <DOSext>: appends DOSext if toDOS, removes if toUNIX
    <noaction>: run without creating output
    '''
    import stat, os

    try:
        stbuf = os.stat(filename)
    except:
        stbuf = None

    fIN = openfile(filename,'rb')
    if not fIN:
        info('convEOL: cannot open %s for input' % filename)
        return False

    if toDOS:
        _from, _to = '\n', '\r\n'
        dd = 'toDOS'
    else:
        _from, _to = '\r\n', '\n'
        dd = 'toUNIX'
    destdir = destdir or dd   # default or specified
    
    newdata = fIN.read()
    fIN.close()
    if '\0' in newdata:
        info('convEOL: %-20s: binary!' % filename)
        return False

    # to DOS: do not convert if already in DOS mode!!
    if not (toDOS and '\r\n' in newdata):
        newdata = newdata.replace(_from, _to)

    # write to file
    # replace source path with dest path
    p, fname  = os.path.split(filename)
    fname = os.path.join(destdir,fname)
    if DOSext:    # add/remove extension
        if not DOSext.startswith('.'):
            DOSext = '.' + DOSext
            
        fn, ext = os.path.splitext(fname)
        if toDOS:
            if ext != DOSext:
                fname += DOSext  # append DOS extension if not yet there
        else:  # toUNIX
            if ext == DOSext:  # remove DOS extension
                fname = fn
                
    if not noaction:
        fout = createfile(fname,'wb')
        if not fout:
            info('convEOL: cannot create %s' % (fname))  # debug
            return False
        fout.write(newdata)
        fout.close()

        # copy mode, access and modify times
        if stbuf:
            try:
                os.chmod(fname,(stbuf[stat.ST_MODE]))
                os.utime(fname,(stbuf[stat.ST_ATIME],stbuf[stat.ST_MTIME]))
            except OSError:
                info('convEOL: error changing file times on %s!' % fname) # debug
                return False

    return True  # convEOL()


def try_system(cmd, error='',success='',abort=False):
    '''Run a system command, catch errors.
    Abort on error if <abort>.'''
    
    retval = os.system(cmd)
    if retval:
        err('system() call %s failed: %s\n' % (cmd,error))
    if abort:
        raise IOError
    return retval


def sudo_system(cmd, cdir='./'):
    '''Run <cmd> as superuser, prompt user if necessary.'''
    
    sucmd = r'su -c "%s"' % cmd
    # use sudo instead if the /etc/sudoers file exists
    if os.path.exists('/etc/sudoers'):
        if os.path.exists('/usr/local/bin/sudo'):
            sucmd = 'sudo %s' % cmd
    try_system('cd %s; %s' % (cdir, sucmd), abort=1)


def abspath(p):
    '''Return normalized, absolute path from <p>.'''
    return os.path.abspath(os.path.normpath(p)) 


def set_confpath(confpath=''):
    '''Set global configuration file name, used by check_conf().
    Set once on program start.'''
    global WDUX_CONF

    # if nothing is specified, search it in the script dir
    defpath = os.path.dirname(sys.argv[0])
    default = os.path.join(defpath,'wdux.conf')
    p = confpath or default
    # set internal variable
    WDUX_CONF = abspath(p)
    return WDUX_CONF


def check_conf():            
    '''Read configuration file and abort on error.'''

    conf = wdux_configfile.Settings(WDUX_CONF)
    if not conf:
        err('Cannot access configuration file "%s"! Aborted.\n' % WDUX_CONF)
        return None
    return conf

 
def has_wildcards(s):
    ''' check if string s contains wildcards.'''
    for ch in '*?[':
        if ch in s:
            return True
    else:
        return False


def opens(namepattern, mode='rU', bufsize=64*1024):
    ''' builtin open() replacement that works with filename patterns.
        For reading modes only!
        Files are searched in current or embedded root dir(s).
        namepattern: either a string with optional path and wildcards,
        or a list or tuple with strings.
        Uses glob and fileinput module.
        Returns a fileinput.Fileinput file-like object if multiple files
        are parsed; otherwise a file object. Multiple filenames are sorted.
    '''

    import glob, os, stat, fileinput

    # namepattern: iff is_string: holds pattern *?[]
    # else is_list: holds patterns or filenames
    # creates a Fileinput instance, a file otherwise
    if isinstance(namepattern, basestring):
        namepattern = [namepattern]
    else:
        namepattern = list(namepattern)
    files = []
    for p in namepattern:
        for f in glob.glob(p):
            # discard non-regular files (ISREG and not ISLNK)
            try:
                _mode = os.stat(f)[stat.ST_MODE]
            except OSError:
                continue  # skip if I can't stat()
            if stat.S_ISREG(_mode) and not stat.S_ISLNK(_mode):
                files.append(f)
    if not files:
        raise IOError,'[Errno 2] No such file or directory: \'%s\'' % repr(namepattern)
    elif len(files) == 1:
        return open(files[0],mode,bufsize)
    else:
        # sort filenames ascending
        files.sort()
        return fileinput.input(files=files, mode=mode, bufsize=bufsize)


def openfile(fname,mode='rU'):
    '''Open file for reading.
    Default mode suits text files; might be 'rb' for binary file
    'U': line ends are converted to '\\n' on any platform
    '''

    try:
        f = opens(fname,mode)
    except IOError,msg:
        err('openfile(%s):\n%s\n' % (fname,msg))
        return None
    else:
        return f



def createfile(fname, mode='w'):
    '''Open text file for writing.
    Creates missing path components if necessary.
    Default mode suits text files; might be 'wb' for binary file
    '''

    path, filename = os.path.split(fname)
    if path:
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except IOError,msg:
                err('createfile()/makedirs(%s):\n%s\n' % (path,msg))
                return None

    try:
        f = open(fname,mode)
    except IOError,msg:
        err('createfile(%s):\n%s\n' % (fname,msg))
        return None
    else:
        return f


def pathfromconf(filename,pl):
    '''Read vars from list <pl> from conf file,
    The first list entry pl[0] must be the section to read.
    Concatenate to path, append <filename>, return absolute path.
    '''
    conf = check_conf()
    section = pl[0]
    paths = [conf.get(section,x) for x in pl[1:]]
    paths.append(filename)

    p = os.path.join('',*paths)
    return abspath(p)


def get_path(key):
    '''Get folder path from configuration file.'''
    conf = check_conf()
    p = conf.get('CURRENT RUN',key)
    return abspath(p)


def out_path():
    '''Get output folder path from configuration file.'''
    return get_path('OUTPATH')

    
def tmp_path():
    '''Get temp folder path from configuration file.'''
    return get_path('TMPPATH')

    
def open_out(fname,mode='rU'):
    '''Open file in output dir as specified in configuration file.'''
    filename = os.path.join(get_path('OUTPATH'),fname)
    m = mode.lower()
    if 'w' in m or 'a' in m:
        return createfile(filename,mode)
    else:
        return openfile(filename,mode)


def open_tmp(fname,mode='w'):
    '''Open file in tmp dir as specified in configuration file.'''
    filename = os.path.join(get_path('TMPPATH'),fname)
    if 'w' in mode.lower() or 'a' in mode.lower():
        return createfile(filename,mode)
    else:
        return openfile(filename,mode)

    
def boolfromconf(section, option):
    '''Get boolean value from conf file.'''
    conf = check_conf()
    return conf.getboolean(section,option)


def mkpaths(root,paths):
    '''Constructs paths from <root> and <paths> list.
    Checks for existence, creates all missing path components
    if necessary.'''

    # convert to list if only a single filename is given
    if isinstance(paths, basestring):        
        paths = [paths]

    ret = True
    for d in paths:
        f = os.path.join(root,d)
        if not os.path.isdir(f):  # doesn't exist, create
            try:
                os.makedirs(f)    # create all intermediates as well
            except IOError,msg:
                err('mkpaths():\n%s\n' % (msg))
                ret = False
                continue
    return ret


def invdict(d):
    ''' Invert a dictionary. Must have unique values!!'''
    return dict(((v,k) for (k,v) in d.iteritems()))


def diffs(file_old,file_new,onlynew=False):
    '''Return a list of unique lines of 2 text files.
    Skips duplicates in each input as well.
    if <onlynew>:
    output lines will be from <file_new> only (e.g. logfiles)
    otherwise, from both files (e.g. /etc/passwd)

    Returned list has same order as input.
    '''

    # open file
    f = openfile(file_old)
    if not f:
        return []

    # read the first file line-wise
    dold = {}
    lineno = 0
    for line in f:
        lineno += 1
        # list to dict; eliminates dups
        # store the linenos so that input order can be restored
        dold[line] = lineno      
    f.close()

    # we can improve memory consumption here:
    # as we read line by line, we silently drop duplicates

    # open file
    f = openfile(file_new)
    if not f:
        return []

    dnew = {}
    dtbd = {}  # to-be-deleted after run
    # just increment lineno so that one can distinguish both inputs
    for line in f:
        lineno += 1
        
        # common entry ?
        if not line in dold:          # fast dict lookup
            dnew[line] = lineno       # list to dict; eliminates dups
            # store the linenos so that input order can be restored
        else:
            if not onlynew:
                dtbd[line] = ''       # any value will do
    f.close()

    if not onlynew:                   # elim. common entries in old list
        for line in dtbd:
            del dold[line]
        dnew.update(dold)             # append the uniq old ones

    # restore input order
    # sort dict by value
    L = dict_sortbyvalue(dnew, descending=False, keys_desc=False)
    return L


def mkdiff(file_old,file_new,file_diff,onlynew=False):
    '''Write differences of 2 files to disk.
    if <onlynew>: save additions only.
    '''


    L = diffs(file_old,file_new,onlynew)
    if not isinstance(L,list):
        return False
    
    # create file
    out = createfile(file_diff)
    if not out:
        return False
    for line in L:
        out.write(line)
    out.close()
    return True


def log_status(status_label,is_OK):
    '''Record time of last run and status in config file.
    Status is 'FAILED' or 'OK'.
    '''
    global DATE_LONG

    now = time.strftime(DATE_LONG)
    s = '%s %s' % (now,('FAILED','OK')[is_OK])
    conf = check_conf()
    conf.add('STATUS',status_label,s)
    conf.save()
    del conf


def get_status(status_label):
    '''Read time of last run and exit status of a module from config file.
    Returns time in seconds since epoch and boolean <is_OK>.
    Ff status is missing, return a very old date and status='FAILED'
    is_OK == True after successful run
    is_OK == False when started but not finished OK
    '''
    global DATE_LONG
    
    conf = check_conf()
    if conf.has_option('STATUS',status_label):
        value = conf.get('STATUS',status_label).rsplit(None,1) # e.g.['2006-08-09 11:22','OK']
    else:
        very_old = time.strftime(DATE_LONG,(2005,1,1,0,0,0,0,1,-1))
        value = (very_old,'FAILED')
    now = time.mktime(time.strptime(value[0],DATE_LONG))
    is_OK = value[1].upper() == 'OK'
    del conf
    return now,is_OK


def redirect_stdout(fname):
    '''Redirect output from stdout to specified file on disk.
    Previous stdout will be saved here.
    Restores stdout if called again.
    '''
    global _saved_stdout, _new_stdout

    sys.stdout.flush()  # flush buffer


    # logic: if stdout is a file AND filename is not <stdout>,
    # then the output is already redirected
    # can only be reset if _saved_stdout is intact!
    redirected = False
    if isinstance(sys.stdout,file):
        if sys.stdout.name != '<stdout>':
            redirected = True

    if not redirected:
        # change stdout to specified file
        if not fname or fname == '-':  # empty or UNIX style stdout: do nothing
            _saved_stdout = _new_stdout = None
            return True
        else:
            _saved_stdout = sys.stdout
            _new_stdout = createfile(fname, 'w') # w/ error msg printed
            if not _new_stdout:
                return False
            sys.stdout = _new_stdout
            # from here on, all print statements print to file
    else:
        if _saved_stdout and _new_stdout:
            sys.stdout = _saved_stdout
            _new_stdout.close()
            _new_stdout = None

    return True


def joinpath(root,parts):
    '''Join string <root> with all other args to form a valid path.
    Returns absolute path.
    '''
    if isinstance(parts,basestring):
        parts = [parts]
    p = os.path.join(root,*parts)
    return abspath(p)


def mtime(fname,fmt=DATE_LONG):
    '''Return last modified date of a file as 'YYYY.mm.dd. HH:MM' '''
    global DATE_LONG
    
    mtime_serial = os.path.getmtime(fname)
    return time.strftime(fmt,time.localtime(mtime_serial))


def myversion(me = ''):
    '''Return last modified date of currently executed program.'''
    import sys

    if not me:
        me = sys.argv[0]
    me = abspath(me)
    me_only = os.path.splitext(os.path.basename(me))[0]
    return '%s  [version %s]\n' % (me_only, mtime(me))
    

def version_header(script, file_, period=None):
    '''Return string with date of script and (if nonempty) of file_.
    Include time period info if given.'''

    sep = sepln
    scriptdt = myversion(script)
    fileinfo = ''
    if file_:
        if has_wildcards(file_):
            filedt = '---'
            fileinfo = 'reading "%(file_)s"\n' % vars()
        else:
            filedt = mtime(file_,'week %W, %a %Y-%m-%d %H:%M')
            fileinfo = 'reading "%(file_)s"\nfrom %(filedt)s\n' % vars()
    p_s = ''
    if period:
        p_s = period_str(period) + '\n'
    s = '\n%(sep)s\n%(scriptdt)s%(fileinfo)s%(p_s)s%(sep)s\n' % vars()
    return s


def day_at_midnight(serialdate=None):
    '''Return the timestamp of <serialdate> at 0:00:00 exactly,
    in seconds since epoch.'''

    from time import localtime, mktime
    
    if not serialdate:
        serialdate = _curserial # current time at module load time

    # midnight 0:00
    tm = list(localtime(serialdate))
    tm[3] = tm[4] = tm[5] = 0  # h:m:s at midnight
    return mktime(tuple(tm))


def yesterday_midnight(serialdate=None):
    '''Return the timestamp of one day before <serialdate> at 0:00:00 exactly,
    in seconds since epoch.'''
    if not serialdate:
        serialdate = _curserial # current time at module load time
    return day_at_midnight(serialdate - one_day)

    
def yesterdays_files(fpatt,reffile='',verbose=False):
    '''Find all files like <fpatt> that were modified one day before <reffile>.
    If filename <reffile> is not given, use current time.
    Include the youngest file just before yesterday and
    the next file afterwards, if existing
    (to avoid orphaned log entries)
    '''
    from time import localtime, mktime, strftime
    import os.path

    global DATE_LONG
    
    
    if reffile:  # filename given
        now = os.path.getmtime(reffile) # in seconds since epoch
    else:
        now = time.mktime(time.localtime()) # current time
        
    # yesterday at midnight 0:00
    lb_s = yesterday_midnight(now)
    # last time of day = 23:59:59
    ub_s = lb_s + one_day - 1.

    files = dir(fpatt)[1] # only files matching pattern <fpatt>
    if not files:
        return []
    
    if verbose:
        print '\n%d files retrieved with pattern "%s":' % (len(files),fpatt)
            
    # sort by age
    fsv = [(os.path.getmtime(f),f) for f in files]
    fsv.sort()
    
    if verbose:
        print '\nsorted by age:'
        for i in fsv:
            print '%-20s %s' % (i[1], strftime(DATE_LONG,localtime(i[0])))
        print '\n%s...%s' % (
            strftime(DATE_LONG,localtime(lb_s)),
            strftime(DATE_LONG,localtime(ub_s))
            )

    D = {}          # collect filenames
    prev = fsv[0]
    for (mt_s, fn) in fsv:
        if mt_s >= lb_s:
            D[fn] = mt_s    # this might add the next above ub
            if mt_s > ub_s:
                break
        else:
            prev = (mt_s, fn)
    # add oldest below lb or next above ub
    (mt_s, fn) = prev
    D[fn] = mt_s

    # sort by name        
    L = D.keys()
    L.sort()
    if verbose:
        print '\nselected:'
        for i in L:
            print '%-20s %s' % (i, strftime(DATE_LONG,localtime(D[i])))
    return L    


def dict_sortbyvalue(d, descending=True, keys_desc=False):
    '''Sort dict <d> by value, order <descending>.
    Secondary sort on keys, order <keys_desc>.
    Return list of tuples (key,value).
    '''
    if not d:
        return []

    import operator
    
    out = d.items() # [(k,v)]
    out.sort(reverse=keys_desc)
    out.sort(reverse=descending,key=operator.itemgetter(1))
    return out


def printTopN(d,desc='values',mx=10):
    '''List <mx> entries from dict <d> in descending order (value,key).
    If the values are ints, longs or floats (e.g. from counting)
    then print each line's percentage, the total for the Top N values
    and the overall total of the values.
    '''
        
    # sort descending by count
    L = dict_sortbyvalue(d,descending=True,keys_desc=False)
    # returns L=[(k,v)]
    do_totals = len(L) and isinstance(L[0][1],(int,long,float))

    if do_totals:   # process list completely to sum up the values
        total = 0
        for k,v in L:
            total += v
        if total == 0:
            do_totals = False # no percentages if total==0
        else:
            pc = 100.0/total
            topNtotal = 0   # sum of values of the Top N list entries
            
    
    # output
    Top = 'Top %d' % mx
    print sepln
    print '%s %s\n' % (Top,desc)
    print '     count   %s' % (desc)
    print sepln

    shown = 0
    for k,v in L:
        if shown >= mx:
            break
        ks = str(k)
        if len(ks) > 40:   # truncate line
            ks = ks[:39] + '>'
        if do_totals:
            print '%10d   %-42s %5.1f%%' % (v,ks,v*pc)
            topNtotal += v
        else:
            print '%10d   %-42s' % (v,ks)
        shown += 1

    if shown < mx:                  # less than Top N list entries
        print '... no more events ...'
    print

    if do_totals:
        x = ''
        if topNtotal != 1: x = 's'
        res = 'event%s in %s' % (x,Top)
        print '%10d   %-42s %5.1f%%' % (topNtotal,res,topNtotal*pc)

        x = ''
        if total != 1: x = 's'
        print '%10d   event%s total' % (total,x)

    print sepln
    print


def printfromfile(filename):
    '''Print formatted output from results file.'''
    f = openfile(filename)
    if not f:
        return False
    for line in f:   #  reads including EOL char
        print line,  # ! trailing comma
    print
    f.close()


def write2file(dict_,desc,filename):
    '''Write whole dict <dict_> to file <filename>.'''

    f = open_out(filename,'w')
    if not f:
        err('write2file: cannot create %s\n' % f.name)
        sys.exit(1)

    print >>f, sepln
    print >>f,'%s\n' % desc
    print >>f,'see file %s\ndated %s\n' % (fname,mtime(fname))
    print >>f,'     count value'
    print >>f, sepln

    if not len(dict_):
        print >>f,'(list empty)'
    else:
        L = dict_sortbyvalue(dict_,descending=True, keys_desc=False)    
        for k,v in L:
            print >>f,'%10s %s' % (str(v),k)
    print >>f, sepln
    f.close()
    

def append2file(list_,desc,filename):
    '''Append whole list <list_> to file <filename>.'''

    f = open_out(filename,'a')
    if not f:
        err('append2file: cannot create %s\n' % f.name)
        sys.exit(1)

    print >>f, '%s' % (desc)
    print >>f, sepln

    if not len(list_):
        print >>f, '(list empty)'
    else:
        for l in list_:
            print >>f, '%s' % l
        
    print >>f, sepln
    

def skip_header(fh):
    '''Read first lines of an open text file, determine if there is
    a separator line (like '-----'). The second char on the first
    non-blank line is taken (so as to allow a comment char).
    This start character must be repeated at least 8 times.
    Lines are skipped until the second sep.line is found, but only
    within the first 10 non-blank lines. If there is none, reset
    the file pointer to BOF.'''

    fh.seek(0)  # reset to BOF
    hlines = []
    sep = ''
    found = n = 0
    while n < 10 and found < 2:  # 'for line in fh' uses buffered I/O!
        line = fh.readline()
        if not line:  # EOF
            break
        if found > 0:
            hlines.append(line)
        if not line.strip():
            continue
        n += 1
        # from first non-blank line, determine separator char
        if not sep:
            startchar = line[1]
            # if this is not repeated, there is no header
            sep = startchar *8
            if not line[1:].startswith(sep):
                break
            hlines.append(line)

        if line[1:].startswith(sep):
            found += 1

    if found < 2:        # no header found
        fh.seek(0)
        hlines = []
    return ''.join(hlines)

            
def center(txt,wid=nDashes):
    print '%*s' % ((wid+len(txt)) // 2,txt)

    
def pr(dig):
    '''Like print '%d', but with thousands separators.'''
    s = str(dig)
    fin = s.find('.')
    if fin < 0:
        fin = len(s)
    l = list(s)
    for j in range(fin-3,(l[0]=='-'),-3):
        l.insert(j,".")
    return ''.join(l)


def write_header(f,desc,legend=''):
    '''Write output header. Return # of bytes written.'''
    
    fs = 'see file %s' % (f.name)
    if legend:
        legend = '\n' + legend + '\n'
    hdr = '%s\n%s\n%s\n%s%s\n'  % (sepln,desc,fs,legend,sepln)
    f.write(hdr)
    return f.tell()


def rm(fname):
    '''Delete file <fname>, check for errors.'''
    try:
        os.unlink(fname)
    except OSError,msg:
        err('rm():\n%s\n' % msg)


def rmdir(path):
    '''Delete <path> and all files in and below.'''
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path,ignore_errors=True)    # remove existing
    

def clearfolder(path):
    '''Delete all files in <path>. Ignore errors silently.'''
    if os.path.exists(path) and os.path.isdir(path):
        for f in os.listdir(path):
            af = os.path.join(path,f)
            if os.path.isfile(af):
                try:
                    os.unlink(af)
                except OSError:
                    pass        


def dir(pat, ignorecase=True):
    '''Returns 2 lists of files matching filename pattern <pat>.
    First [0] dirs, then [1] files.
    Supports wildcards '*' and '?' and mimicks DOS globbing.
    '''
    import os, os.path
    import fnmatch  # does all the globbing

    
    path, fpat = os.path.split(abspath(pat))
    if not fpat:
        fpat = '*'

    # fnmatch.filter() returns a list matching fpat
    if ignorecase:
        fl = fnmatch.filter(os.listdir(path),fpat)
    else:
        fl = fnmatchcase.filter(os.listdir(path),fpat)

    _dirs = []
    _files = []
    for f in fl:
        f = os.path.join(path,f)
        if os.path.isdir(f):
            _dirs.append(f)
        elif os.path.isfile(f):
            _files.append(f)
    _dirs.sort()
    _files.sort()
    
    return _dirs,_files


def hint():
    '''Print notice to stderr if a module is started by itself.'''

    msg = '''\n\nPlease run "wdux.py" to generate a report.
    You may select single events by using command line options.
    See "wdux.py -h" for help.
    Aborting.\n\n'''
    sys.exit(msg)


def is_IPaddr(a):
    '''Bool: valid IPv4 address?'''
    if a.replace('.','').isdigit():
        # might be
        n = a.split('.')
        if len(n) != 4:
            return False
        for i in n:
            if not 0 <= int(i) <= 255:
                return False
        return True
    else:
        return False


def IP2host(IP):
    '''Return hostname and IP string.'''
    import socket
    global IPcache

    if IPcache.has_key(IP):
        hostname = IPcache[IP]
    else:
        try:
            hostname = socket.gethostbyaddr(IP)[0]
        except socket.herror,msg:
            print >>sys.stderr,msg,IP
            hostname = IP
    IPcache[IP] = hostname
    return '%s [%s]' % (hostname,IP)


# -------------------------------------------------------------------------
# globals

__version__ = mtime(__file__)

if __name__ == "__main__":
    print myversion(__file__)
