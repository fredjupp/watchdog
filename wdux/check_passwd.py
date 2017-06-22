#! /usr/bin/python
# -*- coding: iso-8859-1 -*-

''' -----------------------------------------------------
    WatchDog UX module

    module name: check_passwd.py
    purpose    : check /etc/passwd for anomalies    
    created    : 2006-07-02
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
        add: parse_passwd returns False if no output is generated
             so that no files are created unnecessarily
        add: no report if write_passwd() fails to write to file
        chg: oldest_event not global anymore
        fix: write_results: openfile(...,'w') -> createfile()
    2006-08-30
        fix: parse_passwd: passwdpath is handed over to get_passwd
    2006-09-18
        chg: header included in detailed output file, not in report only
        add: write_results will print file structure errors if any
    2006-09-25
        chg: use wdlib.open_out
    2006-09-26
        chg: write_results: output format
        chg: parse_passwd: time filter on period
        fix: removed debug print statement
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
    2007-08-10
        fix: various: if return False is used to signal a failure, an explicit
             return True must be coded when successful!
        fix: main: abort if passwd file not accessible
        fix: main: removed get_status call (superfl.)
    2007-11-19
        chg: validity check on passwd filename: no wildcards allowed
    2007-11-29
        chg: main: added debug output in verbose mode
'''


import os.path, sys
# WDUX specific modules
import wdlib, passwdlib as PWL


# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

__version__ = wdlib.mtime(__file__)
err = sys.stderr.write
outputname = 'passwd_out'

_counters = []
_users = []        # the contents of the passwd file
# results[i]: list of line numbers where check #i failed    
_res = []
# for definition of _checks[], see below after function defs
# for error msgs while reading passwd file
_file_errors = []


def check4duplicates(u,here,keyfield,linenr,skip_blank_keyfield):
    '''Check for duplicates of u[here], using <keyfield> comparison.
    Returns Bool,previous_lineno
    '''
    
    key = u[here][keyfield]
        
    if not key and skip_blank_keyfield:
        return False,0         # == check OK
    
    if key in linenr:
        _prevno = linenr[key]  # last entry with this key
        linenr[key] = here
        return True,_prevno    # == check failed
    else:
        linenr[key] = here
        return False,0         # == check OK


def check_empty_pwd(entry):
    ''' check for users with empty passwords
    '''
    return entry[PWL.PWD_password] == ''


def check_UID_0(entry):
    ''' list users with root UID
    '''
    return entry[PWL.PWD_UID] == '0'


def check_shell(entry):
    ''' list users with login shells != '*sh'
    '''
    s = os.path.basename(entry[PWL.PWD_shell])
    return s == '' or s[-2:] <> 'sh'


# global
_checks = [
    # call check4duplicates():
    # desc, keyfield, sortfield, skip_blank_keyfield
    ('ERROR: Users having a duplicate UID',
        PWL.PWD_UID, PWL.PWD_UID, False),
    ('WARNING: Users with more than one login name',
        PWL.PWD_login, PWL.PWD_UID, False),
    ('WARNING: Users with multiple accounts (according to comment)',
        PWL.PWD_realname, PWL.PWD_UID, True),
    ('WARNING: Users with shared passwords',
        PWL.PWD_password, PWL.PWD_password, False),

    # simple check functions, working on a single field, no storage
    # desc, func, sortfield
    ('ERROR: Users with empty passwords',
     check_empty_pwd, PWL.PWD_UID),
    ('INFO: Super-users (UID == 0)',
     check_UID_0, PWL.PWD_UID),
    ('INFO: Users with unusual shells',
     check_shell, PWL.PWD_shell),
]



