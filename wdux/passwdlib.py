#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

''' -----------------------------------------------------
    WatchDog UX module

    module name: passwdlib.py
    purpose    : library for handling /etc/passwd
    created    : 2006-07-14
    last change: 2007-08-08
    
    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg
    -----------------------------------------------------
'''
''' history:
    2006-08-24
        initial release
    2006-08-30
        chg: get_passwd: expected no. of fields in record now a constant
        chg: PWD_* indices assigned via range()
    2006-09-18
        fix: err() def missing
        chg: get_passwd: lines with wrong format will be indicated, but
             processing will continue (without them)
        add: get_passwd: return list of errors if any
    2007-07-31
        chg: if the passwd file is not readable, return error msg
             (do not use sys.exit(1))
        chg: module 'sys' no longer needed
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
'''

import os.path
# WDUX specific modules
import wdlib


    
# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

__version__ = wdlib.mtime(__file__)


PWD_login   ,                             \
PWD_password,                             \
PWD_UID     ,                             \
PWD_GID     ,                             \
PWD_realname,                             \
PWD_home    ,                             \
PWD_shell   = range(7)


def get_passwd(passwdpath):
    '''Open passwd file, read completely into list, split into fields.
    
    returns: list of entries (each a list), modified time of file in secs
    and a list of parsing errors if any
    attributes of list:
    PWD_login,PWD_password,PWD_UID,PWD_GID,PWD_realname,PWD_home,PWD_shell
    '''
    
    chk = {}
    u = []
    errors = []
    expected = 7  # no. of fields in passwd record

    passwd = wdlib.openfile(passwdpath)
    if not passwd:
        errors.append('ERROR: get_passwd(): cannot open %s' % passwdpath)
        return u, 0, errors

    n = 0
    for line in passwd:
        n += 1
        if line in chk:
            errors.append('ERROR: %s contains duplicate line at line %d!' % (passwdpath, n))
            errors.append('line is: >' + line.rstrip() + '<')
            continue
        else:
            chk[line] = line
        # split into fields
        f = line.strip().split(":")
        if len(f) != expected:
            errors.append('ERROR: bad record structure in %s at line %d' % (passwdpath,n))
            errors.append('expected %d fields, got %d' % (expected,len(f)) )
            errors.append('line is: >' + line.strip() + '<')
            continue
            
        # split comment field, extract first part
        f[PWD_realname] = f[PWD_realname].split(',')[0]
        # collect
        u.append(f)
        
    passwd.close()
    del chk
    mtime = os.path.getmtime(passwdpath)
    return u, mtime, errors


# -----------------------------------------------------
if __name__ == "__main__":
    print wdlib.myversion(__file__)
