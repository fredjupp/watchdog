#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
''' WatchDog/UX module
    
    module name: sysloglib.py
    purpose    : syslog parsing library
    created    : 2006-08-04
    last change: 2007-08-08
    
    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg    
'''
''' history:
    2006-08-24
        initial release
    2007-07-31
        chg: moved get_syslog_path() to scan_syslog.py
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
'''

import time, re
# WDUX specific modules
import wdlib

# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

__version__ = wdlib.mtime(__file__)



##     record structure:
##     MMM DD HH:mm:SS host source: msg
##     blank delimited except for msg
##
##     word1 = month name (!)
##     word2 = day (1..31)
##     word3 = time (17:57:24)
##     word4 = hostname
##     word5 = 'source' + ':'
##     or 'above message repeats 2 times'
##     word6 = message


class SyslogRecord:
    ''' Generic syslog record object. Given a text line, fields are parsed.'''

    _cRE_rawline = re.compile(r'''
        (?ix)                        # ignore case, allow verbose RE
        ^                            # from begin of line
        \s*?                         # white space, non greedy, opt.
        (?P<dt>                      # group:
           [JFMASOND][a-z][a-z]      # abbrev. month name MMM
           \s+                       # white space
           [0-3]?[0-9]               # (D)D
           \s+?                      # white space, non greedy
           [0-2]?[0-9][:][0-5][0-9][:][0-5][0-9] # (H)H:MM:SS
        )
        \s+?                         # white space, non greedy
        (?P<hostname>                # group:
           [^\s]+?                   # anything but white space
        )
        \s+?                         # white space, non greedy
        # here a 'repeats...' message may come -> fail
        (?!above message repeats)    # RE will fail if matching
           (?P<src>                     # group:
              [^\[:]+?                  # string not containing "[" or colon
           )?                           # =optional
           \s*?                         # white space, non greedy, opt.
           (                            # optional:
              \[(?P<PID>                # group: 
                 \d+?                   # '[dddd...]'
                )
              \]
           )?                           # =optional
           [:]                          # one colon
           \s+?                         # white space, non greedy
        (?P<msg>[^\n]*)[\n]$         # message up to EOL, w/o EOL char
    ''') 
    

    def __init__(self,line):
        '''Parse <line> from syslog, split into named fields.
        yields:
        dtserial    timestamp with year as seconds since epoch
        hostname    source host
        src         source process or 'repeated...' message 
        PID         process ID or None
        msg         process specific message
        OK          True if all fields are found, False otherwise
        i.e. no match or a 'above message repeats...' msg is found
        '''
        self.OK = False
        
        # parse <line>
        _mo = SyslogRecord._cRE_rawline.match(line)
        if not _mo:                 # not recognized
            return
        res = _mo.groupdict()
        _src = res['src']
        if not _src:
            return                # skip 'repeating' messages
        self.src = _src.lower()
        self.dtserial = dateserial(res['dt']) # complete datetime with year
        self.hostname = res['hostname']
        self.PID = res['PID']
        self.msg = res['msg']
        self.OK = True
        # - done __init__


# - end of class SyslogRecord


# ---------------------------------
    

def dateserial(dtstring):
    '''Convert syslog timestamp string to seconds since epoch.
    E.g. 'May 20 17:57:15' timestamp with days and month only.
    Append current year except if date_read > currentdate, i.e.
    date_read must be more than 3600 seconds ahead in future
    then append last year (current year - 1).'''
    
    t = dtstring.split()  # mon,day,time
    tm = t[2].split(':')
    limit = wdlib._curserial + 3600.
    # use from current datetime: year and isdst flag
    cy = wdlib._curdate[0]
    dstflag = wdlib._curdate[8]
    cm = wdlib._months[t[0]]

    ct = time.mktime((cy,cm,int(t[1]),
                      int(tm[0]),int(tm[1]),int(tm[2]),
                      0,1,dstflag))

    if ct > limit:   # date is ahead
        ct = time.mktime((cy-1,cm,int(t[1]),
                          int(tm[0]),int(tm[1]),int(tm[2]),
                          0,1,dstflag))
    return ct


# -----------------------------------------------------
if __name__ == "__main__":
    print wdlib.myversion(__file__)
