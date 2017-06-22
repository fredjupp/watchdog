#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

''' -----------------------------------------------------
    WatchDog UX module

    module name: lastlib.py
    purpose    : last/lastb parsing library
    created    : 2006-08-22
    last change: 2007-08-08

    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg    
    -----------------------------------------------------
'''
''' history:
    2006-08-24
        initial release
    2006-09-22
        add: new attribute ttytype: does not contain specific tty number
        fix: last line containing starting date is skipped now
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
##     user name
##     host (or IP)
##     tty or service (e.g. ftp)
##     MMM DD HH:mm   start time
##     "-"
##     HH:mm          end time
##    (HH:mm)         duration


class LastRecord:
    ''' Generic last record object. Given a text line, fields are parsed.'''

    def __init__(self,line,is_lastb):
        '''Parse input <line>, split into named fields.
        input params:
        line        logline to parse
        is_lastb    source is lastb command
        yields:
        dtserial    timestamp with year in seconds since epoch
        user        user
        tty         tty
        ttytype     if tty contains a '/', part before it; otherwise == tty
        host        host
        online      Bool: user is still online, duration is undef.
        duration    duration in minutes
        OK          True if all fields are found, False otherwise
        '''
        
        self.OK = False
        # skip last line stating when list entries begin
        if line.lower().find('begins at') > 0:
            return

        fields_expected = 10
        if is_lastb:
            fields_expected = 7
        # parse <line>
        v = line.strip().split()
        if len(v) != fields_expected:    # not recognized
            return
        # make complete datetime with year
        if not v[4].isalpha:    # month name
            return
        if not v[5].isdigit:    # day date
            return
        self.dtserial = dateserial(v[4],v[5],v[6])

        self.user = v[0]
        self.tty  = v[1]
        # if tty is of type 'pts/xxx', return just the type
        s = v[1]
        i = s.rfind('/')
        if i > 0:
            self.ttytype = s[:i]
        else:
            i = s.rfind(':')
            if i > 0:
                self.ttytype = s[:i]
            else:
                self.ttytype = s
        self.host = v[2]
        # we ignore v[3], the day name
        if not is_lastb:  # last only, not in lastb
            self.online = v[7] != '-'
            if self.online:  # "still logged in"
                self.endtm = dateserial(v[4],v[5],'23:59')
                self.duration = 999999
            else:
                self.endtm = dateserial(v[4],v[5],v[8])
                # str might be '(00:09)' or '(1+04:23)'
                s = v[9][1:-1]
                if '+' in s:
                    i = s.find('+')
                    d = long(s[:i]) * 60 * 60 * 24
                    s = s[i+1:]
                    self.duration = d + toseconds(s) # '(h:mm)'
                else:
                    self.duration = toseconds(s) # '(h:mm)'
        self.OK = True
        # - done __init__


# - end of class


# ---------------------------------
    

def dateserial(monthstr,day,tmstr):
    '''Convert timestamp string to seconds since epoch.
    E.g. 'May 20 17:57' timestamp with days and month only.
    Append current year except if date_read > currentdate, i.e.
    date_read must be more than 3600 seconds ahead in future
    then append last year (current year - 1).'''
    
    tm = tmstr.split(':')
    limit = wdlib._curserial + 3600.
    # use from current datetime: year and isdst flag
    cy = wdlib._curdate[0]
    dstflag = wdlib._curdate[8]
    cm = wdlib._months[monthstr]

    ct = time.mktime((cy,cm,int(day),
        int(tm[0]),int(tm[1]),0,0,1,dstflag))

    if ct > limit:   # date is ahead
        ct = time.mktime((cy-1,cm,int(day),
              int(tm[0]),int(tm[1]),0,0,1,dstflag))
    return ct


def toseconds(st):
    '''Convert 'h:mm' string to seconds.'''
    h, m = st.split(':')
    return (long(h)*60 + long(m)) * 60

# -----------------------------------------------------
if __name__ == "__main__":
    print wdlib.myversion(__file__)