def parse_passwd(passwdpath, period):
    ''' find passwd file, parse content, write results to files
    <period>: time filter interval (serial times)
    '''
    
    global _counters, _users, _res, _file_errors
    

    # open,read,split,close passwd file:
    _users, passwdage, _file_errors = PWL.get_passwd(passwdpath)
    if _file_errors:
        return True
    
    # time filter:
    # in check_* scripts, the timestamp of the input file is compared,
    # not the timestamp of input lines:
    if passwdage < period[0]:
        return False

    # initialize variables
    
    # no. of duplicate checks
    ndf = len([c for c in _checks if len(c) == 4]) # 4: longer tuples for dup checks
    allchecks = (range(len(_checks)))

    # counters for duplicates
    _counters = []
    for i in range(ndf):
        _counters.append({})

    # results[i] : list of line numbers where check #i failed    
    for i in allchecks:
        _res.append([])

    # duplicate checking functions return the previous line no.
    # of the duplicate entry
    where = 0
    for nr in range(len(_users)):  # scan all records
        for i in allchecks:        # call each checking function
            if i < ndf:                     # check for duplicates
                # call check4duplicates(): desc,keyfield,sortfield,skip_blank_keyfield
                keyfield = _checks[i][1]
                skip = _checks[i][3]
                isdup, where = check4duplicates(_users,nr,keyfield,_counters[i],skip)
                if isdup:
                    if where not in _res[i]:
                        _res[i].append(where)
                    _res[i].append(nr)
            else:                           # simple check functions
                # desc, func, sortfield
                func = _checks[i][1]
                if func(_users[nr]):
                    _res[i].append(nr)

    # check if output empty
    for check in allchecks:
        if _res[check]:
            return True
    else:
        return False


def write_results(passwdpath,outputname):
    global _res, _checks, _users, _file_errors
    
    outhdrfmt = '%-14s |%-30s| = %s\n'
    sep = '-' *wdlib.nDashes + '\n'
    allchecks = (range(len(_checks)))

    # write to file
    fh = wdlib.open_out(outputname,'w')
    if not fh:
        return False
    pr = fh.write  # abbrev
    # if there where file structure errors, report them and quit
    if _file_errors:
        pr(sep)
        pr('Errors encountered while parsing %s\n' % passwdpath)
        for msg in _file_errors:
            pr(msg + '\n')
        pr('Aborted.\n')
        pr(sep)
        return True

    for check in allchecks:
        ck = _checks[check]
        listed = _res[check]
        if listed:
            # header for this check
            pr(sep)
            pr('%s\n' % ck[0])   # description
            pr(outhdrfmt % ('name','comment','value'))
            pr(sep)
            # generate formatted output
            out = []
            sortkeyindex = ck[2]
            for rownum in listed:
                u = _users[rownum]
                line = outhdrfmt % (u[PWL.PWD_login],
                                    u[PWL.PWD_realname],
                                    u[sortkeyindex])
                out.append(line)

            out.sort()
            out.sort(key=lambda line: line[line.rfind('=')+1:])
            for line in out:
                pr('%s' % line)
            pr(sep)
    fh.close()
    return True


def reportOn_passwd(outputname):
    ''' print formatted output from results file
        shorten output if repeated
    '''

    maxRepeats = 10

    # read from file
    f = wdlib.open_out(outputname)
    if not f:
        return False
    
    last = ''    
    n = 0
    for line in f:  #  reads including EOL char
        # compare output lines
        # if identical for maxRepeats times, shorten output
        # look at '= value' part only
        key = line[line.rfind('=')+1:] # from 0 if not found
        if key == last:
            n += 1
            if n <= maxRepeats:
                print line,
        else:                    # new output
            if n > maxRepeats:   # print closing comment
                print '... repeated %d more times ...' % (n-maxRepeats)
            n = 1
            print line,
            last = key
    f.close()
    return True

    
def main(filterOnTime=True):
    ''' Check /etc/passwd for anomalies.
    file is parsed, results written to output file, printed.
    '''

    # prepare limit for time filter
    period = wdlib.set_timefilter('last_passwd',filterOnTime)    

    # get filename
    pwdpath = ''
    conf = wdlib.check_conf()
    if conf:
        pwdpath = wdlib.abspath(conf.get('PATHS','passwd'))

    # error checking:
    if not pwdpath:
        err('check_passwd: Cannot find passwd file "%s". Aborted.\n' % pwdpath)
        return False

    if wdlib.has_wildcards(pwdpath):
        err('check_passwd: No wildcards allowed ("%s")! Aborted.\n' % pwdpath)
        return False

    print wdlib.version_header(__file__,pwdpath,period)

    if parse_passwd(pwdpath, period):
        if write_results(pwdpath,outputname):
            reportOn_passwd(outputname)
        else:
            wdlib.info('write_results fails!')
    else:
        wdlib.info('parse_passwd: nothing found!')
        
    # log status at end of processing
    wdlib.log_status('last_passwd',is_OK=True)

# -----------------
# std: run script if not imported as a module
if __name__ == "__main__":
    wdlib.hint()
