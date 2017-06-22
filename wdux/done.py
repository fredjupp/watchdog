#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

'''
    module name: done.py
    purpose    : show history comments in .py files
    created    : 2006-09-28
    last change: 2007-12-05
    
    by E/S/P Dr. Beneicke, Heidelberg
'''

import sys, os.path
import glob                      # handles wildcards in filenames
import optparse
import re
from   time import strftime, strptime, mktime, localtime

# globals
TMFMT = '%Y-%m-%d'
DTFMTinput = '%d.%m.%Y'
DATE_LONG = '%Y-%m-%d %H:%M'
# result containers
byfile = {}   # one list for each filename
bydate = {}   # one list for each date


def mtime(fname,fmt=DATE_LONG):
    ''' Return last modified date of a file as 'YYYY.mm.dd. HH:MM' '''
    
    mtime_serial = os.path.getmtime(fname)
    return strftime(fmt,localtime(mtime_serial))


def parsefile(limit, fname):
    '''Open one file, find history comment (multi-line), return contents.'''

    global byfile, bydate
    
    # search patterns    
    cRE_date = re.compile(r'^\s*(?P<date>\d{4}-\d{2}-\d{2})$')
    sep = "'''"
    alt = 'history:'


    
    try:
        buf = open(fname).read()
    except IOError:
        return byfile,bydate
    if not buf:
        return byfile,bydate

    start = buf.find(sep)
    if start == -1:
        return byfile,bydate
    # from here, find 'history:' and advance to EOL
    start = buf.find(alt,start+3)
    if start == -1:   # other comment
        return byfile,bydate
    
    start = buf.find('\n',start+len(alt)) + 1
    end = buf.find(sep,start+1)
    if end == -1:
        end = len(buf)
    lines = buf[start:end].split('\n')

    found = False
    for l in lines:
        l = l.rstrip()
        if not l:
            continue
        mo = re.match(cRE_date,l)
        if mo:  # each time a date line is encountered...
            ds = mo.group('date')
            d = mktime(strptime(ds,TMFMT))  # get the date
            found = (d >= limit)
        if found:
            if not bydate.has_key(ds):
                bydate[ds] = {}
            if not fname in bydate[ds]:
                bydate[ds][fname] = []
            # skip the line that starts a new date block
            if not mo:
                bydate[ds][fname].append('%s' % (l[8:]))
            
            if not byfile.has_key(fname):
                byfile[fname] = []
            byfile[fname].append('%s' % (l[4:]))

    return byfile, bydate


def main():
    '''Process command line, all options except 'help' handled later.
    'help' will display usage and exit silently.'''
    usage = __doc__ + '\n' + 'usage: %prog [options] file(s)|\'*.py\', -h for help on options'

    VALID_DATEFMT = 'valid date format: d.m.[yy|yyyy]'
    
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('-o', '--overview', action='store_true', dest='bydate_only',
                      help='list changes by date only')
    parser.add_option('-s', '--start', action='store', dest='startdate',
                      type='string', help='list changes since this date; ' + VALID_DATEFMT)
    parser.add_option('-t', '--time', action='store', dest='ndays',
                      default=0, type='int', help='no. of days included')

    # parse command line
    (options, args) = parser.parse_args()

    # ----------------
    # set starting date
    sd = options.startdate
    ndays = options.ndays
    bydate_only = options.bydate_only
    
    now = mktime(localtime())
    # given a specific starting date:
    if sd:
        try:   # get the date
            limit = mktime(strptime(sd,'%d.%m.%Y'))  # '1.1.2007'
        except ValueError:
            try:
                limit = mktime(strptime(sd,'%d.%m.%y'))  # '1.1.07'
            except ValueError:
                (y,m,d,h,mi,s,w,dy,tz) = localtime()
                try:
                    (x,m,d,x,x,x,x,x,x) = strptime(sd,'%d.%m.') # '1.1.'
                    limit = mktime((y,m,d,h,mi,s,w,dy,tz))
                except ValueError:
                    print VALID_DATEFMT
                    sys.exit(2) # give up

    else:
        # given a number of days:
        (y,m,d,h,mi,s,w,dy,tz) = localtime()
        h = mi = s = 0                            # midnight
        d -= ndays                                # deduct no. of days
        limit = mktime((y,m,d,h,mi,s,w,dy,tz))

    # re-calc difference in days
    ndays = int((now - limit) / (24*60*60))
    diff = '%d days' % ndays
    if ndays == 1:
        diff = 'yesterday'
    elif ndays == 0:
        diff = 'today'
        
    # ----------------
    # parse source files
    print '\nchanges since %s (%s)\n' % (strftime(TMFMT,localtime(limit)), diff)

    if not args:
        args = ['*.py']
        
    for arg in args:
        for f in glob.glob(arg):
            if os.path.isfile(f):
                byfile, bydate = parsefile(limit, f)

    # ----------------
    # output

    sep = '-' *70
    # report 1: changes grouped by filename, sorted by date
    if byfile and not bydate_only:
        print sep
        print 'changes grouped by filename, sorted by date'
        print sep
        print
        for f in sorted(byfile.keys()):
            info = '\n%s [%s]' % (f,mtime(f))
            print '%s\n%s' % (info,'-' *len(info))
            for line in byfile[f]:
                print line

        print '\n\f'
    # report 2: changes grouped by date, sorted by filename
    if bydate:
        print sep
        print 'changes grouped by date, sorted by filename'
        print sep
        print
        for ds in sorted(bydate.keys()):
            print '\n%s\n%s' % (ds,'-' *len(ds))
            for fname in sorted(bydate[ds].keys()):
                print '%s' % fname
                for line in bydate[ds][fname]:
                    print '    %s' % line
                
    # ----------------
    # end of main()


# ----------------
if __name__ == "__main__":
    main()

